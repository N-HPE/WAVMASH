"""Read BPM, key, energy, and structure hints from Mixed In Key (MIKStore.db + WAV tags).

Optional integration — if Mixed In Key is not installed, lookups return None and
WaveMash falls back to WAV tags / GetSongBPM / local analysis.
"""

from __future__ import annotations

import os
import re
import sqlite3
import threading
from typing import Any

_CAMELOT_RE = re.compile(r"^(\d{1,2})([AB])$", re.I)
_MIK_TIME_RE = re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{1,2})(?:\.(\d+))?$")

_CAMELOT_TO_KEY: dict[str, str] = {
    "1B": "B Major", "2B": "F# Major", "3B": "C# Major", "4B": "G# Major",
    "5B": "D# Major", "6B": "A# Major", "7B": "F Major", "8B": "C Major",
    "9B": "G Major", "10B": "D Major", "11B": "A Major", "12B": "E Major",
    "1A": "G# Minor", "2A": "D# Minor", "3A": "A# Minor", "4A": "F Minor",
    "5A": "C Minor", "6A": "G Minor", "7A": "D Minor", "8A": "A Minor",
    "9A": "E Minor", "10A": "B Minor", "11A": "F# Minor", "12A": "C# Minor",
}

_store_lock = threading.RLock()
_store_cache: "MikStore | None" = None


def key_from_camelot(raw: str | None) -> str | None:
    if not raw:
        return None
    text = str(raw).strip().upper().replace(" ", "")
    m = _CAMELOT_RE.match(text)
    if not m:
        return None
    code = f"{int(m.group(1))}{m.group(2).upper()}"
    return _CAMELOT_TO_KEY.get(code)


def mik_energy_to_wavemash(value: object) -> int | None:
    """Map MIK energy 1–10 to WaveMash 1–5 scale."""
    try:
        n = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    return max(1, min(5, int(round(n / 2.0))))


def _parse_mik_time(raw: object) -> float | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    m = _MIK_TIME_RE.match(s)
    if not m:
        try:
            return float(s)
        except ValueError:
            return None
    hours = int(m.group(1) or 0)
    mins = int(m.group(2) or 0)
    secs = int(m.group(3) or 0)
    frac = m.group(4) or "0"
    frac_sec = float(f"0.{frac}") if frac else 0.0
    return hours * 3600 + mins * 60 + secs + frac_sec


def norm_audio_path(path: str) -> str:
    try:
        return os.path.normcase(os.path.normpath(os.path.abspath(path)))
    except OSError:
        return os.path.normcase(os.path.normpath(path))


def find_mik_db_path() -> str | None:
    """Locate MIKStore.db (Windows Mixed In Key install)."""
    env = (os.environ.get("MIK_DB_PATH") or "").strip()
    if env and os.path.isfile(env):
        return env

    candidates: list[str] = []
    local = os.environ.get("LOCALAPPDATA") or ""
    appdata = os.environ.get("APPDATA") or ""
    home = os.path.expanduser("~")

    for root in filter(None, [local, appdata, home]):
        candidates.extend(
            [
                os.path.join(root, "Mixed In Key", "MIKStore.db"),
                os.path.join(root, "Mixed_In_Key_LLC", "MIKStore.db"),
            ]
        )
        # Nested version folders
        pattern_roots = [
            os.path.join(root, "Mixed_In_Key_LLC"),
            os.path.join(root, "Mixed In Key"),
        ]
        for pr in pattern_roots:
            if not os.path.isdir(pr):
                continue
            for dirpath, _, files in os.walk(pr):
                if "MIKStore.db" in files:
                    candidates.append(os.path.join(dirpath, "MIKStore.db"))

    # Prefer newest mtime
    existing = [p for p in candidates if os.path.isfile(p)]
    if not existing:
        return None
    existing.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return existing[0]


class MikStore:
    """Read-only index of MIKStore.db keyed by normalized file path."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._by_path: dict[str, dict[str, Any]] = {}
        self._mtime: float = 0.0
        self._reload_if_needed(force=True)

    def _reload_if_needed(self, *, force: bool = False) -> None:
        try:
            mtime = os.path.getmtime(self.db_path)
        except OSError:
            return
        if not force and mtime <= self._mtime:
            return
        self._mtime = mtime
        by_path: dict[str, dict[str, Any]] = {}
        try:
            con = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            con.row_factory = sqlite3.Row
            cur = con.execute(
                """
                SELECT s.File, s.Tempo, s.KeyResultSummary, s.OverallEnergy
                FROM Song s
                WHERE s.File IS NOT NULL AND s.File != ''
                """
            )
            for row in cur:
                file_path = str(row["File"] or "")
                if not file_path:
                    continue
                bpm = 0
                try:
                    bpm = int(float(row["Tempo"] or 0))
                except (TypeError, ValueError):
                    bpm = 0
                camelot = str(row["KeyResultSummary"] or "").strip()
                key = key_from_camelot(camelot) or ""
                energy_raw = row["OverallEnergy"]
                entry = {
                    "bpm": bpm if bpm > 0 else 0,
                    "key": key,
                    "camelot": camelot.upper() if camelot else "",
                    "camelot_key": camelot.upper() if camelot else "",
                    "energy_level": mik_energy_to_wavemash(energy_raw),
                }
                by_path[norm_audio_path(file_path)] = entry
                # Also index by basename for cross-machine path differences
                base = os.path.basename(file_path)
                if base and base not in by_path:
                    by_path[base.lower()] = entry
            con.close()
        except Exception as exc:
            print(f"[mik_metadata] MIKStore read failed: {exc}")
            return
        self._by_path = by_path

    def lookup(self, file_path: str) -> dict[str, Any] | None:
        self._reload_if_needed()
        if not file_path:
            return None
        hit = self._by_path.get(norm_audio_path(file_path))
        if hit:
            return dict(hit)
        base = os.path.basename(file_path).lower()
        hit = self._by_path.get(base)
        return dict(hit) if hit else None


def get_mik_store() -> MikStore | None:
    global _store_cache
    with _store_lock:
        if _store_cache is not None:
            return _store_cache
        db = find_mik_db_path()
        if not db:
            return None
        try:
            _store_cache = MikStore(db)
            return _store_cache
        except Exception as exc:
            print(f"[mik_metadata] init failed: {exc}")
            return None


def lookup_mik_by_path(path: str) -> dict[str, Any] | None:
    store = get_mik_store()
    if not store:
        return None
    return store.lookup(path)


def invalidate_mik_cache() -> None:
    global _store_cache
    with _store_lock:
        _store_cache = None
