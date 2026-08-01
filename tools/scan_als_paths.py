import gzip
import html
import os
import re
import sys
from pathlib import Path

DEFAULT = Path(r"C:\Users\junno\OneDrive\Desktop\Untitled Project\Untitled.als")


def extract_paths(als_path: Path) -> set[str]:
    raw = gzip.open(als_path, "rb").read().decode("utf-8", errors="replace")
    paths: set[str] = set()
    for match in re.finditer(r'<Path Value="([^"]+\.wav)"', raw, flags=re.I):
        paths.add(html.unescape(match.group(1)).replace("/", "\\"))
    return paths


def main() -> None:
    als = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    paths = sorted(extract_paths(als))
    missing = [p for p in paths if not os.path.isfile(p)]
    ok = [p for p in paths if os.path.isfile(p)]

    print(f"Project: {als}")
    print(f"WAV refs: {len(paths)}  OK: {len(ok)}  MISSING: {len(missing)}\n")

    if ok:
        print("=== FOUND ===")
        for p in ok:
            print(" OK", p)

    if missing:
        print("\n=== MISSING ===")
        for p in missing:
            print(" MISS", p)

    # categorize missing
    from collections import Counter

    def bucket(path: str) -> str:
        p = path.lower()
        if "desktop\\wav" in p or "desktop/wav" in p:
            return "Desktop/WAV (WaveMash)"
        if "music\\wav" in p:
            return "Desktop/Music/WAV"
        if "wave file" in p:
            return "Desktop/Music/Wave File"
        if "downloads" in p:
            return "Downloads"
        if "untitled project" in p:
            return "Untitled Project local"
        return "Other"

    print("\n=== MISSING BY BUCKET ===")
    for name, count in Counter(bucket(p) for p in missing).most_common():
        print(f"  {name}: {count}")


if __name__ == "__main__":
    main()
