'use client';

/* ──────────────────────────────────────────────
   WaveMash — 라이브러리 (Library)
   ────────────────────────────────────────────── */

import { useEffect, useState, useCallback, useMemo, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  LayoutGrid,
  List,
  SlidersHorizontal,
  Download,
  Music,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import api from '@/lib/api';
import type { Track, ViewMode, SortField, SortOrder } from '@/lib/types';
import TrackCard from '@/components/TrackCard';
import TrackRow from '@/components/TrackRow';
import Link from 'next/link';
import { requestCoverColor } from '@/lib/coverColors';

const SORT_OPTIONS: { label: string; value: SortField }[] = [
  { label: '최근 추가', value: 'recent' },
  { label: '제목', value: 'title' },
  { label: '아티스트', value: 'artist' },
  { label: 'BPM', value: 'bpm' },
];

function LibraryPageInner() {
  const searchParams = useSearchParams();

  const [tracks, setTracks] = useState<Track[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [search, setSearch] = useState(searchParams.get('search') || '');
  const [genre, setGenre] = useState(searchParams.get('genre') || '');
  const [sortBy, setSortBy] = useState<SortField>(
    (searchParams.get('sort_by') as SortField) || 'recent'
  );
  const [sortOrder] = useState<SortOrder>('desc');
  const [genres, setGenres] = useState<string[]>([]);

  // Fetch genres for filter
  useEffect(() => {
    api
      .getGenres()
      .then((data) => setGenres(data.map((g) => g.name)))
      .catch(() => {});
  }, []);

  // Fetch tracks
  const fetchTracks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getTracks({
        search: search || undefined,
        genre: genre || undefined,
        sort_by: sortBy === 'recent' ? undefined : sortBy,
        sort_order: sortOrder,
        limit: 60,
      });
      setTracks(data);

      // 페이지 로드 시 색상 배치 prefetch (카드 마운트 전에 캐시 워밍)
      const needColor = data
        .filter((t) => t.has_cover && !t.dominant_color)
        .map((t) => t.track_id);
      if (needColor.length) {
        void Promise.all(needColor.map((id) => requestCoverColor(id)));
      } else {
        // 서버에 이미 dominant_color가 있으면 IndexedDB에 심어 둠
        for (const t of data) {
          if (t.dominant_color) {
            void requestCoverColor(t.track_id, t.dominant_color);
          }
        }
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : '트랙을 불러올 수 없습니다.'
      );
    } finally {
      setLoading(false);
    }
  }, [search, genre, sortBy, sortOrder]);

  useEffect(() => {
    const timer = setTimeout(fetchTracks, 300);
    return () => clearTimeout(timer);
  }, [fetchTracks]);

  // Memoize sorted label
  const currentSortLabel = useMemo(
    () => SORT_OPTIONS.find((o) => o.value === sortBy)?.label || '정렬',
    [sortBy]
  );

  return (
    <div className="py-4 space-y-4">
      {/* ── Header ── */}
      <div className="feed-card p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h1 className="text-xl font-bold">라이브러리</h1>

          <div className="flex items-center gap-2 flex-wrap">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px] sm:max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="검색..."
              className="w-full h-9 rounded-lg bg-white/5 border border-white/6 pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:ring-1 focus:ring-[#d4a853]/50 transition-shadow"
            />
          </div>

          {/* Genre Filter */}
          <DropdownMenu>
            <DropdownMenuTrigger
              render={<Button variant="outline" size="sm" className="h-9 gap-1.5" />}
            >
              <SlidersHorizontal className="h-3.5 w-3.5" />
              {genre || '장르'}
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="max-h-60 overflow-y-auto">
              <DropdownMenuItem onClick={() => setGenre('')}>
                전체
              </DropdownMenuItem>
              {genres.map((g) => (
                <DropdownMenuItem key={g} onClick={() => setGenre(g)}>
                  {g}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Sort */}
          <DropdownMenu>
            <DropdownMenuTrigger
              render={<Button variant="outline" size="sm" className="h-9" />}
            >
              {currentSortLabel}
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {SORT_OPTIONS.map((opt) => (
                <DropdownMenuItem
                  key={opt.value}
                  onClick={() => setSortBy(opt.value)}
                >
                  {opt.label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* View Toggle */}
          <div className="flex items-center gap-0.5 glass rounded-lg p-0.5">
            <Button
              variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
              size="icon"
              className="h-8 w-8"
              onClick={() => setViewMode('grid')}
            >
              <LayoutGrid className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'secondary' : 'ghost'}
              size="icon"
              className="h-8 w-8"
              onClick={() => setViewMode('list')}
            >
              <List className="h-3.5 w-3.5" />
            </Button>
          </div>
          </div>
        </div>
      </div>

      {/* ── Content ── */}
      {loading ? (
        <div className="feed-card divide-y divide-border">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="px-4 py-3">
              <Skeleton className="h-14 rounded-md skeleton-shimmer" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="flex min-h-[40vh] items-center justify-center">
          <div className="glass rounded-xl p-8 text-center max-w-md">
            <p className="text-muted-foreground">{error}</p>
          </div>
        </div>
      ) : tracks.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex min-h-[40vh] flex-col items-center justify-center text-center"
        >
          <div className="glass rounded-2xl p-12 max-w-md">
            <Music className="h-16 w-16 text-white/10 mx-auto mb-4" />
            <h2 className="text-xl font-medium mb-2">
              라이브러리가 비어있습니다
            </h2>
            <p className="text-sm text-muted-foreground mb-6">
              첫 번째 트랙을 다운로드하여 컬렉션을 시작하세요.
            </p>
            <Link href="/download">
              <Button className="bg-primary text-primary-foreground">
                <Download className="h-4 w-4 mr-2" />
                다운로드하러 가기
              </Button>
            </Link>
          </div>
        </motion.div>
      ) : viewMode === 'grid' ? (
        <AnimatePresence mode="popLayout">
          <motion.div
            key={`grid-${genre}-${search}-${sortBy}`}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="feed-card p-3 grid grid-cols-2 sm:grid-cols-3 gap-3"
          >
            {tracks.map((track, i) => (
              <TrackCard key={track.track_id} track={track} index={i} />
            ))}
          </motion.div>
        </AnimatePresence>
      ) : (
        <AnimatePresence mode="popLayout">
          <motion.div
            key={`list-${genre}-${search}-${sortBy}`}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="feed-card divide-y divide-border"
          >
            {tracks.map((track) => (
              <div key={track.track_id} className="px-3 py-2">
                <TrackRow track={track} />
              </div>
            ))}
          </motion.div>
        </AnimatePresence>
      )}
    </div>
  );
}

export default function LibraryPage() {
  return (
    <Suspense
      fallback={
        <div className="py-4">
          <div className="feed-card divide-y divide-border">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="px-4 py-3">
                <Skeleton className="h-14 rounded-md skeleton-shimmer" />
              </div>
            ))}
          </div>
        </div>
      }
    >
      <LibraryPageInner />
    </Suspense>
  );
}
