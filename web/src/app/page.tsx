'use client';

/* ──────────────────────────────────────────────
   WaveMash — 대시보드 (Dashboard)
   ────────────────────────────────────────────── */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import api from '@/lib/api';
import type { LibraryStats } from '@/lib/types';
import LibraryStatsView from '@/components/LibraryStats';
import DownloadForm from '@/components/DownloadForm';
import TrackCard from '@/components/TrackCard';

const sectionVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.15, duration: 0.5, ease: 'easeOut' as const },
  }),
};

export default function DashboardPage() {
  const [stats, setStats] = useState<LibraryStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getLibraryStats()
      .then(setStats)
      .catch((err) =>
        setError(err instanceof Error ? err.message : '데이터를 불러올 수 없습니다.')
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl px-4 sm:px-6 py-8 space-y-8">
        {/* Stats skeleton */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl skeleton-shimmer" />
          ))}
        </div>
        {/* Download skeleton */}
        <Skeleton className="h-16 max-w-2xl mx-auto rounded-xl skeleton-shimmer" />
        {/* Tracks skeleton */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="aspect-[3/4] rounded-xl skeleton-shimmer" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="glass rounded-xl p-8 text-center max-w-md">
          <p className="text-muted-foreground">{error}</p>
        </div>
      </div>
    );
  }

  const genres = stats
    ? Object.entries(stats.genres)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 12)
    : [];

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 py-8 space-y-12">
      {/* ── 1. Genre Section (Top) ── */}
      {genres.length > 0 && (
        <motion.section
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <h2 className="text-lg font-medium mb-4">Genre</h2>
          <div className="flex flex-wrap gap-2">
            {genres.map(([genre, count]) => (
              <Link key={genre} href={`/library?genre=${encodeURIComponent(genre)}`}>
                <motion.span
                  className="badge-genre rounded-full px-4 py-2 text-sm font-medium cursor-pointer inline-flex items-center gap-2"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  {genre}
                  <span className="opacity-50 text-xs">{count}</span>
                </motion.span>
              </Link>
            ))}
          </div>
        </motion.section>
      )}

      {/* ── 2. Quick Download ── */}
      <motion.section
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.15 }}
        className="text-center"
      >
        <h2 className="text-lg font-medium mb-4">빠른 다운로드</h2>
        <DownloadForm />
      </motion.section>

      {/* ── 3. Recent Tracks ── */}
      {stats && stats.recent_tracks.length > 0 && (
        <motion.section
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium">최근 추가</h2>
            <Link
              href="/library?sort_by=recent"
              className="flex items-center gap-1 text-sm text-muted-foreground hover:text-[#d4a853] transition-colors"
            >
              더 보기
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          <div className="overflow-x-auto pb-2 -mx-4 px-4 sm:mx-0 sm:px-0">
            <div className="flex gap-4 sm:grid sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
              {stats.recent_tracks.slice(0, 12).map((track, i) => (
                <div
                  key={track.track_id}
                  className="flex-shrink-0 w-[160px] sm:w-auto"
                >
                  <TrackCard track={track} index={i} />
                </div>
              ))}
            </div>
          </div>
        </motion.section>
      )}

      {/* ── 4. Library Stats (Bottom) ── */}
      {stats && (
        <motion.section
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.45 }}
        >
          <LibraryStatsView stats={stats} />
        </motion.section>
      )}
    </div>
  );
}
