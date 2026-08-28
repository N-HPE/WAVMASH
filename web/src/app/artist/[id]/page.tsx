'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { ChevronLeft } from 'lucide-react';
import api from '@/lib/api';
import type { CatalogArtistProfile } from '@/lib/types';
import CatalogTrackRow from '@/components/CatalogTrackRow';
import CatalogAlbumCard from '@/components/CatalogAlbumCard';
import FollowArtistButton from '@/components/FollowArtistButton';
import { Skeleton } from '@/components/ui/skeleton';
import { formatFollowers, popularityTier, type PopularityTierTone } from '@/lib/catalog';
import { cn } from '@/lib/utils';

/** Superstar→흑, Mainstream→빨강, Established→노랑, Rising→초록, Emerging→파랑 */
const TIER_BADGE: Record<PopularityTierTone, string> = {
  superstar: 'bg-neutral-950 ring-1 ring-white/25',
  mainstream: 'bg-red-500',
  established: 'bg-yellow-400',
  rising: 'bg-green-500',
  emerging: 'bg-blue-500',
};

export default function ArtistPage() {
  const params = useParams();
  const artistId = params.id as string;
  const [profile, setProfile] = useState<CatalogArtistProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!artistId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
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
        <Skeleton className="h-24 rounded-lg skeleton-shimmer" />
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

  const { artist, top_tracks, albums, singles } = profile;
  const tier = popularityTier(artist.popularity);

  return (
    <div className="py-4 space-y-6">
      <div>
        <Link
          href="/search"
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground mb-2"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
          검색
        </Link>
        <div className="flex items-start gap-4 min-w-0">
          <div className="h-20 w-20 sm:h-24 sm:w-24 rounded-full overflow-hidden bg-secondary shrink-0">
            {artist.image_url ? (
              <img
                src={artist.image_url}
                alt=""
                className="h-full w-full object-cover"
              />
            ) : null}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-xs text-muted-foreground mb-0.5">아티스트</p>
            <h1 className="text-xl sm:text-2xl font-bold truncate">{artist.name}</h1>
            <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
              <span
                className={cn(
                  'inline-block h-2.5 w-2.5 shrink-0 rounded-full',
                  TIER_BADGE[tier.tone]
                )}
                title={tier.label}
                aria-label={tier.label}
              />
              <span className="text-[11px] text-muted-foreground">
                {formatFollowers(artist.followers)} followers
              </span>
            </div>
            {artist.genres.length > 0 && (
              <p className="text-xs text-muted-foreground mt-1 truncate">
                {artist.genres.slice(0, 3).join(', ')}
              </p>
            )}
            <div className="mt-3">
              <FollowArtistButton
                artistId={artist.id}
                artistName={artist.name}
                artistImageUrl={artist.image_url}
              />
            </div>
          </div>
        </div>
      </div>

      <section className="feed-card">
        <div className="px-4 py-3 border-b border-border">
          <h2 className="text-sm font-semibold">곡</h2>
        </div>
        {top_tracks.length > 0 ? (
          <div className="py-1">
            {top_tracks.map((track, i) => (
              <CatalogTrackRow
                key={track.id}
                track={track}
                rank={i + 1}
                queue={top_tracks}
              />
            ))}
          </div>
        ) : (
          <p className="p-8 text-center text-sm text-muted-foreground">
            곡을 찾지 못했습니다.
          </p>
        )}
      </section>

      {albums.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold mb-3">앨범</h2>
          <div className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1">
            {albums.map((album) => (
              <CatalogAlbumCard
                key={album.id}
                album={album}
                href={`/album/${album.id}`}
              />
            ))}
          </div>
        </section>
      )}

      {singles.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold mb-3">싱글 및 EP</h2>
          <div className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1">
            {singles.map((album) => (
              <CatalogAlbumCard
                key={album.id}
                album={album}
                href={`/album/${album.id}`}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
