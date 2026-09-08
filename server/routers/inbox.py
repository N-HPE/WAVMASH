"""WaveMash Curation Inbox 라우터 (Nexus x WAVMASH 연동).

Nexus 등의 중앙 통제실이나 차트에서 수집된 추천곡을 빠르게 청음하고
Keep(보관/다운로드)/Pass(보류) 결정을 내리는 디깅 워크스테이션 API.
"""

from __future__ import annotations

import time
from typing import Any, Union

from fastapi import APIRouter, HTTPException, Query, status

from server.database import get_inbox_store, load_playlists, save_playlists
from server.models import (
    InboxCreate,
    InboxItem,
    InboxKeepRequest,
    InboxStats,
    MessageResponse,
)
from server.services.download_service import get_download_service

router = APIRouter(prefix="/inbox", tags=["큐레이션 인박스"])


@router.get("", response_model=dict[str, Any])
async def list_inbox_items(
    status: str = Query("inbox", description="필터링할 상태 (inbox, keep, pass, all)"),
    curator: str | None = Query(None, description="추천 큐레이터 필터 (예: nexus_nova)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """인박스 트랙 목록을 조회합니다."""
    store = get_inbox_store()
    items, total = store.list_items(status=status, curator=curator, skip=skip, limit=limit)
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/stats", response_model=InboxStats)
async def get_inbox_stats():
    """인박스 통계(대기/보관/패스 수 및 전환율)를 반환합니다."""
    store = get_inbox_store()
    stats = store.get_stats()
    return InboxStats(**stats)


@router.post("", status_code=status.HTTP_201_CREATED)
async def push_to_inbox(data: Union[InboxCreate, list[InboxCreate]]):
    """Nexus 또는 외부에서 신규 추천곡을 인박스에 등록합니다 (단건/벌크)."""
    store = get_inbox_store()
    items = data if isinstance(data, list) else [data]
    created_items = []

    for item in items:
        raw_dict = item.model_dump()
        created = store.add_item(raw_dict)
        created_items.append(created)

    if isinstance(data, list):
        return {"count": len(created_items), "items": created_items}
    return created_items[0]


@router.post("/{item_id}/keep")
async def keep_inbox_item(
    item_id: str,
    req: InboxKeepRequest = InboxKeepRequest(),
):
    """트랙을 Keep(소장) 처리하고, 선택한 크레이트에 추가 및 백그라운드 다운로드를 시작합니다."""
    store = get_inbox_store()
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    updates: dict[str, Any] = {
        "status": "keep",
        "decision_at": now_str,
    }
    if req.target_crate:
        updates["target_crate"] = req.target_crate

    updated = store.update_item(item_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="인박스 아이템을 찾을 수 없습니다.")

    # 1. 크레이트(플레이리스트)에 추가
    if req.target_crate:
        try:
            pl_data = load_playlists()
            playlists = pl_data.get("playlists", {})
            track_id = updated.get("track_id")
            if track_id:
                track_list = playlists.setdefault(req.target_crate, [])
                if track_id not in track_list:
                    track_list.append(track_id)
                save_playlists(pl_data)
        except Exception as pl_err:
            print(f"[WaveMash] Crate addition error: {pl_err}")

    # 2. 백그라운드 무손실 다운로드 트리거
    job_id = None
    if req.trigger_download:
        dl_url = updated.get("spotify_url") or updated.get("youtube_id")
        if not dl_url and updated.get("track_id"):
            dl_url = f"https://open.spotify.com/track/{updated['track_id']}"
        elif dl_url and len(dl_url) == 11 and not dl_url.startswith("http"):
            dl_url = f"https://www.youtube.com/watch?v={dl_url}"

        if dl_url:
            try:
                dl_service = get_download_service()
                job = dl_service.submit_job(
                    url=dl_url,
                    export_format=req.export_format or "wav",
                )
                job_id = job.job_id
                store.update_item(item_id, {"status": "downloading"})
            except Exception as dl_err:
                print(f"[WaveMash] Auto-download trigger error: {dl_err}")

    return {
        "success": True,
        "item": updated,
        "download_job_id": job_id,
        "message": f"'{updated.get('title')}' 트랙을 컬렉션에 추가했습니다.",
    }


@router.post("/{item_id}/pass")
async def pass_inbox_item(item_id: str):
    """트랙을 Pass(보류/거절) 처리합니다."""
    store = get_inbox_store()
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    updated = store.update_item(
        item_id,
        {
            "status": "pass",
            "decision_at": now_str,
        },
    )
    if not updated:
        raise HTTPException(status_code=404, detail="인박스 아이템을 찾을 수 없습니다.")

    return {
        "success": True,
        "item": updated,
        "message": f"'{updated.get('title')}' 트랙을 패스했습니다.",
    }


@router.delete("/{item_id}", response_model=MessageResponse)
async def delete_inbox_item(item_id: str):
    """인박스 아이템을 삭제합니다."""
    store = get_inbox_store()
    ok = store.delete_item(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="인박스 아이템을 찾을 수 없습니다.")
    return MessageResponse(message="인박스 아이템이 삭제되었습니다.")


@router.post("/batch-download")
async def batch_download_kept():
    """Keep 된 트랙 중 아직 다운로드되지 않은 항목들을 일괄 다운로드 대기열에 등록합니다."""
    store = get_inbox_store()
    kept_items, _ = store.list_items(status="keep", limit=100)
    dl_service = get_download_service()
    triggered = []

    for it in kept_items:
        dl_url = it.get("spotify_url") or it.get("youtube_id")
        if not dl_url and it.get("track_id"):
            dl_url = f"https://open.spotify.com/track/{it['track_id']}"
        elif dl_url and len(dl_url) == 11 and not dl_url.startswith("http"):
            dl_url = f"https://www.youtube.com/watch?v={dl_url}"

        if dl_url:
            try:
                job = dl_service.submit_job(url=dl_url, export_format="wav")
                store.update_item(str(it.get("id")), {"status": "downloading"})
                triggered.append({"title": it.get("title"), "job_id": job.job_id})
            except Exception as e:
                print(f"[WaveMash] Batch download submit error: {e}")

    return {
        "count": len(triggered),
        "triggered": triggered,
        "message": f"{len(triggered)}개 트랙의 무손실 다운로드를 시작했습니다.",
    }
