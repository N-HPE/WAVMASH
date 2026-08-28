import type { CatalogTrack, Track } from '@/lib/types';

export function catalogTrackToPlayerTrack(item: CatalogTrack): Track {
  const rawId = (item.id || '').trim();
  const isBeatport = rawId.startsWith('bp:');
  const trackId =
    rawId.startsWith('sp:') || isBeatport ? rawId : `sp:${rawId}`;
  const externalId = isBeatport
    ? rawId.slice(3)
    : rawId.startsWith('sp:')
      ? rawId.slice(3)
      : rawId;
  return {
    track_id: trackId,
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
    platform: isBeatport ? 'beatport' : 'spotify',
    url: item.spotify_url,
    thumbnail_url: item.thumbnail_url,
    has_cover: Boolean(item.thumbnail_url),
    has_file: false,
    preview_url: item.preview_url || undefined,
    popularity: item.popularity,
    duration_ms: item.duration_ms,
    external_id: externalId,
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

/** Spotify popularity(0–100) 티어 — UI는 색 뱃지만 사용 */
export type PopularityTierTone =
  | 'superstar'
  | 'mainstream'
  | 'established'
  | 'rising'
  | 'emerging';

export function popularityTier(popularity?: number): {
  label: string;
  tone: PopularityTierTone;
} {
  const p = Math.max(0, Math.min(100, Math.round(popularity || 0)));
  if (p >= 85) return { label: 'Superstar', tone: 'superstar' };
  if (p >= 70) return { label: 'Mainstream', tone: 'mainstream' };
  if (p >= 50) return { label: 'Established', tone: 'established' };
  if (p >= 30) return { label: 'Rising', tone: 'rising' };
  return { label: 'Emerging', tone: 'emerging' };
}
