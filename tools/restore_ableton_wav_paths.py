"""Restore flat WAV paths that Ableton projects still reference."""
from __future__ import annotations

import gzip
import html
import os
import re
import sys
from pathlib import Path

WAV_ROOT = Path(os.path.expanduser("~")) / "OneDrive" / "Desktop" / "WAV"
DEFAULT_ALS = Path(os.path.expanduser("~")) / "OneDrive" / "Desktop" / "Music" / "gara Project" / "DNA.als"


def extract_ableton_wav_paths(als_path: Path) -> set[str]:
    raw = gzip.open(als_path, "rb").read().decode("utf-8", errors="replace")
    paths: set[str] = set()
    for match in re.finditer(r'<Path Value="([^"]+\.wav)"', raw, flags=re.I):
        value = html.unescape(match.group(1)).replace("/", "\\")
        if "Desktop\\WAV" in value or "/WAV/" in match.group(1):
            paths.add(value)
    return paths


def normalize_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"\.wav$", "", name, flags=re.I)
    name = re.sub(r"^\d+\s*bpm\s*-\s*", "", name)
    name = re.sub(r"^\d+\s*-\s*[a-g#b]{1,2}[mm]?\s*-\s*", "", name, flags=re.I)
    name = re.sub(r"[^a-z0-9]+", "", name)
    return name


def build_file_index(wav_root: Path) -> dict[str, list[Path]]:
    by_norm: dict[str, list[Path]] = {}
    all_files: list[Path] = []
    for path in wav_root.rglob("*.wav"):
        all_files.append(path)
        by_norm.setdefault(normalize_name(path.stem), []).append(path)
    return by_norm, all_files


def find_match(expected: Path, by_norm: dict[str, list[Path]], all_files: list[Path]) -> Path | None:
    if expected.is_file():
        return expected
    key = normalize_name(expected.stem)
    hits = by_norm.get(key, [])
    if len(hits) == 1:
        return hits[0]
    if hits:
        # Prefer non-hardlink-looking compact file as source
        hits = sorted(hits, key=lambda p: (" BPM - " not in p.name, len(str(p))))
        return hits[0]
    stem = expected.stem.lower()
    partial = [p for p in all_files if stem in p.stem.lower() or p.stem.lower() in stem]
    if len(partial) == 1:
        return partial[0]
    if partial:
        # Require reasonable overlap, avoid short false positives like "GO"
        scored = sorted(
            partial,
            key=lambda p: (
                -len(set(stem.split()) & set(p.stem.lower().split())),
                abs(len(p.stem) - len(stem)),
            ),
        )
        best = scored[0]
        overlap = set(stem.split()) & set(best.stem.lower().split())
        if overlap or stem in best.stem.lower() or best.stem.lower() in stem:
            return best
    return None


def restore_path(expected: str, source: Path, *, dry_run: bool) -> str:
    target = Path(expected)
    if target.is_file():
        return "already_ok"
    target.parent.mkdir(parents=True, exist_ok=True)
    if dry_run:
        return f"would_link {source} -> {target}"
    try:
        os.link(source, target)
        return "linked"
    except OSError:
        try:
            import shutil

            shutil.copy2(source, target)
            return "copied"
        except OSError as exc:
            return f"failed: {exc}"


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    als = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else DEFAULT_ALS
    if not als.is_file():
        print(f"ALS not found: {als}")
        sys.exit(1)

    refs = sorted(extract_ableton_wav_paths(als))
    by_norm, all_files = build_file_index(WAV_ROOT)

    ok = linked = copied = failed = unmatched = 0
    print(f"Project: {als.name}")
    print(f"WAV references in project: {len(refs)}\n")

    for ref in refs:
        expected = Path(ref)
        if expected.is_file():
            ok += 1
            continue
        match = find_match(expected, by_norm, all_files)
        if not match:
            unmatched += 1
            print(f"[NO MATCH] {expected.name}")
            continue
        result = restore_path(ref, match, dry_run=dry_run)
        if result == "linked":
            linked += 1
            print(f"[LINK] {expected.name}")
        elif result == "copied":
            copied += 1
            print(f"[COPY] {expected.name}")
        elif result.startswith("would_"):
            print(f"[DRY] {expected.name} <- {match.name}")
        else:
            failed += 1
            print(f"[FAIL] {expected.name}: {result}")

    print(
        f"\nSummary: already_ok={ok}, linked={linked}, copied={copied}, "
        f"unmatched={unmatched}, failed={failed}"
    )


if __name__ == "__main__":
    main()
