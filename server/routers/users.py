"""사용자 프로필 및 컬렉션 API 라우터."""

from __future__ import annotations

import requests as http_requests
from fastapi import APIRouter, Depends, HTTPException

from server.auth import get_current_user, get_optional_user
from server.models import UserProfile, UserProfileUpdate
from server.supabase_db import get_headers, is_supabase_enabled, _SUPABASE_URL

router = APIRouter(prefix="/users", tags=["Users"])


def _row_to_profile(row: dict) -> UserProfile:
    """Supabase profiles 행을 UserProfile 모델로 변환합니다."""
    return UserProfile(
        user_id=str(row.get("user_id") or row.get("id", "")),
        username=row.get("username", ""),
        display_name=row.get("display_name", ""),
        bio=row.get("bio", ""),
        avatar_url=row.get("avatar_url", ""),
        favorite_genre=row.get("favorite_genre", ""),
        track_count=int(row.get("track_count") or 0),
        friend_count=int(row.get("friend_count") or 0),
        is_public=bool(row.get("is_public", True)),
        created_at=row.get("created_at"),
    )


@router.get("/me", response_model=UserProfile)
async def get_my_profile(user_id: str = Depends(get_current_user)):
    """현재 사용자의 프로필을 조회합니다."""
    if not is_supabase_enabled():
        raise HTTPException(status_code=500, detail="Supabase가 설정되지 않았습니다.")

    url = f"{_SUPABASE_URL}/rest/v1/profiles"
    headers = get_headers()
    params = {"user_id": f"eq.{user_id}", "select": "*", "limit": "1"}

    resp = http_requests.get(url, headers=headers, params=params, timeout=5)
    resp.raise_for_status()
    data = resp.json()

    if not data:
        return UserProfile(user_id=user_id, username=user_id[:8], display_name="User")

    return _row_to_profile(data[0])


@router.put("/me", response_model=UserProfile)
async def update_my_profile(
    update_data: UserProfileUpdate,
    user_id: str = Depends(get_current_user),
):
    """현재 사용자의 프로필을 수정합니다."""
    if not is_supabase_enabled():
        raise HTTPException(status_code=500, detail="Supabase가 설정되지 않았습니다.")

    url = f"{_SUPABASE_URL}/rest/v1/profiles"
    headers = get_headers()
    headers["Prefer"] = "return=representation"
    params = {"user_id": f"eq.{user_id}"}

    payload = update_data.model_dump(exclude_none=True)
    if not payload:
        return await get_my_profile(user_id)

    resp = http_requests.patch(url, headers=headers, params=params, json=payload, timeout=5)
    resp.raise_for_status()
    data = resp.json()

    if not data:
        raise HTTPException(status_code=404, detail="사용자 프로필을 찾을 수 없습니다.")

    return _row_to_profile(data[0])


@router.get("/{username}", response_model=UserProfile)
async def get_user_profile(
    username: str,
    current_user_id: str | None = Depends(get_optional_user),
):
    """특정 사용자의 공개 프로필을 조회합니다."""
    if not is_supabase_enabled():
        raise HTTPException(status_code=500, detail="Supabase가 설정되지 않았습니다.")

    url = f"{_SUPABASE_URL}/rest/v1/profiles"
    headers = get_headers()
    params = {"username": f"eq.{username}", "select": "*", "limit": "1"}

    resp = http_requests.get(url, headers=headers, params=params, timeout=5)
    resp.raise_for_status()
    data = resp.json()

    if not data:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    profile = data[0]
    # 비공개 프로필은 본인만 조회 가능
    if not profile.get("is_public", True) and str(profile.get("user_id")) != current_user_id:
        raise HTTPException(status_code=403, detail="비공개 프로필입니다.")

    return _row_to_profile(profile)





@router.get("/{username}/playlists")
async def get_user_playlists(
    username: str,
    current_user_id: str | None = Depends(get_optional_user),
):
    """특정 사용자의 공개 플레이리스트를 조회합니다."""
    if not is_supabase_enabled():
        raise HTTPException(status_code=500, detail="Supabase가 설정되지 않았습니다.")

    headers = get_headers()

    # 1. username → user_id 조회
    prof_url = f"{_SUPABASE_URL}/rest/v1/profiles"
    prof_resp = http_requests.get(
        prof_url,
        headers=headers,
        params={"username": f"eq.{username}", "select": "user_id", "limit": "1"},
        timeout=5,
    )
    prof_resp.raise_for_status()
    profiles = prof_resp.json()
    if not profiles:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    target_user_id = profiles[0]["user_id"]

    # 2. playlists 테이블에서 해당 유저의 공개 플레이리스트 조회
    pl_url = f"{_SUPABASE_URL}/rest/v1/playlists"
    pl_resp = http_requests.get(
        pl_url,
        headers=headers,
        params={
            "owner_id": f"eq.{target_user_id}",
            "is_public": "eq.true",
            "select": "*",
            "order": "created_at.desc",
        },
        timeout=10,
    )
    pl_resp.raise_for_status()
    playlists = pl_resp.json()

    return {"items": playlists, "total": len(playlists)}
