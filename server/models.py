"""WaveMash Pydantic v2 모델 — 요청/응답 스키마 정의."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Track 모델
# ---------------------------------------------------------------------------

class Track(BaseModel):
    """트랙 전체 정보."""

    track_id: str = Field(..., description="트랙 고유 식별자 (UUID)")
    title: str = ""
    artist: str = ""
    primary_artist: str = ""
    album: str = ""
    genre: str = ""
    year: str = ""
    bpm: str = ""
    key: str = ""
    camelot_key: str = ""
    energy_level: int = 0
    bpm_source: str = ""
    platform: str = ""
    format: str = "WAV"
    url: str = ""
    external_id: str = ""
    thumbnail_url: str = ""
    local_path: str = ""
    has_cover: bool = False
    has_file: bool = False
    dominant_color: str | None = None
    analysis: dict[str, Any] | None = None
    preview_url: str = ""
    duration_ms: int = 0
    popularity: int = 0
    catalog_only: bool = False


class TrackCreate(BaseModel):
    """수동 트랙 생성 요청 (거의 사용 안 함)."""

    title: str
    artist: str
    album: str = "Singles"
    genre: str = "Unknown"
    year: str = ""
    platform: str = "Manual"
    url: str = ""


class TrackUpdate(BaseModel):
    """트랙 메타데이터 수정 요청."""

    title: str | None = None
    artist: str | None = None
    album: str | None = None
    genre: str | None = None
    year: str | None = None
    bpm: str | None = None
    key: str | None = None
    energy_level: int | None = None


# ---------------------------------------------------------------------------
# Playlist 모델
# ---------------------------------------------------------------------------

class Playlist(BaseModel):
    """플레이리스트 정보."""

    name: str
    track_ids: list[str] = Field(default_factory=list)
    track_count: int = 0
    activity: float | None = None
    vibe: str = "other"
    shade: int = 0
    color: str = "#6D4C41"
    # local = 수동/로컬 전용, spotify = 스포티파이 동기화 연동
    source: str = "local"
    spotify_url: str | None = None
    sync_id: str | None = None
    sync_auto: bool | None = None
    sync_status: str | None = None
    last_synced_at: str | None = None
    spotify_count: int | None = None
    local_count: int | None = None
    missing_count: int | None = None


class PlaylistCreate(BaseModel):
    """플레이리스트 생성 요청."""

    name: str = Field(..., min_length=1, description="플레이리스트 이름")
    track_ids: list[str] = Field(default_factory=list)
    vibe: str | None = None
    shade: int | None = None
    color: str | None = None


class PlaylistUpdate(BaseModel):
    """플레이리스트 수정 요청 (이름 변경, 트랙 재정렬, 바이브/색)."""

    name: str | None = None
    track_ids: list[str] | None = None
    vibe: str | None = None
    shade: int | None = None
    color: str | None = None


class PlaylistAddTrack(BaseModel):
    """플레이리스트에 트랙 추가 요청 (로컬 파일 또는 카탈로그 스텁)."""

    track_id: str
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    cover_url: str | None = None
    thumbnail_url: str | None = None
    preview_url: str | None = None
    spotify_url: str | None = None
    platform: str | None = None
    external_id: str | None = None
    duration_ms: int | None = None
    popularity: int | None = None


# ---------------------------------------------------------------------------
# Download 모델
# ---------------------------------------------------------------------------

class DownloadRequest(BaseModel):
    """다운로드 요청."""

    url: str = Field(..., min_length=5, description="YouTube 또는 Spotify URL")
    # Master = wav (무손실), Mobile = mp3 320k
    format: str = Field(default="wav", description="wav | mp3")
    # Spotify 플리/앨범에서 선택한 트랙만 다운로드 (Spotify track id)
    track_ids: list[str] | None = Field(default=None, description="선택 트랙 ID 목록")


class DownloadResolveRequest(BaseModel):
    """다운로드 전 곡 목록 조회."""

    url: str = Field(..., min_length=5, description="Spotify URL")


class DownloadProgress(BaseModel):
    """다운로드 진행 SSE 이벤트 데이터."""

    job_id: str
    status: str = "pending"  # pending | downloading | completed | failed
    progress: float = 0.0  # 0.0 ~ 1.0
    message: str = ""
    stage: str = ""  # listing | downloading | converting | cover | metadata | done
    current: int | None = None  # 현재 곡 번호 (1-based)
    total: int | None = None  # 전체 곡 수
    remaining: int | None = None
    track_title: str | None = None
    track_artist: str | None = None
    skipped: int | None = None
    track: Track | None = None
    tracks: list[Track] | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Library 통계 모델
# ---------------------------------------------------------------------------

class LibraryStats(BaseModel):
    """라이브러리 전체 통계."""

    total_tracks: int = 0
    total_artists: int = 0
    total_albums: int = 0
    total_with_files: int = 0
    genres: dict[str, int] = Field(default_factory=dict)
    platforms: dict[str, int] = Field(default_factory=dict)
    bpm_distribution: dict[str, int] = Field(default_factory=dict)
    recent_tracks: list[Track] = Field(default_factory=list)


class ArtistInfo(BaseModel):
    """아티스트 정보."""

    name: str
    track_count: int = 0


class AlbumInfo(BaseModel):
    """앨범 정보."""

    name: str
    artist: str = ""
    track_count: int = 0
    has_cover: bool = False


class GenreInfo(BaseModel):
    """장르 정보."""

    name: str
    track_count: int = 0


# ---------------------------------------------------------------------------
# Auto-playlist 규칙
# ---------------------------------------------------------------------------

class AutoPlaylistRule(BaseModel):
    """자동 플레이리스트 분류 규칙."""

    name: str = Field(..., description="플레이리스트 이름")
    genre_patterns: list[str] = Field(default_factory=list)
    bpm_min: int | None = None
    bpm_max: int | None = None
    key_patterns: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 사용자 및 소셜 모델
# ---------------------------------------------------------------------------

class UserProfile(BaseModel):
    """사용자 프로필 정보."""
    user_id: str
    username: str
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    track_count: int = 0
    friend_count: int = 0
    created_at: str | None = None

class UserProfileUpdate(BaseModel):
    """사용자 프로필 업데이트."""
    display_name: str | None = None
    bio: str | None = None
    favorite_genre: str | None = None

class ActivityItem(BaseModel):
    """소셜 활동 피드 항목."""
    id: str
    user_id: str
    action_type: str
    target_type: str
    target_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str

class ChartEntry(BaseModel):
    """차트 항목."""
    track_id: str
    title: str
    artist: str
    album: str | None = None
    genre: str | None = None
    collector_count: int = 0
    thumbnail_url: str | None = None

class PostCreate(BaseModel):
    """인스타 피드 포스트 생성 (사진 + 음악/플리 매칭 다이어리)."""
    track_id: str | None = None
    playlist_id: str | None = None
    image_url: str | None = None
    caption: str = ""
    tags: list[str] = Field(default_factory=list)
    visibility: str = "public"  # 'public' | 'private' | 'friends'


class PlaylistTrackAdd(BaseModel):
    """플레이리스트에 트랙 추가 요청."""
    track_id: str
    title: str | None = None
    artist: str | None = None
    cover_url: str | None = None


class PostCommentCreate(BaseModel):
    """포스트 댓글 생성."""
    content: str

class HighlightCreate(BaseModel):
    """스토리 큐레이션 하이라이트 생성."""
    title: str
    cover_url: str = ""
    track_ids: list[str] = Field(default_factory=list)

class UserYouTubeTrackItem(BaseModel):
    videoId: str
    rawTitle: str
    artist: str
    cleanTitle: str
    channelTitle: str = ""
    thumbnailUrl: str = ""
    duration: str = ""

class UserYouTubePlaylistSync(BaseModel):
    id: str
    title: str
    description: str = ""
    thumbnailUrl: str = ""
    itemCount: int = 0
    tracks: list[UserYouTubeTrackItem] = Field(default_factory=list)

class TrackLikeActionReq(BaseModel):

    title: str = "Unknown Title"
    artist: str = "Unknown Artist"
    cover_url: str = ""

class TrackDownloadActionReq(BaseModel):
    title: str = "Unknown Title"
    artist: str = "Unknown Artist"
    cover_url: str = ""

class ArtistFollowActionReq(BaseModel):
    artist_name: str = ""
    artist_image_url: str = ""





# ---------------------------------------------------------------------------
# 공통 응답 모델
# ---------------------------------------------------------------------------

class MessageResponse(BaseModel):
    """단순 메시지 응답."""

    message: str
    success: bool = True


class PaginatedResponse(BaseModel):
    """페이지네이션 응답 래퍼."""

    items: list[Track] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50
    total_pages: int = 0
