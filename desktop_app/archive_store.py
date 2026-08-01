"""Hybrid archive facade — JSON core + SQLite index (see library.py)."""

from __future__ import annotations

from typing import Any

from library import (
    ARCHIVE_JSON_PATH,
    delete_library_record,
    load_library_records,
    move_records_to_front,
    sanitize_record_for_db,
    save_library_records,
    upsert_library_record,
)

DB_FILE = ARCHIVE_JSON_PATH


def load_archive() -> list[dict[str, Any]]:
    return load_library_records()


def save_archive(records: list[dict[str, Any]]) -> None:
    save_library_records(records)


def upsert_record(
    records: list[dict[str, Any]],
    record: dict[str, Any],
    *,
    prepend: bool = False,
) -> list[dict[str, Any]]:
    return upsert_library_record(records, record, prepend=prepend)


def move_records_to_top(records: list[dict[str, Any]], track_ids: list[str]) -> list[dict[str, Any]]:
    return move_records_to_front(records, track_ids)


def delete_record(records: list[dict[str, Any]], track_id: str) -> list[dict[str, Any]]:
    return delete_library_record(records, track_id)


__all__ = [
    'DB_FILE',
    'delete_record',
    'load_archive',
    'move_records_to_top',
    'sanitize_record_for_db',
    'save_archive',
    'upsert_record',
]
