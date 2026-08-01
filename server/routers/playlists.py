"""플레이리스트 API 라우터 — CRUD 및 자동 분류."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException

from server.database import load_playlists, save_playlists, get_archive_cache
from server.models import (
    AutoPlaylistRule,
    MessageResponse,
    Playlist,
    PlaylistAddTrack,
    PlaylistCreate,
    PlaylistUpdate,
)
from server.services.playlist_service import apply_auto_playlists
from server.vibe_palette import make_meta

router = APIRouter(prefix="/playlists", tags=["플레이리스트"])


def _playlist_from_data(
    name: str,
    track_ids: list[str],
    activity: float | None,
    meta: dict[str, Any] | None,
) -> Playlist:
    m = meta if isinstance(meta, dict) else make_meta(name=name)
    return Playlist(
        name=name,
        track_ids=track_ids,
        track_count=len(track_ids),
        activity=activity,
        vibe=str(m.get("vibe") or "other"),
        shade=int(m.get("shade") or 0),
        color=str(m.get("color") or "#6D4C41"),
    )


# ---------------------------------------------------------------------------
# 엔드포인트
# ---------------------------------------------------------------------------

@router.get("", response_model=list[Playlist])
async def list_playlists() -> list[Playlist]:
    """모든 플레이리스트를 반환합니다."""
    data = load_playlists()
    playlists = data.get("playlists", {})
    activity = data.get("activity", {})
    meta = data.get("meta", {})

    result: list[Playlist] = []
    for name, track_ids in playlists.items():
        if not isinstance(track_ids, list):
            continue
        result.append(
            _playlist_from_data(
                name,
                track_ids,
                activity.get(name),
                meta.get(name),
            )
        )
    # 바이브 → shade → 이름 순 (장르 정리 우선)
    vibe_rank = {
        "pop": 0,
        "rnb": 1,
        "hiphop": 2,
        "house": 3,
        "techno": 4,
        "bass": 5,
        "chill": 6,
        "other": 7,
    }
    result.sort(
        key=lambda p: (
            vibe_rank.get(p.vibe, 99),
            p.shade,
            p.name.lower(),
        )
    )
    return result


@router.post("", response_model=Playlist)
async def create_playlist(body: PlaylistCreate) -> Playlist:
    """새 플레이리스트를 생성합니다."""
    data = load_playlists()
    playlists = data.get("playlists", {})

    if body.name in playlists:
        raise HTTPException(status_code=409, detail=f"'{body.name}' 플레이리스트가 이미 존재합니다.")

    playlists[body.name] = body.track_ids
    data["playlists"] = playlists
    data.setdefault("activity", {})[body.name] = time.time()
    data.setdefault("meta", {})[body.name] = make_meta(
        vibe=body.vibe,
        shade=body.shade,
        color=body.color,
        name=body.name,
    )
    save_playlists(data)

    return _playlist_from_data(
        body.name,
        body.track_ids,
        data["activity"][body.name],
        data["meta"][body.name],
    )


@router.put("/{name}", response_model=Playlist)
async def update_playlist(name: str, body: PlaylistUpdate) -> Playlist:
    """플레이리스트를 수정합니다 (이름 변경, 트랙 재정렬, 바이브/색)."""
    data = load_playlists()
    playlists = data.get("playlists", {})
    activity = data.get("activity", {})
    meta = data.setdefault("meta", {})

    if name not in playlists:
        raise HTTPException(status_code=404, detail=f"'{name}' 플레이리스트를 찾을 수 없습니다.")

    current_ids = playlists[name]
    current_meta = dict(meta.get(name) or make_meta(name=name))

    # 트랙 순서 업데이트
    if body.track_ids is not None:
        current_ids = body.track_ids

    # 바이브/색 업데이트
    if body.vibe is not None or body.shade is not None or body.color is not None:
        current_meta = make_meta(
            vibe=body.vibe if body.vibe is not None else current_meta.get("vibe"),
            shade=body.shade if body.shade is not None else current_meta.get("shade"),
            color=body.color if body.color is not None else None,
            name=body.name or name,
        )

    # 이름 변경
    new_name = name
    if body.name is not None and body.name != name:
        if body.name in playlists:
            raise HTTPException(
                status_code=409,
                detail=f"'{body.name}' 플레이리스트가 이미 존재합니다.",
            )
        del playlists[name]
        new_name = body.name
        if name in activity:
            activity[new_name] = activity.pop(name)
        if name in meta:
            del meta[name]

    playlists[new_name] = current_ids
    activity[new_name] = time.time()
    meta[new_name] = current_meta

    data["playlists"] = playlists
    data["activity"] = activity
    data["meta"] = meta
    save_playlists(data)

    return _playlist_from_data(
        new_name,
        current_ids,
        activity.get(new_name),
        meta.get(new_name),
    )


@router.delete("/{name}", response_model=MessageResponse)
async def delete_playlist(name: str) -> MessageResponse:
    """플레이리스트를 삭제합니다."""
    data = load_playlists()
    playlists = data.get("playlists", {})

    if name not in playlists:
        raise HTTPException(status_code=404, detail=f"'{name}' 플레이리스트를 찾을 수 없습니다.")

    del playlists[name]
    data.get("activity", {}).pop(name, None)
    data.get("meta", {}).pop(name, None)
    data["playlists"] = playlists
    save_playlists(data)

    return MessageResponse(message=f"'{name}' 플레이리스트가 삭제되었습니다.")


@router.post("/{name}/tracks", response_model=Playlist)
async def add_track_to_playlist(name: str, body: PlaylistAddTrack) -> Playlist:
    """플레이리스트에 트랙을 추가합니다."""
    data = load_playlists()
    playlists = data.get("playlists", {})
    activity = data.get("activity", {})
    meta = data.get("meta", {})

    if name not in playlists:
        raise HTTPException(status_code=404, detail=f"'{name}' 플레이리스트를 찾을 수 없습니다.")

    # 트랙 존재 확인
    cache = get_archive_cache()
    record = cache.get_record(body.track_id)
    if not record:
        raise HTTPException(status_code=404, detail="트랙을 찾을 수 없습니다.")

    track_ids = playlists[name]
    if body.track_id not in track_ids:
        track_ids.append(body.track_id)

    playlists[name] = track_ids
    activity[name] = time.time()
    data["playlists"] = playlists
    data["activity"] = activity
    save_playlists(data)

    return _playlist_from_data(name, track_ids, activity.get(name), meta.get(name))


@router.delete("/{name}/tracks/{track_id}", response_model=Playlist)
async def remove_track_from_playlist(name: str, track_id: str) -> Playlist:
    """플레이리스트에서 트랙을 제거합니다."""
    data = load_playlists()
    playlists = data.get("playlists", {})
    activity = data.get("activity", {})
    meta = data.get("meta", {})

    if name not in playlists:
        raise HTTPException(status_code=404, detail=f"'{name}' 플레이리스트를 찾을 수 없습니다.")

    track_ids = [tid for tid in playlists[name] if tid != track_id]
    playlists[name] = track_ids
    activity[name] = time.time()
    data["playlists"] = playlists
    data["activity"] = activity
    save_playlists(data)

    return _playlist_from_data(name, track_ids, activity.get(name), meta.get(name))


@router.post("/auto-parse", response_model=dict[str, int])
async def auto_parse_playlists(
    rules: list[AutoPlaylistRule] | None = None,
) -> dict[str, int]:
    """장르/BPM/키를 기준으로 트랙을 자동 분류하여 플레이리스트를 생성합니다.

    규칙을 제공하지 않으면 기본 장르 규칙이 사용됩니다.
    """
    result = apply_auto_playlists(rules)
    return result
