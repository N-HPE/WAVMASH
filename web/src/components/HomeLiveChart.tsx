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
  /** 접근성용만 — UI에는 색상 스와치만 표시 */
  axis: string;
  color: string;
  colorMuted: string;
  subgenres: SubGenre[];
};

/** 빨주노초파남보 (원형: 보→빨 연결). 근본축: 빨(힙합·R&B) · 노(팝·인디) · 파(댄스) · 보(베이스·블랙댄스) */
const GENRE_GROUPS: GenreGroup[] = [
  {
    id: 'red',
    axis: '힙합 · R&B',
    color: '#ef4444',
    colorMuted: 'rgba(239, 68, 68, 0.2)',
    subgenres: [
      { id: 'red', label: '전체' },
      { id: 'red-hiphop', label: '힙합' },
      { id: 'red-trap', label: '트랩' },
      { id: 'red-drill', label: '드릴' },
      { id: 'red-rnb', label: 'R&B' },
      { id: 'red-neo', label: '네오소울' },
      { id: 'red-alt', label: '얼터 R&B' },
      { id: 'red-k-hiphop', label: 'K-힙합' },
      { id: 'red-k-rnb', label: 'K-R&B' },
    ],
  },
  {
    id: 'orange',
    axis: '라틴 · 리듬',
    color: '#f97316',
    colorMuted: 'rgba(249, 115, 22, 0.2)',
    subgenres: [
      { id: 'orange', label: '전체' },
      { id: 'orange-reggaeton', label: '레게톤' },
      { id: 'orange-latin', label: '라틴' },
      { id: 'orange-afrobeats', label: '아프로비트' },
      { id: 'orange-funk', label: '펑크' },
      { id: 'orange-salsa', label: '살사' },
    ],
  },
  {
    id: 'yellow',
    axis: '팝 · 인디',
    color: '#eab308',
    colorMuted: 'rgba(234, 179, 8, 0.2)',
    subgenres: [
      { id: 'yellow', label: '전체' },
      { id: 'yellow-pop', label: '팝' },
      { id: 'yellow-dance-pop', label: '댄스팝' },
      { id: 'yellow-synth', label: '신스팝' },
      { id: 'yellow-kpop', label: 'K-pop' },
      { id: 'yellow-indie', label: '인디' },
      { id: 'yellow-indie-pop', label: '인디팝' },
      { id: 'yellow-indie-rock', label: '인디록' },
    ],
  },
  {
    id: 'green',
    axis: '얼터 · 록',
    color: '#22c55e',
    colorMuted: 'rgba(34, 197, 94, 0.2)',
    subgenres: [
      { id: 'green', label: '전체' },
      { id: 'green-alt', label: '얼터너티브' },
      { id: 'green-rock', label: '록' },
      { id: 'green-folk', label: '포크' },
      { id: 'green-chill', label: '칠' },
    ],
  },
  {
    id: 'blue',
    axis: '댄스',
    color: '#3b82f6',
    colorMuted: 'rgba(59, 130, 246, 0.2)',
    subgenres: [
      { id: 'blue', label: '전체' },
      { id: 'blue-house', label: '하우스' },
      { id: 'blue-techno', label: '테크노' },
      { id: 'blue-trance', label: '트랜스' },
    ],
  },
  {
    id: 'indigo',
    axis: '딥 · 프로그레시브',
    color: '#6366f1',
    colorMuted: 'rgba(99, 102, 241, 0.2)',
    subgenres: [
      { id: 'indigo', label: '전체' },
      { id: 'indigo-deep', label: '딥하우스' },
      { id: 'indigo-prog', label: '프로그레시브' },
      { id: 'indigo-minimal', label: '미니멀' },
      { id: 'indigo-electro', label: '일렉트로니카' },
    ],
  },
  {
    id: 'violet',
    axis: '베이스 · 블랙댄스',
    color: '#a855f7',
    colorMuted: 'rgba(168, 85, 247, 0.2)',
    subgenres: [
      { id: 'violet', label: '전체' },
      { id: 'violet-amapiano', label: '아마피아노' },
      { id: 'violet-afro-house', label: '아프로하우스' },
      { id: 'violet-garage', label: '개러지' },
      { id: 'violet-grime', label: '그라임' },
      { id: 'violet-dancehall', label: '댄스홀' },
      { id: 'violet-jersey', label: '저지클럽' },
      { id: 'violet-baile', label: '바이르펑크' },
      { id: 'violet-dnb', label: '드럼앤베이스' },
      { id: 'violet-dubstep', label: '덥스텝' },
    ],
  },
];

function formatChartDate(isoDate?: string): string {
  try {
    const d = isoDate
      ? new Date(`${isoDate}T12:00:00`)
      : new Date();
    return d.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  } catch {
    return isoDate || '';
  }
}

