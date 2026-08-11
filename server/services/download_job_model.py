"""다운로드 Job 모델 설계 (구현 가이드).

현재 ``download_service.DownloadJob`` 는 인메모리입니다.
서버 재시작 시 SSE/진행 상태가 사라지므로, YouTube 검색·대량 수집으로
갈 때 아래 스키마로 확장하는 것을 권장합니다.

이 모듈은 **스키마·상수만** 정의합니다. 영속 저장소 구현은 후속 작업입니다.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class DownloadJobStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    CONVERTING = "converting"
    METADATA = "metadata"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DownloadJobStage(str, Enum):
    LISTING = "listing"
    SEARCHING = "searching"  # YouTube 검색 매칭
    DOWNLOADING = "downloading"
    CONVERTING = "converting"
    COVER = "cover"
    METADATA = "metadata"
    DONE = "done"


class DownloadSource(str, Enum):
    YOUTUBE_URL = "youtube_url"
    YOUTUBE_SEARCH = "youtube_search"
    SPOTIFY_URL = "spotify_url"  # 마이그레이션 기간만


class DownloadJobCreate(BaseModel):
    """새 다운로드 요청 (미래 YouTube 검색 포함)."""

    source: DownloadSource = DownloadSource.YOUTUBE_URL
    url: str | None = Field(None, description="직접 URL")
    query: str | None = Field(None, description="YouTube 검색어")
    preferred_result_index: int | None = Field(
        None, description="검색 결과 중 선택 인덱스"
    )


class DownloadJobRecord(BaseModel):
    """영속 Job 레코드 초안 (JSONL / SQLite jobs 테이블 후보)."""

    job_id: str
    source: DownloadSource
    url: str | None = None
    query: str | None = None
    status: DownloadJobStatus = DownloadJobStatus.PENDING
    stage: DownloadJobStage | str = ""
    progress: float = 0.0
    message: str = ""
    error: str | None = None
    current: int | None = None
    total: int | None = None
    remaining: int | None = None
    track_ids: list[str] = Field(default_factory=list)
    created_at: float
    updated_at: float
    finished_at: float | None = None
    cancel_requested: bool = False


# 권장 영속 전략 (문서용 상수)
PERSISTENCE_OPTIONS: dict[str, Any] = {
    "recommended": "sqlite",
    "path_env": "WAVMASH_JOBS_DB",
    "default_path": "download_jobs.db",
    "ttl_hours": 72,
    "max_concurrent": 2,
    "notes": [
        "SSE는 job_id 로 재구독 가능해야 함",
        "cancel_requested 플래그로 워커가 안전하게 중단",
        "YouTube 검색 job 은 stage=searching 에서 후보 목록을 이벤트로 보낼 수 있음",
        "Spotify URL source 는 마이그레이션 종료 후 deprecate",
    ],
}

JobPersistBackend = Literal["memory", "sqlite", "jsonl"]
