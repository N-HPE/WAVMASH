"""다운로드 API — 일회성 변환 + SSE + 태그 베이킹 export + GC."""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse

from library import is_ephemeral_mode
from server.database import get_archive_cache
from server.models import DownloadRequest, DownloadResolveRequest
from server.services.download_service import (
    DownloadJob,
    JobStatus,
    get_download_service,
)
from spotify_pipeline import is_spotify_url, resolve_spotify_preview

router = APIRouter(prefix="/download", tags=["다운로드"])


def _sanitize_archive_record(rec: dict[str, Any]) -> dict[str, Any]:
    """메타데이터만 아카이브/Supabase에 남김 — 바이너리 경로 제거."""
    out = dict(rec)
    out["downloaded_at"] = out.get("downloaded_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if out.get("ephemeral") or is_ephemeral_mode():
        out["ephemeral"] = True
        out["path"] = ""
        out["local_path"] = ""
        out["export_path"] = ""
        out["has_file"] = False
        # cover bytes never persist
        out.pop("cover_data", None)
    return out


@router.post("/resolve")
async def resolve_download(body: DownloadResolveRequest) -> dict[str, Any]:
    """Spotify URL의 곡 목록을 다운로드 없이 조회합니다."""
    url = (body.url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL을 입력해 주세요.")
    if not is_spotify_url(url):
        raise HTTPException(
            status_code=400,
            detail="Spotify 플레이리스트·앨범·트랙 URL만 목록 조회가 가능합니다.",
        )

    try:
        return await asyncio.to_thread(resolve_spotify_preview, url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"곡 목록을 불러오지 못했습니다: {str(exc)[:200]}",
        ) from exc


@router.post("", response_model=dict[str, str])
async def start_download(body: DownloadRequest) -> dict[str, str]:
    """다운로드 작업을 시작하고 job_id를 반환합니다."""
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL을 입력해 주세요.")

    fmt = (body.format or "wav").lower().strip()
    if fmt not in ("wav", "mp3"):
        fmt = "wav"

    track_ids = None
    if body.track_ids:
        track_ids = [str(t).strip() for t in body.track_ids if str(t).strip()]
        if not track_ids:
            track_ids = None

    service = get_download_service()
    job = service.create_job(url, export_format=fmt, track_ids=track_ids)

    return {
        "job_id": job.job_id,
        "format": fmt,
        "message": "다운로드 작업이 시작되었습니다.",
    }


@router.get("/status/{job_id}")
async def download_status_sse(job_id: str) -> StreamingResponse:
    """SSE로 진행 상황 전송. 15초 하트비트로 Render Free cold sleep 완화."""
    service = get_download_service()
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="다운로드 작업을 찾을 수 없습니다.")

    async def event_generator():
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def on_update(data: dict[str, Any]) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, data)

        job.add_listener(on_update)
        try:
            initial = job.to_event_dict()
            yield _format_sse("progress", initial)

            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                yield _format_sse("complete", _build_final_event(job))
                return

            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    # Render Free 15분 idle sleep 방어 + 연결 유지
                    yield ": ping\n\n"
                    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                        break
                    continue

                yield _format_sse("progress", data)
                if data.get("status") in ("completed", "failed"):
                    yield _format_sse("complete", _build_final_event(job))
                    break
        finally:
            job.remove_listener(on_update)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/export/{job_id}")
async def export_job_first(job_id: str):
    """첫 번째(또는 단일) 트랙 바이너리 스트림 — 전송 후 GC."""
    return await _export_track(job_id, track_id=None)


@router.get("/export/{job_id}/{track_id}")
async def export_job_track(job_id: str, track_id: str):
    """특정 트랙 바이너리 스트림 — 전송 후 해당 파일 GC."""
    return await _export_track(job_id, track_id=track_id)


@router.get("/jobs", response_model=list[dict[str, Any]])
async def list_download_jobs() -> list[dict[str, Any]]:
    service = get_download_service()
    return [job.to_event_dict() for job in service.list_jobs()]


async def _export_track(job_id: str, track_id: str | None):
    service = get_download_service()
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="다운로드 작업을 찾을 수 없습니다.")
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="아직 변환이 완료되지 않았습니다.")
    if not job.records:
        raise HTTPException(status_code=404, detail="내보낼 트랙이 없습니다.")

    rec = None
    if track_id:
        for r in job.records:
            rid = str(r.get("track_id") or r.get("id") or "")
            if rid == track_id:
                rec = r
                break
        if not rec:
            raise HTTPException(status_code=404, detail="트랙을 찾을 수 없습니다.")
    else:
        rec = job.records[0]

    path = str(rec.get("export_path") or rec.get("path") or rec.get("local_path") or "")
    if not path or not os.path.isfile(path):
        raise HTTPException(
            status_code=410,
            detail="파일이 이미 삭제되었거나 만료되었습니다. 다시 다운로드하세요.",
        )

    export_name = str(rec.get("export_name") or os.path.basename(path))
    ext = os.path.splitext(export_name)[1].lower()
    media = "audio/wav" if ext == ".wav" else "audio/mpeg" if ext == ".mp3" else "application/octet-stream"

    tid = str(rec.get("track_id") or rec.get("id") or "")

    def _gc_after() -> None:
        # 단일 파일 삭제; 전부 없으면 job GC
        try:
            if os.path.isfile(path):
                os.remove(path)
        except OSError:
            pass
        rec["export_path"] = ""
        if rec.get("ephemeral"):
            rec["path"] = ""
            rec["local_path"] = ""
        # 남은 export가 없으면 전체 GC 표시
        still = any(
            os.path.isfile(str(r.get("export_path") or r.get("path") or ""))
            for r in job.records
        )
        if not still:
            service.gc_job_exports(job)

    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(export_name)}",
        "X-WaveMash-Track-Id": tid,
        "X-WaveMash-Filename": quote(export_name),
    }

    return FileResponse(
        path,
        media_type=media,
        filename=export_name,
        background=BackgroundTask(_gc_after),
        headers=headers,
    )


def _format_sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _build_final_event(job: DownloadJob) -> dict[str, Any]:
    from server.routers.tracks import _record_to_track

    result = job.to_event_dict()

    if job.status == JobStatus.COMPLETED and job.records:
        cache = get_archive_cache()
        tracks = []
        exports = []
        for rec in job.records:
            meta = _sanitize_archive_record(rec)
            cache.upsert(meta, prepend=True)
            # upsert may sync to supabase via cache — paths already cleared in meta
            track = _record_to_track(meta)
            tracks.append(track.model_dump())
            tid = str(rec.get("track_id") or rec.get("id") or "")
            exports.append(
                {
                    "track_id": tid,
                    "export_name": rec.get("export_name") or "",
                    "format": (rec.get("format") or job.export_format or "wav").lower(),
                    "url": f"/api/download/export/{job.job_id}/{tid}",
                }
            )
        result["tracks"] = tracks
        result["exports"] = exports
        result["ephemeral"] = is_ephemeral_mode() or any(r.get("ephemeral") for r in job.records)

    return result
