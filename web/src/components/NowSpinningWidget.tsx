'use client';

/* ──────────────────────────────────────────────
   WaveMash — Now Spinning On Deck (Turntable Widget)
   턴테이블 톤암 & 바이닐 회전 인터랙션 위젯
   ────────────────────────────────────────────── */

import React, { useState, useRef } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Play, Pause, Disc3, Radio } from 'lucide-react';
import type { Track } from '@/lib/types';
import api from '@/lib/api';

interface NowSpinningWidgetProps {
  track: Track | null;
  collectorName?: string;
}

export default function NowSpinningWidget({
  track,
  collectorName = 'KYO',
}: NowSpinningWidgetProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  if (!track) return null;

  const coverUrl = api.getCoverUrl(track.track_id, 300);

  const togglePlay = () => {
    if (!audioRef.current) {
      audioRef.current = new Audio(api.getStreamUrl(track.track_id));
      audioRef.current.onended = () => setIsPlaying(false);
    }

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play().catch(console.warn);
      setIsPlaying(true);
    }
  };

  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#151528] via-[#0d0d1a] to-[#070710] border border-white/10 p-5 shadow-2xl backdrop-blur-xl">
      {/* Top Header Badge */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#d4a853] opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[#d4a853]"></span>
          </span>
          <span className="text-xs font-bold uppercase tracking-wider text-[#d4a853]">
            Now Spinning on Deck
          </span>
        </div>
        <span className="text-[10px] text-muted-foreground uppercase font-mono">
          {collectorName}&apos;s Choice
        </span>
      </div>

      <div className="flex items-center gap-5">
        {/* ── Turntable Platter & Vinyl ── */}
        <div
          onClick={togglePlay}
          className="relative w-24 h-24 sm:w-28 sm:h-28 rounded-full bg-[#111] border-4 border-[#252538] shadow-2xl flex items-center justify-center cursor-pointer shrink-0 group"
        >
          {/* Rotating Vinyl */}
          <div
            className={`w-full h-full rounded-full flex items-center justify-center transition-all ${
              isPlaying ? 'animate-spin' : ''
            }`}
            style={{ animationDuration: '3s' }}
          >
            {/* Vinyl grooves */}
            <div className="w-4/5 h-4/5 rounded-full border border-white/10 flex items-center justify-center">
              <div className="w-1/2 h-1/2 rounded-full overflow-hidden border-2 border-[#d4a853]/40 shadow-inner">
                {track.has_cover ? (
                  <img src={coverUrl} alt={track.title} className="w-full h-full object-cover" />
                ) : (
                  <Disc3 className="w-full h-full p-2 text-[#d4a853]" />
                )}
              </div>
            </div>
          </div>

          {/* Center Center Hole */}
          <div className="absolute w-3 h-3 rounded-full bg-black border border-white/30" />

          {/* Play/Pause Overlay */}
          <div className="absolute inset-0 rounded-full bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
            {isPlaying ? (
              <Pause className="w-6 h-6 text-[#d4a853] fill-current" />
            ) : (
              <Play className="w-6 h-6 text-[#d4a853] fill-current ml-0.5" />
            )}
          </div>
        </div>

        {/* ── Track Details ── */}
        <div className="flex-1 min-w-0">
          <Link href={`/track/${track.track_id}`}>
            <h4 className="font-bold text-base text-white truncate hover:text-[#d4a853] transition-colors">
              {track.title}
            </h4>
          </Link>
          <p className="text-xs text-muted-foreground truncate mt-0.5">{track.artist}</p>

          {/* Tags & BPM */}
          <div className="flex items-center gap-2 mt-3">
            {track.bpm > 0 && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#d4a853]/15 text-[#d4a853] border border-[#d4a853]/30 font-semibold">
                {Math.round(track.bpm)} BPM
              </span>
            )}
            {track.key && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 text-white/80 border border-white/10">
                {track.key}
              </span>
            )}
            {track.genre && (
              <span className="text-[10px] px-2 py-0.5 rounded bg-white/5 text-white/70 border border-white/10 truncate max-w-[80px]">
                {track.genre}
              </span>
            )}
          </div>

          {/* Mini Equalizer Bar Animation when playing */}
          {isPlaying && (
            <div className="flex items-end gap-1 h-3 mt-3">
              {[40, 80, 60, 100, 50, 90, 70].map((h, i) => (
                <motion.span
                  key={i}
                  animate={{ height: ['20%', `${h}%`, '30%'] }}
                  transition={{
                    repeat: Infinity,
                    duration: 0.6 + i * 0.1,
                    ease: 'easeInOut',
                  }}
                  className="w-1 bg-[#d4a853] rounded-full"
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
