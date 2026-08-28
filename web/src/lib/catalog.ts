import type { CatalogTrack, Track } from '@/lib/types';

export function catalogTrackToPlayerTrack(item: CatalogTrack): Track {
  return {
    track_id: `sp:${item.id}`,
    title: item.title,
    artist: item.artist,
    primary_artist: item.primary_artist || item.artist,
    album: item.album,
    genre: '',
    year: '',
    bpm: 0,
    key: '',
    camelot_key: '',
    energy_level: 0,
    platform: 'spotify',
    url: item.spotify_url,
    thumbnail_url: item.thumbnail_url,
    has_cover: Boolean(item.thumbnail_url),
    has_file: false,
    preview_url: item.preview_url || undefined,
    popularity: item.popularity,
    duration_ms: item.duration_ms,
    external_id: item.id,
  };
}

export function formatDuration(ms?: number): string {
  if (!ms || ms <= 0) return '';
  const total = Math.round(ms / 1000);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function formatFollowers(n?: number): string {
  if (!n) return '0';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}
