"""다운로드 서비스 — YouTube/Spotify 일회성 변환 + SSE + 동시성 1.

Render Free(512MB) 보호: 동시 변환 1개.
Ephemeral: 태그 베이킹된 파일을 브라우저로 보낸 뒤 GC.
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from library import ensure_track_id, is_ephemeral_mode
from spotify_pipeline import is_spotify_url, process_spotify_url_sync
from pipeline import process_url_sync


class JobStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DownloadJob:
    job_id: str
    url: str
    export_format: str = "wav"
    track_ids: list[str] | None = None
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    message: str = ""
    error: str | None = None
    stage: str = ""
    current: int | None = None
    total: int | None = None
    remaining: int | None = None
    track_title: str | None = None
    track_artist: str | None = None
    skipped: int | None = None
    records: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    exported: bool = False
    _listeners: list[Callable] = field(default_factory=list, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add_listener(self, callback: Callable[[dict[str, Any]], None]) -> None:
        with self._lock:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[dict[str, Any]], None]) -> None:
        with self._lock:
            self._listeners = [cb for cb in self._listeners if cb is not callback]

    def notify(self) -> None:
        data = self.to_event_dict()
        with self._lock:
            for cb in list(self._listeners):
                try:
                    cb(data)
                except Exception:
                    pass

    def apply_progress(
        self,
        pct: float,
        msg: str,
        info: dict[str, Any] | None = None,
    ) -> None:
        self.progress = max(0.0, min(1.0, float(pct)))
        self.message = msg or self.message
        if info:
            if "stage" in info and info["stage"] is not None:
                self.stage = str(info["stage"])
            if "current" in info:
                self.current = info["current"]
            if "total" in info:
                self.total = info["total"]
            if "remaining" in info:
                self.remaining = info["remaining"]
            elif self.current is not None and self.total is not None:
                self.remaining = max(0, self.total - self.current)
            if "track_title" in info:
                self.track_title = info["track_title"]
            if "track_artist" in info:
                self.track_artist = info["track_artist"]
            if "skipped" in info:
                self.skipped = info["skipped"]
        self.notify()

    def to_event_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "job_id": self.job_id,
            "status": self.status.value,
            "progress": round(self.progress, 3),
            "message": self.message,
            "stage": self.stage or "",
            "format": self.export_format,
            "ephemeral": is_ephemeral_mode(),
        }
        if self.error:
            result["error"] = self.error
        if self.current is not None:
            result["current"] = self.current
        if self.total is not None:
            result["total"] = self.total
        if self.remaining is not None:
            result["remaining"] = self.remaining
        if self.track_title:
            result["track_title"] = self.track_title
        if self.track_artist:
            result["track_artist"] = self.track_artist
        if self.skipped is not None:
            result["skipped"] = self.skipped
        if self.records:
            result["track_count"] = len(self.records)
        return result


class DownloadService:
    # Render Free 512MB: yt-dlp + ffmpeg 동시 2개면 OOM — 강제 1
    _MAX_CONCURRENT = 1
    _JOB_TTL = 1800  # 30분 후 job + export 파일 GC

    def __init__(self) -> None:
        self._jobs: dict[str, DownloadJob] = {}
        self._lock = threading.Lock()
        self._semaphore = threading.Semaphore(self._MAX_CONCURRENT)

    def create_job(
        self,
        url: str,
        export_format: str = "wav",
        track_ids: list[str] | None = None,
    ) -> DownloadJob:
        fmt = (export_format or "wav").lower().strip()
        if fmt not in ("wav", "mp3"):
            fmt = "wav"
        job_id = str(uuid.uuid4())
        ids = [str(t).strip() for t in (track_ids or []) if str(t).strip()] or None
        job = DownloadJob(
            job_id=job_id,
            url=url.strip(),
            export_format=fmt,
            track_ids=ids,
        )

        with self._lock:
            self._cleanup_old_jobs()
            self._jobs[job_id] = job

        thread = threading.Thread(
            target=self._run_download,
            args=(job,),
            daemon=True,
            name=f"download-{job_id[:8]}",
        )
        thread.start()
        return job

    def get_job(self, job_id: str) -> DownloadJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self) -> list[DownloadJob]:
        with self._lock:
            return list(self._jobs.values())

    def gc_job_exports(self, job: DownloadJob) -> None:
        """브라우저로 내보낸 뒤 / TTL 만료 시 바이너리 삭제."""
        for rec in job.records:
            for key in ("export_path", "path", "local_path"):
                p = str(rec.get(key) or "")
                if p and os.path.isfile(p) and ("_temp" in p.replace("\\", "/") or rec.get("ephemeral")):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
            # sidecar next to export
            for key in ("export_path", "path"):
                p = str(rec.get(key) or "")
                if not p:
                    continue
                cover = os.path.join(os.path.dirname(p), "cover.jpg")
                if os.path.isfile(cover) and "_temp" in cover.replace("\\", "/"):
                    try:
                        os.remove(cover)
                    except OSError:
                        pass
            rec["export_path"] = ""
            if rec.get("ephemeral"):
                rec["path"] = ""
                rec["local_path"] = ""
        job.exported = True

    def _run_download(self, job: DownloadJob) -> None:
        self._semaphore.acquire()
        try:
            job.status = JobStatus.DOWNLOADING
            job.stage = "listing"
            job.message = "다운로드 준비 중... (대기열 1개씩 처리)"
            job.notify()

            def progress_callback(
                pct: float,
                msg: str,
                info: dict[str, Any] | None = None,
            ) -> None:
                job.apply_progress(pct, msg, info)

            url = job.url
            fmt = job.export_format

            if is_spotify_url(url):
                result = process_spotify_url_sync(
                    url,
                    progress_callback,
                    export_format=fmt,
                    track_ids=job.track_ids,
                )
            else:
                result = process_url_sync(url, progress_callback, export_format=fmt)

            if isinstance(result, dict):
                if "records" in result:
                    records = result.get("records", [])
                    for rec in records:
                        ensure_track_id(rec)
                    job.records = records
                    if result.get("skipped") is not None:
                        job.skipped = int(result["skipped"])
                else:
                    ensure_track_id(result)
                    job.records = [result]
            else:
                job.records = []

            job.status = JobStatus.COMPLETED
            job.progress = 1.0
            job.stage = "done"
            job.current = len(job.records) if job.records else job.current
            job.remaining = 0
            job.message = f"완료! ({len(job.records)}곡) — 브라우저로 파일 저장하세요"
            job.notify()

            # Ephemeral: schedule GC if client never downloads (30 min via TTL)
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.stage = "error"
            job.error = str(exc)
            job.message = f"다운로드 실패: {exc}"
            job.notify()
        finally:
            self._semaphore.release()

    def _cleanup_old_jobs(self) -> None:
        now = time.time()
        expired = [
            jid
            for jid, job in self._jobs.items()
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED)
            and (now - job.created_at) > self._JOB_TTL
        ]
        for jid in expired:
            job = self._jobs.get(jid)
            if job:
                self.gc_job_exports(job)
            del self._jobs[jid]


_download_service: DownloadService | None = None
_service_lock = threading.Lock()


def get_download_service() -> DownloadService:
    global _download_service
    if _download_service is None:
        with _service_lock:
            if _download_service is None:
                _download_service = DownloadService()
    return _download_service
