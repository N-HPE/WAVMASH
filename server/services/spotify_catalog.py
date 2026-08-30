"""Spotify catalog search — artists, tracks, albums, and artist pages."""

from __future__ import annotations

import json
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import requests as http_requests
from fastapi import HTTPException

from spotify_metadata import _user_spotify_credentials

logger = logging.getLogger("wavemash.catalog")

# Spotify Charts 공개 엔드포인트 (음반 차트 등 보조)
_SPOTIFY_PUBLIC_CHARTS_URL = (
    "https://charts-spotify-com-service.spotify.com/public/v0/charts"
)
# 장르 차트 캐시 (메모리 + 디스크). Render 콜드스타트 대비.
_chart_cache: dict[str, tuple[str, dict[str, Any]]] = {}
_chart_cache_lock = threading.Lock()
_DISK_CACHE_PATH = Path(
    os.environ.get(
        "WAVMASH_CHART_CACHE",
        str(Path(__file__).resolve().parents[2] / ".cache" / "genre_charts.json"),
    )
)
_CHART_KINDS: dict[str, dict[str, str]] = {
    "songs": {
        "alias": "REGIONAL_GLOBAL_WEEKLY",
        "label": "노래",
        "name": "Global Top Songs (Weekly)",
    },
    "albums": {
        "alias": "ALBUM_GLOBAL_WEEKLY",
        "label": "음반",
        "name": "Global Top Albums (Weekly)",
    },
}

