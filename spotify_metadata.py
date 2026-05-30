"""Spotify Web API — fast BPM/Key lookup (audio_features only, no long retries)."""

from __future__ import annotations

import difflib
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Any

from env_loader import ensure_env_loaded
from library import UNKNOWN, normalize_artist_meta

PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_CAMELOT = {
    "B Major": "1B", "F# Major": "2B", "C# Major": "3B", "G# Major": "4B",
    "D# Major": "5B", "A# Major": "6B", "F Major": "7B", "C Major": "8B",
    "G Major": "9B", "D Major": "10B", "A Major": "11B", "E Major": "12B",
    "G# Minor": "1A", "D# Minor": "2A", "A# Minor": "3A", "F Minor": "4A",
    "C Minor": "5A", "G Minor": "6A", "D Minor": "7A", "A Minor": "8A",
    "E Minor": "9A", "B Minor": "10A", "F# Minor": "11A", "C# Minor": "12A",
}

_SPOTIFY_TRACK_RE = re.compile(
    r"(?:open\.)?spotify\.com/track/([a-zA-Z0-9]+)",
    re.IGNORECASE,
)
_SPOTIFY_ID_RE = re.compile(r"^[A-Za-z0-9]{22}$")
_API_TIMEOUT_SEC = 12
_SEARCH_TIMEOUT_SEC = 10
_RATE_LIMIT_COOLDOWN_SEC = 300

_client_ready = False
_token_cache: dict[str, Any] = {"token": "", "expires": 0.0}
_api_blocked_until = 0.0


def _camelot(key: str) -> str:
    return _CAMELOT.get(key, "")


def spotify_track_id(url: str | None) -> str | None:
    if not url:
        return None
    m = _SPOTIFY_TRACK_RE.search(url.strip())
    return m.group(1) if m else None


def spotify_client_options() -> dict[str, Any]:
    ensure_env_loaded()
    import os

    client_id = (
        os.environ.get("SPOTIFY_CLIENT_ID", "").strip()
        or os.environ.get("SPOTIPY_CLIENT_ID", "").strip()
    )
    client_secret = (
        os.environ.get("SPOTIFY_CLIENT_SECRET", "").strip()
        or os.environ.get("SPOTIPY_CLIENT_SECRET", "").strip()
    )
    if client_id and client_secret:
        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "use_official_api": True,
            "headless": True,
            "max_retries": 0,
            "no_cache": True,
        }
    from spotdl.utils.config import SPOTIFY_OPTIONS

    opts = dict(SPOTIFY_OPTIONS)
    opts["max_retries"] = 0
    return opts


def init_spotify_client(*, force: bool = False) -> bool:
    global _client_ready
    if _client_ready and not force:
        return True
    if _spotify_api_blocked():
        return False
    try:
        from spotdl.utils.spotify import SpotifyClient

        opts = spotify_client_options()
        opts["use_official_api"] = True
        SpotifyClient.init(**opts)
        _client_ready = True
        return True
    except Exception as exc:
        print(f"[Spotify] client init failed: {exc}")
        _client_ready = False
        return False


def reset_spotify_rate_limit() -> None:
    global _api_blocked_until, _token_cache
    _api_blocked_until = 0.0
    _token_cache = {"token": "", "expires": 0.0}


def _mark_rate_limited() -> None:
    global _api_blocked_until
    _api_blocked_until = time.time() + _RATE_LIMIT_COOLDOWN_SEC
    print("[Spotify] rate limit — BPM/Key 조회 5분간 건너뜀")


def _spotify_api_blocked() -> bool:
    return time.time() < _api_blocked_until


def _credentials() -> tuple[str, str]:
    opts = spotify_client_options()
    return str(opts.get("client_id") or ""), str(opts.get("client_secret") or "")


def _get_access_token() -> str | None:
    if _spotify_api_blocked():
        return None
    if _token_cache["token"] and time.time() < float(_token_cache["expires"]) - 30:
        return str(_token_cache["token"])

    client_id, client_secret = _credentials()
    if not client_id or not client_secret:
        return None

    try:
        import requests

        resp = requests.post(
            "https://accounts.spotify.com/api/token",
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            timeout=_API_TIMEOUT_SEC,
        )
        if resp.status_code == 429:
            _mark_rate_limited()
            return None
        if resp.status_code != 200:
            print(f"[Spotify] token HTTP {resp.status_code}")
            return None
        payload = resp.json()
        token = str(payload.get("access_token") or "")
        if not token:
            return None
        _token_cache["token"] = token
        _token_cache["expires"] = time.time() + int(payload.get("expires_in") or 3600)
        return token
    except Exception as exc:
        print(f"[Spotify] token error: {exc}")
        return None


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def _match_score(artist: str, title: str, cand_artist: str, cand_title: str) -> float:
    ta, tt = _norm(artist), _norm(title)
    ca, ct = _norm(cand_artist), _norm(cand_title)
    if not tt:
        return 0.0
    title_ratio = difflib.SequenceMatcher(None, tt, ct).ratio() if ct else 0.0
    artist_ratio = difflib.SequenceMatcher(None, ta, ca).ratio() if ca and ta else 0.0
    return 0.65 * title_ratio + 0.35 * artist_ratio


def _search_spotify_track_id_impl(artist: str, title: str) -> str | None:
    if not init_spotify_client():
        return None
    from spotdl.utils.search import get_search_results

    query = f"{artist} - {title}".strip(" -")
    best_id = None
    best_score = 0.58
    for song in get_search_results(query)[:8]:
        score = _match_score(artist, title, song.artist or "", song.name or "")
        if score > best_score:
            best_score = score
            best_id = str(song.song_id)
    return best_id


