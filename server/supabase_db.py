"""WaveMash Supabase Database Client.

Provides seamless cloud database integration with Supabase for WAVMASH.
When SUPABASE_URL and SUPABASE_KEY are set in environment variables,
this client interacts with Supabase PostgreSQL (PostgREST).
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import requests

logger = logging.getLogger("wavemash.supabase")

_SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
_SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY", "")


def is_supabase_enabled() -> bool:
    """Returns True if Supabase credentials are configured."""
    return bool(_SUPABASE_URL and _SUPABASE_KEY)


def get_headers() -> dict[str, str]:
    """Returns Supabase request headers."""
    return {
        "apikey": _SUPABASE_KEY,
        "Authorization": f"Bearer {_SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


# ---------------------------------------------------------------------------
# Tracks Operations
# ---------------------------------------------------------------------------

def fetch_tracks_from_supabase(
    *,
    search: str | None = None,
    genre: str | None = None,
    platform: str | None = None,
    bpm_min: int | None = None,
    bpm_max: int | None = None,
    key: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[dict[str, Any]], int]:
    """Fetch tracks from Supabase with filtering, sorting, and pagination."""
    if not is_supabase_enabled():
        return [], 0

    url = f"{_SUPABASE_URL}/rest/v1/tracks"
    headers = get_headers()
    headers["Prefer"] = "count=exact"

    params: dict[str, str] = {
        "offset": str(skip),
        "limit": str(limit),
    }

    # Sorting
    order_col = sort_by if sort_by in ("created_at", "title", "artist", "album", "bpm_num", "year") else "created_at"
    order_dir = "desc" if sort_order.lower() == "desc" else "asc"
    params["order"] = f"{order_col}.{order_dir}"

    # Filters
    if genre and genre.lower() != "all":
        params["genre"] = f"ilike.%{genre}%"
    if platform and platform.lower() != "all":
        params["platform"] = f"ilike.%{platform}%"
    if key and key.lower() != "all":
        params["or"] = f"(key.ilike.%{key}%,camelot_key.ilike.%{key}%)"
    if bpm_min is not None:
        params["bpm_num"] = f"gte.{bpm_min}"
    if bpm_max is not None:
        if "bpm_num" in params:
            params["bpm_num"] += f",lte.{bpm_max}"
        else:
            params["bpm_num"] = f"lte.{bpm_max}"
    if search:
        s = search.strip()
        params["or"] = f"(title.ilike.%{s}%,artist.ilike.%{s}%,album.ilike.%{s}%,genre.ilike.%{s}%)"

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()

        # Extract total count from Content-Range header (e.g. 0-49/120)
        total = 0
        cr = resp.headers.get("Content-Range", "")
        if "/" in cr:
            try:
                total = int(cr.split("/")[-1])
            except ValueError:
                total = len(resp.json())
        else:
            total = len(resp.json())

        return resp.json(), total
    except Exception as e:
        logger.error(f"Supabase fetch_tracks error: {e}")
        return [], 0


def get_track_from_supabase(track_id: str) -> dict[str, Any] | None:
    """Fetch single track by track_id."""
    if not is_supabase_enabled():
        return None

    url = f"{_SUPABASE_URL}/rest/v1/tracks"
    headers = get_headers()
    params = {"track_id": f"eq.{track_id}", "limit": "1"}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        resp.raise_for_status()
        items = resp.json()
        return items[0] if items else None
    except Exception as e:
        logger.error(f"Supabase get_track error: {e}")
        return None


def upsert_track_to_supabase(record: dict[str, Any]) -> bool:
    """Upsert a single track record into Supabase."""
    if not is_supabase_enabled():
        return False

    url = f"{_SUPABASE_URL}/rest/v1/tracks"
    headers = get_headers()
    headers["Prefer"] = "resolution=merge-duplicates"

    track_id = str(record.get("track_id") or record.get("id") or "")
    if not track_id:
        return False

    payload = {
        "track_id": track_id,
        "title": str(record.get("title") or ""),
        "artist": str(record.get("artist") or ""),
        "primary_artist": str(record.get("primary_artist") or record.get("artist") or ""),
        "album": str(record.get("album") or ""),
        "genre": str(record.get("genre") or "Unknown"),
        "year": str(record.get("year") or ""),
        "bpm": str(record.get("bpm") or ""),
        "key": str(record.get("key") or ""),
        "camelot_key": str(record.get("camelot_key") or record.get("camelot") or ""),
        "energy_level": int(record.get("energy_level") or 0),
        "bpm_source": str(record.get("bpm_source") or ""),
        "platform": str(record.get("platform") or "Spotify"),
        "format": str(record.get("format") or "WAV"),
        "url": str(record.get("url") or ""),
        "external_id": str(record.get("external_id") or ""),
        "thumbnail_url": str(record.get("thumbnail_url") or ""),
        "local_path": str(record.get("local_path") or record.get("path") or ""),
        "has_cover": bool(record.get("has_cover", False)),
        "has_file": bool(record.get("has_file", False)),
        "dominant_color": record.get("dominant_color"),
        "analysis": record.get("analysis") if isinstance(record.get("analysis"), dict) else {},
        "mix_data": record.get("mix_data") if isinstance(record.get("mix_data"), dict) else {},
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        return resp.status_code in (200, 201, 204)
    except Exception as e:
        logger.error(f"Supabase upsert_track error: {e}")
        return False


def delete_track_from_supabase(track_id: str) -> bool:
    """Delete a track from Supabase."""
    if not is_supabase_enabled():
        return False

    url = f"{_SUPABASE_URL}/rest/v1/tracks"
    headers = get_headers()
    params = {"track_id": f"eq.{track_id}"}

    try:
        resp = requests.delete(url, headers=headers, params=params, timeout=5)
        return resp.status_code in (200, 204)
    except Exception as e:
        logger.error(f"Supabase delete_track error: {e}")
        return False


# ---------------------------------------------------------------------------
# Playlists Operations
# ---------------------------------------------------------------------------

def fetch_playlists_from_supabase() -> dict[str, Any]:
    """Fetch all playlists with their ordered track_ids and metadata."""
    if not is_supabase_enabled():
        return {"playlists": {}, "activity": {}, "meta": {}}

    pl_url = f"{_SUPABASE_URL}/rest/v1/playlists?order=created_at.asc"
    tr_url = f"{_SUPABASE_URL}/rest/v1/playlist_tracks?order=position.asc"
    headers = get_headers()

    try:
        pl_resp = requests.get(pl_url, headers=headers, timeout=10)
        tr_resp = requests.get(tr_url, headers=headers, timeout=10)
        pl_resp.raise_for_status()
        tr_resp.raise_for_status()

        playlists_data = pl_resp.json()
        tracks_data = tr_resp.json()

        playlists: dict[str, list[str]] = {}
        activity: dict[str, float] = {}
        meta: dict[str, dict[str, Any]] = {}

        for p in playlists_data:
            name = p.get("name")
            if not name:
                continue
            playlists[name] = []
            activity[name] = float(p.get("activity") or time.time())
            m = p.get("meta") or {}
            m["vibe"] = p.get("vibe", "other")
            m["shade"] = p.get("shade", 0)
            m["color"] = p.get("color", "#6D4C41")
            m["source"] = p.get("source", "local")
            m["spotify_url"] = p.get("spotify_url")
            m["sync_id"] = p.get("sync_id")
            m["sync_auto"] = p.get("sync_auto")
            m["sync_status"] = p.get("sync_status")
            meta[name] = m

        for t in tracks_data:
            p_name = t.get("playlist_name")
            t_id = t.get("track_id")
            if p_name in playlists and t_id:
                playlists[p_name].append(t_id)

        return {"playlists": playlists, "activity": activity, "meta": meta}
    except Exception as e:
        logger.error(f"Supabase fetch_playlists error: {e}")
        return {"playlists": {}, "activity": {}, "meta": {}}


def upsert_playlist_to_supabase(
    name: str,
    track_ids: list[str],
    meta: dict[str, Any],
    activity_ts: float | None = None,
) -> bool:
    """Upsert playlist and its tracks into Supabase."""
    if not is_supabase_enabled():
        return False

    pl_url = f"{_SUPABASE_URL}/rest/v1/playlists"
    tr_url = f"{_SUPABASE_URL}/rest/v1/playlist_tracks"
    headers = get_headers()
    headers["Prefer"] = "resolution=merge-duplicates"

    pl_payload = {
        "name": name,
        "vibe": meta.get("vibe", "other"),
        "shade": int(meta.get("shade", 0)),
        "color": meta.get("color", "#6D4C41"),
        "source": meta.get("source", "local"),
        "spotify_url": meta.get("spotify_url"),
        "sync_id": meta.get("sync_id"),
        "sync_auto": meta.get("sync_auto"),
        "sync_status": meta.get("sync_status"),
        "activity": activity_ts or time.time(),
        "meta": meta,
    }

    try:
        # 1. Upsert playlist record
        resp = requests.post(pl_url, headers=headers, json=pl_payload, timeout=10)
        if resp.status_code not in (200, 201, 204):
            return False

        # 2. Refresh playlist_tracks (delete old and insert new)
        del_headers = get_headers()
        requests.delete(tr_url, headers=del_headers, params={"playlist_name": f"eq.{name}"}, timeout=10)

        if track_ids:
            tracks_payload = [
                {"playlist_name": name, "track_id": tid, "position": idx}
                for idx, tid in enumerate(track_ids)
                if tid
            ]
            requests.post(tr_url, headers=headers, json=tracks_payload, timeout=15)

        return True
    except Exception as e:
        logger.error(f"Supabase upsert_playlist error: {e}")
        return False


def delete_playlist_from_supabase(name: str) -> bool:
    """Delete playlist from Supabase (cascades to playlist_tracks)."""
    if not is_supabase_enabled():
        return False

    pl_url = f"{_SUPABASE_URL}/rest/v1/playlists"
    headers = get_headers()

    try:
        resp = requests.delete(pl_url, headers=headers, params={"name": f"eq.{name}"}, timeout=5)
        return resp.status_code in (200, 204)
    except Exception as e:
        logger.error(f"Supabase delete_playlist error: {e}")
        return False
