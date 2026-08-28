"""WaveMash 데이터베이스 레이어 — archive.json + SQLite 인덱스 래퍼.

기존 ``library.py`` 및 ``desktop_app/archive_store.py``를 감싸서
서버에서 안전하게 사용할 수 있는 스레드 안전 인터페이스를 제공합니다.
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any

from server.config import get_settings

# 기존 모듈 임포트 (config.py가 sys.path를 이미 설정)
from library import (
    PLAYLISTS_JSON_PATH,
    TrackIndexDB,
    ensure_track_id,
    find_cover_sidecar,
    version_group_key,
)
from desktop_app.archive_store import (
    delete_record,
    load_archive,
    save_archive,
    upsert_record,
)


# ---------------------------------------------------------------------------
# 스레드 안전 아카이브 캐시
# ---------------------------------------------------------------------------

class ArchiveCache:
    """archive.json 레코드의 인-메모리 캐시 (락 기반 동시성 보호 + Supabase 연동)."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._records: list[dict[str, Any]] = []
        self._loaded = False

    def load(self, *, force: bool = False) -> list[dict[str, Any]]:
        """아카이브를 로드합니다. force=True이면 디스크/Supabase에서 새로 로드합니다."""
        from server.supabase_db import is_supabase_enabled, fetch_tracks_from_supabase

        with self._lock:
            if not self._loaded or force:
                records: list[dict[str, Any]] = []
                if is_supabase_enabled():
                    try:
                        sb_records, _ = fetch_tracks_from_supabase(limit=5000)
                        if sb_records:
                            records = sb_records
                    except Exception:
                        pass
                
                if not records:
                    records = load_archive()

                self._records = records
                self._loaded = True
            return list(self._records)

    def get_records(self) -> list[dict[str, Any]]:
        """현재 캐시된 레코드를 반환합니다."""
        with self._lock:
            if not self._loaded:
                return self.load()
            return list(self._records)

    def get_record(self, track_id: str) -> dict[str, Any] | None:
        """track_id로 단일 레코드를 찾습니다."""
        with self._lock:
            records = self.get_records()
            for rec in records:
                if str(rec.get("track_id") or rec.get("id")) == track_id:
                    return dict(rec)
        return None

    def upsert(self, record: dict[str, Any], *, prepend: bool = True) -> list[dict[str, Any]]:
        """레코드를 추가/갱신하고 디스크 및 Supabase에 저장합니다."""
        from server.supabase_db import is_supabase_enabled, upsert_track_to_supabase

        with self._lock:
            self._records = upsert_record(self._records, record, prepend=prepend)
            save_archive(self._records)
            if is_supabase_enabled():
                try:
                    upsert_track_to_supabase(record)
                except Exception:
                    pass
            return list(self._records)

    def delete(self, track_id: str) -> list[dict[str, Any]]:
        """레코드를 삭제하고 디스크 및 Supabase에서 제거합니다."""
        from server.supabase_db import is_supabase_enabled, delete_track_from_supabase

        with self._lock:
            self._records = delete_record(self._records, track_id)
            save_archive(self._records)
            if is_supabase_enabled():
                try:
                    delete_track_from_supabase(track_id)
                except Exception:
                    pass
            return list(self._records)

    def save(self) -> None:
        """현재 캐시를 디스크에 저장합니다."""
        with self._lock:
            save_archive(self._records)

    def reload(self) -> list[dict[str, Any]]:
        """디스크 및 Supabase에서 강제로 다시 로드합니다."""
        return self.load(force=True)


# ---------------------------------------------------------------------------
# 플레이리스트 I/O
# ---------------------------------------------------------------------------

def _playlists_path() -> str:
    return PLAYLISTS_JSON_PATH


def load_playlists() -> dict[str, Any]:
    """playlists.json 또는 Supabase를 읽어 ``{playlists, activity, meta}`` 형태로 반환합니다."""
    from server.vibe_palette import ensure_playlist_meta
    from server.supabase_db import is_supabase_enabled, fetch_playlists_from_supabase

    if is_supabase_enabled():
        try:
            sb_data = fetch_playlists_from_supabase()
            if sb_data.get("playlists"):
                return ensure_playlist_meta(sb_data)
        except Exception:
            pass

    path = _playlists_path()
    if not os.path.isfile(path):
        return {"playlists": {}, "activity": {}, "meta": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"playlists": {}, "activity": {}, "meta": {}}
        result = {
            "playlists": data.get("playlists", {}) or {},
            "activity": data.get("activity", {}) or {},
            "meta": data.get("meta", {}) or {},
        }
        return ensure_playlist_meta(result)
    except Exception:
        return {"playlists": {}, "activity": {}, "meta": {}}


def save_playlists(data: dict[str, Any]) -> None:
    """playlists.json 및 Supabase에 저장합니다."""
    from server.vibe_palette import ensure_playlist_meta
    from server.supabase_db import is_supabase_enabled, upsert_playlist_to_supabase

    path = _playlists_path()
    ensure_playlist_meta(data)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    if is_supabase_enabled():
        playlists = data.get("playlists", {}) or {}
        meta_dict = data.get("meta", {}) or {}
        activity_dict = data.get("activity", {}) or {}
        for name, t_ids in playlists.items():
            m = meta_dict.get(name, {}) or {}
            act = activity_dict.get(name)
            try:
                upsert_playlist_to_supabase(name, t_ids, m, act)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# 유틸리티
# ---------------------------------------------------------------------------

def find_version_tracks(
    records: list[dict[str, Any]],
    track_id: str,
) -> list[dict[str, Any]]:
    """같은 곡의 다른 버전(Extended, Radio Edit 등)을 찾습니다."""
    target = None
    for rec in records:
        if str(rec.get("track_id") or rec.get("id")) == track_id:
            target = rec
            break
    if not target:
        return []

    target_key = version_group_key(
        target.get("artist", ""),
        target.get("title", ""),
    )
    versions: list[dict[str, Any]] = []
    for rec in records:
        if str(rec.get("track_id") or rec.get("id")) == track_id:
            continue
        rec_key = version_group_key(
            rec.get("artist", ""),
            rec.get("title", ""),
        )
        if rec_key == target_key:
            versions.append(rec)
    return versions


def record_has_cover(record: dict[str, Any]) -> bool:
    """트랙의 앨범 커버가 존재하는지 확인합니다 (사이드카 / CDN)."""
    if str(record.get("thumbnail_url") or "").startswith("http"):
        return True
    path = str(record.get("path") or record.get("local_path") or "")
    if not path or not os.path.isfile(path):
        return False
    return find_cover_sidecar(path) is not None


def record_has_file(record: dict[str, Any]) -> bool:
    """WAV 파일이 디스크에 존재하는지 확인합니다."""
    path = str(record.get("path") or record.get("local_path") or "")
    return bool(path and os.path.isfile(path))


# ---------------------------------------------------------------------------
# 싱글턴 인스턴스
# ---------------------------------------------------------------------------

_archive_cache = ArchiveCache()


def get_archive_cache() -> ArchiveCache:
    """글로벌 ArchiveCache 인스턴스를 반환합니다."""
    return _archive_cache
