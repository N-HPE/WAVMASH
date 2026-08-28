"""Spotify catalog search — artists, tracks, albums, and artist pages."""

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


def _album_payload(item: dict[str, Any]) -> dict[str, Any]:
    album_id = item.get("id") or ""
    artists = item.get("artists") or []
    artist_names = ", ".join(a.get("name") or "" for a in artists if a.get("name"))
    release = str(item.get("release_date") or "")
    return {
        "id": album_id,
        "name": item.get("name") or "",
        "album_type": item.get("album_type") or item.get("type") or "album",
        "artist": artist_names,
        "thumbnail_url": _best_image(item.get("images")),
        "spotify_url": (item.get("external_urls") or {}).get("spotify")
        or (f"https://open.spotify.com/album/{album_id}" if album_id else ""),
        "release_date": release,
        "total_tracks": int(item.get("total_tracks") or 0),
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
    _ = spotify_id
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


def _artist_tracks_via_search(
    sp: Any, artist_name: str, artist_id: str, limit: int = 20
) -> list[dict[str, Any]]:
    """Client Credentials에서 top-tracks가 403이라 검색으로 인기곡을 대체.

    현재 Spotify 앱 한도로 search limit 최대 10 — offset으로 페이지네이션.
    """
    queries = [
        f'artist:"{artist_name}"',
        artist_name,
    ]
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    page_size = 10

    for q in queries:
        offset = 0
        while len(out) < limit and offset < 30:
            try:
                data = sp.search(
                    q=q,
                    type="track",
                    limit=page_size,
                    offset=offset,
                    market="US",
                )
            except Exception:
                break
            items = (data.get("tracks") or {}).get("items") or []
            if not items:
                break
            for item in items:
                tid = item.get("id") or ""
                if not tid or tid in seen:
                    continue
                artist_ids = {a.get("id") for a in (item.get("artists") or [])}
                if artist_id and artist_id not in artist_ids:
                    continue
                seen.add(tid)
                out.append(_track_payload(item))
                if len(out) >= limit:
                    break
            offset += page_size
            total = int(((data.get("tracks") or {}).get("total") or 0))
            if offset >= total:
                break
        if out:
            break

    if not out:
        try:
            data = sp.search(q=artist_name, type="track", limit=page_size, market="US")
            for item in (data.get("tracks") or {}).get("items") or []:
                tid = item.get("id") or ""
                if tid and tid not in seen:
                    seen.add(tid)
                    out.append(_track_payload(item))
        except Exception:
            pass

    out.sort(key=lambda t: int(t.get("popularity") or 0), reverse=True)
    return out[:limit]


def _artist_discography(
    sp: Any, artist_id: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    albums: list[dict[str, Any]] = []
    singles: list[dict[str, Any]] = []
    seen: set[str] = set()
    page_size = 10
    offset = 0
    items: list[dict[str, Any]] = []

    while offset < 50:
        try:
            results = sp.artist_albums(
                artist_id,
                album_type="album,single",
                limit=page_size,
                offset=offset,
                country="US",
            )
        except Exception:
            try:
                results = sp.artist_albums(
                    artist_id,
                    album_type="album,single",
                    limit=page_size,
                    offset=offset,
                )
            except Exception:
                break
        batch = list((results or {}).get("items") or [])
        if not batch:
            break
        items.extend(batch)
        offset += page_size
        total = int((results or {}).get("total") or 0)
        if offset >= total:
            break

    for item in items:
        aid = item.get("id") or ""
        name = (item.get("name") or "").strip().lower()
        key = aid or name
        if not key or key in seen:
            continue
        name_key = f"{item.get('album_type')}:{name}"
        if name_key in seen:
            continue
        seen.add(key)
        seen.add(name_key)
        payload = _album_payload(item)
        if payload["album_type"] == "single":
            singles.append(payload)
        else:
            albums.append(payload)

    return albums[:30], singles[:30]


@lru_cache(maxsize=128)
def get_artist_profile(artist_id: str) -> dict[str, Any]:
    aid = (artist_id or "").strip()
    if not aid:
        raise HTTPException(status_code=400, detail="아티스트 ID가 필요합니다.")

    sp = _spotify_client()
    try:
        artist = sp.artist(aid)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"아티스트 정보를 불러오지 못했습니다: {exc}"
        ) from exc

    tracks: list[dict[str, Any]] = []
    # top-tracks는 Client Credentials에서 403이 나는 경우가 많음 → 검색 폴백
    try:
        top = sp.artist_top_tracks(aid, country="US")
        tracks = [_track_payload(t) for t in (top.get("tracks") or [])[:20]]
    except Exception:
        tracks = []

    if not tracks:
        tracks = _artist_tracks_via_search(sp, artist.get("name") or "", aid, limit=20)

    albums, singles = _artist_discography(sp, aid)

    # 검색 결과가 적으면 최신 앨범 트랙으로 보강
    if len(tracks) < 12 and albums:
        seen = {t["id"] for t in tracks if t.get("id")}
        for alb in albums[:4]:
            if len(tracks) >= 20:
                break
            try:
                detail = sp.album(alb["id"], market="US")
            except Exception:
                continue
            for item in (detail.get("tracks") or {}).get("items") or []:
                tid = item.get("id") or ""
                if not tid or tid in seen:
                    continue
                merged = dict(item)
                merged["album"] = {
                    "name": detail.get("name"),
                    "images": detail.get("images"),
                    "id": detail.get("id"),
                }
                seen.add(tid)
                tracks.append(_track_payload(merged))
                if len(tracks) >= 20:
                    break

    return {
        "artist": _artist_payload(artist),
        "top_tracks": tracks[:20],
        "albums": albums,
        "singles": singles,
    }


@lru_cache(maxsize=64)
def get_album_tracks(album_id: str) -> dict[str, Any]:
    alid = (album_id or "").strip()
    if not alid:
        raise HTTPException(status_code=400, detail="앨범 ID가 필요합니다.")

    sp = _spotify_client()
    try:
        album = sp.album(alid, market="US")
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"앨범 정보를 불러오지 못했습니다: {exc}"
        ) from exc

    tracks_out: list[dict[str, Any]] = []
    for item in (album.get("tracks") or {}).get("items") or []:
        # album_tracks 응답에는 album 이미지가 없으므로 부모 앨범 주입
        merged = dict(item)
        merged["album"] = {
            "name": album.get("name"),
            "images": album.get("images"),
            "id": album.get("id"),
        }
        if not merged.get("preview_url"):
            merged["preview_url"] = ""
        tracks_out.append(_track_payload(merged))

    return {
        "album": _album_payload(album),
        "tracks": tracks_out,
    }
