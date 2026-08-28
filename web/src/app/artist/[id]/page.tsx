'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { ChevronDown, ChevronUp } from 'lucide-react';
import api from '@/lib/api';
import type { CatalogArtistProfile } from '@/lib/types';
import CatalogTrackRow from '@/components/CatalogTrackRow';
import { Skeleton } from '@/components/ui/skeleton';
import { formatFollowers } from '@/lib/catalog';

export default function ArtistPage() {
  const params = useParams();
  const artistId = params.id as string;
  const [profile, setProfile] = useState<CatalogArtistProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showMore, setShowMore] = useState(false);

  useEffect(() => {
    if (!artistId) return;
    let cancelled = false;
    setLoading(true);
    api
      .getCatalogArtist(artistId)
      .then((data) => {
        if (!cancelled) setProfile(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : '아티스트를 불러오지 못했습니다.');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [artistId]);

  if (loading) {
    return (
      <div className="py-4 space-y-4">
        <Skeleton className="h-40 rounded-lg skeleton-shimmer" />
        <Skeleton className="h-64 rounded-lg skeleton-shimmer" />
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="py-16 text-center text-sm text-muted-foreground">
        {error || '아티스트를 찾을 수 없습니다.'}
      </div>
    );
  }

  const { artist, top_tracks } = profile;
  const visible = showMore ? top_tracks.slice(0, 10) : top_tracks.slice(0, 5);

  return (
    <div className="py-4 space-y-4">
      <div className="feed-card overflow-hidden">
        <div className="h-28 sm:h-36 bg-gradient-to-r from-[#1a1a2e] via-[#2d1f3d] to-[#1a1a2e]" />
        <div className="px-4 pb-5 -mt-12 relative flex flex-col sm:flex-row sm:items-end gap-4">
          <div className="h-28 w-28 sm:h-36 sm:w-36 rounded-full overflow-hidden border-4 border-card bg-secondary shrink-0 shadow-lg">
            {artist.image_url ? (
              <img
                src={artist.image_url}
                alt={artist.name}
                className="h-full w-full object-cover"
              />
            ) : null}
          </div>
          <div className="pb-1 min-w-0">
            <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">
              아티스트
            </p>
            <h1 className="text-2xl sm:text-3xl font-bold truncate">{artist.name}</h1>
            <p className="text-sm text-muted-foreground mt-1">
              {formatFollowers(artist.followers)} 팔로워
              {artist.genres.length > 0 ? ` · ${artist.genres.slice(0, 3).join(', ')}` : ''}
            </p>
          </div>
        </div>
      </div>

      <div className="feed-card">
        <div className="px-4 py-3 border-b border-border">
          <h2 className="text-base font-semibold">인기</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            이 아티스트의 가장 많이 재생된 곡
          </p>
        </div>
        <div className="py-1">
          {visible.map((track, i) => (
            <CatalogTrackRow
              key={track.id}
              track={track}
              rank={i + 1}
              queue={top_tracks}
            />
          ))}
        </div>
        {top_tracks.length > 5 && (
          <button
            type="button"
            onClick={() => setShowMore((v) => !v)}
            className="w-full flex items-center justify-center gap-1 py-3 text-xs font-medium text-muted-foreground hover:text-foreground border-t border-border"
          >
            {showMore ? (
              <>
                접기 <ChevronUp className="h-3.5 w-3.5" />
              </>
            ) : (
              <>
                Show more <ChevronDown className="h-3.5 w-3.5" />
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}
