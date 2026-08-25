"""소셜 상호작용 및 커뮤니티 활동 API 라우터."""

from __future__ import annotations

import requests as http_requests
from fastapi import APIRouter, Depends, HTTPException

from server.auth import get_current_user, get_optional_user
from server.models import (
    ActivityItem,
    ChartEntry,
    HighlightCreate,
    MessageResponse,
    PostCommentCreate,
    PostCreate,
    TrackDownloadActionReq,
    TrackLikeActionReq,
    UserYouTubePlaylistSync,
)

from server.supabase_db import get_headers, is_supabase_enabled, _SUPABASE_URL



router = APIRouter(prefix="/social", tags=["Social"])


# ---------------------------------------------------------------------------
# 트랙 좋아요 & 다운로드 (Track Likes & Downloads)
# ---------------------------------------------------------------------------

@router.post("/tracks/{track_id}/like")
async def toggle_track_like(
    track_id: str,
    req: TrackLikeActionReq = None,
    user_id: str = Depends(get_current_user),
):
    """WAVMASH 내부 트랙 좋아요 토글 및 친구 피드 공유."""
    if not is_supabase_enabled():
        raise HTTPException(status_code=500, detail="Supabase가 설정되지 않았습니다.")

    headers = get_headers()
    url = f"{_SUPABASE_URL}/rest/v1/track_likes"

    # 1. 이미 좋아요를 눌렀는지 확인
    check_resp = http_requests.get(
        url,
        headers=headers,
        params={"user_id": f"eq.{user_id}", "track_id": f"eq.{track_id}", "select": "track_id"},
        timeout=5,
    )
    already_liked = bool(check_resp.ok and check_resp.json())

    if already_liked:
        # 좋아요 취소
        http_requests.delete(
            url,
            headers=headers,
            params={"user_id": f"eq.{user_id}", "track_id": f"eq.{track_id}"},
            timeout=5,
        )
        liked = False
    else:
        # 좋아요 추가
        payload = {"user_id": user_id, "track_id": track_id}
        http_requests.post(url, headers=headers, json=payload, timeout=5)
        liked = True

        # 친구 피드에 'liked_track' 활동 기록
        meta = {
            "track_id": track_id,
            "title": req.title if req else "Unknown Title",
            "artist": req.artist if req else "Unknown Artist",
            "cover_url": req.cover_url if req else "",
        }
        _create_activity(user_id, "liked_track", "track", track_id, meta)

    # 2. 현재 트랙의 총 좋아요 수 조회
    count_resp = http_requests.get(
        url,
        headers={**headers, "Prefer": "count=exact"},
        params={"track_id": f"eq.{track_id}", "select": "track_id"},
        timeout=5,
    )
    total_likes = int(count_resp.headers.get("content-range", "0/0").split("/")[-1]) if count_resp.ok else 0

    return {"liked": liked, "likes_count": total_likes}


@router.post("/tracks/{track_id}/download-event", response_model=MessageResponse)
async def record_track_download(
    track_id: str,
    req: TrackDownloadActionReq = None,
    user_id: str = Depends(get_current_user),
):
    """WAVMASH를 통한 트랙 다운로드/소장 기록 및 친구 활동 피드 전파."""
    if not is_supabase_enabled():
        raise HTTPException(status_code=500, detail="Supabase가 설정되지 않았습니다.")

    headers = get_headers()
    headers["Prefer"] = "resolution=merge-duplicates"

    # 1. track_downloads 테이블에 기록
    url = f"{_SUPABASE_URL}/rest/v1/track_downloads"
    payload = {"user_id": user_id, "track_id": track_id}
    http_requests.post(url, headers=headers, json=payload, timeout=5)

    # 2. Activity 피드에 'downloaded_track' 기록
    meta = {
        "track_id": track_id,
        "title": req.title if req else "Unknown Title",
        "artist": req.artist if req else "Unknown Artist",
        "cover_url": req.cover_url if req else "",
    }
    _create_activity(user_id, "downloaded_track", "track", track_id, meta)

    # 3. tracks 테이블의 collector_count 증가 RPC
    try:
        rpc_url = f"{_SUPABASE_URL}/rest/v1/rpc/increment_collector_count"
        http_requests.post(rpc_url, headers=get_headers(), json={"p_track_id": track_id}, timeout=5)
    except Exception:
        pass

    return MessageResponse(message="다운로드 활동이 기록되었습니다.")


