"""Spotify catalog search — artists, tracks, albums, and artist pages."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

import requests as http_requests
from fastapi import HTTPException

from spotify_metadata import _user_spotify_credentials

# Spotify Charts 공개 엔드포인트 (음반 차트 등 보조)
_SPOTIFY_PUBLIC_CHARTS_URL = (
    "https://charts-spotify-com-service.spotify.com/public/v0/charts"
)
# 장르 신곡 차트는 하루 1회(날짜 키)만 갱신
_chart_cache: dict[str, tuple[str, dict[str, Any]]] = {}

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

# 장르별 신곡 검색 쿼리 (Spotify search). genre: 필터가 빈 결과를 내는
# 장르는 키워드+연도 검색으로 폴백합니다.
_GENRE_CHART_DEFS: list[dict[str, Any]] = [
    {
        "id": "pop",
        "label": "팝",
        "queries": ["genre:pop year:{y0}-{y1}", "pop year:{y1}"],
    },
    {
        "id": "hiphop",
        "label": "힙합",
        "queries": [
            "hip hop year:{y1}",
            "rap year:{y1}",
            "hip hop year:{y0}",
            "rap year:{y0}",
        ],
    },
    {
        "id": "rnb",
        "label": "R&B",
        "queries": [
            "r&b year:{y1}",
            "r&b year:{y0}",
            "genre:soul year:{y0}-{y1}",
        ],
    },
    {
        "id": "dance",
        "label": "댄스",
        "queries": [
            "genre:dance year:{y0}-{y1}",
            "genre:electronic year:{y0}-{y1}",
            "dance pop year:{y1}",
        ],
    },
    {
        "id": "rock",
        "label": "록",
        "queries": ["genre:rock year:{y0}-{y1}", "rock year:{y1}"],
    },
    {
        "id": "indie",
        "label": "인디",
        "queries": ["genre:indie year:{y0}-{y1}", "indie year:{y1}"],
    },
    {
        "id": "latin",
        "label": "라틴",
        "queries": ["genre:latin year:{y0}-{y1}", "latin year:{y1}"],
    },
    {
        "id": "kpop",
        "label": "K-pop",
        "queries": ["k-pop year:{y1}", "k-pop year:{y0}", "kpop year:{y1}"],
    },
]


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


def list_chart_regions() -> list[dict[str, str]]:
    """차트 종류 / 장르 목록."""
    genres = [
        {"id": g["id"], "label": g["label"], "name": g["label"]}
        for g in _GENRE_CHART_DEFS
    ]
    return [
        {"id": "genres", "label": "장르별 신곡", "name": "Genre New Tracks"},
        *genres,
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


def _search_new_tracks_for_genre(
    sp: Any,
    queries: list[str],
    *,
    limit: int = 10,
    lookback_days: int = 540,
) -> list[dict[str, Any]]:
    """장르 쿼리로 최근 발매곡을 모아 신곡 순으로 상위 N곡 반환."""
    today = date.today()
    y1 = today.year
    y0 = y1 - 1
    cutoff = today - timedelta(days=lookback_days)
    seen: set[str] = set()
    collected: list[tuple[date, dict[str, Any]]] = []
    noise_titles = {"pop", "rap", "rock", "latin", "k-pop", "kpop", "r&b", "indie"}

    def _consume(items: list[dict[str, Any]]) -> None:
        for item in items:
            tid = item.get("id") or ""
            if not tid or tid in seen:
                continue
            album = item.get("album") or {}
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
            collected.append((released, payload))

    for template in queries:
        q = template.format(y0=y0, y1=y1)
        for offset in (0, 10):
            try:
                data = sp.search(
                    q=q, type="track", limit=10, offset=offset, market="US"
                )
            except Exception:
                break
            _consume(list((data.get("tracks") or {}).get("items") or []))
            if len(collected) >= limit * 3:
                break
        if len(collected) >= limit * 3:
            break

    collected.sort(key=lambda pair: pair[0], reverse=True)
    out: list[dict[str, Any]] = []
    for i, (_, track) in enumerate(collected[:limit], start=1):
        track = dict(track)
        track["rank"] = i
        track["item_type"] = "track"
        out.append(track)
    return out


def get_genre_new_charts(per_genre: int = 10) -> dict[str, Any]:
    """장르별 최근 신곡 Top N (하루 1회 캐시)."""
    capped = max(1, min(int(per_genre or 10), 20))
    today_key = date.today().isoformat()
    cache_key = f"genres:{capped}"
    cached = _chart_cache.get(cache_key)
    if cached and cached[0] == today_key:
        return cached[1]

    sp = _spotify_client()
    genres_out: list[dict[str, Any]] = []
    for gdef in _GENRE_CHART_DEFS:
        tracks = _search_new_tracks_for_genre(
            sp, list(gdef["queries"]), limit=capped
        )
        genres_out.append(
            {
                "id": gdef["id"],
                "label": gdef["label"],
                "tracks": tracks,
            }
        )

    result: dict[str, Any] = {
        "region": "genres",
        "region_label": "장르별 신곡",
        "playlist_name": "Genre New Tracks",
        "playlist_id": "genre-new",
        "chart_date": today_key,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "tracks": [],
        "genres": genres_out,
    }
    _chart_cache[cache_key] = (today_key, result)
    return result


def get_spotify_charts(region: str = "genres", limit: int = 10) -> dict[str, Any]:
    """홈 차트. genres=장르별 신곡, songs|albums=주간 글로벌 차트."""
    raw = (region or "genres").strip().lower()
    capped = min(max(int(limit or 10), 1), 50)

    if raw in {"songs", "song"}:
        return _get_public_weekly_chart("songs", limit=capped)
    if raw in {"albums", "album"}:
        return _get_public_weekly_chart("albums", limit=capped)

    if raw in {"genres", "genre", ""}:
        return get_genre_new_charts(per_genre=min(capped, 20))

    for gdef in _GENRE_CHART_DEFS:
        if gdef["id"] == raw:
            full = get_genre_new_charts(per_genre=min(capped, 20))
            matched = next(
                (g for g in full["genres"] if g["id"] == raw),
                {"id": raw, "label": gdef["label"], "tracks": []},
            )
            return {
                **full,
                "region": raw,
                "region_label": gdef["label"],
                "tracks": matched.get("tracks") or [],
                "genres": [matched],
            }

    return get_genre_new_charts(per_genre=min(capped, 20))


def _get_public_weekly_chart(key: str, limit: int = 50) -> dict[str, Any]:
    """Spotify 공개 주간 글로벌 차트 (음반 등)."""
    meta = _CHART_KINDS.get(key)
    if not meta:
        raise HTTPException(status_code=400, detail="지원하지 않는 차트입니다.")

    capped = max(1, min(int(limit or 50), 50))
    today_key = date.today().isoformat()
    cache_key = f"public:{key}:{capped}"
    cached = _chart_cache.get(cache_key)
    if cached and cached[0] == today_key:
        return cached[1]

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
    _chart_cache[cache_key] = (today_key, result)
    return result