# 스펙트럼 대분류 (빨주노초파남보). 근본축: 빨=힙합·R&B, 노=팝·인디, 파=댄스.
# 대분류 UI는 색상만 노출. genre: 빈 결과는 키워드+연도 폴백.
_GENRE_GROUPS: list[dict[str, Any]] = [
    {
        "id": "red",
        "label": "빨",
        "subgenres": [
            {
                "id": "red",
                "label": "전체",
                "queries": ["hip hop year:{y1}", "r&b year:{y1}"],
            },
            {
                "id": "red-hiphop",
                "label": "힙합",
                "queries": ["hip hop year:{y1}", "rap year:{y1}"],
            },
            {
                "id": "red-trap",
                "label": "트랩",
                "queries": ["trap year:{y1}", "genre:trap year:{y1}"],
            },
            {
                "id": "red-drill",
                "label": "드릴",
                "queries": ["drill year:{y1}", "uk drill year:{y1}"],
            },
            {
                "id": "red-rnb",
                "label": "R&B",
                "queries": ["r&b year:{y1}", "genre:soul year:{y1}"],
            },
            {
                "id": "red-neo",
                "label": "네오소울",
                "queries": ["neo soul year:{y1}", "genre:neo soul year:{y1}"],
            },
            {
                "id": "red-alt",
                "label": "얼터 R&B",
                "queries": ["alternative r&b year:{y1}", "alt r&b year:{y1}"],
            },
            {
                "id": "red-k-hiphop",
                "label": "K-힙합",
                "queries": ["k-hip hop year:{y1}", "korean hip hop year:{y1}"],
            },
            {
                "id": "red-k-rnb",
                "label": "K-R&B",
                "queries": ["korean r&b year:{y1}", "k-r&b year:{y1}"],
            },
        ],
    },
    {
        "id": "orange",
        "label": "주",
        "subgenres": [
            {
                "id": "orange",
                "label": "전체",
                "queries": ["reggaeton year:{y1}", "afrobeats year:{y1}"],
            },
            {
                "id": "orange-reggaeton",
                "label": "레게톤",
                "queries": ["reggaeton year:{y1}", "genre:reggaeton year:{y1}"],
            },
            {
                "id": "orange-latin",
                "label": "라틴",
                "queries": ["latin pop year:{y1}", "genre:latin year:{y1}"],
            },
            {
                "id": "orange-afrobeats",
                "label": "아프로비트",
                "queries": ["afrobeats year:{y1}", "afrobeat year:{y1}"],
            },
            {
                "id": "orange-funk",
                "label": "펑크",
                "queries": ["funk year:{y1}", "genre:funk year:{y1}"],
            },
            {
                "id": "orange-salsa",
                "label": "살사",
                "queries": ["salsa year:{y1}", "genre:salsa year:{y1}"],
            },
        ],
    },
    {
        "id": "yellow",
        "label": "노",
        "subgenres": [
            {
                "id": "yellow",
                "label": "전체",
                "queries": ["pop year:{y1}", "indie year:{y1}"],
            },
            {
                "id": "yellow-pop",
                "label": "팝",
                "queries": ["genre:pop year:{y1}", "pop year:{y1}"],
            },
            {
                "id": "yellow-dance-pop",
                "label": "댄스팝",
                "queries": ["dance pop year:{y1}", "genre:dance pop year:{y1}"],
            },
            {
                "id": "yellow-synth",
                "label": "신스팝",
                "queries": ["synth-pop year:{y1}", "electropop year:{y1}"],
            },
            {
                "id": "yellow-kpop",
                "label": "K-pop",
                "queries": ["k-pop year:{y1}", "kpop year:{y1}"],
            },
            {
                "id": "yellow-indie",
                "label": "인디",
                "queries": ["genre:indie year:{y1}", "indie year:{y1}"],
            },
            {
                "id": "yellow-indie-pop",
                "label": "인디팝",
                "queries": ["indie pop year:{y1}", "genre:indie pop year:{y1}"],
            },
            {
                "id": "yellow-indie-rock",
                "label": "인디록",
                "queries": ["indie rock year:{y1}", "genre:indie rock year:{y1}"],
            },
        ],
    },
    {
        "id": "green",
        "label": "초",
        "subgenres": [
            {
                "id": "green",
                "label": "전체",
                "queries": ["alternative year:{y1}", "indie rock year:{y1}"],
            },
            {
                "id": "green-alt",
                "label": "얼터너티브",
                "queries": ["alternative year:{y1}", "alt rock year:{y1}"],
            },
            {
                "id": "green-rock",
                "label": "록",
                "queries": ["rock year:{y1}", "genre:rock year:{y1}"],
            },
            {
                "id": "green-folk",
                "label": "포크",
                "queries": ["folk year:{y1}", "indie folk year:{y1}"],
            },
            {
                "id": "green-chill",
                "label": "칠",
                "queries": ["chill year:{y1}", "lo-fi year:{y1}"],
            },
        ],
    },
    {
        "id": "blue",
        "label": "파",
        "subgenres": [
            {
                "id": "blue",
                "label": "전체",
                "queries": ["edm year:{y1}", "electronic year:{y1}"],
            },
            {
                "id": "blue-house",
                "label": "하우스",
                "queries": ["house year:{y1}", "deep house year:{y1}"],
            },
            {
                "id": "blue-techno",
                "label": "테크노",
                "queries": ["techno year:{y1}", "genre:techno year:{y1}"],
            },
            {
                "id": "blue-trance",
                "label": "트랜스",
                "queries": ["trance year:{y1}", "genre:trance year:{y1}"],
            },
        ],
    },
    {
        "id": "indigo",
        "label": "남",
        "subgenres": [
            {
                "id": "indigo",
                "label": "전체",
                "queries": ["deep house year:{y1}", "progressive house year:{y1}"],
            },
            {
                "id": "indigo-deep",
                "label": "딥하우스",
                "queries": ["deep house year:{y1}", "genre:deep house year:{y1}"],
            },
            {
                "id": "indigo-prog",
                "label": "프로그레시브",
                "queries": ["progressive house year:{y1}", "progressive trance year:{y1}"],
            },
            {
                "id": "indigo-minimal",
                "label": "미니멀",
                "queries": ["minimal techno year:{y1}", "minimal year:{y1}"],
            },
            {
                "id": "indigo-electro",
                "label": "일렉트로니카",
                "queries": ["electronica year:{y1}", "intelligent dance year:{y1}"],
            },
        ],
    },
    {
        # 보 = 파(댄스)×빨(흑인음악) 교차축. 스펙트럼이 다시 빨강으로 이어짐.
        "id": "violet",
        "label": "보",
        "subgenres": [
            {
                "id": "violet",
                "label": "전체",
                "queries": ["amapiano year:{y1}", "uk garage year:{y1}"],
            },
            {
                "id": "violet-amapiano",
                "label": "아마피아노",
                "queries": ["amapiano year:{y1}", "genre:amapiano year:{y1}"],
            },
            {
                "id": "violet-afro-house",
                "label": "아프로하우스",
                "queries": ["afro house year:{y1}", "afrohouse year:{y1}"],
            },
            {
                "id": "violet-garage",
                "label": "개러지",
                "queries": ["uk garage year:{y1}", "2-step year:{y1}"],
            },
            {
                "id": "violet-grime",
                "label": "그라임",
                "queries": ["grime year:{y1}", "genre:grime year:{y1}"],
            },
            {
                "id": "violet-dancehall",
                "label": "댄스홀",
                "queries": ["dancehall year:{y1}", "genre:dancehall year:{y1}"],
            },
            {
                "id": "violet-jersey",
                "label": "저지클럽",
                "queries": ["jersey club year:{y1}", "baltimore club year:{y1}"],
            },
            {
                "id": "violet-baile",
                "label": "바이르펑크",
                "queries": ["baile funk year:{y1}", "funk carioca year:{y1}"],
            },
            {
                "id": "violet-dnb",
                "label": "드럼앤베이스",
                "queries": ["drum and bass year:{y1}", "dnb year:{y1}"],
            },
            {
                "id": "violet-dubstep",
                "label": "덥스텝",
                "queries": ["dubstep year:{y1}", "genre:dubstep year:{y1}"],
            },
        ],
    },
]


