'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { TrendingUp } from 'lucide-react';
import api from '@/lib/api';
import type { CatalogChartGenre, CatalogChartTrack } from '@/lib/types';
import CatalogTrackRow from '@/components/CatalogTrackRow';
import { Skeleton } from '@/components/ui/skeleton';

type SubGenre = { id: string; label: string };
type GenreGroup = {
  id: string;
  label: string;
  color: string;
  colorMuted: string;
  textOnActive: string;
  subgenres: SubGenre[];
};

const GENRE_GROUPS: GenreGroup[] = [
  {
    id: 'pop',
    label: '팝',
    color: '#eab308',
    colorMuted: 'rgba(234, 179, 8, 0.18)',
    textOnActive: '#111',
    subgenres: [
      { id: 'pop', label: '전체' },
      { id: 'pop-dance', label: '댄스팝' },
      { id: 'pop-synth', label: '신스팝' },
      { id: 'pop-kpop', label: 'K-pop' },
      { id: 'pop-latin', label: '라틴팝' },
    ],
  },
  {
    id: 'hiphop',
    label: '힙합',
    color: '#f97316',
    colorMuted: 'rgba(249, 115, 22, 0.18)',
    textOnActive: '#111',
    subgenres: [
      { id: 'hiphop', label: '전체' },
      { id: 'hiphop-trap', label: '트랩' },
      { id: 'hiphop-drill', label: '드릴' },
      { id: 'hiphop-k', label: 'K-힙합' },
      { id: 'hiphop-reggaeton', label: '레게톤' },
    ],
  },
  {
    id: 'rnb',
    label: 'R&B',
    color: '#ef4444',
    colorMuted: 'rgba(239, 68, 68, 0.18)',
    textOnActive: '#fff',
    subgenres: [
      { id: 'rnb', label: '전체' },
      { id: 'rnb-neo', label: '네오소울' },
      { id: 'rnb-alt', label: '얼터 R&B' },
      { id: 'rnb-k', label: 'K-R&B' },
    ],
  },
  {
    id: 'dance',
    label: '댄스',
    color: '#3b82f6',
    colorMuted: 'rgba(59, 130, 246, 0.18)',
    textOnActive: '#fff',
    subgenres: [
      { id: 'dance', label: '전체' },
      { id: 'dance-house', label: '하우스' },
      { id: 'dance-techno', label: '테크노' },
      { id: 'dance-trance', label: '트랜스' },
      { id: 'dance-dnb', label: '드럼앤베이스' },
      { id: 'dance-dubstep', label: '덥스텝' },
      { id: 'dance-salsa', label: '살사' },
    ],
  },
  {
    id: 'indie',
    label: '인디',
    color: '#22c55e',
    colorMuted: 'rgba(34, 197, 94, 0.18)',
    textOnActive: '#111',
    subgenres: [
      { id: 'indie', label: '전체' },
      { id: 'indie-pop', label: '인디팝' },
      { id: 'indie-rock', label: '인디록' },
    ],
  },
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
  const [groupId, setGroupId] = useState('pop');
  const [subId, setSubId] = useState('pop');
  const [tracksByGenre, setTracksByGenre] = useState<
    Record<string, CatalogChartTrack[]>
  >({});
  const [chartDate, setChartDate] = useState(formatToday());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const cacheRef = useRef<Record<string, CatalogChartTrack[]>>({});
  const prefetchStarted = useRef(false);

  const activeGroup = useMemo(
    () => GENRE_GROUPS.find((g) => g.id === groupId) || GENRE_GROUPS[0],
    [groupId]
  );

  const selectGroup = useCallback((id: string) => {
    const group = GENRE_GROUPS.find((g) => g.id === id);
    if (!group) return;
    setGroupId(id);
    setSubId(group.subgenres[0]?.id || id);
  }, []);

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
    void loadGenre(subId);
  }, [subId, loadGenre]);

  useEffect(() => {
    if (prefetchStarted.current) return;
    if (!tracksByGenre[subId]?.length) return;
    prefetchStarted.current = true;
    const primaryIds = GENRE_GROUPS.map((g) => g.subgenres[0]?.id).filter(
      Boolean
    ) as string[];
    const siblingIds = activeGroup.subgenres.map((s) => s.id);
    const queue = [...new Set([...siblingIds, ...primaryIds])].filter(
      (id) => id !== subId
    );
    void (async () => {
      for (const id of queue) {
        await loadGenre(id, true);
      }
    })();
  }, [tracksByGenre, subId, loadGenre, activeGroup]);

  useEffect(() => {
    const ids = activeGroup.subgenres.map((s) => s.id);
    void (async () => {
      for (const id of ids) {
        if (cacheRef.current[id]?.length) continue;
        await loadGenre(id, true);
      }
    })();
  }, [activeGroup, loadGenre]);

  const tracks = tracksByGenre[subId] || [];
  const showSkeleton = loading && tracks.length === 0;

  return (
    <section className="feed-card overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-2 px-3 pt-3 pb-1">
        <div className="flex gap-1.5 overflow-x-auto min-w-0 flex-1">
          {GENRE_GROUPS.map((g) => {
            const active = groupId === g.id;
            return (
              <button
                key={g.id}
                type="button"
                onClick={() => selectGroup(g.id)}
                className="shrink-0 rounded-md px-3 py-1.5 text-xs font-medium transition-all border"
                style={
                  active
                    ? {
                        backgroundColor: g.color,
                        color: g.textOnActive,
                        borderColor: g.color,
                      }
                    : {
                        backgroundColor: g.colorMuted,
                        color: g.color,
                        borderColor: `${g.color}55`,
                      }
                }
              >
                {g.label}
              </button>
            );
          })}
        </div>
        <span className="text-[11px] text-muted-foreground tabular-nums shrink-0 px-1">
          {chartDate}
        </span>
      </div>

      {activeGroup.subgenres.length > 1 && (
        <div className="flex gap-1 overflow-x-auto px-3 pb-2 pt-0.5">
          {activeGroup.subgenres.map((s) => {
            const active = subId === s.id;
            return (
              <button
                key={s.id}
                type="button"
                onClick={() => setSubId(s.id)}
                className={`shrink-0 rounded px-2.5 py-1 text-[11px] font-medium transition-colors ${
                  active
                    ? 'text-foreground'
                    : 'text-muted-foreground hover:bg-white/5 hover:text-foreground'
                }`}
                style={
                  active
                    ? { backgroundColor: activeGroup.colorMuted }
                    : undefined
                }
              >
                {s.label}
              </button>
            );
          })}
        </div>
      )}

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
            <li key={`${subId}-${track.id}`} className="flex items-stretch">
              <div className="w-9 shrink-0 flex items-center justify-center pl-2">
                <span
                  className="text-xs font-bold tabular-nums text-muted-foreground"
                  style={
                    track.rank <= 3
                      ? { color: activeGroup.color }
                      : undefined
                  }
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
