'use client';

import { FormEvent, useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Disc3,
  Download,
  ArrowRight,
  Music2,
  ListMusic,
  Search,
  Clock,
} from 'lucide-react';
import api from '@/lib/api';
import type { LibraryStats, Track } from '@/lib/types';
import TrackRow from '@/components/TrackRow';
import HomeLiveChart from '@/components/HomeLiveChart';
import { Skeleton } from '@/components/ui/skeleton';
import { buttonVariants } from '@/components/ui/button';
import { useDownload } from '@/contexts/DownloadContext';
import { cn } from '@/lib/utils';

export default function DashboardPage() {
  const router = useRouter();
  const [stats, setStats] = useState<LibraryStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const { completedTracks } = useDownload();

  const loadStats = useCallback(async () => {
    try {
      const data = await api.getLibraryStats();
      setStats(data);
    } catch {
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  useEffect(() => {
    if (completedTracks.length > 0) {
      loadStats();
    }
  }, [completedTracks, loadStats]);

  const handleSearch = (e: FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    router.push(`/search?q=${encodeURIComponent(q)}`);
  };

  const recentTracks: Track[] = stats?.recent_tracks ?? [];

  return (
    <div className="py-4 space-y-4">
      {/* Search hero */}
      <div className="feed-card p-5 sm:p-6">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold mb-1">탐색</h1>
            <p className="text-sm text-muted-foreground">
              아티스트·곡을 검색하고, 실시간 차트와 내 라이브러리를 한곳에서 보세요.
            </p>
          </div>
          <Link
            href="/download"
            className={cn(
              buttonVariants({ size: 'sm' }),
              'gap-1.5 shrink-0'
            )}
          >
            <Download className="h-3.5 w-3.5" />
            다운로드
          </Link>
        </div>

        <form onSubmit={handleSearch} className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="아티스트, 곡 검색..."
            className="w-full h-11 rounded-lg border border-border bg-secondary/40 pl-10 pr-4 text-sm outline-none placeholder:text-muted-foreground focus:border-[#d4a853]/50 focus:ring-1 focus:ring-[#d4a853]/30"
          />
        </form>
      </div>

      {/* Quick stats */}
      {stats && !loading && (
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: '트랙', value: stats.total_tracks, icon: Music2 },
            { label: '아티스트', value: stats.total_artists, icon: Disc3 },
            { label: '앨범', value: stats.total_albums, icon: ListMusic },
          ].map(({ label, value, icon: Icon }) => (
            <div key={label} className="feed-card p-3 text-center">
              <Icon className="h-4 w-4 text-[#d4a853] mx-auto mb-1" />
              <p className="text-lg font-bold tabular-nums">{value.toLocaleString()}</p>
              <p className="text-xs text-muted-foreground">{label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Live popularity chart */}
      <HomeLiveChart />

      {/* Recent library */}
      <div className="feed-card">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-[#d4a853]" />
            <h2 className="text-base font-semibold">최근 라이브러리</h2>
          </div>
          <Link
            href="/library?sort_by=recent"
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-[#d4a853] transition-colors"
          >
            전체 라이브러리
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        {loading ? (
          <div className="divide-y divide-border">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="px-4 py-3">
                <Skeleton className="h-14 rounded-md skeleton-shimmer" />
              </div>
            ))}
          </div>
        ) : recentTracks.length > 0 ? (
          <div className="divide-y divide-border">
            {recentTracks.map((track) => (
              <div key={track.track_id} className="px-3 py-2">
                <TrackRow track={track} />
              </div>
            ))}
          </div>
        ) : (
          <div className="p-10 text-center">
            <Download className="h-10 w-10 text-muted-foreground/30 mx-auto mb-3" />
            <p className="text-sm font-medium mb-1">아직 보관된 트랙이 없습니다</p>
            <p className="text-xs text-muted-foreground mb-4">
              다운로드 메뉴에서 첫 트랙을 추가하세요.
            </p>
            <Link
              href="/download"
              className={cn(buttonVariants({ size: 'sm' }), 'gap-1.5 inline-flex')}
            >
              <Download className="h-3.5 w-3.5" />
              다운로드로 이동
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
