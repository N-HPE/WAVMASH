'use client';

/* ──────────────────────────────────────────────
   WaveMash — Mini Player (Bottom Bar)
   ────────────────────────────────────────────── */

import { motion, AnimatePresence } from 'framer-motion';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Volume2,
  VolumeX,
} from 'lucide-react';
import { useCallback } from 'react';
import { usePlayer } from '@/contexts/PlayerContext';
import api from '@/lib/api';

function formatTime(seconds: number): string {
  if (!seconds || !isFinite(seconds)) return '0:00';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

const CROSSFADE_STEPS = [4, 6, 8, 12];

export default function MiniPlayer() {
  const {
    currentTrack,
    isPlaying,
    progress,
    duration,
    currentTime,
    volume,
    autoMix,
    crossfadeSec,
    isMixing,
    togglePlay,
    next,
    prev,
    setVolume,
    seekTo,
    setAutoMix,
    setCrossfadeSec,
  } = usePlayer();

  const cycleCrossfade = useCallback(() => {
    const i = CROSSFADE_STEPS.indexOf(crossfadeSec);
    setCrossfadeSec(CROSSFADE_STEPS[(i + 1) % CROSSFADE_STEPS.length]);
  }, [crossfadeSec, setCrossfadeSec]);

  const handleProgressClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const rect = e.currentTarget.getBoundingClientRect();
      const percent = ((e.clientX - rect.left) / rect.width) * 100;
      seekTo(Math.max(0, Math.min(100, percent)));
    },
    [seekTo]
  );

  const handleVolumeChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setVolume(parseFloat(e.target.value));
    },
    [setVolume]
  );

  return (
    <AnimatePresence>
      {currentTrack && (
        <motion.div
          className="fixed bottom-0 left-0 right-0 z-50 h-20 glass-strong"
          initial={{ y: 80, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 80, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        >
          {/* Gold accent line at top */}
          <div
            className="absolute top-0 left-0 right-0 h-px"
            style={{
              background:
                'linear-gradient(90deg, transparent 0%, #d4a853 50%, transparent 100%)',
              opacity: 0.3,
            }}
          />

          <div className="mx-auto flex h-full max-w-7xl items-center gap-4 px-4 sm:px-6">
            {/* ── Left: Track Info ── */}
            <div className="flex items-center gap-3 min-w-0 w-[200px] flex-shrink-0">
              <div className="h-12 w-12 flex-shrink-0 overflow-hidden rounded-lg">
                {currentTrack.thumbnail_url ? (
                  <img
                    src={currentTrack.thumbnail_url}
                    alt={currentTrack.title}
                    className="h-full w-full object-cover"
                  />
                ) : currentTrack.has_cover ? (
                  <img
                    src={api.getCoverUrl(currentTrack.track_id, 96)}
                    alt={currentTrack.title}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-[#1a1a2e] to-[#0a0a14]">
                    <Play className="h-4 w-4 text-white/20" />
                  </div>
                )}
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">
                  {currentTrack.title}
                </p>
                <p className="truncate text-xs text-muted-foreground">
                  {currentTrack.artist}
                </p>
              </div>
            </div>

            {/* ── Center: Controls ── */}
            <div className="flex flex-1 flex-col items-center gap-1">
              {/* Transport buttons */}
              <div className="flex items-center gap-3">
                <button
                  onClick={prev}
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  <SkipBack className="h-[18px] w-[18px]" />
                </button>

                <button
                  onClick={togglePlay}
                  className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-foreground transition-transform hover:scale-105 active:scale-95"
                >
                  {isPlaying ? (
                    <Pause className="h-5 w-5" />
                  ) : (
                    <Play className="h-5 w-5 ml-0.5" />
                  )}
                </button>

                <button
                  onClick={next}
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  <SkipForward className="h-[18px] w-[18px]" />
                </button>
              </div>

              {/* Progress bar */}
              <div className="flex w-full max-w-md items-center gap-2">
                <span className="w-10 text-right text-[10px] tabular-nums text-muted-foreground">
                  {formatTime(currentTime)}
                </span>
                <div
                  className="relative h-1 flex-1 cursor-pointer rounded-full bg-white/10"
                  onClick={handleProgressClick}
                >
                  <motion.div
                    className="absolute inset-y-0 left-0 rounded-full"
                    style={{
                      width: `${progress}%`,
                      background:
                        'linear-gradient(90deg, #d4a853, #f5c542)',
                    }}
                    transition={{ duration: 0.1 }}
                  />
                </div>
                <span className="w-10 text-[10px] tabular-nums text-muted-foreground">
                  {formatTime(duration)}
                </span>
              </div>
            </div>

            {/* ── Right: DJ mix (always) + Volume (sm+) ── */}
            <div className="flex items-center gap-2 flex-shrink-0 justify-end sm:w-[220px]">
              <button
                onClick={() => setAutoMix(!autoMix)}
                title={
                  autoMix
                    ? `DJ 믹스 켜짐 — 곡 끝 ${crossfadeSec}초 크로스페이드`
                    : 'DJ 믹스 꺼짐 — 곡이 끝나면 바로 다음 곡'
                }
                className={`rounded px-1.5 py-0.5 text-[10px] font-bold tracking-wide transition-colors ${
                  autoMix
                    ? 'bg-[#d4a853] text-black'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                DJ
              </button>

              {autoMix && (
                <button
                  onClick={cycleCrossfade}
                  title="크로스페이드 길이 변경"
                  className="text-[10px] tabular-nums text-muted-foreground transition-colors hover:text-foreground"
                >
                  {crossfadeSec}s
                </button>
              )}

              {isMixing && (
                <span className="text-[10px] font-medium text-[#d4a853]">
                  mixing
                </span>
              )}

              <div className="hidden sm:flex items-center gap-2">
                <button
                  onClick={() => setVolume(volume === 0 ? 0.8 : 0)}
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  {volume === 0 ? (
                    <VolumeX className="h-4 w-4" />
                  ) : (
                    <Volume2 className="h-4 w-4" />
                  )}
                </button>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.01}
                  value={volume}
                  onChange={handleVolumeChange}
                  className="w-20 accent-[#d4a853]"
                />
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
