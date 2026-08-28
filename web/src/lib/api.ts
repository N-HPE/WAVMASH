/* ──────────────────────────────────────────────
   WaveMash — API Client
   ────────────────────────────────────────────── */

import type {
  Track,
  TrackUpdate,
  Playlist,
  PlaylistCreate,
  PlaylistUpdate,
  LibraryStats,
  ArtistInfo,
  AlbumInfo,
  GenreInfo,
  DownloadProgress,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class WaveMashAPI {
  private baseUrl: string;
  private authToken: string | null = null;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  setAuthToken(token: string | null) {
    this.authToken = token;
  }

  /* ── Generic Fetch Wrapper ── */

  private async fetch<T>(path: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...options?.headers as Record<string, string>,
      };

      if (this.authToken) {
        headers['Authorization'] = `Bearer ${this.authToken}`;
      }

      const res = await fetch(url, {
        ...options,
        headers,
      });

      if (!res.ok) {
        const errorBody = await res.text().catch(() => '');
        throw new Error(
          `API 오류 (${res.status}): ${errorBody || res.statusText}`
        );
      }

      // Handle 204 No Content
      if (res.status === 204) {
        return undefined as T;
      }

      return res.json() as Promise<T>;
    } catch (error) {
      if (error instanceof Error && error.message.startsWith('API 오류')) {
        throw error;
      }
      throw new Error(`네트워크 오류: 서버에 연결할 수 없습니다.`);
    }
  }

  private buildQueryString(params: Record<string, unknown>): string {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.append(key, String(value));
      }
    }
    const qs = searchParams.toString();
    return qs ? `?${qs}` : '';
  }

  /* ── Track Endpoints ── */

  async getTracks(params?: {
    search?: string;
    genre?: string;
    platform?: string;
    bpm_min?: number;
    bpm_max?: number;
    key?: string;
    sort_by?: string;
    sort_order?: string;
    skip?: number;
    limit?: number;
    page?: number;
    page_size?: number;
  }): Promise<Track[]> {
    const mapped = params
      ? {
          ...params,
          // 프론트 limit/skip → 서버 page/page_size
          page:
            params.page ??
            (params.skip != null && params.limit
              ? Math.floor(params.skip / params.limit) + 1
              : undefined),
          page_size: params.page_size ?? params.limit,
        }
      : undefined;
    const qs = mapped ? this.buildQueryString(mapped) : '';
    const res = await this.fetch<{ items: Track[] }>(`/api/tracks${qs}`);
    return res.items ?? [];
  }

  async getTrack(trackId: string): Promise<Track> {
    return this.fetch<Track>(`/api/tracks/${encodeURIComponent(trackId)}`);
  }

  async updateTrack(trackId: string, data: TrackUpdate): Promise<Track> {
    return this.fetch<Track>(`/api/tracks/${encodeURIComponent(trackId)}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteTrack(trackId: string): Promise<void> {
    return this.fetch<void>(`/api/tracks/${encodeURIComponent(trackId)}`, {
      method: 'DELETE',
    });
  }

  /* ── Download Endpoints ── */

  async startDownload(
    url: string,
    format: 'wav' | 'mp3' = 'wav'
  ): Promise<{ job_id: string; format?: string }> {
    return this.fetch<{ job_id: string; format?: string }>('/api/download', {
      method: 'POST',
      body: JSON.stringify({ url, format }),
    });
  }

  /** 태그 베이킹된 오디오 바이너리를 브라우저로 받아 로컬 저장. */
  async downloadExportBlob(
    jobId: string,
    trackId: string,
    fallbackName?: string
  ): Promise<void> {
    const url = `${this.baseUrl}/api/download/export/${encodeURIComponent(jobId)}/${encodeURIComponent(trackId)}`;
    const res = await fetch(url);
    if (!res.ok) {
      const detail = await res.text().catch(() => '');
      throw new Error(detail || `Export failed (${res.status})`);
    }
    const blob = await res.blob();
    let filename = fallbackName || 'track.wav';
    const cd = res.headers.get('Content-Disposition') || '';
    const m = cd.match(/filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i);
    if (m) {
      try {
        filename = decodeURIComponent(m[1] || m[2]);
      } catch {
        filename = m[1] || m[2] || filename;
      }
    }
    const a = document.createElement('a');
    const objectUrl = URL.createObjectURL(blob);
    a.href = objectUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(objectUrl);
  }

  subscribeDownloadProgress(
    jobId: string,
    onProgress: (data: DownloadProgress) => void
  ): () => void {
    const url = `${this.baseUrl}/api/download/status/${encodeURIComponent(jobId)}`;
    const eventSource = new EventSource(url);

    const handlePayload = (raw: string) => {
      try {
        const data = JSON.parse(raw) as DownloadProgress;
        onProgress(data);
        if (data.status === 'completed' || data.status === 'failed') {
          eventSource.close();
        }
      } catch {
        // Ignore parse errors
      }
    };

    // 서버는 event: progress / event: complete 로 보냄
    eventSource.addEventListener('progress', (event) => {
      handlePayload((event as MessageEvent).data);
    });
    eventSource.addEventListener('complete', (event) => {
      handlePayload((event as MessageEvent).data);
    });
    // 하트비트/unnamed 이벤트 대비
    eventSource.onmessage = (event) => {
      handlePayload(event.data);
    };

    eventSource.onerror = () => {
      // 연결이 끊겨도 완료 이벤트를 못 받았을 수 있음 — 닫기만
      if (eventSource.readyState === EventSource.CLOSED) {
        eventSource.close();
      }
    };

    return () => {
      eventSource.close();
    };
  }

  /* ── Playlist Endpoints ── */

  async getPlaylists(): Promise<Playlist[]> {
    return this.fetch<Playlist[]>('/api/playlists');
  }

  async getPlaylistTracks(name: string): Promise<(Track & { missing?: boolean })[]> {
    return this.fetch<(Track & { missing?: boolean })[]>(
      `/api/playlists/${encodeURIComponent(name)}/tracks`
    );
  }

  async createPlaylist(data: PlaylistCreate): Promise<Playlist> {
    return this.fetch<Playlist>('/api/playlists', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updatePlaylist(
    name: string,
    data: PlaylistUpdate
  ): Promise<Playlist> {
    return this.fetch<Playlist>(
      `/api/playlists/${encodeURIComponent(name)}`,
      {
        method: 'PUT',
        body: JSON.stringify(data),
      }
    );
  }

  async deletePlaylist(name: string): Promise<void> {
    return this.fetch<void>(
      `/api/playlists/${encodeURIComponent(name)}`,
      { method: 'DELETE' }
    );
  }

  async addTrackToPlaylist(
    nameOrId: string,
    trackId: string,
    meta?: { title?: string; artist?: string; cover_url?: string }
  ): Promise<any> {
    const isSocial = nameOrId.includes('-') && nameOrId.length > 20;
    const url = isSocial
      ? `/api/social/playlists/${encodeURIComponent(nameOrId)}/tracks`
      : `/api/playlists/${encodeURIComponent(nameOrId)}/tracks`;

    return this.fetch<any>(url, {
      method: 'POST',
      body: JSON.stringify({
        track_id: trackId,
        title: meta?.title,
        artist: meta?.artist,
        cover_url: meta?.cover_url,
      }),
    });
  }


  async removeTrackFromPlaylist(
    name: string,
    trackId: string
  ): Promise<void> {
    return this.fetch<void>(
      `/api/playlists/${encodeURIComponent(name)}/tracks/${encodeURIComponent(trackId)}`,
      { method: 'DELETE' }
    );
  }

  async autoParsePlaylist(): Promise<Playlist[]> {
    return this.fetch<Playlist[]>('/api/playlists/auto-parse', {
      method: 'POST',
    });
  }

  /* ── Cover Endpoints ── */

  getCoverUrl(trackId: string, size?: number): string {
    const base = `${this.baseUrl}/api/covers/${encodeURIComponent(trackId)}`;
    return size ? `${base}?size=${size}` : base;
  }

  async getCoverColor(trackId: string): Promise<string> {
    const data = await this.fetch<{
      color?: string;
      dominant_color?: string;
    }>(`/api/covers/${encodeURIComponent(trackId)}/color`);
    return data.color || data.dominant_color || '#d4a853';
  }

  async getCoverColors(
    trackIds: string[]
  ): Promise<Record<string, string | null>> {
    if (!trackIds.length) return {};
    const data = await this.fetch<{ colors: Record<string, string | null> }>(
      '/api/covers/colors',
      {
        method: 'POST',
        body: JSON.stringify({ track_ids: trackIds }),
      }
    );
    return data.colors ?? {};
  }

  /* ── Library Endpoints ── */

  async getLibraryStats(): Promise<LibraryStats> {
    return this.fetch<LibraryStats>('/api/library/stats');
  }

  async getArtists(): Promise<ArtistInfo[]> {
    return this.fetch<ArtistInfo[]>('/api/library/artists');
  }

  async getAlbums(): Promise<AlbumInfo[]> {
    return this.fetch<AlbumInfo[]>('/api/library/albums');
  }

  async getGenres(): Promise<GenreInfo[]> {
    return this.fetch<GenreInfo[]>('/api/library/genres');
  }

  async searchLibrary(query: string): Promise<Track[]> {
    return this.fetch<Track[]>(
      `/api/library/search${this.buildQueryString({ q: query })}`
    );
  }

  async searchCatalog(query: string): Promise<import('./types').CatalogSearchResult> {
    return this.fetch<import('./types').CatalogSearchResult>(
      `/api/catalog/search${this.buildQueryString({ q: query })}`
    );
  }

  async getCatalogArtist(
    artistId: string
  ): Promise<import('./types').CatalogArtistProfile> {
    return this.fetch<import('./types').CatalogArtistProfile>(
      `/api/catalog/artists/${encodeURIComponent(artistId)}`
    );
  }

  async getCatalogAlbum(
    albumId: string
  ): Promise<import('./types').CatalogAlbumDetail> {
    return this.fetch<import('./types').CatalogAlbumDetail>(
      `/api/catalog/albums/${encodeURIComponent(albumId)}`
    );
  }

  async resolveCatalogPreview(
    title: string,
    artist: string,
    spotifyId?: string
  ): Promise<{ youtube_id: string; youtube_url: string; preview_url: string }> {
    return this.fetch<{
      youtube_id: string;
      youtube_url: string;
      preview_url: string;
    }>(
      `/api/catalog/preview${this.buildQueryString({
        title,
        artist,
        spotify_id: spotifyId || '',
      })}`
    );
  }

  /* ── Spotify Sync Endpoints ── */

  async getSpotifySyncConfigs(): Promise<import('./types').SpotifySyncConfig[]> {
    return this.fetch<import('./types').SpotifySyncConfig[]>('/api/spotify-sync/configs');
  }

  async addSpotifySyncConfig(
    url: string,
    auto_sync_enabled: boolean = true,
    sync_deletions: boolean = true
  ): Promise<import('./types').SpotifySyncConfig> {
    return this.fetch<import('./types').SpotifySyncConfig>('/api/spotify-sync/configs', {
      method: 'POST',
      body: JSON.stringify({ url, auto_sync_enabled, sync_deletions }),
    });
  }

  async updateSpotifySyncConfig(
    configId: string,
    data: { auto_sync_enabled?: boolean; sync_deletions?: boolean }
  ): Promise<import('./types').SpotifySyncConfig> {
    return this.fetch<import('./types').SpotifySyncConfig>(
      `/api/spotify-sync/configs/${encodeURIComponent(configId)}`,
      {
        method: 'PUT',
        body: JSON.stringify(data),
      }
    );
  }

  async deleteSpotifySyncConfig(configId: string): Promise<void> {
    return this.fetch<void>(
      `/api/spotify-sync/configs/${encodeURIComponent(configId)}`,
      { method: 'DELETE' }
    );
  }

  async triggerSpotifySync(configId: string): Promise<import('./types').SpotifySyncResult> {
    return this.fetch<import('./types').SpotifySyncResult>(
      `/api/spotify-sync/sync/${encodeURIComponent(configId)}`,
      { method: 'POST' }
    );
  }

  async triggerSpotifySyncAll(): Promise<import('./types').SpotifySyncResult[]> {
    return this.fetch<import('./types').SpotifySyncResult[]>(
      '/api/spotify-sync/sync-all',
      { method: 'POST' }
    );
  }

  /* ── Stream Endpoint ── */

  getStreamUrl(trackId: string): string {
    return `${this.baseUrl}/api/stream/${encodeURIComponent(trackId)}`;
  }

  /* ── Social / Profile Endpoints ── */

  async getMyProfile(): Promise<import('./types').UserProfile> {
    return this.fetch<import('./types').UserProfile>('/api/users/me');
  }

  async getProfile(username: string): Promise<import('./types').UserProfile> {
    return this.fetch<import('./types').UserProfile>(`/api/users/${encodeURIComponent(username)}`);
  }

  async updateMyProfile(data: Partial<import('./types').UserProfile>): Promise<import('./types').UserProfile> {
    return this.fetch<import('./types').UserProfile>('/api/users/me', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async collectTrack(trackId: string): Promise<void> {
    return this.fetch<void>(`/api/social/collect/${encodeURIComponent(trackId)}`, {
      method: 'POST',
    });
  }

  async uncollectTrack(trackId: string): Promise<void> {
    return this.fetch<void>(`/api/social/collect/${encodeURIComponent(trackId)}`, {
      method: 'DELETE',
    });
  }

  async getFeed(): Promise<import('./types').ActivityItem[]> {
    return this.fetch<import('./types').ActivityItem[]>('/api/social/feed');
  }

  async getMostCollectedChart(): Promise<import('./types').ChartEntry[]> {
    return this.fetch<import('./types').ChartEntry[]>('/api/social/charts/most-collected');
  }

  /* ── Instagram-Style Collection Feed & Posts Endpoints ── */

  async getPosts(params?: {
    user_id?: string;
    username?: string;
    tag?: string;
    limit?: number;
    offset?: number;
  }): Promise<import('./types').Post[]> {
    const qs = this.buildQueryString(params || {});
    return this.fetch<import('./types').Post[]>(`/api/social/posts${qs}`);
  }

  async createPost(data: {
    track_id?: string;
    playlist_id?: string;
    image_url?: string;
    caption: string;
    tags?: string[];
    visibility?: 'public' | 'private' | 'friends';
  }): Promise<import('./types').Post> {
    return this.fetch<import('./types').Post>('/api/social/posts', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }




  async deletePost(postId: string): Promise<void> {
    return this.fetch<void>(`/api/social/posts/${encodeURIComponent(postId)}`, {
      method: 'DELETE',
    });
  }

  async togglePostLike(postId: string): Promise<{ liked: boolean; likes_count: number }> {
    return this.fetch<{ liked: boolean; likes_count: number }>(
      `/api/social/posts/${encodeURIComponent(postId)}/like`,
      { method: 'POST' }
    );
  }

  async sharePost(postId: string): Promise<{ shares_count: number }> {
    return this.fetch<{ shares_count: number }>(
      `/api/social/posts/${encodeURIComponent(postId)}/share`,
      { method: 'POST' }
    );
  }

  async shareTrack(trackId: string): Promise<{ message: string; success: boolean }> {
    return this.fetch<{ message: string; success: boolean }>(
      `/api/social/tracks/${encodeURIComponent(trackId)}/share`,
      { method: 'POST' }
    );
  }


  async getPostComments(postId: string): Promise<import('./types').PostComment[]> {
    return this.fetch<import('./types').PostComment[]>(
      `/api/social/posts/${encodeURIComponent(postId)}/comments`
    );
  }

  async addPostComment(postId: string, content: string): Promise<import('./types').PostComment> {
    return this.fetch<import('./types').PostComment>(
      `/api/social/posts/${encodeURIComponent(postId)}/comments`,
      {
        method: 'POST',
        body: JSON.stringify({ content }),
      }
    );
  }

  async getHighlights(userIdOrUsername?: string): Promise<import('./types').HighlightItem[]> {
    const qs = userIdOrUsername ? `?user=${encodeURIComponent(userIdOrUsername)}` : '';
    return this.fetch<import('./types').HighlightItem[]>(`/api/social/highlights${qs}`);
  }

  async createHighlight(data: {
    title: string;
    cover_url?: string;
    track_ids: string[];
  }): Promise<import('./types').HighlightItem> {
    return this.fetch<import('./types').HighlightItem>('/api/social/highlights', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /* ── Track Social Interactions & Friend Activity Feed ── */

  async toggleTrackLike(
    trackId: string,
    meta?: { title?: string; artist?: string; cover_url?: string }
  ): Promise<{ liked: boolean; likes_count: number }> {
    return this.fetch<{ liked: boolean; likes_count: number }>(
      `/api/social/tracks/${encodeURIComponent(trackId)}/like`,
      {
        method: 'POST',
        body: JSON.stringify(meta || {}),
      }
    );
  }

  async recordTrackDownload(
    trackId: string,
    meta?: { title?: string; artist?: string; cover_url?: string }
  ): Promise<{ message: string; success: boolean }> {
    return this.fetch<{ message: string; success: boolean }>(
      `/api/social/tracks/${encodeURIComponent(trackId)}/download-event`,
      {
        method: 'POST',
        body: JSON.stringify(meta || {}),
      }
    );
  }

  async getTrackSocialStatus(
    trackId: string
  ): Promise<{ liked: boolean; likes_count: number; downloaded: boolean }> {
    return this.fetch<{ liked: boolean; likes_count: number; downloaded: boolean }>(
      `/api/social/tracks/${encodeURIComponent(trackId)}/status`
    );
  }

  async getActivityFeed(): Promise<any[]> {
    return this.fetch<any[]>('/api/social/feed');
  }

  async getUserLikedTracks(usernameOrId: string): Promise<any[]> {
    return this.fetch<any[]>(`/api/social/users/${encodeURIComponent(usernameOrId)}/liked-tracks`);
  }

  async getUserDownloadedTracks(usernameOrId: string): Promise<any[]> {
    return this.fetch<any[]>(`/api/social/users/${encodeURIComponent(usernameOrId)}/downloaded-tracks`);
  }


  /* ── User YouTube Database Persistence ── */

  async syncUserYouTubePlaylists(
    playlists: Array<{
      id: string;
      title: string;
      description?: string;
      thumbnailUrl?: string;
      itemCount?: number;
      tracks: Array<{
        videoId: string;
        rawTitle: string;
        artist: string;
        cleanTitle: string;
        channelTitle?: string;
        thumbnailUrl?: string;
        duration?: string;
      }>;
    }>
  ): Promise<{ message: string; success: boolean }> {
    return this.fetch<{ message: string; success: boolean }>('/api/social/youtube/sync', {
      method: 'POST',
      body: JSON.stringify(playlists),
    });
  }

  async getSavedYouTubePlaylists(userId?: string): Promise<any[]> {
    const qs = userId ? `?user_id=${encodeURIComponent(userId)}` : '';
    return this.fetch<any[]>(`/api/social/youtube/playlists${qs}`);
  }

  async getSavedYouTubePlaylistTracks(playlistId: string, userId?: string): Promise<any[]> {
    const qs = userId ? `?user_id=${encodeURIComponent(userId)}` : '';
    return this.fetch<any[]>(`/api/social/youtube/playlists/${encodeURIComponent(playlistId)}/tracks${qs}`);
  }
}


export const api = new WaveMashAPI();
export default api;

