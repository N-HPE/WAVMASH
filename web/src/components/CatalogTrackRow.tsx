'use client';

import { useState } from 'react';
import type { MouseEvent } from 'react';
import { ListPlus, Loader2, Pause, Play } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { usePlayer } from '@/contexts/PlayerContext';
import api from '@/lib/api';
import type { CatalogTrack } from '@/lib/types';
import { catalogTrackToPlayerTrack, formatDuration } from '@/lib/catalog';
import AddToPlaylistModal from '@/components/AddToPlaylistModal';

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
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewMissing, setPreviewMissing] = useState(false);
  const [youtubeId, setYoutubeId] = useState<string | null>(null);
  const [saveOpen, setSaveOpen] = useState(false);

  const playerTrack = catalogTrackToPlayerTrack(track);
  if (youtubeId) {
    playerTrack.url = `https://www.youtube.com/watch?v=${youtubeId}`;
    playerTrack.external_id = youtubeId;
    // preview 유지: YouTube embed 실패 시 Player가 폴백
    playerTrack.platform = 'youtube';
  }

  const isCurrent = currentTrack?.track_id === playerTrack.track_id;

  const handlePlay = async () => {
    if (isCurrent) {
      togglePlay();
      return;
    }

    let next = { ...playerTrack };
    let resolvedYt: string | null = youtubeId;

    // preview가 있으면 즉시 재생 (YouTube resolve 대기 없음)
    if (!resolvedYt && track.preview_url) {
      next = { ...next, preview_url: track.preview_url };
      const q = (queue || [track]).map((t) => {
        const mapped = catalogTrackToPlayerTrack(t);
        return mapped.track_id === next.track_id ? next : mapped;
      });
      play(next, q);
      // 백그라운드로 풀트랙 YouTube 해석 (다음 재생용)
      void api
        .resolveCatalogPreview(
          track.title,
          track.artist || track.primary_artist,
          track.id
        )
        .then((res) => {
          if (res.youtube_id) setYoutubeId(res.youtube_id);
        })
        .catch(() => {});
      return;
    }

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
            preview_url: track.preview_url || next.preview_url,
            platform: 'youtube',
          };
          setPreviewMissing(false);
        } else if (track.preview_url) {
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
        preview_url: track.preview_url || next.preview_url,
        platform: 'youtube',
      };
    }

    const q = (queue || [track]).map((t) => {
      const mapped = catalogTrackToPlayerTrack(t);
      return mapped.track_id === next.track_id ? next : mapped;
    });
    play(next, q);
  };

  const handleSave = (e: MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setSaveOpen(true);
  };

  return (
    <>
      <div className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-white/[0.04] group min-w-0">
        {rank != null && (
          <div className="w-6 shrink-0 text-center text-xs tabular-nums text-muted-foreground">
            {rank}
          </div>
        )}

        <button
          type="button"
          onClick={() => void handlePlay()}
          disabled={previewLoading}
          className="relative h-11 w-11 shrink-0 overflow-hidden rounded-md bg-secondary"
          title={
            previewMissing
              ? 'YouTube에서 곡을 찾지 못했습니다'
              : '재생'
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
          className="shrink-0 h-8 w-8 p-0"
          onClick={handleSave}
          title="플레이리스트에 담기"
        >
          <ListPlus className="h-3.5 w-3.5" />
        </Button>
      </div>

      <AddToPlaylistModal
        isOpen={saveOpen}
        onClose={() => setSaveOpen(false)}
        track={catalogTrackToPlayerTrack(track)}
      />
    </>
  );
}