@router.get("/tracks/{track_id}/status")
async def get_track_social_status(
    track_id: str,
    user_id: str | None = Depends(get_optional_user),
):
    """트랙의 좋아요 여부 및 총 좋아요/다운로드 수를 반환합니다."""
    if not is_supabase_enabled():
        return {"liked": False, "likes_count": 0, "downloaded": False}

    headers = get_headers()

    # 총 좋아요 수
    likes_resp = http_requests.get(
        f"{_SUPABASE_URL}/rest/v1/track_likes",
        headers={**headers, "Prefer": "count=exact"},
        params={"track_id": f"eq.{track_id}", "select": "track_id"},
        timeout=5,
    )
    likes_count = int(likes_resp.headers.get("content-range", "0/0").split("/")[-1]) if likes_resp.ok else 0

    liked = False
    downloaded = False
    if user_id:
        # 내 좋아요 여부
        user_like_resp = http_requests.get(
            f"{_SUPABASE_URL}/rest/v1/track_likes",
            headers=headers,
            params={"user_id": f"eq.{user_id}", "track_id": f"eq.{track_id}", "select": "track_id"},
            timeout=5,
        )
        liked = bool(user_like_resp.ok and user_like_resp.json())

        # 내 다운로드 여부
        user_dl_resp = http_requests.get(
            f"{_SUPABASE_URL}/rest/v1/track_downloads",
            headers=headers,
            params={"user_id": f"eq.{user_id}", "track_id": f"eq.{track_id}", "select": "track_id"},
            timeout=5,
        )
        downloaded = bool(user_dl_resp.ok and user_dl_resp.json())

    return {"liked": liked, "likes_count": likes_count, "downloaded": downloaded}


@router.get("/users/{target}/liked-tracks")
async def get_user_liked_tracks(target: str):
    """특정 사용자(username 또는 user_id)가 WM에서 좋아요를 누른 트랙 목록."""
    if not is_supabase_enabled():
        return []

    headers = get_headers()
    # UUID인지 username인지 판별
    user_id = target
    if "-" not in target or len(target) < 30:
        prof_resp = http_requests.get(
            f"{_SUPABASE_URL}/rest/v1/profiles",
            headers=headers,
            params={"username": f"eq.{target}", "select": "user_id"},
            timeout=5,
        )
        if prof_resp.ok and prof_resp.json():
            user_id = prof_resp.json()[0]["user_id"]
        else:
            return []

    likes_resp = http_requests.get(
        f"{_SUPABASE_URL}/rest/v1/track_likes",
        headers=headers,
        params={"user_id": f"eq.{user_id}", "order": "created_at.desc", "limit": "50", "select": "*"},
        timeout=5,
    )
    return likes_resp.json() if likes_resp.ok else []


