"""Spotify catalog search — artists, tracks, and artist top charts."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import HTTPException

from spotify_metadata import _user_spotify_credentials


def _spotify_client():
    client_id, client_secret = _user_spotify_credentials()
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=503,
            detail="Spotify 검색을 쓰려면 SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET 가 필요합니다.",
        )
    try:
        import spotipy
        from spotipy.oauth2 import SpotifyClientCredentials
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="spotipy 패키지가 설치되어 있지 않습니다.",
        ) from exc

    return spotipy.Spotify(
        auth_manager=SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret,
        ),
        requests_timeout=12,
        retries=2,
    )


def _best_image(images: list[dict] | None, min_size: int = 160) -> str:
    if not images:
        return ""
    for img in reversed(images):
        if int(img.get("width") or 0) >= min_size:
            return str(img.get("url") or "")
    return str(images[0].get("url") or "")


def _track_payload(item: dict[str, Any]) -> dict[str, Any]:
    album = item.get("album") or {}
    artists = item.get("artists") or []
    artist_names = ", ".join(a.get("name") or "" for a in artists if a.get("name"))
    primary = artists[0].get("name") if artists else ""
    spotify_id = item.get("id") or ""
    return {
        "id": spotify_id,
        "title": item.get("name") or "",
        "artist": artist_names,
        "primary_artist": primary,
        "album": album.get("name") or "",
        "thumbnail_url": _best_image(album.get("images")),
        "spotify_url": (item.get("external_urls") or {}).get("spotify")
        or (f"https://open.spotify.com/track/{spotify_id}" if spotify_id else ""),
        "preview_url": item.get("preview_url") or "",
        "popularity": int(item.get("popularity") or 0),
        "duration_ms": int(item.get("duration_ms") or 0),
        "explicit": bool(item.get("explicit")),
    }


def _artist_payload(item: dict[str, Any]) -> dict[str, Any]:
    artist_id = item.get("id") or ""
    return {
        "id": artist_id,
        "name": item.get("name") or "",
        "image_url": _best_image(item.get("images"), min_size=320),
        "followers": int((item.get("followers") or {}).get("total") or 0),
        "genres": (item.get("genres") or [])[:6],
        "spotify_url": (item.get("external_urls") or {}).get("spotify")
        or (f"https://open.spotify.com/artist/{artist_id}" if artist_id else ""),
        "popularity": int(item.get("popularity") or 0),
    }


def _youtube_search(artist: str, title: str) -> dict[str, str]:
    """yt-dlp ytsearch로 매칭 영상 ID를 찾는다 (다운로드 없음)."""
    query = " ".join(p for p in (artist, title, "audio") if p).strip()
    if not query:
        return {}
    try:
        import yt_dlp
    except ImportError:
        return {}

    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "skip_download": True,
        "noplaylist": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
    except Exception:
        return {}

    entries = (info or {}).get("entries") or []
    if not entries:
        return {}
    entry = entries[0] or {}
    vid = str(entry.get("id") or "").strip()
    if not vid or len(vid) != 11:
        return {}
    return {
        "youtube_id": vid,
        "youtube_url": f"https://www.youtube.com/watch?v={vid}",
    }


def resolve_preview(artist: str, title: str, spotify_id: str = "") -> dict[str, str]:
    """카탈로그 미리듣기: YouTube 영상을 찾아 인페이지 재생용 ID를 반환."""
    _ = spotify_id  # 호환용 (프론트에서 넘김)
    return _resolve_preview_cached(
        (artist or "").strip(),
        (title or "").strip(),
    )


@lru_cache(maxsize=256)
def _resolve_preview_cached(artist: str, title: str) -> dict[str, str]:
    empty = {"youtube_id": "", "youtube_url": "", "preview_url": ""}
    if not title:
        return empty
    yt = _youtube_search(artist, title)
    if yt.get("youtube_id"):
        return {
            "youtube_id": yt["youtube_id"],
            "youtube_url": yt["youtube_url"],
            "preview_url": "",
        }
    return empty


def search_catalog(query: str) -> dict[str, Any]:
    q = (query or "").strip()
    if not q:
        return {"artists": [], "tracks": []}

    sp = _spotify_client()
    try:
        data = sp.search(q=q, type="artist,track", limit=10, market="US")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Spotify 검색 실패: {exc}") from exc

    artists = [_artist_payload(a) for a in (data.get("artists") or {}).get("items") or []]
    tracks = [_track_payload(t) for t in (data.get("tracks") or {}).get("items") or []]
    return {"artists": artists, "tracks": tracks}


@lru_cache(maxsize=128)
def get_artist_profile(artist_id: str) -> dict[str, Any]:
    aid = (artist_id or "").strip()
    if not aid:
        raise HTTPException(status_code=400, detail="아티스트 ID가 필요합니다.")

    sp = _spotify_client()
    try:
        artist = sp.artist(aid)
        top = sp.artist_top_tracks(aid, country="US")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"아티스트 정보를 불러오지 못했습니다: {exc}") from exc

    tracks = [_track_payload(t) for t in (top.get("tracks") or [])[:10]]
    return {
        "artist": _artist_payload(artist),
        "top_tracks": tracks,
    }
