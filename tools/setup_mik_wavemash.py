#!/usr/bin/env python3
"""One-time WaveMash + Mixed In Key integration setup (safe, non-destructive)."""

from __future__ import annotations

import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from env_loader import ensure_env_loaded
from library import WAV_ROOT
from paths import PROJECT_DIR

ENV_PATH = os.path.join(PROJECT_DIR, ".env")
MIK_CONFIG_ROOT = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "Mixed_In_Key_LLC",
)


def _patch_env() -> list[str]:
    ensure_env_loaded()
    wanted = {
        "MIK_BRIDGE_ENABLED": "1",
        "MIK_AUTO_PULL": "1",
        "MIK_LAUNCH_ON_DOWNLOAD": "0",
    }
    existing: set[str] = set()
    if os.path.isfile(ENV_PATH):
        with open(ENV_PATH, encoding="utf-8") as fh:
            for ln in fh:
                if "=" in ln and not ln.strip().startswith("#"):
                    existing.add(ln.split("=", 1)[0].strip())
    added = [k for k in wanted if k not in existing]
    if added:
        with open(ENV_PATH, "a", encoding="utf-8") as fh:
            fh.write("\n# Mixed In Key bridge\n")
            for key in added:
                fh.write(f"{key}={wanted[key]}\n")
    return added


def _patch_mik_user_config() -> int:
    """Turn on tempo + initial key tag writing in MIK user.config files."""
    count = 0
    pattern = os.path.join(MIK_CONFIG_ROOT, "**", "user.config")
    for path in glob.glob(pattern, recursive=True):
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        orig = text
        text = re.sub(
            r"(<setting name=\"UpdateTempoTag\"[^>]*>\s*<value>)\s*False\s*(</value>)",
            r"\1True\2",
            text,
            count=1,
        )
        text = re.sub(
            r"(<setting name=\"UpdateInitialKeyTag\"[^>]*>\s*<value>)\s*False\s*(</value>)",
            r"\1True\2",
            text,
            count=1,
        )
        text = re.sub(
            r"(<setting name=\"EnableMidiLogging\"[^>]*>\s*<value>)\s*True\s*(</value>)",
            r"\1False\2",
            text,
            count=1,
        )
        text = re.sub(
            r"(<setting name=\"EnableMidiControl\"[^>]*>\s*<value>)\s*True\s*(</value>)",
            r"\1False\2",
            text,
            count=1,
        )
        if text != orig:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            count += 1
    return count


def _export_m3u() -> tuple[int, int]:
    from mik_bridge import export_all_playlists, mik_export_dir, rebuild_inbox_m3u
    from desktop_app.archive_store import load_archive

    records = load_archive()
    playlists_path = os.path.join(PROJECT_DIR, "playlists.json")
    playlists: dict[str, list[str]] = {}
    if os.path.isfile(playlists_path):
        import json

        with open(playlists_path, encoding="utf-8") as fh:
            raw = json.load(fh)
        if isinstance(raw, dict) and "playlists" in raw:
            playlists = raw.get("playlists") or {}
        elif isinstance(raw, dict):
            playlists = raw
    pl_paths = export_all_playlists(playlists, records)
    inbox_n = rebuild_inbox_m3u(records)
    return len(pl_paths), inbox_n


def _verify() -> dict[str, str]:
    from mik_metadata import find_mik_db_path
    from mik_bridge import _mik_exe_path

    return {
        "wav_root": WAV_ROOT,
        "wav_exists": str(os.path.isdir(WAV_ROOT)),
        "mik_db": find_mik_db_path() or "(not found)",
        "mik_exe": _mik_exe_path() or "(not found)",
        "mik_export": os.path.join(PROJECT_DIR, "mik_export"),
    }


def main() -> int:
    ensure_env_loaded()
    added = _patch_env()
    cfg_patched = _patch_mik_user_config()
    pl_count, inbox_n = _export_m3u()
    info = _verify()

    print("=== WaveMash + Mixed In Key setup ===\n")
    if added:
        print(f".env added: {', '.join(added)}")
    else:
        print(".env MIK options already present.")
    print(f"MIK user.config patched: {cfg_patched} file(s)")
    print(f"M3U playlists exported: {pl_count}, inbox pending: {inbox_n} track(s)")
    print()
    for k, v in info.items():
        print(f"  {k}: {v}")
    print("\n--- Manual steps in Mixed In Key (once) ---")
    print("1. Open Mixed In Key")
    print(f"2. Add library/collection folder:\n   {WAV_ROOT}")
    print("3. (Optional) File -> Import playlist ->")
    print(f"   {info['mik_export']}\\WaveMash_Inbox.m3u8")
    print("4. Select folder or playlist -> Analyze")
    print("\nThen: WaveMash download -> MIK analyze -> auto pull (~90s)")
    print("Or: WaveMash Settings -> Sync from Mixed In Key")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
