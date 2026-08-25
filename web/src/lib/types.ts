/* ──────────────────────────────────────────────
   WaveMash — TypeScript 타입 정의
   ────────────────────────────────────────────── */

export interface Track {
  track_id: string;
  title: string;
  artist: string;
  primary_artist: string;
  album: string;
  genre: string;
  year: string;
  /** API는 number로 통일 (0 = 미상) */
  bpm: number;
  key: string;
  camelot_key: string;
  energy_level: number;
  platform: string;
  url: string;
  external_id?: string;
  thumbnail_url?: string;
  local_path?: string;
  has_cover: boolean;
  has_file: boolean;
  dominant_color?: string;
  format?: string;
  missing?: boolean;
}



export interface TrackUpdate {
  title?: string;
  artist?: string;
  album?: string;
  genre?: string;
  year?: string;
  bpm?: number | string;
  key?: string;
  energy_level?: number;
}

export interface Playlist {
  id?: string;
  name: string;
  title?: string;
  description?: string;
  is_public?: boolean;
  track_ids: string[];
  track_count: number;
  activity?: number | null;
  last_activity?: number | null;
  /** 바이브(장르) 카테고리: pop | rnb | hiphop | house | techno | bass | chill | other */
  vibe?: string;
  /** 같은 바이브 안 세부 톤 (0=코어/대중, 클수록 밝고 가벼움) */
  shade?: number;
  /** 표시용 hex 색상 */
  color?: string;
  /**
   * local = 로컬/YouTube 수집
   * spotify = Spotify 마이그레이션(이전용)으로 들어온 플리
   */
  source?: 'local' | 'spotify' | string;
  spotify_url?: string | null;
  sync_id?: string | null;
  sync_auto?: boolean | null;
  sync_status?: string | null;
  last_synced_at?: string | null;
  spotify_count?: number | null;
  local_count?: number | null;
  missing_count?: number | null;
}


export interface PlaylistCreate {
  name: string;
  title?: string;
  description?: string;
  is_public?: boolean;
  track_ids?: string[];
  vibe?: string;
  shade?: number;
  color?: string;
}


export interface PlaylistUpdate {
  name?: string;
  track_ids?: string[];
  vibe?: string;
  shade?: number;
  color?: string;
}

export type PlaylistViewMode = 'block' | 'list';

export interface LibraryStats {
  total_tracks: number;
  total_artists: number;
  total_albums: number;
  total_playlists: number;
  total_with_files?: number;
  genres: Record<string, number>;
  platforms: Record<string, number>;
  bpm_distribution?: Record<string, number>;
  recent_tracks: Track[];
}

export interface ArtistInfo {
  name: string;
  track_count: number;
  albums: string[];
}

export interface AlbumInfo {
  name: string;
  artist: string;
  track_count: number;
  year: string;
  has_cover: boolean;
  track_ids: string[];
}

export interface GenreInfo {
  name: string;
  track_count: number;
}

export interface DownloadRequest {
  url: string;
}

export interface DownloadProgress {
  job_id: string;
  progress: number; // 0.0 ~ 1.0
  message: string;
  status: "pending" | "downloading" | "completed" | "failed";
  stage?: string;
  current?: number | null;
  total?: number | null;
  remaining?: number | null;
  track_title?: string | null;
  track_artist?: string | null;
  skipped?: number | null;
  track_count?: number;
  track?: Track;
  tracks?: Track[];
  error?: string;
}

export interface PaginatedResponse<T> {
  items?: T[];
  tracks?: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AutoParseResponse {
  created: Record<string, number>;
  playlists: Playlist[];
}

export interface BatchEnrichRequest {
  track_ids?: string[] | null;
  only_missing?: boolean;
}

export interface BatchEnrichResponse {
  updated: number;
  skipped: number;
  failed: number;
}

export interface LibrarySyncStatus {
  archive_path: string;
  playlists_path: string;
  archive_track_count: number;
  playlist_count: number;
  archive_mtime?: number | null;
  playlists_mtime?: number | null;
  archive_sha256?: string | null;
  playlists_sha256?: string | null;
}

export interface LibraryImportResponse {
  success: boolean;
  mode: string;
  archive_added: number;
  archive_updated: number;
  playlist_count: number;
  status?: LibrarySyncStatus | null;
}

export type ViewMode = "grid" | "list";
export type SortField = "title" | "artist" | "bpm" | "year" | "genre" | "recent";
export type SortOrder = "asc" | "desc";

/** Spotify 동기화 = 구독 해지 전 WaveMash로 옮기는 임시 마이그레이션 툴 */
export interface SpotifySyncConfig {
  id: string;
  url: string;
  name: string;
  auto_sync_enabled: boolean;
  sync_deletions: boolean;
  last_synced_at: string | null;
  status?: string;
  track_count: number;
  local_count?: number;
  missing_count?: number;
  missing_ids?: string[];
  synced_track_ids: string[];
}

export interface SpotifySyncResult {
  config_id: string;
  name?: string;
  total_spotify_tracks?: number;
  local_count?: number;
  missing_count?: number;
  missing_ids?: string[];
  downloaded?: number;
  deleted?: number;
  deleted_titles?: string[];
  status?: string;
  synced_at?: string;
  error?: string;
}

export interface UserProfile {
  user_id: string;
  username: string;
  display_name: string;
  bio: string;
  avatar_url: string;
  track_count: number;
  friend_count: number;
  is_public: boolean;
  favorite_genre: string;
}

export interface ActivityItem {
  id: string;
  user_id: string;
  action_type: string;
  target_type: string;
  target_id: string;
  metadata: any;
  created_at: string;
  user?: UserProfile;
}

export interface ChartEntry {
  track_id: string;
  title: string;
  artist: string;
  album: string;
  genre: string;
  collector_count: number;
  thumbnail_url: string;
}

export interface Post {
  id: string;
  user_id: string;
  track_id?: string;
  playlist_id?: string;
  image_url?: string;
  caption: string;
  tags: string[];
  visibility?: 'public' | 'private' | 'friends';
  likes_count: number;
  comments_count: number;
  shares_count?: number;
  downloads_count?: number;
  created_at: string;
  user?: UserProfile;
  track?: Track;
  is_liked?: boolean;
}

export interface PostComment {
  id: string;
  post_id: string;
  user_id: string;
  content: string;
  created_at: string;
  user?: UserProfile;
}

export interface HighlightItem {
  id: string;
  user_id: string;
  title: string;
  cover_url?: string;
  track_ids: string[];
  created_at: string;
}
