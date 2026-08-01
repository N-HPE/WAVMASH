"""다운로드 API 라우터 — YouTube/Spotify 다운로드 및 SSE 진행 스트리밍."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, HTTPException
from starlette.responses import StreamingResponse

from server.database import get_archive_cache
from server.models import DownloadRequest, MessageResponse
from server.services.download_service import (
    DownloadJob,
    JobStatus,
    get_download_service,
)

router = APIRouter(prefix="/download", tags=["다운로드"])


@router.post("", response_model=dict[str, str])
async def start_download(body: DownloadRequest) -> dict[str, str]:
    """다운로드 작업을 시작하고 job_id를 반환합니다.

    작업은 백그라운드 스레드에서 실행되며, SSE를 통해 진행 상황을 확인할 수 있습니다.
    """
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL을 입력해 주세요.")

    service = get_download_service()
    job = service.create_job(url)

    return {"job_id": job.job_id, "message": "다운로드 작업이 시작되었습니다."}


@router.get("/status/{job_id}")
async def download_status_sse(job_id: str) -> StreamingResponse:
    """SSE 스트림으로 다운로드 진행 상황을 전송합니다.

    이벤트 형식:
    ```
    event: progress
    data: {"job_id": "...", "status": "downloading", "progress": 0.45, "message": "..."}
    ```
    """
    service = get_download_service()
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="다운로드 작업을 찾을 수 없습니다.")

    async def event_generator():
        """SSE 이벤트 생성기."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def on_update(data: dict[str, Any]) -> None:
            """백그라운드 스레드에서 호출 — asyncio 큐에 이벤트 추가."""
            loop.call_soon_threadsafe(queue.put_nowait, data)

        job.add_listener(on_update)
        try:
            # 현재 상태 즉시 전송
            initial = job.to_event_dict()
            yield _format_sse("progress", initial)

            # 이미 완료/실패 상태면 완료 이벤트 전송 후 종료
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                final_data = _build_final_event(job)
                yield _format_sse("complete", final_data)
                return

            # 실시간 이벤트 수신
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    # 하트비트 (연결 유지)
                    yield ": heartbeat\n\n"
                    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                        break
                    continue

                yield _format_sse("progress", data)

                status = data.get("status", "")
                if status in ("completed", "failed"):
                    final_data = _build_final_event(job)
                    yield _format_sse("complete", final_data)
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


@router.get("/jobs", response_model=list[dict[str, Any]])
async def list_download_jobs() -> list[dict[str, Any]]:
    """모든 다운로드 작업 목록을 반환합니다."""
    service = get_download_service()
    jobs = service.list_jobs()
    return [job.to_event_dict() for job in jobs]


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _format_sse(event: str, data: dict[str, Any]) -> str:
    """SSE 형식의 문자열을 생성합니다."""
    json_data = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {json_data}\n\n"


def _build_final_event(job: DownloadJob) -> dict[str, Any]:
    """완료/실패 시 최종 이벤트 데이터를 구축합니다."""
    from server.routers.tracks import _record_to_track

    result = job.to_event_dict()

    if job.status == JobStatus.COMPLETED and job.records:
        # 다운로드된 트랙을 라이브러리에 추가
        cache = get_archive_cache()
        tracks = []
        for rec in job.records:
            cache.upsert(rec, prepend=True)
            tracks.append(_record_to_track(rec).model_dump())
        result["tracks"] = tracks

    return result
