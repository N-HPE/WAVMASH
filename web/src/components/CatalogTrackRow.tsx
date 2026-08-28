'use client';

import { Download, Loader2, Pause, Play } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useDownload } from '@/contexts/DownloadContext';
import { usePlayer } from '@/contexts/PlayerContext';
import type { CatalogTrack } from '@/lib/types';
import { catalogTrackToPlayerTrack, formatDuration } from '@/lib/catalog';

interface CatalogTrackRowProps {
  track: CatalogTrack;
  rank?: number;
  queue?: CatalogTrack[];
}

export default function CatalogTrackRow({
  track,
  rank,
  queue,
}: CatalogTrackRowProps) {
  const { play, togglePlay, currentTrack, isPlaying } = usePlayer();
  const { startDownload, active } = useDownload();
  const playerTrack = catalogTrackToPlayerTrack(track);
  const isCurrent = currentTrack?.track_id === playerTrack.track_id;
  const canPreview = Boolean(track.preview_url);

  const handlePlay = () => {
    if (isCurrent) {
      togglePlay();
      return;
    }
    const q = (queue || [track]).map(catalogTrackToPlayerTrack);
    play(playerTrack, q);
  };

  return (
    <div className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-white/[0.04] group min-w-0">
      <div className="w-6 shrink-0 text-center text-xs tabular-nums text-muted-foreground">
        {rank ?? ''}
      </div>

      <button
        type="button"
        onClick={handlePlay}
        disabled={!canPreview && !isCurrent}
        className="relative h-11 w-11 shrink-0 overflow-hidden rounded-md bg-secondary"
        title={canPreview ? '미리듣기' : '미리듣기가 없는 곡입니다'}
      >
        {track.thumbnail_url ? (
          <img
            src={track.thumbnail_url}
            alt=""
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="h-full w-full bg-secondary" />
        )}
        <div
          className={`absolute inset-0 flex items-center justify-center bg-black/45 transition-opacity ${
            isCurrent ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
          }`}
        >
          {isCurrent && isPlaying ? (
            <Pause className="h-4 w-4 text-white fill-white" />
          ) : (
            <Play className="h-4 w-4 text-white fill-white" />
          )}
        </div>
      </button>

      <div className="min-w-0 flex-1">
        <p
          className={`truncate text-sm font-medium ${
            isCurrent ? 'text-[#d4a853]' : ''
          }`}
        >
          {track.title}
        </p>
        <p className="truncate text-xs text-muted-foreground">{track.artist}</p>
      </div>

      <span className="hidden sm:block truncate text-xs text-muted-foreground max-w-[140px]">
        {track.album}
      </span>
      <span className="hidden md:block text-xs tabular-nums text-muted-foreground w-10 text-right">
        {formatDuration(track.duration_ms)}
      </span>

      <Button
        type="button"
        size="sm"
        variant="outline"
        disabled={active || !track.spotify_url}
        className="shrink-0 h-8 gap-1.5 text-xs"
        onClick={() => startDownload(track.spotify_url)}
      >
        {active ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <Download className="h-3.5 w-3.5" />
        )}
        <span className="hidden sm:inline">WAV</span>
      </Button>
    </div>
  );
}
