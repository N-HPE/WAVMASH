"""Project root and shared filesystem paths (cross-platform)."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def project_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


PROJECT_DIR = project_dir()


def default_wav_root() -> str:
    """Resolve the WAV library folder.

    Priority:
      1. WAVMASH_WAV_ROOT
      2. WAV_STORAGE_PATH (docker / legacy)
      3. Existing common folders (~/Music/WaveMash, ~/WAV, OneDrive Desktop/WAV)
      4. Platform default (macOS → ~/Music/WaveMash, else → ~/WAV)
    """
    for key in ("WAVMASH_WAV_ROOT", "WAV_STORAGE_PATH"):
        raw = (os.environ.get(key) or "").strip()
        if raw:
            return str(Path(os.path.expanduser(raw)).resolve())

    home = Path.home()
    candidates = [
        home / "Music" / "WaveMash",
        home / "WAV",
        home / "OneDrive" / "Desktop" / "WAV",
        home / "Desktop" / "WAV",
    ]
    for path in candidates:
        if path.is_dir():
            return str(path.resolve())

    if sys.platform == "darwin":
        return str((home / "Music" / "WaveMash").resolve())
    return str((home / "WAV").resolve())
