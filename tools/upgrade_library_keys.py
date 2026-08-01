"""One-shot upgrade: legacy keys (e.g. 'C#') -> full form ('C# Major' / 'C# Minor')."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from library import key_has_mode, upgrade_record_key

DB_FILE = os.path.join(ROOT, "archive.json")


def main() -> int:
    if not os.path.isfile(DB_FILE):
        print('No archive.json found.')
        return 1

    with open(DB_FILE, 'r', encoding='utf-8') as f:
        records = json.load(f)

    if not isinstance(records, list):
        print('Invalid archive format.')
        return 1

    updated = 0
    skipped = 0
    failed = []

    for rec in records:
        if not isinstance(rec, dict):
            continue
        title = rec.get('title', rec.get('id', '?'))
        if key_has_mode(str(rec.get('key', ''))):
            continue
        print(f'Upgrading: {title} ({rec.get("key", "?")}) ...', flush=True)
        try:
            if upgrade_record_key(rec, reanalyze=True):
                updated += 1
                print(f'  -> {rec.get("key")}', flush=True)
            else:
                skipped += 1
                print('  -> could not detect Major/Minor', flush=True)
        except Exception as e:
            failed.append((title, str(e)))
            print(f'  -> ERROR: {e}', flush=True)

    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=4, ensure_ascii=False)

    print(f'\nDone. Updated {updated}, skipped {skipped}, failed {len(failed)}.')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
