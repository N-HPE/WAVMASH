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

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  /* ── Generic Fetch Wrapper ── */

  private async fetch<T>(path: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    try {
      const res = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
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

  async startDownload(url: string): Promise<{ job_id: string }> {
    return this.fetch<{ job_id: string }>('/api/download', {
      method: 'POST',
      body: JSON.stringify({ url }),
    });
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

  async addTrackToPlaylist(name: string, trackId: string): Promise<void> {
    return this.fetch<void>(
      `/api/playlists/${encodeURIComponent(name)}/tracks`,
      {
        method: 'POST',
        body: JSON.stringify({ track_id: trackId }),
      }
    );
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
}

export const api = new WaveMashAPI();
export default api;
