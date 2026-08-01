'use client';

/* ──────────────────────────────────────────────
   WaveMash — Playlist Block Grid
   각 플레이리스트의 바이브(장르) 색으로 블록 표시
   ────────────────────────────────────────────── */

import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Music } from 'lucide-react';
import type { Playlist } from '@/lib/types';
import {
  resolvePlaylistColor,
  isDarkColor,
  getVibeCategory,
} from '@/lib/vibePalette';

const COLS = 5;
const EMPTY_SLOTS = 30;

interface PlaylistGridProps {
  playlists: Playlist[];
  onPlaylistClick?: (playlist: Playlist) => void;
}

export default function PlaylistGrid({ playlists, onPlaylistClick }: PlaylistGridProps) {
  const [hovered, setHovered] = useState<number | null>(null);

  const slots = useMemo(() => {
    const filled = playlists.map((p) => {
      const color = resolvePlaylistColor({
        color: p.color,
        vibe: p.vibe,
        shade: p.shade,
      });
      return {
        playlist: p,
        color,
        dark: isDarkColor(color),
      };
    });
    const emptyCount = Math.max(0, EMPTY_SLOTS - filled.length);
    return [
      ...filled.map((f, i) => ({ index: i, ...f })),
      ...Array.from({ length: emptyCount }, (_, i) => ({
        index: filled.length + i,
        playlist: null as Playlist | null,
        color: '#16161f',
        dark: true,
      })),
    ];
  }, [playlists]);

  return (
    <div
      className="grid"
      style={{
        gridTemplateColumns: `repeat(${COLS}, 1fr)`,
        gridTemplateRows: `repeat(${Math.ceil(slots.length / COLS)}, 1fr)`,
        gap: '10px',
        height: '100%',
      }}
    >
      {slots.map(({ index, color, dark, playlist }) => {
        const filled = !!playlist;
        const active = hovered === index && filled;
        const txt = dark ? 'rgba(255,255,255,' : 'rgba(0,0,0,';
        const vibeLabel = playlist ? getVibeCategory(playlist.vibe).label : '';

        return (
          <motion.button
            key={playlist?.name ?? `empty-${index}`}
            type="button"
            layout
            initial={{ opacity: 0 }}
            animate={{
              opacity: 1,
              scale: active ? 1.06 : 1,
            }}
            transition={{
              opacity: { duration: 0.2 },
              scale: { type: 'spring', stiffness: 500, damping: 28 },
              layout: { type: 'spring', stiffness: 400, damping: 30 },
            }}
            className={`relative overflow-hidden outline-none select-none ${
              filled ? 'cursor-pointer' : 'cursor-default'
            }`}
            style={{
              background: color,
              boxShadow: active
                ? `0 14px 44px ${color}77, 0 0 0 2px ${color}bb`
                : filled
                  ? `0 2px 8px ${color}33`
                  : 'inset 0 0 0 1px rgba(255,255,255,0.04)',
              zIndex: active ? 10 : 1,
              transition: 'box-shadow 0.2s ease',
            }}
            onMouseEnter={() => filled && setHovered(index)}
            onMouseLeave={() => setHovered(null)}
            onClick={() => playlist && onPlaylistClick?.(playlist)}
            disabled={!filled}
          >
            {filled && (
              <div className="flex flex-col items-center justify-center h-full gap-[3px] px-2 pointer-events-none">
                <div
                  className="w-5 h-5 rounded-full flex items-center justify-center shrink-0"
                  style={{ background: dark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.08)' }}
                >
                  <Music className="w-[10px] h-[10px]" style={{ color: `${txt}${dark ? 0.8 : 0.5})` }} />
                </div>
                <span
                  className="text-[10px] font-bold leading-[1.15] line-clamp-2 text-center tracking-tight"
                  style={{
                    color: `${txt}${dark ? 0.92 : 0.72})`,
                    textShadow: dark ? '0 1px 4px rgba(0,0,0,0.35)' : 'none',
                  }}
                >
                  {playlist!.name}
                </span>
                <span className="text-[8px] font-semibold" style={{ color: `${txt}${dark ? 0.45 : 0.35})` }}>
                  {vibeLabel} · {playlist!.track_count ?? playlist!.track_ids?.length ?? 0}곡
                </span>
              </div>
            )}
          </motion.button>
        );
      })}
    </div>
  );
}
