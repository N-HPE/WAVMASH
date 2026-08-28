'use client';

import { useCallback, useEffect, useState } from 'react';
import { TrendingUp } from 'lucide-react';
import api from '@/lib/api';
import type {
  CatalogChart,
  CatalogChartGenre,
  CatalogChartTrack,
} from '@/lib/types';
import CatalogTrackRow from '@/components/CatalogTrackRow';
import { Skeleton } from '@/components/ui/skeleton';

function msUntilNextMidnight(): number {
  const now = new Date();
  const next = new Date(now);
  next.setHours(24, 0, 0, 0);
  return Math.max(next.getTime() - now.getTime(), 1000);
}

function formatChartDate(date: string | undefined): string {
  const raw = date || new Date().toISOString().slice(0, 10);
  try {
    return new Date(`${raw}T12:00:00`).toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  } catch {
    return raw;
  }
}

export default function HomeLiveChart() {
  const [chart, setChart] = useState<CatalogChart | null>(null);
  const [genreId, setGenreId] = useState<string>('pop');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadGenreChart = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setError(null);
    try {
      const data = await api.getSpotifyChart('genres', 10);
      setChart(data);
      const genres = data.genres || [];
      if (genres.length > 0) {
        setGenreId((prev) =>
          genres.some((g) => g.id === prev) ? prev : genres[0].id
        );
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : '차트를 불러오지 못했습니다.'
      );
      if (!silent) setChart(null);
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadGenreChart();
  }, [loadGenreChart]);

  useEffect(() => {
    let timeoutId = 0;
    let cancelled = false;

    const schedule = () => {
      timeoutId = window.setTimeout(() => {
        if (cancelled) return;
        void loadGenreChart(true).finally(() => {
          if (!cancelled) schedule();
        });
      }, msUntilNextMidnight());
    };

    schedule();
    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [loadGenreChart]);

  const genres: CatalogChartGenre[] = chart?.genres ?? [];
  const activeGenre = genres.find((g) => g.id === genreId) ?? genres[0];
  const tracks: CatalogChartTrack[] = activeGenre?.tracks ?? [];

  return (
    <section className="feed-card overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-2 px-3 pt-3 pb-1">
        <div className="flex gap-1.5 overflow-x-auto min-w-0 flex-1">
          {(genres.length > 0
            ? genres
            : [
                { id: 'pop', label: '팝', tracks: [] },
                { id: 'hiphop', label: '힙합', tracks: [] },
                { id: 'rnb', label: 'R&B', tracks: [] },
                { id: 'dance', label: '댄스', tracks: [] },
                { id: 'rock', label: '록', tracks: [] },
                { id: 'indie', label: '인디', tracks: [] },
                { id: 'latin', label: '라틴', tracks: [] },
                { id: 'kpop', label: 'K-pop', tracks: [] },
              ]
          ).map((g) => (
            <button
              key={g.id}
              type="button"
              onClick={() => setGenreId(g.id)}
              className={`shrink-0 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                (activeGenre?.id || genreId) === g.id
                  ? 'bg-[#d4a853] text-black'
                  : 'bg-secondary/80 text-muted-foreground hover:bg-white/10 hover:text-foreground'
              }`}
            >
              {g.label}
            </button>
          ))}
        </div>
        <span className="text-[11px] text-muted-foreground tabular-nums shrink-0 px-1">
          {formatChartDate(chart?.chart_date)}
        </span>
      </div>

      {loading ? (
        <div className="divide-y divide-border px-1 py-2">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="px-3 py-2">
              <Skeleton className="h-12 rounded-md skeleton-shimmer" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="p-10 text-center">
          <TrendingUp className="h-10 w-10 text-muted-foreground/30 mx-auto mb-3" />
          <p className="text-sm font-medium mb-1">차트를 불러올 수 없습니다</p>
          <p className="text-xs text-muted-foreground max-w-sm mx-auto">{error}</p>
        </div>
      ) : tracks.length > 0 ? (
        <ol className="divide-y divide-border">
          {tracks.map((track) => (
            <li key={`${activeGenre?.id}-${track.id}`} className="flex items-stretch">
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
