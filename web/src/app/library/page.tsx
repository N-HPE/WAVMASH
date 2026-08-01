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
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
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
    <div className="mx-auto max-w-7xl px-4 sm:px-6 py-8">
      {/* ── Header ── */}
      <div className="flex flex-col gap-4 mb-6 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold">라이브러리</h1>

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

      {/* ── Content ── */}
      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {[...Array(12)].map((_, i) => (
            <Skeleton
              key={i}
              className="aspect-[3/4] rounded-xl skeleton-shimmer"
            />
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
            className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4"
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
            className="space-y-2"
          >
            {tracks.map((track, i) => (
              <motion.div
                key={track.track_id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.03 }}
              >
                <Link
                  href={`/track/${track.track_id}`}
                  className="flex items-center gap-4 glass rounded-lg p-3 hover-lift group"
                >
                  <div className="h-12 w-12 flex-shrink-0 overflow-hidden rounded-md">
                    {track.has_cover ? (
                      <img
                        src={api.getCoverUrl(track.track_id, 96)}
                        alt={track.title}
                        className="h-full w-full object-cover"
                        loading="lazy"
                        decoding="async"
                      />
                    ) : (
                      <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-[#1a1a2e] to-[#0a0a14]">
                        <Music className="h-5 w-5 text-white/10" />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="truncate text-sm font-medium">
                      {track.title}
                    </p>
                    <p className="truncate text-xs text-muted-foreground">
                      {track.artist}
                    </p>
                  </div>
                  <div className="hidden sm:flex items-center gap-2 flex-shrink-0">
                    {track.bpm > 0 && (
                      <span className="badge-bpm rounded-md px-2 py-0.5 text-xs">
                        {Math.round(track.bpm)} BPM
                      </span>
                    )}
                    {track.key && (
                      <span className="badge-key rounded-md px-2 py-0.5 text-xs">
                        {track.key}
                      </span>
                    )}
                    {track.genre && (
                      <span className="badge-genre rounded-md px-2 py-0.5 text-xs">
                        {track.genre}
                      </span>
                    )}
                  </div>
                </Link>
              </motion.div>
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
        <div className="mx-auto max-w-7xl px-4 sm:px-6 py-8">
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
            {[...Array(12)].map((_, i) => (
              <Skeleton
                key={i}
                className="aspect-[3/4] rounded-xl skeleton-shimmer"
              />
            ))}
          </div>
        </div>
      }
    >
      <LibraryPageInner />
    </Suspense>
  );
}