def _flatten_genre_defs() -> list[dict[str, Any]]:
    """세부장르 leaf 목록 (조회·캐시용). group_id / group_label 포함."""
    out: list[dict[str, Any]] = []
    for group in _GENRE_GROUPS:
        for sub in group.get("subgenres") or []:
            out.append(
                {
                    **sub,
                    "group_id": group["id"],
                    "group_label": group["label"],
                }
            )
    return out


_GENRE_CHART_DEFS: list[dict[str, Any]] = _flatten_genre_defs()


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


_PREVIEW_OK: dict[tuple[str, str], dict[str, str]] = {}


def resolve_preview(artist: str, title: str, spotify_id: str = "") -> dict[str, str]:
    """카탈로그 미리듣기: YouTube 영상을 찾아 인페이지 재생용 ID를 반환.

    성공 결과만 캐시한다. 빈 결과(검색 실패)를 캐시하면 일시 오류가 고착된다.
    """
    _ = spotify_id
    a = (artist or "").strip()
    t = (title or "").strip()
    empty = {"youtube_id": "", "youtube_url": "", "preview_url": ""}
    if not t:
        return empty

    cached = _PREVIEW_OK.get((a, t))
    if cached is not None:
        return cached

    yt = _youtube_search(a, t)
    if yt.get("youtube_id"):
        result = {
            "youtube_id": yt["youtube_id"],
            "youtube_url": yt["youtube_url"],
            "preview_url": "",
        }
        if len(_PREVIEW_OK) >= 256:
            _PREVIEW_OK.clear()
        _PREVIEW_OK[(a, t)] = result
        return result
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


def _uri_id(uri: str | None) -> str:
    if not uri:
        return ""
    parts = str(uri).split(":")
    return parts[-1] if parts else ""


def _artist_names(artists: list[dict[str, Any]] | None) -> str:
    if not artists:
        return ""
    return ", ".join(a.get("name") or "" for a in artists if a.get("name"))


