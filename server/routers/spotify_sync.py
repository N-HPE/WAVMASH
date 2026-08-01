"""스포티파이 동기화 API 라우터 — 지정 플레이리스트 자동 동기화 및 삭제 연동 CRUD."""

from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from server.services.spotify_sync_service import (
    add_sync_config,
    delete_sync_config,
    get_sync_config,
    get_sync_configs,
    sync_all_active_playlists,
    sync_single_playlist,
    update_sync_config,
)

router = APIRouter(prefix="/spotify-sync", tags=["스포티파이 동기화"])


class SyncConfigCreate(BaseModel):
    url: str = Field(..., description="스포티파이 플레이리스트 URL")
    auto_sync_enabled: bool = Field(True, description="자동 동기화 활성화 여부")
    sync_deletions: bool = Field(True, description="스포티파이에서 삭제 시 WAVMASH 음원/폴더 자동 삭제 여부")


class SyncConfigUpdate(BaseModel):
    auto_sync_enabled: Optional[bool] = Field(None, description="자동 동기화 활성화 여부")
    sync_deletions: Optional[bool] = Field(None, description="스포티파이에서 삭제 시 WAVMASH 음원/폴더 자동 삭제 여부")


@router.get("/configs")
async def list_configs() -> list[dict[str, Any]]:
    """등록된 지정 스포티파이 동기화 플레이리스트 목록을 반환합니다."""
    return get_sync_configs()


@router.post("/configs")
async def create_config(body: SyncConfigCreate) -> dict[str, Any]:
    """동기화할 스포티파이 플레이리스트를 새로 등록합니다."""
    try:
        return add_sync_config(
            url=body.url,
            auto_sync_enabled=body.auto_sync_enabled,
            sync_deletions=body.sync_deletions,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"플레이리스트 등록 실패: {exc}")


@router.put("/configs/{config_id}")
async def update_config(config_id: str, body: SyncConfigUpdate) -> dict[str, Any]:
    """동기화 옵션(자동 동기화 ON/OFF, 삭제 동기화 ON/OFF)을 변경합니다."""
    try:
        return update_sync_config(
            config_id=config_id,
            auto_sync_enabled=body.auto_sync_enabled,
            sync_deletions=body.sync_deletions,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/configs/{config_id}")
async def delete_config(config_id: str) -> dict[str, str]:
    """등록된 동기화 설정을 삭제합니다."""
    delete_sync_config(config_id)
    return {"message": "동기화 설정이 삭제되었습니다."}


import asyncio

@router.post("/sync/{config_id}")
async def trigger_sync(config_id: str) -> dict[str, Any]:
    """지정한 단일 플레이리스트 동기화를 즉시 실행합니다 (새 곡 다운로드 + 삭제 동기화 + 빈 폴더 정리)."""
    cfg = get_sync_config(config_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="동기화 설정을 찾을 수 없습니다.")
    try:
        return await asyncio.to_thread(sync_single_playlist, config_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"동기화 실행 실패: {exc}")


@router.post("/sync-all")
async def trigger_sync_all() -> list[dict[str, Any]]:
    """활성화된 모든 지정 스포티파이 플레이리스트 동기화를 실행합니다."""
    try:
        return await asyncio.to_thread(sync_all_active_playlists)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"전체 동기화 실행 실패: {exc}")
