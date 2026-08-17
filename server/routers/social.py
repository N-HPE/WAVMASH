"""소셜 상호작용 및 커뮤니티 활동 API 라우터."""

from __future__ import annotations

import requests as http_requests
from fastapi import APIRouter, Depends, HTTPException

from server.auth import get_current_user, get_optional_user
from server.models import ActivityItem, ChartEntry, MessageResponse
from server.supabase_db import get_headers, is_supabase_enabled, _SUPABASE_URL

router = APIRouter(prefix="/social", tags=["Social"])


# ---------------------------------------------------------------------------
# 트랙 소장 (Collect / Uncollect)
# ---------------------------------------------------------------------------

@router.post("/collect/{track_id}", response_model=MessageResponse)
async def collect_track(track_id: str, user_id: str = Depends(get_current_user)):
    """트랙을 현재 사용자의 컬렉션에 추가합니다."""
    if not is_supabase_enabled():
        raise HTTPException(status_code=500, detail="Supabase가 설정되지 않았습니다.")

    url = f"{_SUPABASE_URL}/rest/v1/rpc/increment_collector_count"
    headers = get_headers()
    
    # RPC call
    payload = {"p_track_id": track_id}
    
    resp = http_requests.post(url, headers=headers, json=payload, timeout=5)
    resp.raise_for_status()

    # Activity 피드에 기록
    _create_activity(user_id, "added_track", "track", track_id)

    return MessageResponse(message="트랙이 컬렉션에 추가되었습니다.")


@router.delete("/collect/{track_id}", response_model=MessageResponse)
async def remove_collected_track(track_id: str, user_id: str = Depends(get_current_user)):
    """트랙을 현재 사용자의 컬렉션에서 제거합니다."""
    if not is_supabase_enabled():
        raise HTTPException(status_code=500, detail="Supabase가 설정되지 않았습니다.")

    url = f"{_SUPABASE_URL}/rest/v1/rpc/decrement_collector_count"
    headers = get_headers()
    
    # RPC call
    payload = {"p_track_id": track_id}

    resp = http_requests.post(url, headers=headers, json=payload, timeout=5)
    resp.raise_for_status()

    return MessageResponse(message="트랙이 컬렉션에서 제거되었습니다.")


# ---------------------------------------------------------------------------
# 활동 피드 (Activity Feed)
# ---------------------------------------------------------------------------

@router.get("/feed")
async def get_activity_feed(user_id: str = Depends(get_current_user)):
    """친구들의 최근 활동 피드를 조회합니다."""
    if not is_supabase_enabled():
        return []

    headers = get_headers()

    # 1. 내 친구 목록 조회
    fr_url = f"{_SUPABASE_URL}/rest/v1/friendships"
    fr_resp = http_requests.get(
        fr_url,
        headers=headers,
        params={
            "or": f"(user_id.eq.{user_id},friend_id.eq.{user_id})",
            "status": "eq.accepted",
            "select": "user_id,friend_id",
        },
        timeout=5,
    )

    friend_ids = set()
    friend_ids.add(user_id)  # 내 활동도 포함
    if fr_resp.ok:
        for row in fr_resp.json():
            friend_ids.add(str(row.get("user_id", "")))
            friend_ids.add(str(row.get("friend_id", "")))

    # 2. 친구들의 최근 활동 조회
    act_url = f"{_SUPABASE_URL}/rest/v1/activities"
    friend_filter = ",".join(friend_ids)
    act_resp = http_requests.get(
        act_url,
        headers=headers,
        params={
            "user_id": f"in.({friend_filter})",
            "order": "created_at.desc",
            "limit": "50",
            "select": "*,profiles:user_id(username,display_name,avatar_url)",
        },
        timeout=10,
    )

    if not act_resp.ok:
        return []

    return act_resp.json()


# ---------------------------------------------------------------------------
# 인기 차트 (Most Collected)
# ---------------------------------------------------------------------------

@router.get("/charts/most-collected")
async def get_most_collected_chart(
    limit: int = 20,
    current_user_id: str | None = Depends(get_optional_user),
):
    """가장 많이 소장된 트랙 차트를 반환합니다."""
    if not is_supabase_enabled():
        return []

    url = f"{_SUPABASE_URL}/rest/v1/tracks"
    headers = get_headers()
    params = {
        "collector_count": "gt.0",
        "order": "collector_count.desc",
        "limit": str(limit),
        "select": "track_id,title,artist,album,genre,collector_count,thumbnail_url",
    }

    resp = http_requests.get(url, headers=headers, params=params, timeout=5)
    if not resp.ok:
        return []

    return resp.json()


# ---------------------------------------------------------------------------
# 친구 관계 (Friendships)
# ---------------------------------------------------------------------------