@router.get("/users/{target}/downloaded-tracks")
async def get_user_downloaded_tracks(target: str):
    """특정 사용자(username 또는 user_id)가 WM을 통해 다운로드/소장한 트랙 목록."""
    if not is_supabase_enabled():
        return []

    headers = get_headers()
    user_id = target
    if "-" not in target or len(target) < 30:
        prof_resp = http_requests.get(
            f"{_SUPABASE_URL}/rest/v1/profiles",
            headers=headers,
            params={"username": f"eq.{target}", "select": "user_id"},
            timeout=5,
        )
        if prof_resp.ok and prof_resp.json():
            user_id = prof_resp.json()[0]["user_id"]
        else:
            return []

    dl_resp = http_requests.get(
        f"{_SUPABASE_URL}/rest/v1/track_downloads",
        headers=headers,
        params={"user_id": f"eq.{user_id}", "order": "created_at.desc", "limit": "50", "select": "*"},
        timeout=5,
    )
    return dl_resp.json() if dl_resp.ok else []



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

    # 2. 친구들의 최근 활동 조회 (친구가 적을 경우 전체 커뮤니티 활동 포함)
    act_url = f"{_SUPABASE_URL}/rest/v1/activities"
    params = {
        "order": "created_at.desc",
        "limit": "50",
        "select": "*,profiles:user_id(username,display_name,avatar_url)",
    }
    if len(friend_ids) > 1:
        friend_filter = ",".join(friend_ids)
        params["user_id"] = f"in.({friend_filter})"

    act_resp = http_requests.get(
        act_url,
        headers=headers,
        params=params,
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


# ---------------------------------------------------------------------------
# 인스타그램 감성 컬렉션 피드 (Instagram-Style Collection Posts)
# ---------------------------------------------------------------------------

@router.get("/posts")
async def list_posts(
    user_id: str | None = None,
    username: str | None = None,
    tag: str | None = None,
    limit: int = 30,
    offset: int = 0,
    current_user_id: str | None = Depends(get_optional_user),
):
    """컬렉션 자랑 피드 포스트 목록을 조회합니다."""
    if not is_supabase_enabled():
        return []

    headers = get_headers()
    params: dict[str, str] = {
        "order": "created_at.desc",
        "limit": str(limit),
        "offset": str(offset),
        "select": "*,profiles:user_id(user_id,username,display_name,avatar_url),tracks:track_id(*)",
    }

    if user_id:
        params["user_id"] = f"eq.{user_id}"
        # 본인이 아니면 private 제외
        if not current_user_id or current_user_id != user_id:
            params["visibility"] = "neq.private"
    elif username:
        # username으로 profile 조회 후 user_id 필터링
        prof_res = http_requests.get(
            f"{_SUPABASE_URL}/rest/v1/profiles",
            headers=headers,
            params={"username": f"eq.{username}", "select": "user_id"},
            timeout=5,
        )
        if prof_res.ok and prof_res.json():
            target_uid = prof_res.json()[0].get("user_id")
            params["user_id"] = f"eq.{target_uid}"
            if not current_user_id or current_user_id != target_uid:
                params["visibility"] = "neq.private"
        else:
            return []
    else:
        # 메인 피드는 무조건 공개 포스트만 노출
        params["visibility"] = "neq.private"

    if tag:
        params["tags"] = f"cs.{{{tag}}}"

    resp = http_requests.get(f"{_SUPABASE_URL}/rest/v1/posts", headers=headers, params=params, timeout=10)
    if not resp.ok:
        return []

    posts_data = resp.json()

    # 현재 로그인 사용자의 좋아요 여부(is_liked) 체크
    if current_user_id and posts_data:
        post_ids = [p["id"] for p in posts_data if "id" in p]
        if post_ids:
            likes_resp = http_requests.get(
                f"{_SUPABASE_URL}/rest/v1/post_likes",
                headers=headers,
                params={
                    "user_id": f"eq.{current_user_id}",
                    "post_id": f"in.({','.join(post_ids)})",
                    "select": "post_id",
                },
                timeout=5,
            )
            if likes_resp.ok:
                liked_set = {r["post_id"] for r in likes_resp.json()}
                for p in posts_data:
                    p["is_liked"] = p.get("id") in liked_set

    # Supabase 조인 결과를 프론트엔드 포맷(user, track)으로 매핑
    result = []
    for p in posts_data:
        p_copy = dict(p)
        if "profiles" in p_copy:
            p_copy["user"] = p_copy.pop("profiles")
        if "tracks" in p_copy:
            p_copy["track"] = p_copy.pop("tracks")
        result.append(p_copy)

    return result


@router.post("/posts")
async def create_post(
    req: PostCreate,
    user_id: str = Depends(get_current_user),
):
    """사진 및 음악/플리를 매칭한 감성 피드 & 다이어리 포스트를 작성합니다."""
    if not is_supabase_enabled():
        raise HTTPException(status_code=500, detail="Supabase가 설정되지 않았습니다.")

    url = f"{_SUPABASE_URL}/rest/v1/posts"
    headers = get_headers()
    headers["Prefer"] = "return=representation"

    payload = {
        "user_id": user_id,
        "track_id": req.track_id,
        "playlist_id": req.playlist_id,
        "image_url": req.image_url or "",
        "caption": req.caption,
        "tags": req.tags,
        "visibility": req.visibility or "public",
    }

    resp = http_requests.post(url, headers=headers, json=payload, timeout=10)
    if not resp.ok:
        raise HTTPException(status_code=resp.status_code, detail=f"포스트 생성 실패: {resp.text}")

    post = resp.json()[0] if resp.json() else payload

    # 활동 피드 기록 (공개 포스트일 때만 친구 피드에 알림)
    if (req.visibility or "public") == "public":
        _create_activity(
            user_id,
            "created_post",
            "post",
            str(post.get("id", "")),
            {"track_id": req.track_id, "image_url": req.image_url, "caption": req.caption[:50]},
        )


    return post


@router.post("/playlists/{playlist_id}/tracks")
async def add_track_to_playlist(
    playlist_id: str,
    req: PlaylistTrackAdd,
    user_id: str = Depends(get_current_user),
):
    """내 플레이리스트에 트랙을 추가(소장)합니다."""
    if not is_supabase_enabled():
        raise HTTPException(status_code=500, detail="Supabase가 설정되지 않았습니다.")

    headers = get_headers()
    headers["Prefer"] = "return=representation"

    # 1. 플레이리스트 소유자 검증
    p_resp = http_requests.get(
        f"{_SUPABASE_URL}/rest/v1/playlists",
        headers=headers,
        params={"id": f"eq.{playlist_id}", "user_id": f"eq.{user_id}"},
        timeout=5,
    )
    if not p_resp.ok or not p_resp.json():
        raise HTTPException(status_code=403, detail="플레이리스트 접근 권한이 없습니다.")

    # 2. playlist_tracks에 추가
    pt_url = f"{_SUPABASE_URL}/rest/v1/playlist_tracks"
    payload = {
        "playlist_id": playlist_id,
        "track_id": req.track_id,
    }
    resp = http_requests.post(pt_url, headers=headers, json=payload, timeout=5)

    # 3. 활동 피드 기록 (소장 활동)
    _create_activity(
        user_id,
        "collected_track",
        "playlist",
        playlist_id,
        {"track_id": req.track_id, "title": req.title, "artist": req.artist},
    )

    return {"message": "플레이리스트에 트랙이 추가되었습니다.", "success": True}



@router.delete("/posts/{post_id}", response_model=MessageResponse)
async def delete_post(
    post_id: str,
    user_id: str = Depends(get_current_user),
):
    """피드 포스트를 삭제합니다."""
    if not is_supabase_enabled():
        raise HTTPException(status_code=500, detail="Supabase가 설정되지 않았습니다.")

    url = f"{_SUPABASE_URL}/rest/v1/posts"
    headers = get_headers()

    resp = http_requests.delete(
        url,
        headers=headers,
        params={"id": f"eq.{post_id}", "user_id": f"eq.{user_id}"},
        timeout=5,
    )
    if not resp.ok:
        raise HTTPException(status_code=resp.status_code, detail="포스트 삭제 실패")

    return MessageResponse(message="포스트가 삭제되었습니다.")


@router.post("/posts/{post_id}/like")
async def toggle_post_like(
    post_id: str,
    user_id: str = Depends(get_current_user),
):
    """포스트 좋아요를 토글합니다."""
    if not is_supabase_enabled():
        raise HTTPException(status_code=500, detail="Supabase가 설정되지 않았습니다.")

    headers = get_headers()
    # 1. 이미 좋아요 했는지 확인
    check_resp = http_requests.get(
        f"{_SUPABASE_URL}/rest/v1/post_likes",
        headers=headers,
        params={"post_id": f"eq.{post_id}", "user_id": f"eq.{user_id}"},
        timeout=5,
    )

    liked = False
    if check_resp.ok and check_resp.json():
        # 좋아요 취소
        http_requests.delete(
            f"{_SUPABASE_URL}/rest/v1/post_likes",
            headers=headers,
            params={"post_id": f"eq.{post_id}", "user_id": f"eq.{user_id}"},
            timeout=5,
        )
        liked = False
    else:
        # 좋아요 추가
        http_requests.post(
            f"{_SUPABASE_URL}/rest/v1/post_likes",
            headers=headers,
            json={"post_id": post_id, "user_id": user_id},
            timeout=5,
        )
        liked = True

    # 최신 likes_count 조회
    post_resp = http_requests.get(
        f"{_SUPABASE_URL}/rest/v1/posts",
        headers=headers,
        params={"id": f"eq.{post_id}", "select": "likes_count"},
        timeout=5,
    )
    count = 0
    if post_resp.ok and post_resp.json():
        count = post_resp.json()[0].get("likes_count", 0)

    return {"liked": liked, "likes_count": count}


@router.post("/posts/{post_id}/share")
async def share_post(
    post_id: str,
    user_id: str = Depends(get_current_user),
):
    """포스트 공유 카운트를 1 증가시키고 공유 활동을 기록합니다."""
    if not is_supabase_enabled():
        return {"shares_count": 1}

    headers = get_headers()
    # 1. 포스트 조회
    p_resp = http_requests.get(
        f"{_SUPABASE_URL}/rest/v1/posts",
        headers=headers,
        params={"id": f"eq.{post_id}", "select": "shares_count,track_id"},
        timeout=5,
    )
    curr_shares = 0
    track_id = ""
    if p_resp.ok and p_resp.json():
        curr_shares = p_resp.json()[0].get("shares_count") or 0
        track_id = p_resp.json()[0].get("track_id") or ""

    new_shares = curr_shares + 1
    http_requests.patch(
        f"{_SUPABASE_URL}/rest/v1/posts",
        headers=headers,
        params={"id": f"eq.{post_id}"},
        json={"shares_count": new_shares},
        timeout=5,
    )

    _create_activity(user_id, "shared_post", "post", post_id, {"track_id": track_id})

    return {"shares_count": new_shares}


@router.post("/tracks/{track_id}/share")
async def share_track(
    track_id: str,
    user_id: str = Depends(get_current_user),
):
    """트랙 공유 카운트를 증가시키고 활동 피드에 공유 이벤트를 기록합니다."""
    if not is_supabase_enabled():
        return {"shares_count": 1}

    headers = get_headers()
    _create_activity(user_id, "shared_track", "track", track_id)

    return {"message": "트랙이 공유되었습니다.", "success": True}



@router.get("/posts/{post_id}/comments")
async def get_post_comments(post_id: str):
    """포스트 댓글 목록을 조회합니다."""
    if not is_supabase_enabled():
        return []

    headers = get_headers()
    params = {
        "post_id": f"eq.{post_id}",
        "order": "created_at.asc",
        "select": "*,profiles:user_id(user_id,username,display_name,avatar_url)",
    }

    resp = http_requests.get(f"{_SUPABASE_URL}/rest/v1/post_comments", headers=headers, params=params, timeout=10)
    if not resp.ok:
        return []

    comments = resp.json()
    for c in comments:
        if "profiles" in c:
            c["user"] = c.pop("profiles")
    return comments


@router.post("/posts/{post_id}/comments")
async def add_post_comment(
    post_id: str,
    req: PostCommentCreate,
    user_id: str = Depends(get_current_user),
):
    """포스트에 댓글을 작성합니다."""
    if not is_supabase_enabled():
        raise HTTPException(status_code=500, detail="Supabase가 설정되지 않았습니다.")

    url = f"{_SUPABASE_URL}/rest/v1/post_comments"
    headers = get_headers()
    headers["Prefer"] = "return=representation"

    payload = {
        "post_id": post_id,
        "user_id": user_id,
        "content": req.content,
    }

    resp = http_requests.post(url, headers=headers, json=payload, timeout=10)
    if not resp.ok:
        raise HTTPException(status_code=resp.status_code, detail="댓글 작성 실패")

    comment = resp.json()[0] if resp.json() else payload
    return comment


# ---------------------------------------------------------------------------
# 스토리 하이라이트 (Highlights)
# ---------------------------------------------------------------------------

@router.get("/highlights")
async def list_highlights(user: str | None = None):
    """유저의 스토리 하이라이트 큐레이션 목록을 조회합니다."""
    if not is_supabase_enabled():
        return []

    headers = get_headers()
    params: dict[str, str] = {
        "order": "created_at.desc",
        "select": "*",
    }

    if user:
        # UUID or username
        if len(user) == 36 and "-" in user:
            params["user_id"] = f"eq.{user}"
        else:
            prof_res = http_requests.get(
                f"{_SUPABASE_URL}/rest/v1/profiles",
                headers=headers,
                params={"username": f"eq.{user}", "select": "user_id"},
                timeout=5,
            )
            if prof_res.ok and prof_res.json():
                params["user_id"] = f"eq.{prof_res.json()[0]['user_id']}"
            else:
                return []

    resp = http_requests.get(f"{_SUPABASE_URL}/rest/v1/highlights", headers=headers, params=params, timeout=10)
    if not resp.ok:
        return []

    return resp.json()


@router.post("/highlights")
async def create_highlight(
    req: HighlightCreate,
    user_id: str = Depends(get_current_user),
):
    """새 하이라이트 큐레이션을 생성합니다."""
    if not is_supabase_enabled():
        raise HTTPException(status_code=500, detail="Supabase가 설정되지 않았습니다.")

    url = f"{_SUPABASE_URL}/rest/v1/highlights"
    headers = get_headers()
    headers["Prefer"] = "return=representation"

    payload = {
        "user_id": user_id,
        "title": req.title,
        "cover_url": req.cover_url,
        "track_ids": req.track_ids,
    }

    resp = http_requests.post(url, headers=headers, json=payload, timeout=10)
    if not resp.ok:
        raise HTTPException(status_code=resp.status_code, detail="하이라이트 생성 실패")

    return resp.json()[0] if resp.json() else payload


# ---------------------------------------------------------------------------
# 계정별 YouTube 플레이리스트 & 트랙 영구 DB 동기화
# ---------------------------------------------------------------------------

@router.post("/youtube/sync", response_model=MessageResponse)
async def sync_user_youtube_playlists(
    playlists_sync: list[UserYouTubePlaylistSync],
    user_id: str = Depends(get_current_user),
):
    """유저의 YouTube 플레이리스트 및 트랙 목록을 Supabase DB에 일괄 저장/갱신합니다."""
    if not is_supabase_enabled():
        raise HTTPException(status_code=500, detail="Supabase가 설정되지 않았습니다.")

    headers = get_headers()
    headers["Prefer"] = "resolution=merge-duplicates"

    # 1. Playlists 일괄 Upsert
    playlists_payload = [
        {
            "id": pl.id,
            "user_id": user_id,
            "title": pl.title,
            "description": pl.description,
            "thumbnail_url": pl.thumbnailUrl,
            "item_count": pl.itemCount,
            "last_synced_at": "now()",
        }
        for pl in playlists_sync
    ]

    if playlists_payload:
        http_requests.post(
            f"{_SUPABASE_URL}/rest/v1/user_youtube_playlists",
            headers=headers,
            json=playlists_payload,
            timeout=10,
        )

    # 2. Tracks 일괄 Upsert
    tracks_payload = []
    for pl in playlists_sync:
        for t in pl.tracks:
            tracks_payload.append(
                {
                    "user_id": user_id,
                    "playlist_id": pl.id,
                    "video_id": t.videoId,
                    "raw_title": t.rawTitle,
                    "artist": t.artist,
                    "clean_title": t.cleanTitle,
                    "channel_title": t.channelTitle,
                    "thumbnail_url": t.thumbnailUrl,
                    "duration": t.duration,
                }
            )

    if tracks_payload:
        # 50개씩 청크 분할 전송
        chunk_size = 50
        for i in range(0, len(tracks_payload), chunk_size):
            chunk = tracks_payload[i : i + chunk_size]
            http_requests.post(
                f"{_SUPABASE_URL}/rest/v1/user_youtube_tracks",
                headers=headers,
                json=chunk,
                timeout=10,
            )

    return MessageResponse(message="YouTube 플레이리스트가 계정 DB에 성공적으로 동기화되었습니다.")


@router.get("/youtube/playlists")
async def get_user_youtube_playlists(
    user_id: str | None = None,
    current_user_id: str = Depends(get_current_user),
):
    """현재 계정 또는 특정 사용자의 DB에 저장된 YouTube 플레이리스트를 조회합니다."""
    if not is_supabase_enabled():
        return []

    target_user_id = user_id or current_user_id
    headers = get_headers()
    params = {
        "user_id": f"eq.{target_user_id}",
        "order": "last_synced_at.desc",
        "select": "*",
    }

    resp = http_requests.get(
        f"{_SUPABASE_URL}/rest/v1/user_youtube_playlists",
        headers=headers,
        params=params,
        timeout=10,
    )
    if not resp.ok:
        return []

    return resp.json()


@router.get("/youtube/playlists/{playlist_id}/tracks")
async def get_user_youtube_playlist_tracks(
    playlist_id: str,
    user_id: str | None = None,
    current_user_id: str = Depends(get_current_user),
):
    """특정 YouTube 플레이리스트에 속한 트랙 목록을 DB에서 조회합니다."""
    if not is_supabase_enabled():
        return []

    target_user_id = user_id or current_user_id
    headers = get_headers()
    params = {
        "user_id": f"eq.{target_user_id}",
        "playlist_id": f"eq.{playlist_id}",
        "order": "created_at.asc",
        "select": "*",
    }

    resp = http_requests.get(
        f"{_SUPABASE_URL}/rest/v1/user_youtube_tracks",
        headers=headers,
        params=params,
        timeout=10,
    )
    if not resp.ok:
        return []

    return resp.json()


