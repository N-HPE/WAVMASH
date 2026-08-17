'use client';

/* ──────────────────────────────────────────────
   WaveMash — Track Card (Album + LP Vinyl + Instant Play)
   앨범 커버 클릭 시 YouTube/Audio 즉시 자동 재생
   ────────────────────────────────────────────── */

import React, { useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Music, Play, Pause } from 'lucide-react';
import api from '@/lib/api';
import { useCoverGlow } from '@/lib/coverColors';
import { usePlayer } from '@/contexts/PlayerContext';
import type { Track } from '@/lib/types';

interface TrackCardProps {
  track: Track;
  index?: number;
}

export default function TrackCard({ track, index = 0 }: TrackCardProps) {
  const { currentTrack, isPlaying: globalPlaying, play, togglePlay: globalTogglePlay } = usePlayer();
  const isCurrentTrackPlaying = globalPlaying && currentTrack?.track_id === track.track_id;

  const glowColor = useCoverGlow(
    track.track_id,
    track.has_cover,
    track.dominant_color
  );
  const [imgError, setImgError] = useState(false);

  const coverUrl = api.getCoverUrl(track.track_id, 320);

  const handlePlayClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (currentTrack?.track_id === track.track_id) {
      globalTogglePlay();
    } else {
      play(track);
    }
  };

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
      <div className="block group">
        <div className="glass rounded-xl overflow-hidden hover-lift">
          {/* ── Cover + Vinyl ── */}
          <div
            className="cover-glow vinyl-container relative aspect-square overflow-hidden cursor-pointer"
            style={{ '--glow-color': glowColor } as React.CSSProperties}
            onClick={handlePlayClick}
          >
            {/* LP Vinyl Disc */}
            <div
              className={`vinyl-disc transition-all ${
                isCurrentTrackPlaying ? 'translate-x-4 animate-spin' : ''
              }`}
              style={{ animationDuration: '3s' }}
            />

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

            {/* Center Play/Pause Button Overlay */}
            <div className="absolute inset-0 z-20 flex items-center justify-center bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity">
              <div className="w-10 h-10 rounded-full bg-[#d4a853] text-black flex items-center justify-center shadow-xl transform group-hover:scale-110 active:scale-95 transition-transform">
                {isCurrentTrackPlaying ? (
                  <Pause className="w-5 h-5 fill-current" />
                ) : (
                  <Play className="w-5 h-5 fill-current ml-0.5" />
                )}
              </div>
            </div>

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
          <Link href={`/track/${track.track_id}`} className="block p-3">
            <p className="truncate text-sm font-medium text-foreground group-hover:text-[#d4a853] transition-colors">
              {track.title}
            </p>
            <p className="truncate text-xs text-muted-foreground">
              {track.artist}
            </p>
          </Link>
        </div>
      </div>
    </motion.div>
  );
}
