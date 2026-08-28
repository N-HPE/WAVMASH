'use client';

import { useState } from 'react';
import type { MouseEvent } from 'react';
import { Download, Loader2, Pause, Play } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useDownload } from '@/contexts/DownloadContext';
import { usePlayer } from '@/contexts/PlayerContext';
import api from '@/lib/api';
import type { CatalogTrack } from '@/lib/types';
import { catalogTrackToPlayerTrack, formatDuration } from '@/lib/catalog';

interface CatalogTrackRowProps {
  track: CatalogTrack;
  rank?: number;
  queue?: CatalogTrack[];
}

function trackSpotifyUrl(track: CatalogTrack): string {
  if (track.spotify_url?.includes('/track/')) {
    return track.spotify_url.split('?')[0];
  }
  if (track.id) return `https://open.spotify.com/track/${track.id}`;
  return (track.spotify_url || '').split('?')[0];
}

export default function CatalogTrackRow({
  track,
  rank,
  queue,
}: CatalogTrackRowProps) {
  const { play, togglePlay, currentTrack, isPlaying } = usePlayer();
  const { startDownload, active, activeUrl } = useDownload();
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewMissing, setPreviewMissing] = useState(false);
  const [youtubeId, setYoutubeId] = useState<string | null>(null);

  const playerTrack = catalogTrackToPlayerTrack(track);
  if (youtubeId) {
    playerTrack.url = `https://www.youtube.com/watch?v=${youtubeId}`;
    playerTrack.external_id = youtubeId;
    playerTrack.preview_url = undefined;
    playerTrack.platform = 'youtube';
  }

  const isCurrent = currentTrack?.track_id === playerTrack.track_id;
  const downloadUrl = trackSpotifyUrl(track);
  const isThisDownloading =
    active &&
    !!downloadUrl &&
    (activeUrl === downloadUrl ||
      (!!track.id && !!activeUrl && activeUrl.includes(track.id)));

  const handlePlay = async () => {
    if (isCurrent) {
      togglePlay();
      return;
    }

    let next = { ...playerTrack };
    let resolvedYt: string | null = youtubeId;

    if (!resolvedYt) {
      setPreviewLoading(true);
      try {
        const res = await api.resolveCatalogPreview(
          track.title,
          track.artist || track.primary_artist,
          track.id
        );
        if (res.youtube_id) {
          resolvedYt = res.youtube_id;
          setYoutubeId(res.youtube_id);
          next = {
            ...next,
            url: res.youtube_url || `https://www.youtube.com/watch?v=${res.youtube_id}`,
            external_id: res.youtube_id,
            preview_url: undefined,
            platform: 'youtube',
          };
          setPreviewMissing(false);
        } else if (track.preview_url) {
          // YouTube 매칭 실패 시 Spotify/카탈로그 미리듣기 폴백
          next = { ...next, preview_url: track.preview_url };
          setPreviewMissing(false);
        } else {
          setPreviewMissing(true);
          setPreviewLoading(false);
          return;
        }
      } catch {
        if (track.preview_url) {
          next = { ...next, preview_url: track.preview_url };
        } else {
          setPreviewMissing(true);
          setPreviewLoading(false);
          return;
        }
      } finally {
        setPreviewLoading(false);
      }
    } else {
      next = {
        ...next,
        url: `https://www.youtube.com/watch?v=${resolvedYt}`,
        external_id: resolvedYt,
        preview_url: undefined,
        platform: 'youtube',
      };
    }

    const q = (queue || [track]).map((t) => {
      const mapped = catalogTrackToPlayerTrack(t);
      return mapped.track_id === next.track_id ? next : mapped;
    });
    play(next, q);
  };

  const handleDownload = (e: MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (active || !downloadUrl) return;
    void startDownload(downloadUrl);
  };

  return (
    <div className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-white/[0.04] group min-w-0">
      <div className="w-6 shrink-0 text-center text-xs tabular-nums text-muted-foreground">
        {rank ?? ''}
      </div>

      <button
        type="button"
        onClick={() => void handlePlay()}
        disabled={previewLoading}
        className="relative h-11 w-11 shrink-0 overflow-hidden rounded-md bg-secondary"
        title={
          previewMissing
            ? 'YouTube에서 곡을 찾지 못했습니다'
            : 'YouTube로 재생'
        }
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
            isCurrent || previewLoading
              ? 'opacity-100'
              : 'opacity-0 group-hover:opacity-100'
          }`}
        >
          {previewLoading ? (
            <Loader2 className="h-4 w-4 text-white animate-spin" />
          ) : isCurrent && isPlaying ? (
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
        disabled={active || !downloadUrl}
        className="shrink-0 h-8 w-8 p-0"
        onClick={handleDownload}
      >
        {isThisDownloading ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <Download className="h-3.5 w-3.5" />
        )}
      </Button>
    </div>
  );
}