export default function HomeLiveChart() {
  const [groupId, setGroupId] = useState('red');
  const [subId, setSubId] = useState('red');
  const [tracksByGenre, setTracksByGenre] = useState<
    Record<string, CatalogChartTrack[]>
  >({});
  const [chartDate, setChartDate] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const cacheRef = useRef<Record<string, CatalogChartTrack[]>>({});
  const inflightRef = useRef<Map<string, Promise<CatalogChartTrack[]>>>(
    new Map()
  );
  const prefetchDoneRef = useRef<Set<string>>(new Set());

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

  const fetchGenre = useCallback(async (id: string): Promise<CatalogChartTrack[]> => {
    const cached = cacheRef.current[id];
    if (cached?.length) return cached;

    const existing = inflightRef.current.get(id);
    if (existing) return existing;

    const promise = (async () => {
      const data = await api.getSpotifyChart(id, 10);
      const genre: CatalogChartGenre | undefined =
        (data.genres || []).find((g) => g.id === id) || data.genres?.[0];
      const tracks = genre?.tracks || data.tracks || [];
      // 빈 결과는 캐시하지 않아 재시도 가능
      if (tracks.length) {
        cacheRef.current[id] = tracks;
      }
      setTracksByGenre((prev) => ({ ...prev, [id]: tracks }));
      if (data.chart_date) {
        setChartDate(formatChartDate(data.chart_date));
      }
      return tracks;
    })().finally(() => {
      inflightRef.current.delete(id);
    });

    inflightRef.current.set(id, promise);
    return promise;
  }, []);

  const loadActive = useCallback(
    async (id: string) => {
      if (cacheRef.current[id]?.length) {
        setTracksByGenre((prev) => ({ ...prev, [id]: cacheRef.current[id] }));
        setLoading(false);
        setError(null);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const tracks = await fetchGenre(id);
        if (!tracks.length) {
          setError(null);
        }
      } catch (err) {
        setError(
          err instanceof Error ? err.message : '차트를 불러오지 못했습니다.'
        );
      } finally {
        setLoading(false);
      }
    },
    [fetchGenre]
  );

  // 활성 장르만 먼저 로드
  useEffect(() => {
    void loadActive(subId);
  }, [subId, loadActive]);

  // 활성 장르 성공 후, 같은 그룹 세부와 다른 대분류 '전체'만 idle에 prefetch
  useEffect(() => {
    const activeTracks = tracksByGenre[subId];
    if (!activeTracks?.length) return;
    if (prefetchDoneRef.current.has(groupId)) return;
    prefetchDoneRef.current.add(groupId);

    const siblingIds = activeGroup.subgenres.map((s) => s.id);
    const primaryIds = GENRE_GROUPS.map((g) => g.subgenres[0]?.id).filter(
      Boolean
    ) as string[];
    const queue = [...new Set([...siblingIds, ...primaryIds])].filter(
      (id) => id !== subId && !cacheRef.current[id]?.length
    );

    let cancelled = false;
    const run = () => {
      void (async () => {
        for (const id of queue) {
          if (cancelled) return;
          try {
            await fetchGenre(id);
          } catch {
            /* prefetch 실패는 무시 */
          }
        }
      })();
    };

    const ric = (
      window as Window & {
        requestIdleCallback?: (cb: () => void, opts?: { timeout: number }) => number;
        cancelIdleCallback?: (id: number) => void;
      }
    ).requestIdleCallback;
    let idleId: number | undefined;
    let timeoutId: ReturnType<typeof setTimeout> | undefined;

    if (typeof ric === 'function') {
      idleId = ric(run, { timeout: 2500 });
    } else {
      timeoutId = setTimeout(run, 400);
    }

    return () => {
      cancelled = true;
      if (idleId != null) {
        (
          window as Window & { cancelIdleCallback?: (id: number) => void }
        ).cancelIdleCallback?.(idleId);
      }
      if (timeoutId != null) clearTimeout(timeoutId);
    };
  }, [tracksByGenre, subId, groupId, activeGroup, fetchGenre]);

  const tracks = tracksByGenre[subId] || [];
  const showSkeleton = loading && tracks.length === 0;

  return (
    <section className="feed-card overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-2 px-3 pt-3.5 pb-1">
        <div
          className="flex items-center gap-2.5 overflow-x-auto min-w-0 flex-1 py-0.5"
          role="tablist"
          aria-label="장르 스펙트럼"
        >
          {GENRE_GROUPS.map((g) => {
            const active = groupId === g.id;
            return (
              <button
                key={g.id}
                type="button"
                role="tab"
                aria-selected={active}
                aria-label={g.axis}
                title={g.axis}
                onClick={() => selectGroup(g.id)}
                className={`shrink-0 rounded-full transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70 focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
                  active
                    ? 'h-7 w-7 ring-2 ring-white/80 scale-110 shadow-md'
                    : 'h-5 w-5 opacity-75 hover:opacity-100 hover:scale-110'
                }`}
                style={{ backgroundColor: g.color }}
              />
            );
          })}
        </div>
        {chartDate ? (
          <span className="text-[11px] text-muted-foreground tabular-nums shrink-0 px-1">
            {chartDate}
          </span>
        ) : null}
      </div>

      {activeGroup.subgenres.length > 1 && (
        <div className="flex gap-1 overflow-x-auto px-3 pb-2 pt-1.5">
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
          <p className="text-xs text-muted-foreground max-w-sm mx-auto mb-3">
            {error}
          </p>
          <button
            type="button"
            onClick={() => void loadActive(subId)}
            className="text-xs font-medium text-foreground underline-offset-2 hover:underline"
          >
            다시 시도
          </button>
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
          <p className="text-xs text-muted-foreground mb-3">
            잠시 후 다시 시도해 주세요.
          </p>
          <button
            type="button"
            onClick={() => void loadActive(subId)}
            className="text-xs font-medium text-foreground underline-offset-2 hover:underline"
          >
            다시 시도
          </button>
        </div>
      )}
    </section>
  );
}
