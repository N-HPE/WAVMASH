"""라이브러리 통계, 검색, 기기 간 메타 동기 API 라우터."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from server.database import get_archive_cache, load_playlists, record_has_cover, record_has_file
from server.models import (
    AlbumInfo,
    ArtistInfo,
    GenreInfo,
    LibraryImportRequest,
    LibraryImportResponse,
    LibraryStats,
    LibrarySyncStatus,
    Track,
)
from server.routers.tracks import _record_to_track
from server.services.library_sync_service import (
    export_library_bundle,
    get_sync_status,
    import_library_bundle,
)

router = APIRouter(prefix="/library", tags=["라이브러리"])


@router.get("/stats", response_model=LibraryStats)
async def get_library_stats() -> LibraryStats:
    """라이브러리 전체 통계를 반환합니다."""
    cache = get_archive_cache()
    records = cache.get_records()
    pdata = load_playlists()
    playlist_count = len(pdata.get("playlists") or {})

    artists: set[str] = set()
    albums: set[str] = set()
    genres: Counter[str] = Counter()
    platforms: Counter[str] = Counter()
    bpm_ranges: Counter[str] = Counter()
    with_files = 0

    for rec in records:
        artist = str(rec.get("primary_artist") or rec.get("artist") or "")
        if artist and artist != "Unknown":
            artists.add(artist)

        album = str(rec.get("album") or "")
        if album and album != "Singles":
            albums.add(f"{artist}||{album}")

        genre = str(rec.get("genre") or "Unknown")
        genres[genre] += 1

        platform = str(rec.get("platform") or "Unknown")
        platforms[platform] += 1

        try:
            bpm = int(float(rec.get("bpm") or 0))
            if bpm > 0:
                bucket = f"{(bpm // 10) * 10}-{(bpm // 10) * 10 + 9}"
                bpm_ranges[bucket] += 1
        except (TypeError, ValueError):
            pass

        if record_has_file(rec):
            with_files += 1

    recent = [_record_to_track(r) for r in records[:10]]

    return LibraryStats(
        total_tracks=len(records),
        total_artists=len(artists),
        total_albums=len(albums),
        total_playlists=playlist_count,
        total_with_files=with_files,
        genres=dict(genres.most_common(30)),
        platforms=dict(platforms),
        bpm_distribution=dict(sorted(bpm_ranges.items())),
        recent_tracks=recent,
    )


@router.get("/artists", response_model=list[ArtistInfo])
async def list_artists(
    search: str | None = Query(None, description="아티스트 이름 검색"),
    limit: int = Query(100, ge=1, le=500, description="최대 반환 수"),
) -> list[ArtistInfo]:
    """모든 아티스트와 트랙 수·앨범 목록을 반환합니다."""
    cache = get_archive_cache()
    records = cache.get_records()

    artist_counts: Counter[str] = Counter()
    artist_albums: dict[str, set[str]] = defaultdict(set)

    for rec in records:
        artist = str(rec.get("primary_artist") or rec.get("artist") or "Unknown")
        artist_counts[artist] += 1
        album = str(rec.get("album") or "").strip()
        if album and album != "Singles":
            artist_albums[artist].add(album)

    if search:
        q = search.lower()
        artist_counts = Counter({
            k: v for k, v in artist_counts.items()
            if q in k.lower()
        })

    return [
        ArtistInfo(
            name=name,
            track_count=count,
            albums=sorted(artist_albums.get(name, set())),
        )
        for name, count in artist_counts.most_common(limit)
    ]


@router.get("/albums", response_model=list[AlbumInfo])
async def list_albums(
    search: str | None = Query(None, description="앨범 이름 검색"),
    artist: str | None = Query(None, description="아티스트 필터"),
    limit: int = Query(100, ge=1, le=500, description="최대 반환 수"),
) -> list[AlbumInfo]:
    """모든 앨범과 트랙 수·연도·트랙 ID를 반환합니다."""
    cache = get_archive_cache()
    records = cache.get_records()

    album_data: dict[str, dict[str, Any]] = {}

    for rec in records:
        rec_artist = str(rec.get("primary_artist") or rec.get("artist") or "Unknown")
        album = str(rec.get("album") or "Singles")
        key = f"{rec_artist}||{album}"
        tid = str(rec.get("track_id") or rec.get("id") or "")

        if key not in album_data:
            album_data[key] = {
                "name": album,
                "artist": rec_artist,
                "count": 0,
                "has_cover": False,
                "year": "",
                "track_ids": [],
            }
        album_data[key]["count"] += 1
        if tid:
            album_data[key]["track_ids"].append(tid)
        year = str(rec.get("year") or "").strip()
        if year and not album_data[key]["year"]:
            album_data[key]["year"] = year
        if not album_data[key]["has_cover"] and record_has_cover(rec):
            album_data[key]["has_cover"] = True

    items = list(album_data.values())

    if search:
        q = search.lower()
        items = [i for i in items if q in i["name"].lower()]
    if artist:
        a_lower = artist.lower()
        items = [i for i in items if a_lower in i["artist"].lower()]

    items.sort(key=lambda x: x["count"], reverse=True)
    items = items[:limit]

    return [
        AlbumInfo(
            name=i["name"],
            artist=i["artist"],
            track_count=i["count"],
            year=i["year"],
            has_cover=i["has_cover"],
            track_ids=i["track_ids"],
        )
        for i in items
    ]


@router.get("/genres", response_model=list[GenreInfo])
async def list_genres(
    limit: int = Query(50, ge=1, le=200, description="최대 반환 수"),
) -> list[GenreInfo]:
    """모든 장르와 트랙 수를 반환합니다."""
    cache = get_archive_cache()
    records = cache.get_records()

    genre_counts: Counter[str] = Counter()
    for rec in records:
        genre = str(rec.get("genre") or "Unknown")
        genre_counts[genre] += 1

    return [
        GenreInfo(name=name, track_count=count)
        for name, count in genre_counts.most_common(limit)
    ]


@router.get("/search", response_model=list[Track])
async def search_library(
    q: str = Query(..., min_length=1, description="검색어"),
    limit: int = Query(50, ge=1, le=200, description="최대 반환 수"),
) -> list[Track]:
    """전체 필드에 대해 검색합니다."""
    cache = get_archive_cache()
    records = cache.get_records()

    query = q.lower()
    scored: list[tuple[float, dict[str, Any]]] = []

    for rec in records:
        score = 0.0
        title = str(rec.get("title") or "").lower()
        artist = str(rec.get("artist") or "").lower()
        album = str(rec.get("album") or "").lower()
        genre = str(rec.get("genre") or "").lower()
        primary = str(rec.get("primary_artist") or "").lower()

        if query == title:
            score += 10.0
        elif query in title:
            score += 5.0
        if query == artist or query == primary:
            score += 8.0
        elif query in artist or query in primary:
            score += 4.0
        if query in album:
            score += 2.0
        if query in genre:
            score += 1.0
        if query in str(rec.get("url") or "").lower():
            score += 3.0

        if score > 0:
            scored.append((score, rec))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [_record_to_track(rec) for _, rec in scored[:limit]]


# ---------------------------------------------------------------------------
# 기기 간 메타데이터 동기 (WAV 파일은 별도 클라우드 동기)
# ---------------------------------------------------------------------------

@router.get("/sync/status", response_model=LibrarySyncStatus)
async def library_sync_status() -> LibrarySyncStatus:
    """현재 기기 archive.json / playlists.json 상태(해시·개수)를 반환합니다."""
    return LibrarySyncStatus(**get_sync_status())


@router.get("/export")
async def export_library(
    include_spotify_sync: bool = Query(
        False,
        description="마이그레이션용 spotify_sync.json 설정도 포함",
    ),
) -> dict[str, Any]:
    """archive + playlists 번들을 JSON으로 내보냅니다 (다른 기기로 복사용)."""
    return export_library_bundle(include_spotify_sync=include_spotify_sync)


@router.post("/import", response_model=LibraryImportResponse)
async def import_library(body: LibraryImportRequest) -> LibraryImportResponse:
    """다른 기기에서 내보낸 번들을 merge 또는 replace로 반영합니다."""
    mode = (body.mode or "merge").lower().strip()
    if mode not in ("merge", "replace"):
        raise HTTPException(status_code=400, detail="mode 는 merge 또는 replace 여야 합니다.")

    bundle: dict[str, Any] = {
        "version": body.version,
        "format": body.format or "wavemash-library-bundle",
    }
    if body.archive is not None:
        bundle["archive"] = body.archive
    if body.playlists is not None:
        bundle["playlists"] = body.playlists

    if "archive" not in bundle and "playlists" not in bundle:
        raise HTTPException(status_code=400, detail="archive 또는 playlists 가 필요합니다.")

    try:
        result = import_library_bundle(
            bundle,
            mode=mode,  # type: ignore[arg-type]
            import_archive=body.import_archive and "archive" in bundle,
            import_playlists=body.import_playlists and "playlists" in bundle,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    status = result.get("status") or get_sync_status()
    return LibraryImportResponse(
        success=bool(result.get("success", True)),
        mode=str(result.get("mode") or mode),
        archive_added=int(result.get("archive_added") or 0),
        archive_updated=int(result.get("archive_updated") or 0),
        playlist_count=int(result.get("playlist_count") or 0),
        status=LibrarySyncStatus(**status),
    )