def list_chart_regions() -> list[dict[str, Any]]:
    """차트 종류 / 대분류·세부장르 트리."""
    groups = [
        {
            "id": g["id"],
            "label": g["label"],
            "name": g["label"],
            "subgenres": [
                {"id": s["id"], "label": s["label"], "name": s["label"]}
                for s in (g.get("subgenres") or [])
            ],
        }
        for g in _GENRE_GROUPS
    ]
    leaves = [
        {"id": g["id"], "label": g["label"], "name": g["label"], "group_id": g["group_id"]}
        for g in _GENRE_CHART_DEFS
    ]
    return [
        {"id": "genres", "label": "장르별 신곡", "name": "Genre New Tracks"},
        *groups,
        *leaves,
        *[
            {"id": key, "label": meta["label"], "name": meta["name"]}
            for key, meta in _CHART_KINDS.items()
        ],
    ]


def _parse_release_date(value: str | None) -> date | None:
    raw = (value or "").strip()
    if not raw:
        return None
    for fmt, n in (("%Y-%m-%d", 10), ("%Y-%m", 7), ("%Y", 4)):
        try:
            return datetime.strptime(raw[:n], fmt).date()
        except ValueError:
            continue
    return None


def _cache_get(key: str) -> dict[str, Any] | None:
    today_key = date.today().isoformat()
    with _chart_cache_lock:
        cached = _chart_cache.get(key)
        if cached and cached[0] == today_key:
            return cached[1]
    # 디스크 폴백 (Render 프로세스 재시작 후에도 당일 캐시 유지)
    try:
        if _DISK_CACHE_PATH.is_file():
            raw = json.loads(_DISK_CACHE_PATH.read_text(encoding="utf-8"))
            entry = raw.get(key) if isinstance(raw, dict) else None
            if (
                isinstance(entry, dict)
                and entry.get("day") == today_key
                and isinstance(entry.get("payload"), dict)
            ):
                payload = entry["payload"]
                with _chart_cache_lock:
                    _chart_cache[key] = (today_key, payload)
                return payload
    except Exception:
        logger.debug("chart disk cache read failed", exc_info=True)
    return None


def _cache_set(key: str, payload: dict[str, Any]) -> None:
    today_key = date.today().isoformat()
    with _chart_cache_lock:
        _chart_cache[key] = (today_key, payload)
        try:
            _DISK_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            raw: dict[str, Any] = {}
            if _DISK_CACHE_PATH.is_file():
                try:
                    loaded = json.loads(_DISK_CACHE_PATH.read_text(encoding="utf-8"))
                    if isinstance(loaded, dict):
                        raw = loaded
                except Exception:
                    raw = {}
            # 오래된 날짜 항목 정리
            raw = {
                k: v
                for k, v in raw.items()
                if isinstance(v, dict) and v.get("day") == today_key
            }
            raw[key] = {"day": today_key, "payload": payload}
            tmp = _DISK_CACHE_PATH.with_suffix(".tmp")
            tmp.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
            tmp.replace(_DISK_CACHE_PATH)
        except Exception:
            logger.debug("chart disk cache write failed", exc_info=True)


