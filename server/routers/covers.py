"""앨범 커버 API 라우터 — 커버 이미지 서빙 및 색상 추출."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from starlette.responses import Response

from server.database import get_archive_cache
from server.services.cover_service import (
    get_cover_bytes,
    make_thumbnail,
    resolve_colors_batch,
    resolve_dominant_color,
)

router = APIRouter(prefix="/covers", tags=["커버"])


class CoverColorsRequest(BaseModel):
    """배치 색상 조회 요청."""

    track_ids: list[str] = Field(
        default_factory=list,
        max_length=200,
        description="색상을 조회할 트랙 ID 목록 (최대 200)",
    )


class CoverColorsResponse(BaseModel):
    """배치 색상 조회 응답."""

    colors: dict[str, str | None] = Field(default_factory=dict)


@router.post("/colors", response_model=CoverColorsResponse)
async def get_cover_colors_batch(body: CoverColorsRequest) -> CoverColorsResponse:
    """여러 트랙의 커버 색상을 한 번에 조회합니다.

    서버 디스크 캐시를 우선 사용하고, 없는 항목만 Pillow로 추출합니다.
    """
    # 중복 제거 + 상한
    unique_ids = list(dict.fromkeys(body.track_ids))[:200]
    if not unique_ids:
        return CoverColorsResponse(colors={})

    cache = get_archive_cache()
    records_by_id: dict[str, dict] = {}
    for tid in unique_ids:
        rec = cache.get_record(tid)
        if rec:
            records_by_id[tid] = rec

    colors = resolve_colors_batch(records_by_id, unique_ids)
    return CoverColorsResponse(colors=colors)


@router.get("/{track_id}")
async def serve_cover(
    track_id: str,
    size: int | None = Query(None, ge=32, le=1200, description="썸네일 크기 (px)"),
) -> Response:
    """트랙의 앨범 커버 이미지를 반환합니다.

    ``size`` 파라미터를 지정하면 해당 크기로 축소된 썸네일을 반환합니다.
    """
    cache = get_archive_cache()
    record = cache.get_record(track_id)
    if not record:
        raise HTTPException(status_code=404, detail="트랙을 찾을 수 없습니다.")

    data, mime = get_cover_bytes(record)
    if not data:
        raise HTTPException(status_code=404, detail="앨범 커버를 찾을 수 없습니다.")

    # 썸네일 크기 요청 시 리사이즈
    if size is not None:
        data, mime = make_thumbnail(
            data, size=size, mime=mime or "image/jpeg", cache_key=track_id
        )

    return Response(
        content=data,
        media_type=mime or "image/jpeg",
        headers={
            "Cache-Control": "public, max-age=604800, immutable",
            "Content-Length": str(len(data)),
        },
    )


@router.get("/{track_id}/color")
async def get_cover_color(track_id: str) -> dict:
    """트랙의 앨범 커버에서 지배적 색상을 추출합니다.

    프론트엔드 글로우 이펙트에 사용됩니다. 결과는 서버 디스크에 캐시됩니다.

    Returns:
        ``{"track_id": "...", "color": "#RRGGBB", "dominant_color": "#RRGGBB", "has_cover": true}``
    """
    cache = get_archive_cache()
    record = cache.get_record(track_id)
    if not record:
        raise HTTPException(status_code=404, detail="트랙을 찾을 수 없습니다.")

    color = resolve_dominant_color(record, compute_if_missing=True)
    return {
        "track_id": track_id,
        "color": color,
        "dominant_color": color,
        "has_cover": color is not None,
    }
