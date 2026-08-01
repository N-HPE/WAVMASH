"""WaveMash 서버 설정 — 환경변수 기반 구성."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from functools import lru_cache

# ---------------------------------------------------------------------------
# 프로젝트 루트를 sys.path에 추가하여 library.py 등 기존 모듈을 임포트할 수 있도록 함
# ---------------------------------------------------------------------------
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from env_loader import ensure_env_loaded  # noqa: E402

ensure_env_loaded()


class Settings:
    """애플리케이션 전역 설정.

    환경변수 또는 기본값에서 값을 가져옵니다.
    """

    # 경로 설정
    PROJECT_ROOT: str = _PROJECT_ROOT
    WAV_ROOT: str = ""  # set in __init__ via default_wav_root()
    ARCHIVE_JSON: str = os.path.join(_PROJECT_ROOT, "archive.json")
    PLAYLISTS_JSON: str = os.path.join(_PROJECT_ROOT, "playlists.json")
    TRACK_INDEX_DB: str = os.path.join(_PROJECT_ROOT, "track_index.db")

    # API 설정
    API_PREFIX: str = "/api"

    # CORS 허용 Origin
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:8080",
    ]

    # 서버 설정
    HOST: str = os.environ.get("WAVMASH_HOST", "127.0.0.1")
    PORT: int = int(os.environ.get("WAVMASH_PORT", "8000"))
    DEBUG: bool = os.environ.get("WAVMASH_DEBUG", "false").lower() in ("1", "true", "yes")
    # 서버 시작 시 등록된 Spotify 동기화 플리 자동 실행 (맥/윈도우 로컬 차이 보정)
    AUTO_SYNC_ON_START: bool = os.environ.get(
        "WAVMASH_AUTO_SYNC_ON_START", "true"
    ).lower() in ("1", "true", "yes")

    def __init__(self) -> None:
        from paths import default_wav_root

        self.WAV_ROOT = default_wav_root()
        extra = os.environ.get("CORS_ORIGINS", "").strip()
        if extra:
            for origin in extra.split(","):
                origin = origin.strip()
                if origin and origin not in self.CORS_ORIGINS:
                    self.CORS_ORIGINS.append(origin)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """싱글턴 설정 인스턴스를 반환합니다."""
    return Settings()
