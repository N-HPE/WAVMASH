"""Spotify → 로컬 아카이브 매칭 (순수 로직).

네트워크/spotdl 없이 단위 테스트 가능합니다.
Spotify 구독 해지 전 마이그레이션용 동기화에서 사용합니다.
"""

from __future__ import annotations

import re
from typing import Any, Protocol

from spotify_metadata import spotify_track_id


class SpotifySongLike(Protocol):
    song_id: str
    name: str
    artist: str


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def find_record_for_spotify_id(
    records: list[dict[str, Any]],
    spotify_id: str,
) -> dict[str, Any] | None:
    """external_id / track_id / url / id 로 Spotify 트랙을 찾습니다."""
    sid = str(spotify_id or "").strip()
    if not sid:
        return None
    for rec in records:
        if str(rec.get("external_id") or "") == sid:
            return rec
        if str(rec.get("track_id") or "") == sid:
            return rec
        if str(rec.get("id") or "") == sid:
            return rec
        if spotify_track_id(str(rec.get("url") or "")) == sid:
            return rec
    return None


def find_record_for_song(
    records: list[dict[str, Any]],
    *,
    song_id: str = "",
    name: str = "",
    artist: str = "",
) -> dict[str, Any] | None:
    """ID 우선, 없으면 title+artist 휴리스틱으로 매칭합니다."""
    found = find_record_for_spotify_id(records, song_id)
    if found:
        return found

    title_key = _norm(name)
    if not title_key:
        return None
    artist_key = _norm(artist)
    for rec in records:
        rec_title = _norm(str(rec.get("title") or ""))
        if not rec_title or rec_title != title_key:
            continue
        if not artist_key:
            return rec
        rec_artist = _norm(str(rec.get("artist") or ""))
        if artist_key in rec_artist or rec_artist in artist_key:
            return rec
    return None


def record_has_local_file(record: dict[str, Any] | None, *, check_disk: bool = False) -> bool:
    """파일이 있는지 판별. 테스트에서는 has_file 플래그 / check_disk=False 사용."""
    if not record:
        return False
    if "has_file" in record and not check_disk:
        return bool(record.get("has_file"))
    if not check_disk:
        path = str(record.get("path") or record.get("local_path") or "")
        return bool(path)
    import os

    path = str(record.get("path") or record.get("local_path") or "")
    return bool(path and os.path.isfile(path))


def map_spotify_songs_to_local(
    songs: list[dict[str, Any]],
    records: list[dict[str, Any]],
    *,
    require_file: bool = True,
    check_disk: bool = False,
) -> dict[str, Any]:
    """Spotify 곡 목록을 로컬 아카이브에 매핑합니다.

    Args:
        songs: ``[{song_id, name, artist}, ...]`` (Spotify 순서 유지)
        records: archive 레코드 목록
        require_file: True면 파일이 있는 곡만 present로 취급
        check_disk: True면 실제 경로 존재 여부 확인

    Returns:
        matching_track_ids, local_spotify_ids, missing_ids, status
    """
    matching_track_ids: list[str] = []
    local_spotify_ids: list[str] = []
    missing_ids: list[str] = []

    for song in songs:
        sid = str(song.get("song_id") or "")
        rec = find_record_for_song(
            records,
            song_id=sid,
            name=str(song.get("name") or ""),
            artist=str(song.get("artist") or ""),
        )
        present = bool(rec) and (
            not require_file or record_has_local_file(rec, check_disk=check_disk)
        )
        if present and rec is not None:
            tid = str(rec.get("track_id") or rec.get("id") or "")
            if tid and tid not in matching_track_ids:
                matching_track_ids.append(tid)
            if sid:
                local_spotify_ids.append(sid)
        elif sid:
            missing_ids.append(sid)

    status = "completed" if not missing_ids else "partial"
    return {
        "matching_track_ids": matching_track_ids,
        "local_spotify_ids": local_spotify_ids,
        "missing_ids": missing_ids,
        "local_count": len(matching_track_ids),
        "missing_count": len(missing_ids),
        "status": status,
    }


def merge_missing_ids(*lists: list[str]) -> list[str]:
    """여러 missing 목록을 순서 유지하며 합칩니다."""
    seen: set[str] = set()
    out: list[str] = []
    for lst in lists:
        for mid in lst:
            if mid and mid not in seen:
                seen.add(mid)
                out.append(mid)
    return out
