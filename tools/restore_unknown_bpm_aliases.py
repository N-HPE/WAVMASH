"""Create 'Unknown BPM - Unknown - Title.wav' aliases for Ableton offline recovery."""
from __future__ import annotations

import gzip
import html
import os
import re
import sys
from pathlib import Path

WAV_ROOT = Path(os.path.expanduser("~")) / "OneDrive" / "Desktop" / "WAV"
UNKNOWN_PREFIX = "Unknown BPM - Unknown - "


def extract_paths(als_path: Path) -> set[str]:
    raw = gzip.open(als_path, "rb").read().decode("utf-8", errors="replace")
    paths: set[str] = set()
    for match in re.finditer(r'<Path Value="([^"]+\.wav)"', raw, flags=re.I):
        paths.add(html.unescape(match.group(1)).replace("/", "\\"))
    return paths


def title_from_unknown_path(path: Path) -> str | None:
    name = path.name
    if not name.startswith(UNKNOWN_PREFIX):
        return None
    return name[len(UNKNOWN_PREFIX) :]


def pick_source(folder: Path, title: str) -> Path | None:
    if not folder.is_dir():
        return None
    title_lower = title.lower()
    candidates = [
        p
        for p in folder.glob("*.wav")
        if p.name.lower().endswith(title_lower)
        and not p.name.startswith(UNKNOWN_PREFIX)
        and not p.name.endswith(".riff.wav")
    ]
    if not candidates:
        candidates = [
            p
            for p in folder.glob("*.wav")
            if title_lower in p.name.lower()
            and not p.name.startswith(UNKNOWN_PREFIX)
            and not p.name.endswith(".riff.wav")
        ]
    if not candidates:
        return None
    # Prefer compact "128 - C#m - Title.wav" over legacy "128 BPM - ..."
    candidates.sort(key=lambda p: (" BPM - " in p.name, len(p.name)))
    return candidates[0]


def link_alias(expected: Path, source: Path, *, dry_run: bool) -> str:
    if expected.is_file():
        return "exists"
    if dry_run:
        return f"would_link {source.name}"
    expected.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, expected)
        return "linked"
    except OSError:
        import shutil

        try:
            shutil.copy2(source, expected)
            return "copied"
        except OSError as exc:
            return f"failed: {exc}"


def restore_for_als(als_path: Path, *, dry_run: bool = False) -> tuple[int, int, int]:
    linked = exists = failed = 0
    for ref in sorted(extract_paths(als_path)):
        expected = Path(ref)
        if expected.is_file():
            exists += 1
            continue
        title = title_from_unknown_path(expected)
        if not title:
            continue
        source = pick_source(expected.parent, title)
        if source is None:
            source = pick_source(WAV_ROOT / expected.relative_to(WAV_ROOT).parent, title) if str(expected).startswith(str(WAV_ROOT)) else None
        if source is None:
            failed += 1
            print(f"[NO SOURCE] {expected.name}")
            continue
        result = link_alias(expected, source, dry_run=dry_run)
        if result in ("linked", "copied", "exists"):
            linked += 1
            print(f"[{result.upper()}] {expected.name} <- {source.name}")
        elif result.startswith("would_"):
            linked += 1
            print(f"[DRY] {expected.name} <- {source.name}")
        else:
            failed += 1
            print(f"[FAIL] {expected.name}: {result}")
    return linked, exists, failed


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    als_files = [Path(a) for a in args] if args else [
        Path(r"C:\Users\junno\OneDrive\Desktop\Untitled Project\Untitled.als"),
    ]
    for als in als_files:
        if not als.is_file():
            print(f"skip missing: {als}")
            continue
        print(f"\n=== {als} ===")
        linked, exists, failed = restore_for_als(als, dry_run=dry_run)
        print(f"summary: linked={linked}, already_ok={exists}, failed={failed}")


if __name__ == "__main__":
    main()
