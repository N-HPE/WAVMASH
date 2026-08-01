"""Remap Mixed In Key library paths after WAV folder reorganization.

Usage:
  # Auto-find moved files by filename/title under common music folders:
  python fix_mik_paths.py

  # Folder rename only (same filenames, path prefix changed):
  python fix_mik_paths.py --replace-prefix "C:\\old\\path" "C:\\new\\path"

MIK must be closed while this script runs (it edits MIKStore.db).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import sqlite3
from pathlib import Path
DB_PATH = Path(
    os.environ.get(
        "MIK_DB",
        r"C:\Users\junno\AppData\Local\Mixed In Key\Mixed In Key\11.0\MIKStore.db",
    )
)
WAV_ROOT = Path(
    os.environ.get("WAV_ROOT", r"C:\Users\junno\OneDrive\Desktop\WAV")
)
SEARCH_ROOTS = [
    WAV_ROOT,
    Path(r"C:\Users\junno\OneDrive\Desktop\Music\WAV"),
    Path(r"C:\Users\junno\OneDrive\Desktop\Music\Wave File"),
    Path(r"C:\Users\junno\OneDrive\Desktop\Music"),
]
AUDIO_EXTS = {".wav", ".mp3", ".flac", ".aiff", ".m4a", ".aif"}


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def title_core(name: str) -> str:
    base = Path(name).stem
    base = re.sub(r"^\d+\s*bpm\s*-\s*[^-]+-\s*", "", base, flags=re.I)
    base = re.sub(r"^\d+\s*-\s*[a-g][#b]?m?\s*-\s*", "", base, flags=re.I)
    base = re.sub(r"^unknown\s*bpm\s*-\s*unknown\s*-\s*", "", base, flags=re.I)
    base = re.sub(r"^unknown\s*-\s*unknown\s*key\s*-\s*", "", base, flags=re.I)
    return normalize(base)


def file_path_hash(path: str) -> str:
    try:
        import clr  # type: ignore

        mik_dir = Path(
            os.environ.get(
                "MIK_DIR",
                r"C:\Users\junno\AppData\Local\Programs\Mixed In Key\Mixed in Key 11",
            )
        )
        import sys

        if str(mik_dir) not in sys.path:
            sys.path.append(str(mik_dir))
        clr.AddReference("MixedInKey.Data")
        from MixedInKey.Data import PathUtilities  # type: ignore

        return str(PathUtilities.CreateFilePathHash(path))
    except Exception:
        return hashlib.md5(path.lower().encode("utf-8")).hexdigest().upper()


def build_file_index(roots: list[Path]) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    seen: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if Path(fn).suffix.lower() not in AUDIO_EXTS:
                    continue
                full = str(Path(dirpath) / fn)
                if full in seen:
                    continue
                seen.add(full)
                rows.append((full, normalize(fn), title_core(fn), fn.lower()))
    return rows


def pick_match(
    song_name: str,
    artist_name: str,
    old_file: str,
    index: list[tuple[str, str, str, str]],
) -> str | None:
    old_name = Path(old_file).name.lower() if old_file else ""
    old_stem = title_core(old_file)
    song_norm = normalize(song_name)
    artist_norm = normalize(artist_name.split(",")[0] if artist_name else "")

    # 1) Exact filename match anywhere (flat -> moved/reorganized).
    if old_name:
        name_hits = [p for p, _, _, fn_lower in index if fn_lower == old_name]
        if len(name_hits) == 1:
            return name_hits[0]
        if len(name_hits) > 1:
            # Prefer reorganized WAV tree, then Music\WAV, then Wave File.
            def rank(path: str) -> tuple[int, int]:
                p = path.lower()
                if str(WAV_ROOT).lower() in p:
                    return (0, len(p))
                if "music\\wav" in p:
                    return (1, len(p))
                if "wave file" in p:
                    return (2, len(p))
                return (3, len(p))

            return sorted(name_hits, key=rank)[0]

    # 2) Exact title-core matches (handles BPM/Key prefixed filenames).
    exact = [p for p, _, core, _ in index if core and core == song_norm]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1 and artist_norm:
        artist_hits = [p for p in exact if artist_norm in normalize(p)]
        if len(artist_hits) == 1:
            return artist_hits[0]

    if old_stem:
        old_hits = [p for p, _, core, _ in index if core == old_stem]
        if len(old_hits) == 1:
            return old_hits[0]

    # 3) Fuzzy contains match on song title.
    contains = [p for p, norm_name, core, _ in index if song_norm and (song_norm in core or song_norm in norm_name)]
    if len(contains) == 1:
        return contains[0]
    if len(contains) > 1 and artist_norm:
        artist_hits = [p for p in contains if artist_norm in normalize(p)]
        if len(artist_hits) == 1:
            return artist_hits[0]

    return None


def replace_prefix(old_prefix: str, new_prefix: str) -> None:
    """Fast path when only a folder segment changed but filenames stayed the same."""
    if not DB_PATH.exists():
        raise SystemExit(f"DB not found: {DB_PATH}")

    old_prefix = old_prefix.rstrip("\\/")
    new_prefix = new_prefix.rstrip("\\/")

    backup = DB_PATH.with_suffix(".db.bak")
    if not backup.exists():
        shutil.copy2(DB_PATH, backup)
        print(f"backup -> {backup}")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute('SELECT Id, File FROM Song')
    updated = 0
    already_ok = 0
    skipped = 0

    for song_id, file_path in cur.fetchall():
        if not file_path:
            skipped += 1
            continue
        if os.path.exists(file_path):
            already_ok += 1
            continue
        norm = file_path.replace("/", "\\")
        if not norm.lower().startswith(old_prefix.lower()):
            skipped += 1
            continue
        new_path = new_prefix + norm[len(old_prefix):]
        if not os.path.exists(new_path):
            skipped += 1
            continue
        cur.execute(
            'UPDATE Song SET File = ?, FilePathHash = ?, DiskLabel = ? WHERE Id = ?',
            (new_path, file_path_hash(new_path), Path(new_path).drive or "", song_id),
        )
        updated += 1

    con.commit()
    con.close()
    print(f"prefix replace: already_ok={already_ok} updated={updated} skipped={skipped}")


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"DB not found: {DB_PATH}")

    backup = DB_PATH.with_suffix(".db.bak")
    if not backup.exists():
        shutil.copy2(DB_PATH, backup)
        print(f"backup -> {backup}")

    index = build_file_index(SEARCH_ROOTS)
    print(f"indexed {len(index)} audio files across {len(SEARCH_ROOTS)} roots")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute('SELECT Id, File, ArtistName, SongName FROM Song')
    songs = cur.fetchall()

    updated = 0
    already_ok = 0
    unresolved = 0
    unresolved_samples: list[str] = []

    for song_id, file_path, artist, title in songs:
        if file_path and os.path.exists(file_path):
            already_ok += 1
            continue
        new_path = pick_match(title or "", artist or "", file_path or "", index)
        if not new_path:
            unresolved += 1
            if len(unresolved_samples) < 15:
                unresolved_samples.append(f"{artist} - {title} | old={file_path}")
            continue
        new_hash = file_path_hash(new_path)
        disk_label = Path(new_path).drive or ""
        cur.execute(
            'UPDATE Song SET File = ?, FilePathHash = ?, DiskLabel = ? WHERE Id = ?',
            (new_path, new_hash, disk_label, song_id),
        )
        updated += 1

    con.commit()
    con.close()

    print(f"already_ok={already_ok} updated={updated} unresolved={unresolved}")
    if unresolved_samples:
        print("unresolved_samples:")
        for line in unresolved_samples:
            print(" ", line)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Repair Mixed In Key library file paths.")
    parser.add_argument(
        "--replace-prefix",
        nargs=2,
        metavar=("OLD", "NEW"),
        help="Replace path prefix when only a folder was renamed/moved.",
    )
    args = parser.parse_args()
    if args.replace_prefix:
        replace_prefix(args.replace_prefix[0], args.replace_prefix[1])
    else:
        main()
