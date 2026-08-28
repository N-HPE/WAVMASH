"""트랙 API 라우터 — CRUD, 필터링, 페이지네이션, 버전 조회."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from server.database import (
    get_archive_cache,
    find_version_tracks,
    record_has_cover,
    record_has_file,
)
from server.models import (
    MessageResponse,
    PaginatedResponse,
    Track,
    TrackUpdate,
)
from server.services.cover_service import get_cached_color
from server.services.metadata_service import enrich_single_track

# 기존 모듈
from library import (
    apply_track_metadata,
    camelot_from_key,
    delete_track_file,
    normalize_artist_meta,
    split_version,
)

router = APIRouter(prefix="/tracks", tags=["트랙"])


# ---------------------------------------------------------------------------
# 변환 유틸
# ---------------------------------------------------------------------------

def _record_to_track(rec: dict[str, Any]) -> Track:
    """내부 레코드 → Pydantic Track 모델 변환."""
    thumb = str(rec.get("thumbnail_url") or "")
    has_file = record_has_file(rec)
    return Track(
        track_id=str(rec.get("track_id") or rec.get("id") or ""),
        title=str(rec.get("title") or ""),
        artist=str(rec.get("artist") or ""),
        primary_artist=str(rec.get("primary_artist") or ""),
        album=str(rec.get("album") or ""),
        genre=str(rec.get("genre") or ""),
        year=str(rec.get("year") or ""),
        bpm=str(rec.get("bpm") or ""),
        key=str(rec.get("key") or ""),
        camelot_key=str(rec.get("camelot_key") or ""),
        energy_level=int(rec.get("energy_level") or 0),
        bpm_source=str(rec.get("bpm_source") or ""),
        platform=str(rec.get("platform") or ""),
        format=str(rec.get("format") or ("catalog" if not has_file else "WAV")),
        url=str(rec.get("url") or ""),
        external_id=str(rec.get("external_id") or ""),
        thumbnail_url=thumb,
        local_path=str(rec.get("local_path") or rec.get("path") or ""),
        has_cover=record_has_cover(rec),
        has_file=has_file,
        dominant_color=get_cached_color(str(rec.get("track_id") or rec.get("id") or "")),
        analysis=rec.get("analysis") if isinstance(rec.get("analysis"), dict) else None,
        preview_url=str(rec.get("preview_url") or ""),
        duration_ms=int(rec.get("duration_ms") or 0),
        popularity=int(rec.get("popularity") or 0),
        catalog_only=bool(rec.get("catalog_only")) or (
            not has_file and str(rec.get("platform") or "").lower() in {"spotify", "youtube", "catalog"}
        ),
    )


# ---------------------------------------------------------------------------
# 엔드포인트
# ---------------------------------------------------------------------------

@router.get("", response_model=PaginatedResponse)
async def list_tracks(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(50, ge=1, le=200, description="페이지 크기"),
    search: str | None = Query(None, description="전체 검색어"),
    artist: str | None = Query(None, description="아티스트 필터"),
    genre: str | None = Query(None, description="장르 필터"),
    album: str | None = Query(None, description="앨범 필터"),
    platform: str | None = Query(None, description="플랫폼 필터"),
    bpm_min: int | None = Query(None, ge=1, description="최소 BPM"),
    bpm_max: int | None = Query(None, ge=1, description="최대 BPM"),
    key: str | None = Query(None, description="키 필터"),
    sort_by: str = Query("default", description="정렬 기준 (default, title, artist, bpm, key)"),
    sort_order: str = Query("asc", description="정렬 방향 (asc, desc)"),
) -> PaginatedResponse:
    """트랙 목록을 필터링/페이지네이션하여 반환합니다."""
    cache = get_archive_cache()
    records = cache.get_records()

    # 필터링
    filtered = records
    if search:
        q = search.lower()
        filtered = [
            r for r in filtered
            if q in str(r.get("title") or "").lower()
            or q in str(r.get("artist") or "").lower()
            or q in str(r.get("album") or "").lower()
            or q in str(r.get("genre") or "").lower()
            or q in str(r.get("primary_artist") or "").lower()
        ]
    if artist:
        a_lower = artist.lower()
        filtered = [
            r for r in filtered
            if a_lower in str(r.get("artist") or "").lower()
            or a_lower in str(r.get("primary_artist") or "").lower()
        ]
    if genre:
        g_lower = genre.lower()
        filtered = [
            r for r in filtered
            if g_lower in str(r.get("genre") or "").lower()
        ]
    if album:
        al_lower = album.lower()
        filtered = [
            r for r in filtered
            if al_lower in str(r.get("album") or "").lower()
        ]
    if platform:
        p_lower = platform.lower()
        filtered = [
            r for r in filtered
            if p_lower == str(r.get("platform") or "").lower()
        ]
    if bpm_min is not None or bpm_max is not None:
        def bpm_filter(r: dict) -> bool:
            try:
                bpm_val = int(float(r.get("bpm") or 0))
            except (TypeError, ValueError):
                return False
            if bpm_val <= 0:
                return False
            if bpm_min is not None and bpm_val < bpm_min:
                return False
            if bpm_max is not None and bpm_val > bpm_max:
                return False
            return True
        filtered = [r for r in filtered if bpm_filter(r)]
    if key:
        k_lower = key.lower()
        filtered = [
            r for r in filtered
            if k_lower in str(r.get("key") or "").lower()
            or k_lower in str(r.get("camelot_key") or "").lower()
        ]

    # 정렬
    reverse = sort_order.lower() == "desc"
    if sort_by == "title":
        filtered.sort(key=lambda r: str(r.get("title") or "").lower(), reverse=reverse)
    elif sort_by == "artist":
        filtered.sort(key=lambda r: str(r.get("artist") or "").lower(), reverse=reverse)
    elif sort_by == "bpm":
        def bpm_sort_key(r: dict) -> float:
            try:
                return float(r.get("bpm") or 0)
            except (TypeError, ValueError):
                return 0.0
        filtered.sort(key=bpm_sort_key, reverse=reverse)
    elif sort_by == "key":
        filtered.sort(key=lambda r: str(r.get("camelot_key") or r.get("key") or ""), reverse=reverse)

    # 페이지네이션
    total = len(filtered)
    total_pages = max(1, (total + page_size - 1) // page_size)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = filtered[start:end]

    tracks = [_record_to_track(r) for r in page_items]

    return PaginatedResponse(
        items=tracks,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{track_id}", response_model=Track)
async def get_track(track_id: str) -> Track:
    """단일 트랙 상세 정보를 반환합니다."""
    cache = get_archive_cache()
    record = cache.get_record(track_id)
    if not record:
        raise HTTPException(status_code=404, detail="트랙을 찾을 수 없습니다.")
    return _record_to_track(record)


@router.put("/{track_id}", response_model=Track)
async def update_track(track_id: str, body: TrackUpdate) -> Track:
    """트랙 메타데이터를 수정합니다."""
    cache = get_archive_cache()
    record = cache.get_record(track_id)
    if not record:
        raise HTTPException(status_code=404, detail="트랙을 찾을 수 없습니다.")

    # 업데이트할 필드만 적용
    update_data = body.model_dump(exclude_none=True)

    if "bpm" in update_data or "key" in update_data or "energy_level" in update_data:
        apply_track_metadata(
            record,
            bpm=update_data.get("bpm"),
            key=update_data.get("key"),
            energy_level=update_data.get("energy_level"),
        )
        update_data.pop("bpm", None)
        update_data.pop("key", None)
        update_data.pop("energy_level", None)

    for field_name, value in update_data.items():
        record[field_name] = value

    if "artist" in update_data:
        record = normalize_artist_meta(record)

    cache.upsert(record, prepend=False)
    return _record_to_track(record)


@router.delete("/{track_id}", response_model=MessageResponse)
async def delete_track(
    track_id: str,
    delete_file: bool = Query(False, description="WAV 파일도 함께 삭제"),
) -> MessageResponse:
    """트랙을 라이브러리에서 삭제합니다."""
    cache = get_archive_cache()
    record = cache.get_record(track_id)
    if not record:
        raise HTTPException(status_code=404, detail="트랙을 찾을 수 없습니다.")

    title = record.get("title", "")

    if delete_file:
        file_path = str(record.get("path") or record.get("local_path") or "")
        if file_path and os.path.isfile(file_path):
            delete_track_file(file_path)

    cache.delete(track_id)
    return MessageResponse(message=f"'{title}' 트랙이 삭제되었습니다.")


@router.get("/{track_id}/versions", response_model=list[Track])
async def get_track_versions(track_id: str) -> list[Track]:
    """같은 곡의 다른 버전(Extended, Radio Edit 등)을 반환합니다."""
    cache = get_archive_cache()
    records = cache.get_records()
    versions = find_version_tracks(records, track_id)
    return [_record_to_track(r) for r in versions]


@router.post("/{track_id}/enrich", response_model=Track)
async def enrich_track(track_id: str) -> Track:
    """트랙의 BPM/Key 메타데이터를 자동으로 보강합니다."""
    result = await enrich_single_track(track_id)
    if result is None:
        raise HTTPException(status_code=404, detail="트랙을 찾을 수 없습니다.")
    return _record_to_track(result)
