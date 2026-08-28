'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { BarChart3, TrendingUp } from 'lucide-react';
import api from '@/lib/api';
import type {
  CatalogChart,
  CatalogChartGenre,
  CatalogChartTrack,
  ChartEntry,
} from '@/lib/types';
import CatalogTrackRow from '@/components/CatalogTrackRow';
import { Skeleton } from '@/components/ui/skeleton';

type MainTab = 'genres' | 'community';

function msUntilNextMidnight(): number {
  const now = new Date();
  const next = new Date(now);
  next.setHours(24, 0, 0, 0);
  return Math.max(next.getTime() - now.getTime(), 1000);
}

function formatChartDate(date: string | undefined): string {
  if (!date) return '';
  try {
    return new Date(`${date}T12:00:00`).toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return date;
  }
}

export default function HomeLiveChart() {
  const [mainTab, setMainTab] = useState<MainTab>('genres');
  const [chart, setChart] = useState<CatalogChart | null>(null);
  const [genreId, setGenreId] = useState<string>('pop');
  const [community, setCommunity] = useState<ChartEntry[]>([]);
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

  const loadCommunity = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getMostCollectedChart();
      setCommunity(data.slice(0, 20));
    } catch {
      setCommunity([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (mainTab === 'community') {
      void loadCommunity();
      return;
    }
    void loadGenreChart();
  }, [mainTab, loadGenreChart, loadCommunity]);

  useEffect(() => {
    if (mainTab !== 'genres') return;
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
  }, [mainTab, loadGenreChart]);

  const genres: CatalogChartGenre[] = chart?.genres ?? [];
  const activeGenre = genres.find((g) => g.id === genreId) ?? genres[0];
  const tracks: CatalogChartTrack[] = activeGenre?.tracks ?? [];

  return (
    <section className="feed-card overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-3 px-4 py-3 border-b border-border">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <BarChart3 className="h-4 w-4 text-[#d4a853] shrink-0" />
            <h2 className="text-base font-semibold">장르별 인기 차트</h2>
          </div>
          <p className="text-xs text-muted-foreground">
            {mainTab === 'genres'
              ? '최근 6개월 발매 · 인기 순위 · 매일 자정 갱신'
              : 'WaveMash에서 가장 많이 수집된 곡'}
          </p>
        </div>
        {mainTab === 'genres' && chart?.chart_date && (
          <span className="text-[11px] text-muted-foreground tabular-nums">
            {formatChartDate(chart.chart_date)} 기준
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-1 px-3 pt-3">
        {(
          [
            { id: 'genres' as const, label: '장르별' },
            { id: 'community' as const, label: '커뮤니티' },
          ] as const
        ).map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setMainTab(t.id)}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              mainTab === t.id
                ? 'bg-[#d4a853]/15 text-[#d4a853]'
                : 'text-muted-foreground hover:bg-white/5 hover:text-foreground'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {mainTab === 'genres' && genres.length > 0 && (
        <div className="flex gap-1.5 overflow-x-auto px-3 pt-2 pb-1 -mx-0">
          {genres.map((g) => (
            <button
              key={g.id}
              type="button"
              onClick={() => setGenreId(g.id)}
              className={`shrink-0 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                activeGenre?.id === g.id
                  ? 'bg-[#d4a853] text-black'
                  : 'bg-secondary/80 text-muted-foreground hover:bg-white/10 hover:text-foreground'
              }`}
            >
              {g.label}
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <div className="divide-y divide-border px-1 py-2">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="px-3 py-2">
              <Skeleton className="h-12 rounded-md skeleton-shimmer" />
            </div>
          ))}
        </div>
      ) : mainTab === 'genres' && error ? (
        <div className="p-10 text-center">
          <TrendingUp className="h-10 w-10 text-muted-foreground/30 mx-auto mb-3" />
          <p className="text-sm font-medium mb-1">차트를 불러올 수 없습니다</p>
          <p className="text-xs text-muted-foreground max-w-sm mx-auto">{error}</p>
        </div>
      ) : mainTab === 'genres' && tracks.length > 0 ? (
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
      ) : mainTab === 'community' && community.length > 0 ? (
        <ol className="divide-y divide-border">
          {community.map((entry, i) => (
            <li key={entry.track_id}>
              <Link
                href={`/track/${entry.track_id}`}
                className="flex items-center gap-3 px-3 py-2.5 hover:bg-white/[0.04] transition-colors"
              >
                <span
                  className={`w-6 shrink-0 text-center text-xs font-bold tabular-nums ${
                    i < 3 ? 'text-[#d4a853]' : 'text-muted-foreground'
                  }`}
                >
                  {i + 1}
                </span>
                <div className="h-11 w-11 shrink-0 overflow-hidden rounded-md bg-secondary">
                  {entry.thumbnail_url ? (
                    <img
                      src={entry.thumbnail_url}
                      alt=""
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center text-[10px] text-muted-foreground">
                      ?
                    </div>
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{entry.title}</p>
                  <p className="truncate text-xs text-muted-foreground">
                    {entry.artist}
                  </p>
                </div>
                <span className="text-xs text-muted-foreground tabular-nums shrink-0">
                  {entry.collector_count.toLocaleString()}명
                </span>
              </Link>
            </li>
          ))}
        </ol>
      ) : (
        <div className="p-10 text-center">
          <TrendingUp className="h-10 w-10 text-muted-foreground/30 mx-auto mb-3" />
          <p className="text-sm font-medium mb-1">차트 데이터가 없습니다</p>
          <p className="text-xs text-muted-foreground">
            {mainTab === 'community'
              ? '아직 커뮤니티 수집 순위가 쌓이지 않았습니다.'
              : '잠시 후 다시 시도해 주세요.'}
          </p>
        </div>
      )}
    </section>
  );
}
