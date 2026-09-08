"""WaveMash Masterpiece Albums 라우터.

아티산별(Nova, Echo, Yachi, Personal) 명반 수집, 조회, 관리 엔드포인트.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from server.models import MasterAlbum, MasterAlbumCreate, MessageResponse
from server.services.album_service import get_album_service

router = APIRouter(prefix="/albums", tags=["명반 라이브러리"])


@router.get("", response_model=list[MasterAlbum])
async def list_albums(
    artisan: str = Query("all", description="아티산 필터 (all, nova, echo, yachi, personal)"),
    search: str | None = Query(None, description="앨범명/아티스트/코멘트 검색"),
    genre: str | None = Query(None, description="장르 필터"),
) -> list[MasterAlbum]:
    """수집된 명반 목록을 반환합니다."""
    svc = get_album_service()
    albums = svc.list_albums(artisan=artisan, search=search, genre=genre)
    return [MasterAlbum(**a) for a in albums]


@router.post("", response_model=MasterAlbum, status_code=status.HTTP_201_CREATED)
async def collect_album(data: MasterAlbumCreate) -> MasterAlbum:
    """새로운 명반을 컬렉션에 추가(수집)합니다."""
    svc = get_album_service()
    created = svc.add_album(data.model_dump())
    return MasterAlbum(**created)


@router.get("/{album_id}", response_model=MasterAlbum)
async def get_album(album_id: str) -> MasterAlbum:
    """명반 상세 정보 및 트랙 목록을 반환합니다."""
    svc = get_album_service()
    album = svc.get_album(album_id)
    if not album:
        raise HTTPException(status_code=404, detail="해당 명반을 찾을 수 없습니다.")
    return MasterAlbum(**album)


@router.delete("/{album_id}", response_model=MessageResponse)
async def delete_album(album_id: str) -> MessageResponse:
    """수집된 명반을 라이브러리에서 제거합니다."""
    svc = get_album_service()
    ok = svc.delete_album(album_id)
    if not ok:
        raise HTTPException(status_code=404, detail="해당 명반을 찾을 수 없습니다.")
    return MessageResponse(message="명반이 라이브러리에서 삭제되었습니다.")


@router.post("/reset-defaults", response_model=list[MasterAlbum])
async def reset_albums_to_defaults() -> list[MasterAlbum]:
    """명반 라이브러리를 아티산 추천 기본 명반들로 초기화합니다."""
    svc = get_album_service()
    albums = svc.reset_to_defaults()
    return [MasterAlbum(**a) for a in albums]


@router.post("/clear-legacy", response_model=MessageResponse)
async def clear_legacy_tracks() -> MessageResponse:
    """기존의 낱개 싱글 트랙들을 라이브러리에서 초기화(삭제)합니다."""
    svc = get_album_service()
    count = svc.clear_legacy_archive()
    return MessageResponse(message=f"기존 {count}개의 낱개 트랙을 초기화했습니다.")
