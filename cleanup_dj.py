"""WaveMash DJ Cleanup Script — documents files and code to remove.

Run with:
    python cleanup_dj.py          # print summary only (safe, no changes)
    python cleanup_dj.py --delete # actually delete the listed files (DESTRUCTIVE)

This script identifies all DJ-specific modules, desktop-app files, MIK
bridge code, and legacy batch/spec files that are no longer needed after
the migration to the web-based architecture (FastAPI + Next.js).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Project root
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# 1. DJ-specific files to delete
# ---------------------------------------------------------------------------
DJ_FILES_TO_DELETE: list[str] = [
    # ── DJ deck / playback engine ──────────────────────────────────────
    "desktop_app/deck_audio.py",       # Audio output backend for DJ decks
    "desktop_app/deck_playback.py",    # Deck transport / play-pause logic
    "desktop_app/deck_waveform.py",    # Waveform rendering for DJ decks
    "desktop_app/deck_workers.py",     # Background workers for deck audio
    "desktop_app/dj_bpm_sync.py",      # BPM sync / beat-matching engine
    "desktop_app/dj_mixer.py",         # Two-channel DJ mixer
    "desktop_app/transition_manager.py",  # Automated transition sequencer
    "desktop_app/transition_strip.py",    # Timeline transition UI strip
    "desktop_app/ipod_controls.py",    # iPod-style playback controls widget

    # ── Waveform analysis / editor ─────────────────────────────────────
    "desktop_app/waveform.py",         # Standalone waveform widget
    "desktop_app/waveform_editor.py",  # Cue-point / waveform editor dialog

    # ── DJ set management ──────────────────────────────────────────────
    "desktop_app/set_model.py",        # DJ set data model
    "desktop_app/sets_store.py",       # JSON persistence for DJ sets
    "sets.json",                       # Stored DJ set data

    # ── Desktop app shell (replaced by web) ────────────────────────────
    "desktop_app/components.py",       # DeckWidget and other desktop-only components
    "desktop_app/app.py",             # 4300-line monolith Qt desktop app
    "desktop_app/analysis.py",        # DJ-oriented audio analysis (essentia)

    # ── Mixed In Key (MIK) bridge ──────────────────────────────────────
    "mik_bridge.py",                   # MIK filesystem bridge (export M3U, pull results)
    "mik_metadata.py",                 # MIK database reader (MIKStore.db)
    "desktop_app/mik_controller.py",   # Qt controller for MIK workflow

    # ── Legacy build / launch scripts ──────────────────────────────────
    "build.bat",                       # PyInstaller build script
    "wavemash.spec",                   # PyInstaller spec file
    "start_desktop.bat",              # Launcher for desktop app
    "start_desktop.vbs",              # Silent VBS launcher
    "install_spotify.bat",            # pip install spotipy helper
    "start_dev.bat",                  # Old dev launcher
    "dev.py",                         # Hot-reload dev runner for desktop app
]

# ---------------------------------------------------------------------------
# 2. mix_data code in library.py that should be cleaned up
# ---------------------------------------------------------------------------
LIBRARY_MIX_DATA_CLEANUP: list[dict[str, str | int]] = [
    {
        "location": "library.py line 31",
        "code": "'mix_data',",
        "context": "ARCHIVE_CORE_KEYS frozenset — remove 'mix_data' entry",
    },
    {
        "location": "library.py line 36",
        "code": "'energy_level', 'bpm_source', 'local_path', 'url', 'platform', 'mix_data',",
        "context": "_INDEX_ROW_KEYS tuple — remove 'mix_data' from the tuple",
    },
    {
        "location": "library.py lines 39-43",
        "code": "DEFAULT_MIX_TRANSITION = { 'duration_ms': 6000, ... }",
        "context": "DEFAULT_MIX_TRANSITION constant — delete entirely (DJ transition defaults)",
    },
    {
        "location": "library.py lines 686-690",
        "code": "def default_mix_data() -> dict[str, Any]: ...",
        "context": "default_mix_data() — delete entire function (DJ mix cue defaults)",
    },
    {
        "location": "library.py lines 693-720",
        "code": "def normalize_mix_data(data) -> dict[str, Any]: ...",
        "context": "normalize_mix_data() — delete entire function (validates DJ cue/transition data)",
    },
    {
        "location": "library.py lines 723-733",
        "code": "def parse_mix_data(raw) -> dict[str, Any]: ...",
        "context": "parse_mix_data() — delete entire function (JSON parsing for mix_data)",
    },
    {
        "location": "library.py lines 736-737",
        "code": "def mix_data_to_json(data) -> str: ...",
        "context": "mix_data_to_json() — delete entire function (serializer for mix_data)",
    },
    {
        "location": "library.py lines 740-771",
        "code": "def mix_data_from_record(record) -> dict[str, Any]: ...",
        "context": "mix_data_from_record() — delete entire function (resolves mix_data from DB record)",
    },
    {
        "location": "library.py lines 774-780",
        "code": "def clear_record_cues(record) -> None: ...",
        "context": "clear_record_cues() — delete entire function (clears DJ cue points)",
    },
    {
        "location": "library.py lines 783-797",
        "code": "def clear_all_record_cues(records) -> int: ...",
        "context": "clear_all_record_cues() — delete entire function (batch cue clear)",
    },
    {
        "location": "library.py lines 800-811",
        "code": "def remove_record_mix_cue(record, *, remove_in, remove_out) -> None: ...",
        "context": "remove_record_mix_cue() — delete entire function (selective cue removal)",
    },
    {
        "location": "library.py lines 814-838",
        "code": "def update_record_mix_cues(record, *, mix_in_ms, mix_out_ms, transition) -> dict: ...",
        "context": "update_record_mix_cues() — delete entire function (cue update + legacy sync)",
    },
    {
        "location": "library.py line 874",
        "code": "'mix_data': mix_data_to_json(mix_data_from_record(record)),",
        "context": "record_to_index_row() — remove mix_data field from returned dict",
    },
    {
        "location": "library.py line 912",
        "code": "merged['mix_data'] = mix_data_from_record({**merged, 'mix_data': index.get('mix_data')})",
        "context": "merge_core_and_index() — remove mix_data merge line",
    },
    {
        "location": "library.py line 932",
        "code": "mix_data TEXT NOT NULL DEFAULT '{}'",
        "context": "TrackIndexDB._SCHEMA — remove mix_data column from tracks table",
    },
    {
        "location": "library.py lines 953, 955-960",
        "code": "self._ensure_mix_data_column(conn)  /  def _ensure_mix_data_column(...): ...",
        "context": "TrackIndexDB.ensure_schema() — remove migration call and method",
    },
    {
        "location": "library.py lines 967-970",
        "code": "if not str(payload.get('mix_data') ...) ... payload['mix_data'] = ...",
        "context": "TrackIndexDB.upsert() — remove mix_data normalisation block",
    },
]

# ---------------------------------------------------------------------------
# 3. Additional cleanup notes
# ---------------------------------------------------------------------------
ADDITIONAL_NOTES: list[str] = [
    "desktop_app/ directory — after removing the DJ files listed above, review "
    "remaining modules (collapsible.py, combo_popup.py, library_search.py, "
    "metadata_controller.py, playlist_picker.py, single_instance.py, "
    "track_dialogs.py, track_widgets.py, ui_menus.py, workers.py, "
    "archive_store.py). Some may still be imported by server/ code. "
    "Migrate any shared logic and then delete the rest of desktop_app/.",

    "docker/Dockerfile — currently references desktop_app/analysis.py for "
    "the Essentia self-test. Update to reference the new analysis location "
    "once DJ analysis code is removed.",

    "mik_export/ directory — contains MIK export artifacts; delete the "
    "entire directory after confirming nothing else depends on it.",

    "requirements.txt — remove Qt/desktop-only deps (PyQt6, pyaudio, "
    "sounddevice, etc.) once desktop_app/ is fully removed.",

    "After removing mix_data from library.py, run a migration on "
    "track_index.db to DROP the mix_data column (SQLite requires "
    "rebuilding the table). Or simply delete track_index.db and "
    "let the server regenerate it on next startup.",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_file(rel_path: str) -> tuple[bool, int]:
    """Return (exists, size_bytes) for a file relative to PROJECT_ROOT."""
    full = PROJECT_ROOT / rel_path
    if full.is_file():
        return True, full.stat().st_size
    return False, 0


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


# ---------------------------------------------------------------------------
# Main: print summary
# ---------------------------------------------------------------------------

def print_summary() -> None:
    sep = "=" * 72
    thin = "-" * 72

    print()
    print(sep)
    print("  WaveMash — DJ Cleanup Summary")
    print("  (no files will be modified — dry run)")
    print(sep)

    # --- Files ---
    print()
    print("1. DJ-SPECIFIC FILES TO DELETE")
    print(thin)

    total_size = 0
    found_count = 0
    missing_count = 0

    for rel in DJ_FILES_TO_DELETE:
        exists, size = _check_file(rel)
        status = "FOUND  " if exists else "GONE   "
        size_str = f"({_format_size(size)})" if exists else ""
        print(f"  [{status}] {rel}  {size_str}")
        if exists:
            found_count += 1
            total_size += size
        else:
            missing_count += 1

    print(thin)
    print(f"  Total: {found_count} files found ({_format_size(total_size)}), "
          f"{missing_count} already removed")
    print()

    # --- library.py mix_data ---
    print("2. mix_data CODE IN library.py TO CLEAN UP")
    print(thin)

    for i, item in enumerate(LIBRARY_MIX_DATA_CLEANUP, 1):
        print(f"  {i:2d}. [{item['location']}]")
        print(f"      {item['context']}")
        print()

    print(thin)
    print(f"  Total: {len(LIBRARY_MIX_DATA_CLEANUP)} code locations to clean up")
    print()

    # --- Additional notes ---
    print("3. ADDITIONAL CLEANUP NOTES")
    print(thin)

    for i, note in enumerate(ADDITIONAL_NOTES, 1):
        print(f"  {i}. {note}")
        print()

    print(sep)
    print("  Run with --delete to actually remove the files listed above.")
    print("  Code changes in library.py must be done manually or via a")
    print("  separate refactoring script.")
    print(sep)
    print()


def delete_files() -> None:
    """Actually delete the DJ files (requires --delete flag)."""
    sep = "=" * 72
    print()
    print(sep)
    print("  WaveMash — DJ Cleanup (DESTRUCTIVE)")
    print(sep)
    print()

    deleted = 0
    skipped = 0
    for rel in DJ_FILES_TO_DELETE:
        full = PROJECT_ROOT / rel
        if full.is_file():
            try:
                full.unlink()
                print(f"  DELETED  {rel}")
                deleted += 1
            except OSError as exc:
                print(f"  ERROR    {rel} — {exc}")
                skipped += 1
        else:
            print(f"  SKIP     {rel} (not found)")
            skipped += 1

    print()
    print(f"  Done: {deleted} deleted, {skipped} skipped")
    print(f"  Remember to clean up mix_data code in library.py manually.")
    print(sep)
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if "--delete" in sys.argv:
        confirm = input(
            "WARNING: This will permanently delete DJ files. Type YES to confirm: "
        )
        if confirm.strip() == "YES":
            delete_files()
        else:
            print("Aborted.")
    else:
        print_summary()