def _search_new_tracks_for_genre(
    sp: Any,
    queries: list[str],
    *,
    limit: int = 10,
    lookback_days: int = 180,
) -> list[dict[str, Any]]:
    """장르 쿼리로 최근 발매곡을 모아 최신·인기 점수로 상위 N곡 반환.

    속도 우선: 쿼리 최대 2개 × offset 0(limit=10) + tracks 보강 1회.
    (이 Spotify 앱은 search limit 최대 10 — 20이면 400 Invalid limit)
    """
    today = date.today()
    y1 = today.year
    y0 = y1 - 1
    cutoff = today - timedelta(days=lookback_days)
    seen: set[str] = set()
    collected: list[dict[str, Any]] = []
    noise_titles = {"pop", "rap", "rock", "latin", "k-pop", "kpop", "r&b", "indie"}
    target = max(limit * 2, 16)

    def _score(released: date, popularity: int) -> float:
        age = max(0, (today - released).days)
        fresh = max(0.0, 1.0 - (age / float(lookback_days)))
        return float(popularity) * (0.30 + 0.70 * fresh) + fresh * 8.0

    def _consume(items: list[dict[str, Any]]) -> None:
        for item in items:
            tid = item.get("id") or ""
            if not tid or tid in seen:
                continue
            album = item.get("album") or {}
            if (album.get("album_type") or "").lower() == "compilation":
                continue
            released = _parse_release_date(album.get("release_date"))
            if released is None or released < cutoff:
                continue
            title = (item.get("name") or "").strip()
            if title.lower() in noise_titles:
                continue
            artists = item.get("artists") or []
            primary = ((artists[0].get("name") if artists else "") or "").strip().lower()
            dedupe_key = f"{title.lower()}|{primary}"
            if dedupe_key in seen:
                continue
            seen.add(tid)
            seen.add(dedupe_key)
            payload = _track_payload(item)
            payload["release_date"] = album.get("release_date") or ""
            payload["_released"] = released
            collected.append(payload)

    for template in queries[:2]:
        q = template.format(y0=y0, y1=y1)
        for offset in (0, 10):
            if len(collected) >= target:
                break
            try:
                data = sp.search(
                    q=q, type="track", limit=10, offset=offset, market="US"
                )
            except Exception:
                continue
            _consume(list((data.get("tracks") or {}).get("items") or []))
        if len(collected) >= target:
            break

    ids = [t["id"] for t in collected if t.get("id")]
    pop_by_id: dict[str, int] = {}
    if ids:
        try:
            detail = sp.tracks(ids[:50], market="US") or {}
            for item in detail.get("tracks") or []:
                if not item:
                    continue
                tid = item.get("id") or ""
                if tid:
                    pop_by_id[tid] = int(item.get("popularity") or 0)
        except Exception:
            pass

    ranked: list[tuple[float, date, dict[str, Any]]] = []
    for track in collected:
        tid = track.get("id") or ""
        if tid in pop_by_id:
            track["popularity"] = pop_by_id[tid]
        released = track.pop("_released", None)
        if not isinstance(released, date):
            released = _parse_release_date(track.get("release_date")) or today
        ranked.append((_score(released, int(track.get("popularity") or 0)), released, track))

    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    out: list[dict[str, Any]] = []
    for i, (_, __, track) in enumerate(ranked[:limit], start=1):
        track = dict(track)
        track["rank"] = i
        track["item_type"] = "track"
        out.append(track)
    return out


def _genre_payload(
    gdef: dict[str, Any],
    tracks: list[dict[str, Any]],
    *,
    today_key: str,
) -> dict[str, Any]:
    group_label = gdef.get("group_label") or gdef["label"]
    sub_label = gdef["label"]
    if sub_label == "전체":
        display = group_label
    else:
        display = f"{group_label} · {sub_label}"
    playlist_name = f"{display} Popular Recent"
    return {
        "region": gdef["id"],
        "region_label": display,
        "group_id": gdef.get("group_id") or gdef["id"],
        "group_label": group_label,
        "playlist_name": playlist_name,
        "playlist_id": f"genre-{gdef['id']}",
        "chart_date": today_key,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "tracks": tracks,
        "genres": [
            {
                "id": gdef["id"],
                "label": gdef["label"],
                "group_id": gdef.get("group_id") or gdef["id"],
                "tracks": tracks,
            }
        ],
    }


