"""기기 간 라이브러리 메타데이터 동기화 (archive.json + playlists.json).

WAV 파일은 OneDrive/Drive/Syncthing 등으로 맞추고,
목록·플레이리스트 메타는 export/import API로 맞춥니다.
"""

from __future__ import annotations

import hashlib
import os
import time
import uuid
from typing import Any, Literal

ImportMode = Literal["merge", "replace"]


def _ensure_track_id(record: dict[str, Any]) -> dict[str, Any]:
    tid = str(record.get("track_id") or record.get("id") or "").strip()
    if not tid:
        tid = str(uuid.uuid4())
        record["track_id"] = tid
    elif not record.get("track_id"):
        record["track_id"] = tid
    return record


def _file_sha256(path: str) -> str | None:
    if not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_mtime(path: str) -> float | None:
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def _paths() -> tuple[str, str]:
    from library import ARCHIVE_JSON_PATH, PLAYLISTS_JSON_PATH

    return ARCHIVE_JSON_PATH, PLAYLISTS_JSON_PATH


def get_sync_status() -> dict[str, Any]:
    """현재 기기 메타데이터 상태 요약."""
    from server.database import get_archive_cache, load_playlists

    archive_path, playlists_path = _paths()
    cache = get_archive_cache()
    records = cache.get_records()
    pdata = load_playlists()
    playlists = pdata.get("playlists") or {}
    return {
        "archive_path": archive_path,
        "playlists_path": playlists_path,
        "archive_track_count": len(records),
        "playlist_count": len(playlists) if isinstance(playlists, dict) else 0,
        "archive_mtime": _file_mtime(archive_path),
        "playlists_mtime": _file_mtime(playlists_path),
        "archive_sha256": _file_sha256(archive_path),
        "playlists_sha256": _file_sha256(playlists_path),
    }


def export_library_bundle(
    *,
    include_spotify_sync: bool = False,
) -> dict[str, Any]:
    """archive + playlists 를 한 번에 내보냅니다."""
    from server.database import get_archive_cache, load_playlists

    cache = get_archive_cache()
    records = cache.get_records()
    pdata = load_playlists()
    bundle: dict[str, Any] = {
        "version": 1,
        "format": "wavemash-library-bundle",
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "archive": records,
        "playlists": {
            "playlists": pdata.get("playlists") or {},
            "activity": pdata.get("activity") or {},
            "meta": pdata.get("meta") or {},
        },
        "stats": {
            "track_count": len(records),
            "playlist_count": len(pdata.get("playlists") or {}),
        },
    }
    if include_spotify_sync:
        from server.services.spotify_sync_service import get_sync_configs

        bundle["spotify_sync"] = get_sync_configs()
    return bundle


def _merge_playlists(
    current: dict[str, Any],
    incoming: dict[str, Any],
) -> dict[str, Any]:
    cur_pl = dict(current.get("playlists") or {})
    cur_act = dict(current.get("activity") or {})
    cur_meta = dict(current.get("meta") or {})

    in_pl = incoming.get("playlists") or {}
    in_act = incoming.get("activity") or {}
    in_meta = incoming.get("meta") or {}

    if not isinstance(in_pl, dict):
        return current

    for name, track_ids in in_pl.items():
        if not isinstance(track_ids, list):
            continue
        if name not in cur_pl:
            cur_pl[name] = list(track_ids)
        else:
            existing = list(cur_pl[name]) if isinstance(cur_pl[name], list) else []
            seen = set(str(t) for t in existing)
            for tid in track_ids:
                sid = str(tid)
                if sid and sid not in seen:
                    existing.append(sid)
                    seen.add(sid)
            cur_pl[name] = existing
        if name in in_act:
            cur_act[name] = max(float(cur_act.get(name) or 0), float(in_act.get(name) or 0))
        if name in in_meta and isinstance(in_meta.get(name), dict):
            base = dict(cur_meta.get(name) or {})
            base.update(in_meta[name])
            cur_meta[name] = base

    return {"playlists": cur_pl, "activity": cur_act, "meta": cur_meta}


def _merge_archive(
    current: list[dict[str, Any]],
    incoming: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int, int]:
    """track_id 기준 병합. incoming 경로가 비어 있으면 기존 로컬 경로 유지."""
    by_id: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for rec in current:
        _ensure_track_id(rec)
        tid = str(rec.get("track_id") or rec.get("id") or "")
        if not tid:
            continue
        by_id[tid] = dict(rec)
        order.append(tid)

    added = 0
    updated = 0
    for rec in incoming:
        if not isinstance(rec, dict):
            continue
        incoming_rec = dict(rec)
        _ensure_track_id(incoming_rec)
        tid = str(incoming_rec.get("track_id") or incoming_rec.get("id") or "")
        if not tid:
            continue
        if tid in by_id:
            existing = by_id[tid]
            old_path = str(existing.get("path") or existing.get("local_path") or "")
            new_path = str(incoming_rec.get("path") or incoming_rec.get("local_path") or "")
            merged = {**existing, **incoming_rec}
            if old_path and not new_path:
                if existing.get("path"):
                    merged["path"] = existing.get("path")
                if "local_path" in existing:
                    merged["local_path"] = existing.get("local_path")
            by_id[tid] = merged
            updated += 1
        else:
            by_id[tid] = incoming_rec
            order.append(tid)
            added += 1

    return [by_id[tid] for tid in order if tid in by_id], added, updated


def import_library_bundle(
    bundle: dict[str, Any],
    *,
    mode: ImportMode = "merge",
    import_archive: bool = True,
    import_playlists: bool = True,
) -> dict[str, Any]:
    """번들을 현재 기기에 반영합니다."""
    from desktop_app.archive_store import save_archive
    from server.database import get_archive_cache, load_playlists, save_playlists

    cache = get_archive_cache()
    archive_added = 0
    archive_updated = 0
    playlist_count = 0

    if import_archive and "archive" in bundle:
        incoming = bundle.get("archive") or []
        if not isinstance(incoming, list):
            raise ValueError("archive 는 배열이어야 합니다.")
        if mode == "replace":
            cleaned: list[dict[str, Any]] = []
            for rec in incoming:
                if isinstance(rec, dict):
                    item = dict(rec)
                    _ensure_track_id(item)
                    cleaned.append(item)
            save_archive(cleaned)
            cache.reload()
            archive_added = len(cleaned)
            archive_updated = 0
        else:
            current = cache.get_records()
            merged, archive_added, archive_updated = _merge_archive(current, incoming)
            save_archive(merged)
            cache.reload()

    if import_playlists and "playlists" in bundle:
        incoming_pl = bundle.get("playlists") or {}
        if isinstance(incoming_pl, dict) and "playlists" not in incoming_pl:
            incoming_pl = {"playlists": incoming_pl, "activity": {}, "meta": {}}
        if not isinstance(incoming_pl, dict):
            raise ValueError("playlists 는 객체여야 합니다.")

        if mode == "replace":
            save_playlists({
                "playlists": incoming_pl.get("playlists") or {},
                "activity": incoming_pl.get("activity") or {},
                "meta": incoming_pl.get("meta") or {},
            })
        else:
            current_pl = load_playlists()
            save_playlists(_merge_playlists(current_pl, incoming_pl))

        playlist_count = len((load_playlists().get("playlists") or {}))

    status = get_sync_status()
    return {
        "success": True,
        "mode": mode,
        "archive_added": archive_added,
        "archive_updated": archive_updated,
        "playlist_count": playlist_count,
        "status": status,
    }
