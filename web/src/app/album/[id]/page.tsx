'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { ChevronLeft, Download, Loader2 } from 'lucide-react';
import api from '@/lib/api';
import type { CatalogAlbumDetail } from '@/lib/types';
import CatalogTrackRow from '@/components/CatalogTrackRow';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { useDownload } from '@/contexts/DownloadContext';

export default function AlbumPage() {
  const params = useParams();
  const albumId = params.id as string;
  const { startDownload, active, activeUrl } = useDownload();
  const [data, setData] = useState<CatalogAlbumDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!albumId) return;
    let cancelled = false;
    setLoading(true);
    api
      .getCatalogAlbum(albumId)
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : '앨범을 불러오지 못했습니다.');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [albumId]);

  if (loading) {
    return (
      <div className="py-4 space-y-4">
        <Skeleton className="h-28 rounded-lg skeleton-shimmer" />
        <Skeleton className="h-64 rounded-lg skeleton-shimmer" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="py-16 text-center text-sm text-muted-foreground">
        {error || '앨범을 찾을 수 없습니다.'}
      </div>
    );
  }

  const { album, tracks } = data;
  const downloadUrl = (album.spotify_url || '').split('?')[0];
  const isThis =
    active &&
    !!downloadUrl &&
    (activeUrl === downloadUrl ||
      (!!album.id && !!activeUrl && activeUrl.includes(album.id)));
  const year = (album.release_date || '').slice(0, 4);

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
        <div className="flex items-end gap-4 min-w-0">
          <div className="h-28 w-28 sm:h-36 sm:w-36 rounded-md overflow-hidden bg-secondary shrink-0 shadow-lg">
            {album.thumbnail_url ? (
              <img
                src={album.thumbnail_url}
                alt=""
                className="h-full w-full object-cover"
              />
            ) : null}
          </div>
          <div className="min-w-0 pb-1 flex-1">
            <p className="text-xs text-muted-foreground mb-0.5 capitalize">
              {album.album_type === 'single' ? '싱글' : '앨범'}
            </p>
            <h1 className="text-xl sm:text-2xl font-bold truncate">{album.name}</h1>
            <p className="text-sm text-muted-foreground mt-1 truncate">
              {album.artist}
              {year ? ` · ${year}` : ''}
              {album.total_tracks ? ` · ${album.total_tracks}곡` : ''}
            </p>
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={active || !downloadUrl}
              className="mt-3 h-8 gap-1.5 text-xs"
              onClick={() => downloadUrl && void startDownload(downloadUrl)}
            >
              {isThis ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Download className="h-3.5 w-3.5" />
              )}
              전체 WAV
            </Button>
          </div>
        </div>
      </div>

      <section className="feed-card">
        <div className="px-4 py-3 border-b border-border">
          <h2 className="text-sm font-semibold">곡</h2>
        </div>
        {tracks.length > 0 ? (
          <div className="py-1">
            {tracks.map((track, i) => (
              <CatalogTrackRow
                key={track.id || `${album.id}-${i}`}
                track={track}
                rank={i + 1}
                queue={tracks}
              />
            ))}
          </div>
        ) : (
          <p className="p-8 text-center text-sm text-muted-foreground">
            트랙 목록이 없습니다.
          </p>
        )}
      </section>
    </div>
  );
}
