'use client';

/* ──────────────────────────────────────────────
   WaveMash — Track Card (Album + LP Vinyl)
   ────────────────────────────────────────────── */

import { useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Music } from 'lucide-react';
import api from '@/lib/api';
import { useCoverGlow } from '@/lib/coverColors';
import type { Track } from '@/lib/types';

interface TrackCardProps {
  track: Track;
  index?: number;
}

export default function TrackCard({ track, index = 0 }: TrackCardProps) {
  const glowColor = useCoverGlow(
    track.track_id,
    track.has_cover,
    track.dominant_color
  );
  const [imgError, setImgError] = useState(false);

  // 그리드용 작은 썸네일 (원본 대신 서버 리사이즈)
  const coverUrl = api.getCoverUrl(track.track_id, 320);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        delay: Math.min(index, 12) * 0.04,
        duration: 0.35,
        ease: [0.25, 0.46, 0.45, 0.94],
      }}
    >
      <Link href={`/track/${track.track_id}`} className="block group">
        <div className="glass rounded-xl overflow-hidden hover-lift">
          {/* ── Cover + Vinyl ── */}
          <div
            className="cover-glow vinyl-container relative aspect-square overflow-hidden"
            style={{ '--glow-color': glowColor } as React.CSSProperties}
          >
            {/* LP Vinyl Disc */}
            <div className="vinyl-disc" />

            {/* Album Cover */}
            {track.has_cover && !imgError ? (
              <img
                src={coverUrl}
                alt={`${track.title} cover`}
                className="relative z-10 h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                loading="lazy"
                decoding="async"
                onError={() => setImgError(true)}
              />
            ) : (
              <div className="relative z-10 flex h-full w-full items-center justify-center bg-gradient-to-br from-[#1a1a2e] to-[#0a0a14]">
                <Music className="h-12 w-12 text-white/10" />
              </div>
            )}

            {/* BPM & Key Badges */}
            <div className="absolute bottom-2 right-2 z-20 flex gap-1">
              {track.bpm > 0 && (
                <span className="badge-bpm rounded-md px-1.5 py-0.5 text-[10px] font-medium backdrop-blur-md">
                  {Math.round(track.bpm)}
                </span>
              )}
              {track.key && (
                <span className="badge-key rounded-md px-1.5 py-0.5 text-[10px] font-medium backdrop-blur-md">
                  {track.key}
                </span>
              )}
            </div>
          </div>

          {/* ── Track Info ── */}
          <div className="p-3">
            <p className="truncate text-sm font-medium text-foreground">
              {track.title}
            </p>
            <p className="truncate text-xs text-muted-foreground">
              {track.artist}
            </p>
          </div>
        </div>
      </Link>
    </motion.div>
  );
}
