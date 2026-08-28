'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Music, Play } from 'lucide-react';
import api from '@/lib/api';
import type { Track } from '@/lib/types';

interface TrackRowProps {
  track: Track;
  showMeta?: boolean;
  compact?: boolean;
}

export default function TrackRow({
  track,
  showMeta = true,
  compact = false,
}: TrackRowProps) {
  const [imgError, setImgError] = useState(false);
  const coverUrl = api.getCoverUrl(track.track_id, compact ? 96 : 128);

  return (
    <Link
      href={`/track/${track.track_id}`}
      className={`feed-track-row group ${compact ? 'feed-track-row-compact' : ''}`}
    >
      <div className="relative shrink-0 overflow-hidden rounded-md bg-secondary">
        {track.has_cover && !imgError ? (
          <img
            src={coverUrl}
            alt=""
            className="feed-track-cover object-cover"
            loading="lazy"
            decoding="async"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="feed-track-cover flex items-center justify-center bg-gradient-to-br from-[#1a1a2e] to-[#0a0a14]">
            <Music className="h-5 w-5 text-white/15" />
          </div>
        )}
        <div className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity">
          <Play className="h-5 w-5 text-white fill-white" />
        </div>
      </div>

      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold group-hover:text-[#d4a853] transition-colors">
          {track.title}
        </p>
        <p className="truncate text-xs text-muted-foreground">{track.artist}</p>
        {track.album && !compact && (
          <p className="truncate text-xs text-muted-foreground/70 mt-0.5">
            {track.album}
          </p>
        )}
      </div>

      {showMeta && (
        <div className="hidden sm:flex items-center gap-1.5 shrink-0">
          {track.bpm > 0 && (
            <span className="badge-bpm rounded px-1.5 py-0.5 text-[10px] font-medium">
              {Math.round(track.bpm)}
            </span>
          )}
          {track.key && (
            <span className="badge-key rounded px-1.5 py-0.5 text-[10px] font-medium">
              {track.key}
            </span>
          )}
          {track.genre && (
            <span className="badge-genre rounded px-1.5 py-0.5 text-[10px] font-medium">
              {track.genre}
            </span>
          )}
        </div>
      )}
    </Link>
  );
}