def get_single_genre_chart(genre_id: str, limit: int = 10) -> dict[str, Any]:
    """단일 세부장르 차트 (빠름). 장르당 독립 캐시."""
    gdef = next((g for g in _GENRE_CHART_DEFS if g["id"] == genre_id), None)
    if not gdef:
        raise HTTPException(status_code=400, detail="지원하지 않는 장르입니다.")

    capped = max(1, min(int(limit or 10), 20))
    today_key = date.today().isoformat()
    cache_key = f"genre-v10:{gdef['id']}:{capped}"
    cached = _cache_get(cache_key)
    if cached:
        # 빈 차트는 캐시 히트로 고착시키지 않음
        cached_tracks = (cached.get("genres") or [{}])[0].get("tracks") or cached.get("tracks") or []
        if cached_tracks:
            return cached

    sp = _spotify_client()
    tracks = _search_new_tracks_for_genre(
        sp, list(gdef.get("queries") or []), limit=capped, lookback_days=180
    )
    result = _genre_payload(gdef, tracks, today_key=today_key)
    if tracks:
        _cache_set(cache_key, result)
    return result


def get_genre_new_charts(per_genre: int = 10) -> dict[str, Any]:
    """대분류별 '전체' 차트만 병렬 조회 (세부는 탭에서 개별 로드)."""
    capped = max(1, min(int(per_genre or 10), 20))
    today_key = date.today().isoformat()
    cache_key = f"genres-v10:{capped}"
    cached = _cache_get(cache_key)
    if cached:
        genres = cached.get("genres") or []
        if any((g.get("tracks") or []) for g in genres):
            return cached

    # 대분류 대표(전체) leaf만 — id == group_id
    primary_defs = [g for g in _GENRE_CHART_DEFS if g["id"] == g.get("group_id")]
    genres_out: list[dict[str, Any]] = []

    def _one(gdef: dict[str, Any]) -> dict[str, Any]:
        single = get_single_genre_chart(gdef["id"], capped)
        return (single.get("genres") or [{}])[0]

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_one, g): g for g in primary_defs}
        by_id: dict[str, dict[str, Any]] = {}
        for fut in as_completed(futures):
            gdef = futures[fut]
            try:
                by_id[gdef["id"]] = fut.result()
            except Exception as exc:
                logger.warning("genre chart failed %s: %s", gdef["id"], exc)
                by_id[gdef["id"]] = {
                    "id": gdef["id"],
                    "label": gdef["group_label"],
                    "tracks": [],
                }

    for gdef in primary_defs:
        row = by_id.get(gdef["id"]) or {
            "id": gdef["id"],
            "label": gdef["group_label"],
            "tracks": [],
        }
        # UI 대분류 탭용으로 그룹 라벨 노출
        row = {**row, "id": gdef["id"], "label": gdef["group_label"]}
        genres_out.append(row)

    result: dict[str, Any] = {
        "region": "genres",
        "region_label": "장르별 인기",
        "playlist_name": "Genre Popular Recent",
        "playlist_id": "genre-popular-recent",
        "chart_date": today_key,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "tracks": [],
        "genres": genres_out,
        "groups": [
            {
                "id": g["id"],
                "label": g["label"],
                "subgenres": [
                    {"id": s["id"], "label": s["label"]}
                    for s in (g.get("subgenres") or [])
                ],
            }
            for g in _GENRE_GROUPS
        ],
    }
    if any((g.get("tracks") or []) for g in genres_out):
        _cache_set(cache_key, result)
    return result


def get_spotify_charts(region: str = "genres", limit: int = 10) -> dict[str, Any]:
    """홈 차트. genres=전체, pop|dance-house|...=세부장르, songs|albums=주간."""
    raw = (region or "genres").strip().lower()
    capped = min(max(int(limit or 10), 1), 50)

    if raw in {"songs", "song"}:
        return _get_public_weekly_chart("songs", limit=capped)
    if raw in {"albums", "album"}:
        return _get_public_weekly_chart("albums", limit=capped)

    if raw in {"genres", "genre", ""}:
        return get_genre_new_charts(per_genre=min(capped, 20))

    if any(g["id"] == raw for g in _GENRE_CHART_DEFS):
        return get_single_genre_chart(raw, limit=min(capped, 20))

    return get_genre_new_charts(per_genre=min(capped, 20))


