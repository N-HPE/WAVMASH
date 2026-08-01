"""Spotify client bootstrap for spotdl — used only on Spotify URL download / library repair."""

from __future__ import annotations

import re
import time
from typing import Any

from env_loader import ensure_env_loaded

_SPOTIFY_TRACK_RE = re.compile(
    r"(?:open\.)?spotify\.com/track/([a-zA-Z0-9]+)",
    re.IGNORECASE,
)
_RATE_LIMIT_COOLDOWN_SEC = 300

_client_ready = False
_api_blocked_until = 0.0


def spotify_track_id(url: str | None) -> str | None:
    if not url:
        return None
    match = _SPOTIFY_TRACK_RE.search(url.strip())
    return match.group(1) if match else None


def _user_spotify_credentials() -> tuple[str, str]:
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
    return client_id, client_secret


def _free_client_options() -> dict[str, Any]:
    from spotdl.utils.config import SPOTIFY_OPTIONS

    opts = dict(SPOTIFY_OPTIONS)
    opts["use_official_api"] = False
    opts["max_retries"] = 3
    return opts


def spotify_client_options(*, prefer_free: bool = False) -> dict[str, Any]:
    """Build spotdl SpotifyClient options.

    - Own SPOTIFY_CLIENT_ID/SECRET in .env → official Web API (your quota).
    - ``prefer_free=True`` or no credentials → spotdl SpotipyFree default.
    """
    if prefer_free:
        return _free_client_options()

    client_id, client_secret = _user_spotify_credentials()
    if client_id and client_secret:
        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "use_official_api": True,
            "headless": True,
            "max_retries": 3,
            "no_cache": False,
        }

    return _free_client_options()


def reset_spotify_client() -> None:
    """Allow re-initializing the spotdl Spotify client (e.g. after rate limit)."""
    global _client_ready
    try:
        from spotdl.utils.spotify import SpotifyClient

        SpotifyClient._instance = None  # type: ignore[attr-defined]
        SpotifyClient._use_official_api = False  # type: ignore[attr-defined]
    except Exception:
        pass
    _client_ready = False


def init_spotify_client(*, force: bool = False, prefer_free: bool = False) -> bool:
    """Initialize spotdl's Spotify client. Call only for Spotify download/repair paths."""
    global _client_ready
    if _client_ready and not force and not prefer_free:
        return True
    if spotify_api_blocked() and not prefer_free:
        prefer_free = True
    if force or prefer_free:
        reset_spotify_client()
    try:
        from spotdl.utils.spotify import SpotifyClient

        opts = spotify_client_options(prefer_free=prefer_free)
        SpotifyClient.init(**opts)
        _client_ready = True
        return True
    except Exception as exc:
        try:
            print(f"[Spotify] client init failed: {exc}")
        except UnicodeEncodeError:
            pass
        _client_ready = False
        return False


def reset_spotify_rate_limit() -> None:
    global _api_blocked_until
    _api_blocked_until = 0.0
    reset_spotify_client()


def mark_rate_limited() -> None:
    global _api_blocked_until
    _api_blocked_until = time.time() + _RATE_LIMIT_COOLDOWN_SEC
    reset_spotify_client()
    try:
        print("[Spotify] rate limit — pausing Spotify downloads for 5 minutes")
    except UnicodeEncodeError:
        pass


def spotify_api_blocked() -> bool:
    return time.time() < _api_blocked_until
