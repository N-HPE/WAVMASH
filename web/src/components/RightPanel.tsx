'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { TrendingUp, Disc3, Users, Library } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import api from '@/lib/api';
import type { LibraryStats, ChartEntry } from '@/lib/types';

export default function RightPanel() {
  const [stats, setStats] = useState<LibraryStats | null>(null);
  const [chart, setChart] = useState<ChartEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getLibraryStats().catch(() => null),
      api.getMostCollectedChart().catch(() => []),
    ])
      .then(([statsData, chartData]) => {
        if (statsData) setStats(statsData);
        setChart(chartData.slice(0, 5));
      })
      .finally(() => setLoading(false));
  }, []);

  const genres = stats
    ? Object.entries(stats.genres)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 8)
    : [];

  if (loading) {
    return (
      <aside className="app-right-panel hidden xl:block">
        <div className="space-y-4">
          <Skeleton className="h-32 rounded-lg skeleton-shimmer" />
          <Skeleton className="h-48 rounded-lg skeleton-shimmer" />
        </div>
      </aside>
    );
  }

  return (
    <aside className="app-right-panel hidden xl:block">
      <div className="space-y-4">
        {/* Stats widget */}
        {stats && (
          <div className="feed-card p-4">
            <h3 className="text-sm font-semibold mb-3">내 라이브러리</h3>
            <div className="space-y-2">
              {[
                { label: '트랙', value: stats.total_tracks, icon: Disc3 },
                { label: '아티스트', value: stats.total_artists, icon: Users },
                { label: '앨범', value: stats.total_albums, icon: Library },
              ].map(({ label, value, icon: Icon }) => (
                <div
                  key={label}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="flex items-center gap-2 text-muted-foreground">
                    <Icon className="h-4 w-4" />
                    {label}
                  </span>
                  <span className="font-medium tabular-nums">
                    {value.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Trending */}
        {chart.length > 0 && (
          <div className="feed-card p-4">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="h-4 w-4 text-[#d4a853]" />
              <h3 className="text-sm font-semibold">인기 수집</h3>
            </div>
            <ol className="space-y-2">
              {chart.map((entry, i) => (
                <li key={entry.track_id}>
                  <Link
                    href={`/track/${entry.track_id}`}
                    className="flex items-center gap-3 rounded-md p-1.5 -mx-1.5 hover:bg-white/5 transition-colors"
                  >
                    <span className="text-xs font-bold text-muted-foreground w-4 tabular-nums">
                      {i + 1}
                    </span>
                    <div className="h-9 w-9 shrink-0 overflow-hidden rounded-md bg-secondary">
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
                      {entry.collector_count}
                    </span>
                  </Link>
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* Genres */}
        {genres.length > 0 && (
          <div className="feed-card p-4">
            <h3 className="text-sm font-semibold mb-3">장르</h3>
            <div className="flex flex-wrap gap-1.5">
              {genres.map(([genre, count]) => (
                <Link
                  key={genre}
                  href={`/library?genre=${encodeURIComponent(genre)}`}
                  className="inline-flex items-center gap-1 rounded-md bg-secondary px-2.5 py-1 text-xs hover:bg-secondary/80 transition-colors"
                >
                  {genre}
                  <span className="text-muted-foreground">{count}</span>
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
