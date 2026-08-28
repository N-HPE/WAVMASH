'use client';

import Link from 'next/link';
import { Download, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useDownload } from '@/contexts/DownloadContext';
import type { CatalogAlbum } from '@/lib/types';

interface CatalogAlbumCardProps {
  album: CatalogAlbum;
  href?: string;
}

export default function CatalogAlbumCard({ album, href }: CatalogAlbumCardProps) {
  const { startDownload, active, activeUrl } = useDownload();
  const url = (album.spotify_url || '').split('?')[0];
  const isThis =
    active && !!url && (activeUrl === url || (!!album.id && !!activeUrl && activeUrl.includes(album.id)));
  const year = (album.release_date || '').slice(0, 4);
  const typeLabel =
    album.album_type === 'single'
      ? '싱글'
      : album.album_type === 'compilation'
        ? '컴필레이션'
        : '앨범';

  const body = (
    <>
      <div className="aspect-square rounded-md overflow-hidden bg-secondary mb-2">
        {album.thumbnail_url ? (
          <img
            src={album.thumbnail_url}
            alt=""
            className="h-full w-full object-cover"
          />
        ) : null}
      </div>
      <p className="truncate text-sm font-medium">{album.name}</p>
      <p className="truncate text-[11px] text-muted-foreground">
        {[year, typeLabel].filter(Boolean).join(' · ')}
      </p>
    </>
  );

  return (
    <div className="w-[140px] shrink-0 group">
      {href ? (
        <Link
          href={href}
          className="block feed-card p-2.5 hover:bg-white/[0.03] transition-colors"
        >
          {body}
        </Link>
      ) : (
        <div className="feed-card p-2.5">{body}</div>
      )}
      <Button
        type="button"
        size="sm"
        variant="outline"
        disabled={active || !url}
        className="mt-1.5 w-full h-7 gap-1 text-[11px]"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          if (!active && url) void startDownload(url);
        }}
      >
        {isThis ? (
          <Loader2 className="h-3 w-3 animate-spin" />
        ) : (
          <Download className="h-3 w-3" />
        )}
        WAV
      </Button>
    </div>
  );
}
