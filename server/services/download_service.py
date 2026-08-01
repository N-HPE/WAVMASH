"""다운로드 서비스 — YouTube/Spotify 다운로드 작업 관리.

Background 스레드에서 다운로드를 실행하고 SSE로 진행 상황을 스트리밍합니다.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from library import ensure_track_id
from spotify_pipeline import is_spotify_url, process_spotify_url_sync
from pipeline import process_url_sync


class JobStatus(str, Enum):
    """다운로드 작업 상태."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DownloadJob:
    """개별 다운로드 작업 정보."""

    job_id: str
    url: str
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
    _listeners: list[Callable] = field(default_factory=list, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add_listener(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """SSE 리스너를 추가합니다."""
        with self._lock:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """SSE 리스너를 제거합니다."""
        with self._lock:
            self._listeners = [cb for cb in self._listeners if cb is not callback]

    def notify(self) -> None:
        """등록된 모든 리스너에게 현재 상태를 전파합니다."""
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
        """진행률·메시지를 갱신하고 리스너에 알립니다."""
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
        """SSE 이벤트로 변환합니다."""
        result: dict[str, Any] = {
            "job_id": self.job_id,
            "status": self.status.value,
            "progress": round(self.progress, 3),
            "message": self.message,
            "stage": self.stage or "",
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
    """다운로드 작업 큐 관리자."""

    _MAX_CONCURRENT = 2
    _JOB_TTL = 3600

    def __init__(self) -> None:
        self._jobs: dict[str, DownloadJob] = {}
        self._lock = threading.Lock()
        self._semaphore = threading.Semaphore(self._MAX_CONCURRENT)

    def create_job(self, url: str) -> DownloadJob:
        """새 다운로드 작업을 생성하고 백그라운드 스레드에서 실행합니다."""
        job_id = str(uuid.uuid4())
        job = DownloadJob(job_id=job_id, url=url.strip())

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

    def _run_download(self, job: DownloadJob) -> None:
        self._semaphore.acquire()
        try:
            job.status = JobStatus.DOWNLOADING
            job.stage = "listing"
            job.message = "다운로드 준비 중..."
            job.notify()

            def progress_callback(
                pct: float,
                msg: str,
                info: dict[str, Any] | None = None,
            ) -> None:
                job.apply_progress(pct, msg, info)

            url = job.url

            if is_spotify_url(url):
                result = process_spotify_url_sync(url, progress_callback)
            else:
                result = process_url_sync(url, progress_callback)

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
            job.message = f"완료! ({len(job.records)}곡 다운로드)"
            job.notify()

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