@router.post("/friends/{friend_user_id}", response_model=MessageResponse)
async def send_friend_request(friend_user_id: str, user_id: str = Depends(get_current_user)):
    """친구 요청을 보냅니다."""
    if not is_supabase_enabled():
        raise HTTPException(status_code=500, detail="Supabase가 설정되지 않았습니다.")

    if friend_user_id == user_id:
        raise HTTPException(status_code=400, detail="자기 자신에게 친구 요청을 보낼 수 없습니다.")

    url = f"{_SUPABASE_URL}/rest/v1/friendships"
    headers = get_headers()
    headers["Prefer"] = "resolution=ignore-duplicates"

    payload = {"user_id": user_id, "friend_id": friend_user_id, "status": "pending"}

    resp = http_requests.post(url, headers=headers, json=payload, timeout=5)
    resp.raise_for_status()

    _create_activity(user_id, "added_friend", "user", friend_user_id)

    return MessageResponse(message="친구 요청을 보냈습니다.")


@router.put("/friends/{friend_user_id}", response_model=MessageResponse)
async def accept_friend_request(friend_user_id: str, user_id: str = Depends(get_current_user)):
    """친구 요청을 수락합니다."""
    if not is_supabase_enabled():
        raise HTTPException(status_code=500, detail="Supabase가 설정되지 않았습니다.")

    url = f"{_SUPABASE_URL}/rest/v1/friendships"
    headers = get_headers()

    # 상대방이 보낸 요청을 accepted로 변경
    params = {"user_id": f"eq.{friend_user_id}", "friend_id": f"eq.{user_id}"}
    payload = {"status": "accepted"}

    resp = http_requests.patch(url, headers=headers, params=params, json=payload, timeout=5)
    resp.raise_for_status()

    return MessageResponse(message="친구 요청을 수락했습니다.")


@router.delete("/friends/{friend_user_id}", response_model=MessageResponse)
async def remove_friend(friend_user_id: str, user_id: str = Depends(get_current_user)):
    """친구를 삭제하거나 요청을 거절합니다."""
    if not is_supabase_enabled():
        raise HTTPException(status_code=500, detail="Supabase가 설정되지 않았습니다.")

    url = f"{_SUPABASE_URL}/rest/v1/friendships"
    headers = get_headers()

    # 양쪽 관계 모두 삭제
    http_requests.delete(
        url, headers=headers,
        params={"user_id": f"eq.{user_id}", "friend_id": f"eq.{friend_user_id}"},
        timeout=5,
    )
    http_requests.delete(
        url, headers=headers,
        params={"user_id": f"eq.{friend_user_id}", "friend_id": f"eq.{user_id}"},
        timeout=5,
    )

    return MessageResponse(message="친구 삭제 완료.")


@router.get("/friends")
async def list_friends(user_id: str = Depends(get_current_user)):
    """현재 사용자의 친구 목록을 조회합니다."""
    if not is_supabase_enabled():
        return []

    url = f"{_SUPABASE_URL}/rest/v1/friendships"
    headers = get_headers()

    # 내가 보냈거나 받은 accepted 관계 조회
    resp = http_requests.get(
        url,
        headers=headers,
        params={
            "or": f"(user_id.eq.{user_id},friend_id.eq.{user_id})",
            "status": "eq.accepted",
            "select": "user_id,friend_id",
        },
        timeout=5,
    )

    if not resp.ok:
        return []

    # 친구의 user_id 목록 추출
    friend_ids = set()
    for row in resp.json():
        uid = str(row.get("user_id", ""))
        fid = str(row.get("friend_id", ""))
        if uid != user_id:
            friend_ids.add(uid)
        if fid != user_id:
            friend_ids.add(fid)

    if not friend_ids:
        return []

    # 친구 프로필 조회
    prof_url = f"{_SUPABASE_URL}/rest/v1/profiles"
    ids_filter = ",".join(friend_ids)
    prof_resp = http_requests.get(
        prof_url,
        headers=headers,
        params={
            "user_id": f"in.({ids_filter})",
            "select": "user_id,username,display_name,avatar_url,track_count,friend_count",
        },
        timeout=5,
    )

    if not prof_resp.ok:
        return []

    return prof_resp.json()


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _create_activity(
    user_id: str,
    action_type: str,
    target_type: str,
    target_id: str,
    metadata: dict | None = None,
) -> None:
    """활동 피드에 이벤트를 기록합니다. (fire-and-forget)"""
    try:
        url = f"{_SUPABASE_URL}/rest/v1/activities"
        headers = get_headers()
        payload = {
            "user_id": user_id,
            "action_type": action_type,
            "target_type": target_type,
            "target_id": target_id,
            "metadata": metadata or {},
        }
        http_requests.post(url, headers=headers, json=payload, timeout=5)
    except Exception:
        pass  # 피드 기록 실패는 무시
