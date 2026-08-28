'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import {
  ArrowDown,
  ArrowUp,
  BarChart3,
  Minus,
  RefreshCw,
  TrendingUp,
} from 'lucide-react';
import api from '@/lib/api';
import type { CatalogChart, CatalogChartTrack, ChartEntry } from '@/lib/types';
import CatalogTrackRow from '@/components/CatalogTrackRow';
import { Skeleton } from '@/components/ui/skeleton';

type ChartTab = 'songs' | 'albums' | 'community';

const POLL_MS = 5 * 60 * 1000;

function formatChartDate(date: string | undefined, iso: string | null): string {
  if (date) {
    try {
      return new Date(`${date}T12:00:00`).toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      /* fall through */
    }
  }
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString('ko-KR', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

function RankDelta({
  rank,
  previous,
  status,
}: {
  rank: number;
  previous?: number | null;
  status?: string;
}) {
  if (status === 'NEW') {
    return <span className="text-[10px] font-semibold text-emerald-400">NEW</span>;
  }
  if (previous == null || previous <= 0) {
    return <Minus className="h-3 w-3 text-muted-foreground/50" />;
  }
  const delta = previous - rank;
  if (delta > 0) {
    return (
      <span className="inline-flex items-center gap-0.5 text-[10px] font-medium text-emerald-400 tabular-nums">
        <ArrowUp className="h-3 w-3" />
        {delta}
      </span>
    );
  }
  if (delta < 0) {
    return (
      <span className="inline-flex items-center gap-0.5 text-[10px] font-medium text-rose-400 tabular-nums">
        <ArrowDown className="h-3 w-3" />
        {Math.abs(delta)}
      </span>
    );
  }
  return <Minus className="h-3 w-3 text-muted-foreground/50" />;
}

export default function HomeLiveChart() {
  const [tab, setTab] = useState<ChartTab>('songs');
  const [chart, setChart] = useState<CatalogChart | null>(null);
  const [community, setCommunity] = useState<ChartEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSpotify = useCallback(
    async (kind: 'songs' | 'albums', silent = false) => {
      if (!silent) setLoading(true);
      else setRefreshing(true);
      setError(null);
      try {
        const data = await api.getSpotifyChart(kind, 50);
        setChart(data);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : '차트를 불러오지 못했습니다.'
        );
        setChart(null);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    []
  );

  const loadCommunity = useCallback(async () => {
    try {
      const data = await api.getMostCollectedChart();
      setCommunity(data.slice(0, 20));
    } catch {
      setCommunity([]);
    }
  }, []);

  useEffect(() => {
    if (tab === 'community') {
      setLoading(true);
      void loadCommunity().finally(() => setLoading(false));
      return;
    }
    void loadSpotify(tab);
  }, [tab, loadSpotify, loadCommunity]);

  useEffect(() => {
    if (tab === 'community') return;
    const id = window.setInterval(() => {
      void loadSpotify(tab, true);
    }, POLL_MS);
    return () => window.clearInterval(id);
  }, [tab, loadSpotify]);

  const tracks: CatalogChartTrack[] = chart?.tracks ?? [];
  const isAlbumChart = tab === 'albums' || chart?.region === 'albums';

  return (
    <section className="feed-card overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-3 px-4 py-3 border-b border-border">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <BarChart3 className="h-4 w-4 text-[#d4a853] shrink-0" />
            <h2 className="text-base font-semibold">실시간 차트</h2>
            {tab !== 'community' && (
              <span className="inline-flex items-center gap-1.5 text-[11px] text-muted-foreground">
                <span className="relative flex h-1.5 w-1.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400/70" />
                  <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
                </span>
                LIVE
              </span>
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            {tab === 'songs' && 'Spotify 글로벌 주간 Top 50 · 스트리밍 인기 순위'}
            {tab === 'albums' && 'Spotify 글로벌 주간 Top 50 · 음반 차트'}
            {tab === 'community' && 'WaveMash에서 가장 많이 수집된 곡'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {tab !== 'community' && (
            <span className="hidden sm:inline text-[11px] text-muted-foreground tabular-nums">
              {formatChartDate(chart?.chart_date, chart?.updated_at ?? null)}
            </span>
          )}
          {tab !== 'community' && (
            <button
              type="button"
              onClick={() => void loadSpotify(tab, true)}
              disabled={refreshing}
              className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-white/5 hover:text-[#d4a853] transition-colors disabled:opacity-50"
              title="새로고침"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`}
              />
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-1 px-3 pt-3 pb-1">
        {(
          [
            { id: 'songs' as const, label: '인기 노래' },
            { id: 'albums' as const, label: '음반' },
            { id: 'community' as const, label: '커뮤니티' },
          ] as const
        ).map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              tab === t.id
                ? 'bg-[#d4a853]/15 text-[#d4a853]'
                : 'text-muted-foreground hover:bg-white/5 hover:text-foreground'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="divide-y divide-border px-1 py-2">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="px-3 py-2">
              <Skeleton className="h-12 rounded-md skeleton-shimmer" />
            </div>
          ))}
        </div>
      ) : tab !== 'community' && error ? (
        <div className="p-10 text-center">
          <TrendingUp className="h-10 w-10 text-muted-foreground/30 mx-auto mb-3" />
          <p className="text-sm font-medium mb-1">차트를 불러올 수 없습니다</p>
          <p className="text-xs text-muted-foreground max-w-sm mx-auto">{error}</p>
        </div>
      ) : tab !== 'community' && tracks.length > 0 && !isAlbumChart ? (
        <ol className="divide-y divide-border max-h-[min(70vh,720px)] overflow-y-auto">
          {tracks.map((track) => (
            <li key={track.id} className="flex items-stretch">
              <div className="w-11 shrink-0 flex flex-col items-center justify-center gap-0.5 pl-2">
                <span
                  className={`text-xs font-bold tabular-nums ${
                    track.rank <= 3 ? 'text-[#d4a853]' : 'text-muted-foreground'
                  }`}
                >
                  {track.rank}
                </span>
                <RankDelta
                  rank={track.rank}
                  previous={track.previous_rank}
                  status={track.entry_status}
                />
              </div>
              <div className="min-w-0 flex-1">
                <CatalogTrackRow track={track} queue={tracks} />
              </div>
            </li>
          ))}
        </ol>
      ) : tab === 'albums' && tracks.length > 0 ? (
        <ol className="divide-y divide-border max-h-[min(70vh,720px)] overflow-y-auto">
          {tracks.map((entry, i) => (
            <li key={entry.id}>
              <Link
                href={`/album/${entry.id}`}
                className="flex items-center gap-3 px-3 py-2.5 hover:bg-white/[0.04] transition-colors"
              >
                <div className="w-10 shrink-0 flex flex-col items-center gap-0.5">
                  <span
                    className={`text-xs font-bold tabular-nums ${
                      i < 3 ? 'text-[#d4a853]' : 'text-muted-foreground'
                    }`}
                  >
                    {entry.rank}
                  </span>
                  <RankDelta
                    rank={entry.rank}
                    previous={entry.previous_rank}
                    status={entry.entry_status}
                  />
                </div>
                <div className="h-11 w-11 shrink-0 overflow-hidden rounded-md bg-secondary">
                  {entry.thumbnail_url ? (
                    <img
                      src={entry.thumbnail_url}
                      alt=""
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="h-full w-full bg-secondary" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{entry.title}</p>
                  <p className="truncate text-xs text-muted-foreground">
                    {entry.artist}
                  </p>
                </div>
              </Link>
            </li>
          ))}
        </ol>
      ) : tab === 'community' && community.length > 0 ? (
        <ol className="divide-y divide-border max-h-[min(70vh,720px)] overflow-y-auto">
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
            {tab === 'community'
              ? '아직 커뮤니티 수집 순위가 쌓이지 않았습니다.'
              : '잠시 후 다시 시도해 주세요.'}
          </p>
        </div>
      )}
    </section>
  );
}