def search_spotify_track_id(artist: str, title: str) -> str | None:
    if not artist or not title or artist == UNKNOWN or title == UNKNOWN:
        return None
    if _spotify_api_blocked():
        return None
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_search_spotify_track_id_impl, artist, title)
            return future.result(timeout=_SEARCH_TIMEOUT_SEC)
    except FuturesTimeout:
        print("[Spotify] search timeout — BPM/Key 건너뜀")
        return None
    except Exception as exc:
        print(f"[Spotify] search failed: {exc}")
        return None


def _key_from_features(key_idx: int, mode: int) -> str:
    if key_idx is None or int(key_idx) < 0:
        return UNKNOWN
    pitch = PITCH_CLASSES[int(key_idx) % 12]
    scale = "Major" if int(mode) == 1 else "Minor"
    return f"{pitch} {scale}"


def _features_from_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    tempo = float(row.get("tempo") or 0)
    if tempo <= 0:
        return None
    key = _key_from_features(row.get("key", -1), row.get("mode", 0))
    return {
        "bpm": int(round(tempo)),
        "key": key,
        "camelot": _camelot(key),
        "source": "spotify",
    }


def fetch_audio_features(track_id: str) -> dict[str, Any] | None:
    return fetch_audio_features_batch([track_id]).get(track_id)


def fetch_audio_features_batch(track_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Direct HTTP audio-features — no spotipy 86400s retry loop."""
    ids = [tid for tid in dict.fromkeys(track_ids) if tid and _SPOTIFY_ID_RE.match(tid)]
    if not ids or _spotify_api_blocked():
        return {}

    token = _get_access_token()
    if not token:
        return {}

    import requests

    out: dict[str, dict[str, Any]] = {}
    headers = {"Authorization": f"Bearer {token}"}

    for start in range(0, len(ids), 100):
        chunk = ids[start : start + 100]
        params = {"ids": ",".join(chunk)}
        try:
            resp = requests.get(
                "https://api.spotify.com/v1/audio-features",
                headers=headers,
                params=params,
                timeout=_API_TIMEOUT_SEC,
            )
        except requests.Timeout:
            print("[Spotify] audio-features timeout")
            break
        except Exception as exc:
            print(f"[Spotify] audio-features error: {exc}")
            break

        if resp.status_code == 429:
            _mark_rate_limited()
            break
        if resp.status_code == 401:
            _token_cache["token"] = ""
            _token_cache["expires"] = 0.0
            token = _get_access_token()
            if not token:
                break
            headers["Authorization"] = f"Bearer {token}"
            continue
        if resp.status_code != 200:
            print(f"[Spotify] audio-features HTTP {resp.status_code}")
            break

        for row in resp.json().get("audio_features") or []:
            if not isinstance(row, dict):
                continue
            tid = str(row.get("id") or "")
            parsed = _features_from_row(row)
            if tid and parsed:
                out[tid] = parsed

    return out


def resolve_track_id(meta: dict[str, Any], *, allow_search: bool = True) -> str | None:
    tid = spotify_track_id(str(meta.get("url") or ""))
    if tid:
        return tid
    rid = str(meta.get("id") or "")
    if _SPOTIFY_ID_RE.match(rid):
        return rid
    if allow_search and not _spotify_api_blocked():
        return search_spotify_track_id(
            str(meta.get("artist") or ""),
            str(meta.get("title") or ""),
        )
    return None


def lookup_bpm_key_for_meta(
    meta: dict[str, Any],
    *,
    features_cache: dict[str, dict[str, Any]] | None = None,
    allow_search: bool = True,
) -> tuple[dict[str, Any], int | str, str]:
    meta = dict(meta or {})
    track_id = resolve_track_id(meta, allow_search=allow_search)

    if track_id and not spotify_track_id(str(meta.get("url") or "")):
        meta["id"] = track_id
        meta["url"] = f"https://open.spotify.com/track/{track_id}"

    bpm: int | str = meta.get("bpm") or 0
    key = str(meta.get("key") or UNKNOWN)

    feat = None
    if track_id:
        if features_cache is not None:
            feat = features_cache.get(track_id)
        elif not _spotify_api_blocked():
            feat = fetch_audio_features(track_id)

    if feat:
        bpm = feat.get("bpm") or bpm
        if feat.get("key") and feat["key"] != UNKNOWN:
            key = feat["key"]

    return normalize_artist_meta(meta), bpm, key


def enrich_from_spotify(
    meta: dict[str, Any],
    *,
    fallback_bpm: int | str | None = None,
    fallback_key: str | None = None,
    features_cache: dict[str, dict[str, Any]] | None = None,
    allow_search: bool = True,
) -> tuple[dict[str, Any], int | str, str, None, None]:
    meta = dict(meta or {})
    if fallback_bpm:
        meta.setdefault("bpm", fallback_bpm)
    if fallback_key:
        meta.setdefault("key", fallback_key)
    meta, bpm, key = lookup_bpm_key_for_meta(
        meta,
        features_cache=features_cache,
        allow_search=allow_search,
    )
    return meta, bpm, key, None, None


def hints_for_url(spotify_url: str | None) -> tuple[float | None, str | None]:
    tid = spotify_track_id(spotify_url)
    if not tid:
        return None, None
    meta = fetch_audio_features(tid)
    if not meta:
        return None, None
    bpm = meta.get("bpm") or 0
    key = meta.get("key")
    return (float(bpm) if bpm else None), (str(key) if key else None)
