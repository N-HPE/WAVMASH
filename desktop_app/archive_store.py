import json
import os
from typing import Any

from paths import PROJECT_DIR

DB_FILE = os.path.join(PROJECT_DIR, "archive.json")


JSON_SKIP_KEYS = {"cover_data", "cover_mime"}


def sanitize_record_for_db(record: dict[str, Any]) -> dict[str, Any]:
    return {
        k: v
        for k, v in record.items()
        if k not in JSON_SKIP_KEYS and not isinstance(v, (bytes, bytearray))
    }


def load_archive() -> list[dict[str, Any]]:
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        return [sanitize_record_for_db(r) for r in data if isinstance(r, dict)]
    except Exception:
        broken = DB_FILE + ".broken"
        try:
            os.replace(DB_FILE, broken)
        except OSError:
            pass
        return []


def save_archive(records: list[dict[str, Any]]) -> None:
    records = [sanitize_record_for_db(r) for r in records]
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=4, ensure_ascii=False)


def upsert_record(records: list[dict[str, Any]], record: dict[str, Any]) -> list[dict[str, Any]]:
    record = sanitize_record_for_db(record)
    existing = next((r for r in records if r.get("id") == record.get("id")), None)
    if existing:
        existing.update(record)
    else:
        records.append(record)
    save_archive(records)
    return records


def delete_record(records: list[dict[str, Any]], track_id: str) -> list[dict[str, Any]]:
    records = [r for r in records if r.get("id") != track_id]
    save_archive(records)
    return records

