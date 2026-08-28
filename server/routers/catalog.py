"""공개 음악 카탈로그 검색 (Spotify)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from server.services.spotify_catalog import get_artist_profile, search_catalog

router = APIRouter(prefix="/catalog", tags=["카탈로그"])


@router.get("/search")
async def catalog_search(q: str = Query("", min_length=1, max_length=120)):
    return search_catalog(q)


@router.get("/artists/{artist_id}")
async def catalog_artist(artist_id: str):
    return get_artist_profile(artist_id)
