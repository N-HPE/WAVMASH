"""BPM/key lookup — Mixed In Key DB & tags first, then GetSongBPM, then local analysis."""

from __future__ import annotations

import json
import os
import re
import urllib.parse
from typing import Any, Callable

from library import UNKNOWN

_GETSONGBPM_MIN_SCORE = 0.70
_PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_ENHARMONIC = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}
_CAMELOT = {
    "B Major": "1B", "F# Major": "2B", "C# Major": "3B", "G# Major": "4B",
    "D# Major": "5B", "A# Major": "6B", "F Major": "7B", "C Major": "8B",
    "G Major": "9B", "D Major": "10B", "A Major": "11B", "E Major": "12B",
    "G# Minor": "1A", "D# Minor": "2A", "A# Minor": "3A", "F Minor": "4A",
    "C Minor": "5A", "G Minor": "6A", "D Minor": "7A", "A Minor": "8A",
    "E Minor": "9A", "B Minor": "10A", "F# Minor": "11A", "C# Minor": "12A",
}
_GSBPM_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://getsongbpm.com/",
    "Origin": "https://getsongbpm.com",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 WaveMash/1.0"
    ),
}


def _camelot(key: str) -> str:
    return _CAMELOT.get(key, "")


def _getsongbpm_key() -> str:
    try:
        from env_loader import ensure_env_loaded

        ensure_env_loaded()
    except Exception:
        pass
    return os.environ.get("GETSONGBPM_API_KEY", "").strip()


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


def _key_from_getsongbpm_key_of(raw: object) -> str | None:
    """Parse GetSongBPM ``key_of`` strings like ``Cm``, ``G#m``, ``F``."""
    if raw is None:
        return None
    s = str(raw).strip().replace("♯", "#").replace("♭", "b")
    if not s or s.lower() in ("unknown", "none"):
        return None

    minor = len(s) > 1 and s.endswith("m")
    pitch = s[:-1] if minor else s
    if not pitch:
        return None
    pitch = pitch[0].upper() + pitch[1:] if len(pitch) > 1 else pitch.upper()
    if len(pitch) >= 2 and pitch[1] in "#b":
        pitch = _ENHARMONIC.get(pitch[:2], pitch[:2]) + pitch[2:]
    elif pitch in _ENHARMONIC:
        pitch = _ENHARMONIC[pitch]
    scale = "Minor" if minor else "Major"
    key = f"{pitch} {scale}"
    return key if key in _CAMELOT else None


def _key_from_getsongbpm_legacy(key_of: object, mode: object) -> str | None:
    try:
        idx = int(key_of) % 12
        pitch = _PITCH_CLASSES[idx]
        scale = "Major" if int(mode) == 1 else "Minor"
        return f"{pitch} {scale}"
    except (TypeError, ValueError):
        return None


def _normalize_gsbpm_songs(data: dict[str, Any]) -> list[dict[str, Any]]:
    search = data.get("search")
    if isinstance(search, list):
        return [item for item in search if isinstance(item, dict)]
    if isinstance(search, dict):
        if search.get("error"):
            return []
        return [search]
    return []


def _getsongbpm_search(lookup: str, search_type: str = "song", *, limit: int = 8) -> list[dict[str, Any]]:
    """Call GetSongBPM ``/search/``; returns song dicts or []."""
    api_key = _getsongbpm_key()
    if not api_key or not lookup.strip():
        return []

    params = {
        "api_key": api_key,
        "type": search_type,
        "lookup": lookup.strip(),
        "limit": str(limit),
    }

    try:
        import requests

        resp = requests.get(
            "https://api.getsongbpm.com/search/",
            params=params,
            headers={**_GSBPM_HEADERS, "X-API-KEY": api_key},
            timeout=20,
        )
        body = resp.text.strip()
        if not body:
            return []
        data = resp.json()
        if isinstance(data, dict) and data.get("error"):
            err = str(data["error"])
            if "missing" in err.lower() or "invalid" in err.lower():
                print(f"[Track metadata] GetSongBPM: {err}")
            return []
        if resp.status_code != 200:
            if "Just a moment" in body:
                print(
                    "[Track metadata] GetSongBPM: Cloudflare 차단 "
                    "(Referer 헤더 필요 — WaveMash 업데이트 후 재시도)"
                )
            else:
                print(f"[Track metadata] GetSongBPM: HTTP {resp.status_code}")
            return []
        return _normalize_gsbpm_songs(data if isinstance(data, dict) else {})
    except Exception as exc:
        print(f"[Track metadata] GetSongBPM: {exc}")
        return []


