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
  bpm: number;
  key: string;
  camelot_key: string;
  energy_level: number;
  platform: string;
  url: string;
  thumbnail_url?: string;
  local_path?: string;
  has_cover: boolean;
  has_file: boolean;
  dominant_color?: string;
  format?: string;
  external_id?: string;
  preview_url?: string;
  popularity?: number;
  duration_ms?: number;
  catalog_only?: boolean;
}

export interface CatalogTrack {
  id: string;
  title: string;
  artist: string;
  primary_artist: string;
  album: string;
  thumbnail_url: string;
  spotify_url: string;
  preview_url: string;
  popularity: number;
  duration_ms: number;
  explicit?: boolean;
}

export interface CatalogArtist {
  id: string;
  name: string;
  image_url: string;
  followers: number;
  genres: string[];
  spotify_url: string;
  popularity: number;
}

export interface CatalogAlbum {
  id: string;
  name: string;
  album_type: string;
  artist: string;
  thumbnail_url: string;
  spotify_url: string;
  release_date: string;
  total_tracks: number;
}

export interface CatalogSearchResult {
  artists: CatalogArtist[];
  tracks: CatalogTrack[];
}

export interface CatalogArtistProfile {
  artist: CatalogArtist;
  top_tracks: CatalogTrack[];
  albums: CatalogAlbum[];
  singles: CatalogAlbum[];
}

export interface CatalogAlbumDetail {
  album: CatalogAlbum;
  tracks: CatalogTrack[];
}

export interface CatalogChartTrack extends CatalogTrack {
  rank: number;
  previous_rank?: number | null;
  entry_status?: string;
  item_type?: 'track' | 'album';
  release_date?: string;
}

export interface CatalogChartGenre {
  id: string;
  label: string;
  tracks: CatalogChartTrack[];
}

export interface CatalogChart {
  region: string;
  region_label: string;
  playlist_name: string;
  playlist_id: string;
  chart_date?: string;
  updated_at: string;
  tracks: CatalogChartTrack[];
  genres?: CatalogChartGenre[];
}



export interface TrackUpdate {
  title?: string;
  artist?: string;
  album?: string;
  genre?: string;
  year?: string;
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
  /** local = 로컬 전용, spotify = 스포티파이 동기화 */
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
  genres: Record<string, number>;
  platforms: Record<string, number>;
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
  /** Master = wav, Mobile = mp3 */
  format?: "wav" | "mp3";
  /** Spotify playlist/album에서 선택한 트랙 ID */
  track_ids?: string[];
}

export interface DownloadResolveTrack {
  id: string;
  title: string;
  artist: string;
  album: string;
  spotify_url: string;
  duration_ms: number;
  image_url: string;
  in_library: boolean;
}

export interface DownloadResolveResult {
  kind: string;
  title: string;
  url: string;
  track_count: number;
  tracks: DownloadResolveTrack[];
}

export interface DownloadExport {
  track_id: string;
  export_name: string;
  format: string;
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
  exports?: DownloadExport[];
  ephemeral?: boolean;
  format?: string;
  error?: string;
}

export interface PaginatedResponse<T> {
  tracks: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export type ViewMode = "grid" | "list" | "crate" | "harmonic";
export type SortField = "title" | "artist" | "bpm" | "year" | "genre" | "recent";
export type SortOrder = "asc" | "desc";

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

