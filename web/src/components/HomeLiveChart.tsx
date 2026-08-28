'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { TrendingUp } from 'lucide-react';
import api from '@/lib/api';
import type { CatalogChartGenre, CatalogChartTrack } from '@/lib/types';
import CatalogTrackRow from '@/components/CatalogTrackRow';
import { Skeleton } from '@/components/ui/skeleton';

const GENRE_TABS: Array<{ id: string; label: string }> = [
  { id: 'pop', label: '팝' },
  { id: 'hiphop', label: '힙합' },
  { id: 'rnb', label: 'R&B' },
  { id: 'dance', label: '댄스' },
  { id: 'rock', label: '록' },
  { id: 'indie', label: '인디' },
  { id: 'latin', label: '라틴' },
  { id: 'kpop', label: 'K-pop' },
];

function formatToday(): string {
  try {
    return new Date().toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  } catch {
    return new Date().toISOString().slice(0, 10);
  }
}

export default function HomeLiveChart() {
  const [genreId, setGenreId] = useState('pop');
  const [tracksByGenre, setTracksByGenre] = useState<
    Record<string, CatalogChartTrack[]>
  >({});
  const [chartDate, setChartDate] = useState(formatToday());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const cacheRef = useRef<Record<string, CatalogChartTrack[]>>({});
  const prefetchStarted = useRef(false);

  const loadGenre = useCallback(async (id: string, silent = false) => {
    if (cacheRef.current[id]?.length) {
      setTracksByGenre((prev) => ({ ...prev, [id]: cacheRef.current[id] }));
      if (!silent) setLoading(false);
      return;
    }
    if (!silent) {
      setLoading(true);
      setError(null);
    }
    try {
      const data = await api.getSpotifyChart(id, 10);
      const genre: CatalogChartGenre | undefined =
        (data.genres || []).find((g) => g.id === id) || data.genres?.[0];
      const tracks = genre?.tracks || data.tracks || [];
      cacheRef.current[id] = tracks;
      setTracksByGenre((prev) => ({ ...prev, [id]: tracks }));
      if (data.chart_date) {
        try {
          setChartDate(
            new Date(`${data.chart_date}T12:00:00`).toLocaleDateString('ko-KR', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })
          );
        } catch {
          /* keep */
        }
      }
    } catch (err) {
      if (!silent) {
        setError(
          err instanceof Error ? err.message : '차트를 불러오지 못했습니다.'
        );
      }
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadGenre(genreId);
  }, [genreId, loadGenre]);

  // 첫 장르 뜬 뒤 나머지 장르 백그라운드 prefetch (탭 전환 즉시)
  useEffect(() => {
    if (prefetchStarted.current) return;
    if (!tracksByGenre[genreId]?.length) return;
    prefetchStarted.current = true;
    const others = GENRE_TABS.map((g) => g.id).filter((id) => id !== genreId);
    void (async () => {
      for (const id of others) {
        await loadGenre(id, true);
      }
    })();
  }, [tracksByGenre, genreId, loadGenre]);

  const tracks = tracksByGenre[genreId] || [];
  const showSkeleton = loading && tracks.length === 0;

  return (
    <section className="feed-card overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-2 px-3 pt-3 pb-1">
        <div className="flex gap-1.5 overflow-x-auto min-w-0 flex-1">
          {GENRE_TABS.map((g) => (
            <button
              key={g.id}
              type="button"
              onClick={() => setGenreId(g.id)}
              className={`shrink-0 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                genreId === g.id
                  ? 'bg-[#d4a853] text-black'
                  : 'bg-secondary/80 text-muted-foreground hover:bg-white/10 hover:text-foreground'
              }`}
            >
              {g.label}
            </button>
          ))}
        </div>
        <span className="text-[11px] text-muted-foreground tabular-nums shrink-0 px-1">
          {chartDate}
        </span>
      </div>

      {showSkeleton ? (
        <div className="divide-y divide-border px-1 py-2">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="px-3 py-2">
              <Skeleton className="h-12 rounded-md skeleton-shimmer" />
            </div>
          ))}
        </div>
      ) : error && tracks.length === 0 ? (
        <div className="p-10 text-center">
          <TrendingUp className="h-10 w-10 text-muted-foreground/30 mx-auto mb-3" />
          <p className="text-sm font-medium mb-1">차트를 불러올 수 없습니다</p>
          <p className="text-xs text-muted-foreground max-w-sm mx-auto">{error}</p>
        </div>
      ) : tracks.length > 0 ? (
        <ol className="divide-y divide-border">
          {tracks.map((track) => (
            <li key={`${genreId}-${track.id}`} className="flex items-stretch">
              <div className="w-9 shrink-0 flex items-center justify-center pl-2">
                <span
                  className={`text-xs font-bold tabular-nums ${
                    track.rank <= 3 ? 'text-[#d4a853]' : 'text-muted-foreground'
                  }`}
                >
                  {track.rank}
                </span>
              </div>
              <div className="min-w-0 flex-1">
                <CatalogTrackRow track={track} queue={tracks} />
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <div className="p-10 text-center">
          <TrendingUp className="h-10 w-10 text-muted-foreground/30 mx-auto mb-3" />
          <p className="text-sm font-medium mb-1">차트 데이터가 없습니다</p>
          <p className="text-xs text-muted-foreground">잠시 후 다시 시도해 주세요.</p>
        </div>
      )}
    </section>
  );
}