def _pick_gsbpm_match(artist: str, title: str, songs: list[dict[str, Any]]) -> dict[str, Any] | None:
    best = None
    best_score = _GETSONGBPM_MIN_SCORE
    for item in songs:
        cand_artist = item.get("artist")
        if isinstance(cand_artist, dict):
            cand_artist = cand_artist.get("name")
        score = _match_score(
            artist,
            title,
            str(cand_artist or ""),
            str(item.get("title") or item.get("song_title") or ""),
        )
        if score > best_score:
            best_score = score
            best = item
    return best


def lookup_getsongbpm_only(artist: str, title: str) -> dict[str, Any] | None:
    if not _getsongbpm_key() or not artist or not title:
        return None

    songs = _getsongbpm_search(title, "song")
    best = _pick_gsbpm_match(artist, title, songs)
    if best is None and artist != UNKNOWN:
        songs = _getsongbpm_search(f"{artist} {title}", "song")
        best = _pick_gsbpm_match(artist, title, songs)
    if not best:
        return None

    try:
        bpm = int(round(float(best.get("tempo"))))
    except (TypeError, ValueError):
        return None
    if bpm <= 0:
        return None

    key = _key_from_getsongbpm_key_of(best.get("key_of"))
    if not key:
        key = _key_from_getsongbpm_legacy(best.get("key_of"), best.get("mode")) or UNKNOWN

    return {
        "bpm": bpm,
        "key": key,
        "camelot": _camelot(key) if key != UNKNOWN else (best.get("open_key") or ""),
        "source": "getsongbpm",
    }


def _metadata_from_wav_tags(path: str) -> dict[str, Any] | None:
    from library import UNKNOWN, key_has_mode, read_wav_tags

    try:
        from mik_metadata import key_from_camelot
    except ImportError:
        key_from_camelot = lambda _raw: None  # noqa: E731

    tags = read_wav_tags(path)
    if not tags:
        return None
    bpm = 0.0
    try:
        bpm = float(str(tags.get("bpm") or "").strip())
    except (TypeError, ValueError):
        bpm = 0.0
    raw_key = str(tags.get("key") or "").strip()
    key = raw_key if raw_key and key_has_mode(raw_key) else ""
    camelot = ""
    if not key and raw_key:
        key = key_from_camelot(raw_key) or ""
        camelot = raw_key.upper() if not key else ""
    if key and not camelot:
        camelot = _camelot(key)
    if bpm <= 0 and not key:
        return None
    return {
        "bpm": bpm if bpm > 0 else 0,
        "key": key or UNKNOWN,
        "camelot": camelot or (_camelot(key) if key and key != UNKNOWN else ""),
        "source": "tags",
    }


def _merge_metadata_field(
    result: dict[str, Any],
    patch: dict[str, Any] | None,
    *,
    source: str,
) -> None:
    if not patch:
        return
    if patch.get("bpm") and (not result.get("bpm") or float(result["bpm"]) <= 0):
        result["bpm"] = patch["bpm"]
    patch_key = str(patch.get("key") or "")
    if patch_key and patch_key != UNKNOWN and (
        not result.get("key") or result.get("key") == UNKNOWN
    ):
        result["key"] = patch_key
    if patch.get("camelot_key") and not result.get("camelot"):
        result["camelot"] = str(patch["camelot_key"])
    if patch.get("camelot") and not result.get("camelot"):
        result["camelot"] = patch["camelot"]
    if patch.get("energy_level") and not result.get("energy_level"):
        result["energy_level"] = patch["energy_level"]
    if patch.get("beat_offset_sec") is not None and result.get("beat_offset_sec") is None:
        result["beat_offset_sec"] = patch["beat_offset_sec"]
    prev = str(result.get("source") or "")
    result["source"] = source if not prev else f"{prev}+{source}"


