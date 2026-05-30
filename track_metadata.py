"""BPM/key lookup — GetSongBPM database first, local WAV analysis as fallback."""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from typing import Any

from library import UNKNOWN

_GETSONGBPM_KEY = os.environ.get("GETSONGBPM_API_KEY", "").strip()
# Minimum artist/title similarity before trusting a GetSongBPM hit.
_GETSONGBPM_MIN_SCORE = 0.70
_PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_CAMELOT = {
    "B Major": "1B", "F# Major": "2B", "C# Major": "3B", "G# Major": "4B",
    "D# Major": "5B", "A# Major": "6B", "F Major": "7B", "C Major": "8B",
    "G Major": "9B", "D Major": "10B", "A Major": "11B", "E Major": "12B",
    "G# Minor": "1A", "D# Minor": "2A", "A# Minor": "3A", "F Minor": "4A",
    "C Minor": "5A", "G Minor": "6A", "D Minor": "7A", "A Minor": "8A",
    "E Minor": "9A", "B Minor": "10A", "F# Minor": "11A", "C# Minor": "12A",
}


def _camelot(key: str) -> str:
    return _CAMELOT.get(key, "")


def _match_score(artist: str, title: str, cand_artist: str, cand_title: str) -> float:
    import difflib

    def norm(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", (text or "").lower())

    ta, tt = norm(artist), norm(title)
    ca, ct = norm(cand_artist), norm(cand_title)
    if not tt:
        return 0.0
    title_ratio = difflib.SequenceMatcher(None, tt, ct).ratio() if ct else 0.0
    artist_ratio = difflib.SequenceMatcher(None, ta, ca).ratio() if ca and ta else 0.0
    return 0.65 * title_ratio + 0.35 * artist_ratio


def _key_from_getsongbpm(key_of: object, mode: object) -> str | None:
    try:
        idx = int(key_of) % 12
        pitch = _PITCH_CLASSES[idx]
        scale = "Major" if int(mode) == 1 else "Minor"
        return f"{pitch} {scale}"
    except (TypeError, ValueError):
        return None


def lookup_getsongbpm_only(artist: str, title: str) -> dict[str, Any] | None:
    if not _GETSONGBPM_KEY or not artist or not title:
        return None
    lookup = urllib.parse.quote(f"song:{title} artist:{artist}")
    url = (
        f"https://api.getsongbpm.com/search/?api_key={_GETSONGBPM_KEY}"
        f"&type=both&lookup={lookup}&limit=5"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "WaveMash/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:
        print(f"[Track metadata] GetSongBPM: {exc}")
        return None

    songs = data.get("search") or []
    if isinstance(songs, dict):
        songs = [songs]
    best = None
    best_score = _GETSONGBPM_MIN_SCORE
    for item in songs:
        if not isinstance(item, dict):
            continue
        cand_artist = item.get("artist")
        if isinstance(cand_artist, dict):
            cand_artist = cand_artist.get("name")
        score = _match_score(
            artist,
            title,
            str(cand_artist or ""),
            str(item.get("song_title") or item.get("title") or ""),
        )
        if score > best_score:
            best_score = score
            best = item
    if not best:
        return None

    try:
        bpm = int(round(float(best.get("tempo"))))
    except (TypeError, ValueError):
        return None
    if bpm <= 0:
        return None

    key = _key_from_getsongbpm(best.get("key_of"), best.get("mode")) or UNKNOWN
    return {
        "bpm": bpm,
        "key": key,
        "camelot": _camelot(key) if key != UNKNOWN else "",
        "source": "getsongbpm",
        "match_score": round(best_score, 3),
    }


def _analyze_local_bpm_key(path: str) -> dict[str, Any] | None:
    if not path or not os.path.isfile(path):
        return None
    try:
        from desktop_app.analysis import analyze_bpm_key

        local = analyze_bpm_key(path)
        bpm = int(local.get("bpm") or 0)
        key = str(local.get("key") or UNKNOWN)
        if bpm <= 0 and (not key or key == UNKNOWN):
            return None
        return {
            "bpm": bpm,
            "key": key,
            "camelot": local.get("camelot") or _camelot(key),
            "source": "local",
            "key_confidence": local.get("key_confidence"),
            "backends": local.get("backends"),
        }
    except Exception as exc:
        print(f"[Track metadata] local analysis: {exc}")
        return None


def resolve_bpm_key_for_track(
    path: str,
    artist: str,
    title: str,
) -> dict[str, Any]:
    """GetSongBPM (curated DB) first, then local WAV analysis for gaps/no match."""
    bpm = 0
    key = UNKNOWN
    source = ""

    db = lookup_getsongbpm_only(artist, title)
    if db:
        bpm = int(db.get("bpm") or 0)
        key = str(db.get("key") or UNKNOWN)
        source = str(db.get("source") or "getsongbpm")

    bpm_missing = bpm <= 0
    key_missing = not key or key == UNKNOWN
    if bpm_missing or key_missing:
        local = _analyze_local_bpm_key(path)
        if local:
            if bpm_missing and local.get("bpm"):
                bpm = int(local["bpm"])
            if key_missing and local.get("key") and local["key"] != UNKNOWN:
                key = str(local["key"])
            local_src = str(local.get("source") or "local")
            source = local_src if not source else f"{source}+{local_src}"

    return {
        "bpm": bpm,
        "key": key,
        "camelot": _camelot(key) if key != UNKNOWN else "",
        "source": source,
    }


def lookup_track_metadata(
    *,
    artist: str = "",
    title: str = "",
    url: str | None = None,
    file_path: str | None = None,
    features_cache: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """BPM/key from GetSongBPM when possible, else local WAV analysis."""
    _ = url, features_cache  # kept for call-site compatibility
    empty: dict[str, Any] = {"bpm": 0, "key": UNKNOWN, "camelot": "", "source": ""}
    if file_path and os.path.isfile(file_path):
        result = resolve_bpm_key_for_track(file_path, artist, title)
    else:
        fallback = lookup_getsongbpm_only(artist, title)
        result = fallback or empty
    if result.get("bpm") or (result.get("key") and result.get("key") != UNKNOWN):
        return {
            "bpm": result.get("bpm") or 0,
            "key": result.get("key") or UNKNOWN,
            "camelot": result.get("camelot") or "",
            "source": result.get("source") or "",
        }
    return empty


def lookup_bpm_key(
    artist: str,
    title: str,
    url: str | None = None,
    *,
    file_path: str | None = None,
    features_cache: dict[str, dict[str, Any]] | None = None,
) -> tuple[int | str, str]:
    _ = url, features_cache
    if file_path and os.path.isfile(file_path):
        result = resolve_bpm_key_for_track(file_path, artist, title)
        return result.get("bpm") or 0, str(result.get("key") or UNKNOWN)
    fallback = lookup_getsongbpm_only(artist, title)
    if fallback:
        return fallback.get("bpm") or 0, str(fallback.get("key") or UNKNOWN)
    return 0, UNKNOWN
