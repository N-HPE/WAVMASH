"""메타데이터 서비스 — BPM/Key 보강 래퍼.

track_metadata.py의 ``enrich_record_metadata``를 비동기 친화적으로 감싸고,
일괄 메타데이터 갱신을 지원합니다.
"""

from __future__ import annotations

import asyncio
from typing import Any

from server.database import get_archive_cache

# 기존 모듈 임포트
from library import (
    apply_bpm_key_to_record,
    apply_track_metadata,
    needs_bpm_key_update,
)
from track_metadata import enrich_record_metadata


async def enrich_single_track(track_id: str) -> dict[str, Any] | None:
    """단일 트랙의 BPM/Key 메타데이터를 보강합니다.

    Returns:
        업데이트된 레코드, 또는 트랙을 찾지 못한 경우 None.
    """
    cache = get_archive_cache()
    record = cache.get_record(track_id)
    if not record:
        return None

    updated = await asyncio.to_thread(enrich_record_metadata, record)
    if updated:
        cache.upsert(record, prepend=False)
    return record


async def batch_enrich_metadata(
    track_ids: list[str] | None = None,
    *,
    only_missing: bool = True,
) -> dict[str, Any]:
    """여러 트랙의 메타데이터를 일괄 보강합니다.

    Args:
        track_ids: 대상 트랙 ID 목록. None이면 전체 라이브러리.
        only_missing: True이면 BPM/Key가 없는 트랙만 대상.

    Returns:
        ``{"updated": int, "skipped": int, "failed": int}``
    """
    cache = get_archive_cache()
    records = cache.get_records()

    if track_ids:
        target_set = set(track_ids)
        targets = [
            r for r in records
            if str(r.get("track_id") or r.get("id")) in target_set
        ]
    else:
        targets = list(records)

    if only_missing:
        targets = [r for r in targets if needs_bpm_key_update(r)]

    updated = 0
    skipped = 0
    failed = 0

    for record in targets:
        try:
            result = await asyncio.to_thread(enrich_record_metadata, record)
            if result:
                cache.upsert(record, prepend=False)
                updated += 1
            else:
                skipped += 1
        except Exception:
            failed += 1

    return {"updated": updated, "skipped": skipped, "failed": failed}