def resolve_track_metadata(
    path: str,
    artist: str,
    title: str,
) -> dict[str, Any]:
    """MIK DB → WAV tags → GetSongBPM → local analysis (first hit wins per field)."""
    result: dict[str, Any] = {
        "bpm": 0,
        "key": UNKNOWN,
        "camelot": "",
        "energy_level": 0,
        "beat_offset_sec": None,
        "source": "",
    }

    if path:
        try:
            from mik_metadata import lookup_mik_by_path

            _merge_metadata_field(result, lookup_mik_by_path(path), source="mik")
        except ImportError:
            pass
        if os.path.isfile(path):
            _merge_metadata_field(result, _metadata_from_wav_tags(path), source="tags")

    bpm_missing = not result.get("bpm") or float(result["bpm"]) <= 0
    key_missing = not result.get("key") or result.get("key") == UNKNOWN
    if bpm_missing or key_missing:
        db = lookup_getsongbpm_only(artist, title)
        if db:
            _merge_metadata_field(
                result,
                {
                    "bpm": int(db.get("bpm") or 0),
                    "key": str(db.get("key") or UNKNOWN),
                    "camelot": db.get("camelot") or "",
                },
                source="getsongbpm",
            )

    bpm_missing = not result.get("bpm") or float(result["bpm"]) <= 0
    key_missing = not result.get("key") or result.get("key") == UNKNOWN
    if path and (bpm_missing or key_missing):
        local = _analyze_local_bpm_key(path)
        if local:
            _merge_metadata_field(result, local, source="local")

    if result.get("key") and result["key"] != UNKNOWN and not result.get("camelot"):
        result["camelot"] = _camelot(str(result["key"]))
    return result


def enrich_record_metadata(
    record: dict[str, Any],
    progress_callback: Callable[[str], None] | None = None,
) -> bool:
    """Fill record fields from MIK/tags/APIs; returns True if updated."""
    from library import UNKNOWN, apply_track_metadata, effective_artist_title

    path = str(record.get("path") or record.get("local_path") or "")
    if not path or not os.path.isfile(path):
        return False
    artist, title = effective_artist_title(
        str(record.get("artist") or ""),
        str(record.get("title") or ""),
    )
    if progress_callback:
        try:
            progress_callback("BPM · Key · 메타데이터 추출 중...")
        except Exception:
            pass
    meta = resolve_track_metadata(path, artist, title)
    has_bpm = bool(meta.get("bpm") and float(meta["bpm"]) > 0)
    has_key = bool(meta.get("key") and meta["key"] != UNKNOWN)
    if not has_bpm and not has_key and not meta.get("energy_level"):
        return False
    if progress_callback:
        bits = []
        if has_bpm:
            bits.append(f"BPM {int(float(meta['bpm']))}")
        if has_key:
            bits.append(f"Key {meta['key']}")
        try:
            progress_callback(
                f"메타데이터 적용: {', '.join(bits)}" if bits else "메타데이터 저장 중..."
            )
        except Exception:
            pass
    return apply_track_metadata(
        record,
        bpm=meta.get("bpm") if has_bpm else None,
        key=str(meta.get("key")) if has_key else None,
        camelot_key=str(meta.get("camelot") or ""),
        energy_level=int(meta.get("energy_level") or 0) or None,
        bpm_source=str(meta.get("source") or ""),
        beat_offset_sec=meta.get("beat_offset_sec"),
    )


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
    """Backward-compatible wrapper around :func:`resolve_track_metadata`."""
    meta = resolve_track_metadata(path, artist, title)
    return {
        "bpm": meta.get("bpm") or 0,
        "key": meta.get("key") or UNKNOWN,
        "camelot": meta.get("camelot") or "",
        "source": meta.get("source") or "",
        "energy_level": meta.get("energy_level") or 0,
        "beat_offset_sec": meta.get("beat_offset_sec"),
    }


def lookup_track_metadata(
    *,
    artist: str = "",
    title: str = "",
    url: str | None = None,
    file_path: str | None = None,
    features_cache: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """BPM/key from MIK, tags, GetSongBPM, or local WAV analysis."""
    _ = url, features_cache
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
