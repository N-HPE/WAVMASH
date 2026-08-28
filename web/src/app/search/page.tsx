'use client';

import { Suspense, useEffect, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Search } from 'lucide-react';
import api from '@/lib/api';
import type { CatalogSearchResult } from '@/lib/types';
import CatalogTrackRow from '@/components/CatalogTrackRow';
import { Skeleton } from '@/components/ui/skeleton';
import { formatFollowers } from '@/lib/catalog';

function SearchInner() {
  const params = useSearchParams();
  const q = (params.get('q') || '').trim();
  const [data, setData] = useState<CatalogSearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!q) {
      setData(null);
      setError(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .searchCatalog(q)
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : '검색에 실패했습니다.');
          setData(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [q]);

  if (!q) {
    return (
      <div className="py-16 text-center">
        <Search className="h-10 w-10 text-muted-foreground/40 mx-auto mb-3" />
        <h1 className="text-lg font-semibold mb-1">아티스트 · 곡 검색</h1>
        <p className="text-sm text-muted-foreground">
          상단 검색창에 이름이나 곡명을 입력하세요.
        </p>
      </div>
    );
  }

  return (
    <div className="py-4 space-y-6">
      <div>
        <p className="text-xs text-muted-foreground mb-1">검색</p>
        <h1 className="text-xl font-bold truncate">{q}</h1>
      </div>

      {loading && (
        <div className="space-y-3">
          <Skeleton className="h-24 rounded-lg skeleton-shimmer" />
          <Skeleton className="h-48 rounded-lg skeleton-shimmer" />
        </div>
      )}

      {error && (
        <div className="feed-card p-6 text-sm text-muted-foreground">{error}</div>
      )}

      {!loading && data && (
        <>
          {data.artists.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold mb-3">아티스트</h2>
              <div className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1">
                {data.artists.map((artist) => (
                  <Link
                    key={artist.id}
                    href={`/artist/${artist.id}`}
                    className="w-[140px] shrink-0 feed-card p-3 hover:bg-white/[0.03] transition-colors"
                  >
                    <div className="h-[116px] w-[116px] mx-auto rounded-full overflow-hidden bg-secondary mb-3">
                      {artist.image_url ? (
                        <img
                          src={artist.image_url}
                          alt=""
                          className="h-full w-full object-cover"
                        />
                      ) : null}
                    </div>
                    <p className="truncate text-sm font-semibold text-center">
                      {artist.name}
                    </p>
                    <p className="text-[11px] text-muted-foreground text-center">
                      {formatFollowers(artist.followers)} 팔로워
                    </p>
                  </Link>
                ))}
              </div>
            </section>
          )}

          <section className="feed-card">
            <div className="px-4 py-3 border-b border-border">
              <h2 className="text-sm font-semibold">곡</h2>
            </div>
            {data.tracks.length > 0 ? (
              <div className="py-1">
                {data.tracks.map((track, i) => (
                  <CatalogTrackRow
                    key={track.id}
                    track={track}
                    rank={i + 1}
                    queue={data.tracks}
                  />
                ))}
              </div>
            ) : (
              <p className="p-8 text-center text-sm text-muted-foreground">
                곡 검색 결과가 없습니다.
              </p>
            )}
          </section>
        </>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <div className="py-8">
          <Skeleton className="h-48 rounded-lg skeleton-shimmer" />
        </div>
      }
    >
      <SearchInner />
    </Suspense>
  );
}