def _get_public_weekly_chart(key: str, limit: int = 50) -> dict[str, Any]:
    """Spotify 공개 주간 글로벌 차트 (음반 등)."""
    meta = _CHART_KINDS.get(key)
    if not meta:
        raise HTTPException(status_code=400, detail="지원하지 않는 차트입니다.")

    capped = max(1, min(int(limit or 50), 50))
    today_key = date.today().isoformat()
    cache_key = f"public:{key}:{capped}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    try:
        resp = http_requests.get(
            _SPOTIFY_PUBLIC_CHARTS_URL,
            headers={
                "Accept": "application/json",
                "User-Agent": "WaveMash/1.0 (charts)",
            },
            timeout=12,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Spotify 차트 서버에 연결하지 못했습니다: {exc}",
        ) from exc

    if not resp.ok:
        raise HTTPException(
            status_code=502,
            detail=f"Spotify 차트를 불러오지 못했습니다 (HTTP {resp.status_code})",
        )

    try:
        payload = resp.json()
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail="Spotify 차트 응답을 파싱하지 못했습니다."
        ) from exc

    views = payload.get("chartEntryViewResponses") or []
    view = None
    for candidate in views:
        display = candidate.get("displayChart") or {}
        chart_meta = display.get("chartMetadata") or {}
        if (chart_meta.get("alias") or "") == meta["alias"]:
            view = candidate
            break

    if view is None:
        raise HTTPException(
            status_code=502, detail=f"{meta['name']} 차트를 찾지 못했습니다."
        )

    display = view.get("displayChart") or {}
    chart_date = display.get("date") or today_key
    entries = view.get("entries") or []
    tracks: list[dict[str, Any]] = []

    for entry in entries[:capped]:
        chart_data = entry.get("chartEntryData") or {}
        rank = int(chart_data.get("currentRank") or (len(tracks) + 1))
        prev = chart_data.get("previousRank")
        status = chart_data.get("entryStatus") or ""

        if key == "songs":
            tm = entry.get("trackMetadata") or {}
            track_id = _uri_id(tm.get("trackUri"))
            artists = tm.get("artists") or []
            artist = _artist_names(artists)
            primary = (artists[0].get("name") if artists else "") or ""
            tracks.append(
                {
                    "id": track_id,
                    "title": tm.get("trackName") or "",
                    "artist": artist,
                    "primary_artist": primary,
                    "album": "",
                    "thumbnail_url": tm.get("displayImageUri") or "",
                    "spotify_url": (
                        f"https://open.spotify.com/track/{track_id}" if track_id else ""
                    ),
                    "preview_url": "",
                    "popularity": 0,
                    "duration_ms": 0,
                    "explicit": False,
                    "rank": rank,
                    "previous_rank": prev,
                    "entry_status": status,
                    "item_type": "track",
                }
            )
        else:
            am = entry.get("albumMetadata") or {}
            album_id = _uri_id(am.get("albumUri"))
            artists = am.get("artists") or []
            artist = _artist_names(artists)
            primary = (artists[0].get("name") if artists else "") or ""
            tracks.append(
                {
                    "id": album_id,
                    "title": am.get("albumName") or "",
                    "artist": artist,
                    "primary_artist": primary,
                    "album": am.get("albumName") or "",
                    "thumbnail_url": am.get("displayImageUri") or "",
                    "spotify_url": (
                        f"https://open.spotify.com/album/{album_id}" if album_id else ""
                    ),
                    "preview_url": "",
                    "popularity": 0,
                    "duration_ms": 0,
                    "explicit": False,
                    "rank": rank,
                    "previous_rank": prev,
                    "entry_status": status,
                    "item_type": "album",
                }
            )

    result: dict[str, Any] = {
        "region": key,
        "region_label": meta["label"],
        "playlist_name": meta["name"],
        "playlist_id": meta["alias"],
        "chart_date": chart_date,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "tracks": tracks,
        "genres": [],
    }
    _cache_set(cache_key, result)
    return result
