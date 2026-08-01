"""WaveMash FastAPI 백엔드 서버 — 메인 애플리케이션.

Usage:
    python -m server.main          # 또는
    uvicorn server.main:app --reload
"""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

# ---------------------------------------------------------------------------
# 프로젝트 루트를 sys.path에 추가 (기존 모듈 임포트용)
# 이 작업은 가장 먼저 수행되어야 합니다.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from server.config import get_settings
from server.database import get_archive_cache
from server.routers import (
    covers,
    download,
    library,
    playlists,
    spotify_sync,
    stream,
    tracks,
)

# 기존 모듈
from library import TrackIndexDB



# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """서버 시작/종료 시 실행되는 라이프사이클."""
    settings = get_settings()
    print(f"[WaveMash] Server starting -- project root: {settings.PROJECT_ROOT}")
    print(f"[WaveMash] WAV storage path: {settings.WAV_ROOT}")

    # SQLite 인덱스 스키마 보장
    try:
        index_db = TrackIndexDB()
        index_db.ensure_schema()
        print("[WaveMash] SQLite index schema OK")
    except Exception as exc:
        print(f"[WaveMash] SQLite schema error: {exc}")

    # 아카이브 프리로드
    try:
        cache = get_archive_cache()
        records = cache.load()
        print(f"[WaveMash] Archive loaded -- {len(records)} tracks")
    except Exception as exc:
        print(f"[WaveMash] Archive load error: {exc}")

    yield

    print("[WaveMash] Server shutting down")


# ---------------------------------------------------------------------------
# FastAPI 앱 생성
# ---------------------------------------------------------------------------

settings = get_settings()

app = FastAPI(
    title="WaveMash API",
    description="프리미엄 뮤직 컬렉션 웹 앱 백엔드",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range", "Accept-Ranges", "Content-Length"],
)


# ---------------------------------------------------------------------------
# 글로벌 예외 핸들러
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """처리되지 않은 예외를 잡아 한국어 에러 응답을 반환합니다."""
    print(f"[WaveMash] 처리되지 않은 오류: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
            "error": str(exc),
        },
    )


# ---------------------------------------------------------------------------
# 라우터 등록
# ---------------------------------------------------------------------------

api_prefix = settings.API_PREFIX

app.include_router(tracks.router, prefix=api_prefix)
app.include_router(download.router, prefix=api_prefix)
app.include_router(playlists.router, prefix=api_prefix)
app.include_router(spotify_sync.router, prefix=api_prefix)
app.include_router(covers.router, prefix=api_prefix)
app.include_router(library.router, prefix=api_prefix)
app.include_router(stream.router, prefix=api_prefix)


# ---------------------------------------------------------------------------
# 헬스 체크
# ---------------------------------------------------------------------------

@app.get("/health", tags=["시스템"])
async def health_check() -> dict[str, str]:
    """서버 상태 확인 엔드포인트."""
    return {"status": "ok", "service": "WaveMash API"}


@app.get(f"{api_prefix}/health", tags=["시스템"])
async def api_health_check() -> dict[str, str]:
    """API 상태 확인 엔드포인트."""
    cache = get_archive_cache()
    records = cache.get_records()
    return {
        "status": "ok",
        "service": "WaveMash API",
        "tracks_loaded": str(len(records)),
    }


# ---------------------------------------------------------------------------
# 직접 실행
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
