'use client';

/* ──────────────────────────────────────────────
   WaveMash — 장르(바이브)별 플레이리스트 리스트
   ────────────────────────────────────────────── */

import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Music, ChevronRight } from 'lucide-react';
import type { Playlist } from '@/lib/types';
import {
  VIBE_CATEGORIES,
  VIBE_ORDER,
  resolvePlaylistColor,
  isDarkColor,
  getVibeCategory,
  type VibeId,
} from '@/lib/vibePalette';

interface PlaylistListByGenreProps {
  playlists: Playlist[];
  onPlaylistClick?: (playlist: Playlist) => void;
  onAssignVibe?: (playlist: Playlist, vibe: VibeId, shade: number) => void;
}

export default function PlaylistListByGenre({
  playlists,
  onPlaylistClick,
  onAssignVibe,
}: PlaylistListByGenreProps) {
  const groups = useMemo(() => {
    const map = new Map<string, Playlist[]>();
    for (const id of VIBE_ORDER) map.set(id, []);
    for (const p of playlists) {
      const vibe = p.vibe && map.has(p.vibe) ? p.vibe : 'other';
      map.get(vibe)!.push(p);
    }
    for (const list of map.values()) {
      list.sort((a, b) => (a.shade ?? 0) - (b.shade ?? 0) || a.name.localeCompare(b.name));
    }
    return VIBE_ORDER.map((id) => ({
      category: getVibeCategory(id),
      items: map.get(id) ?? [],
    })).filter((g) => g.items.length > 0);
  }, [playlists]);

  if (!playlists.length) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-white/30">
        플레이리스트가 없습니다
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto pr-1 space-y-6">
      {groups.map(({ category, items }) => (
        <section key={category.id}>
          <div className="flex items-center gap-2 mb-2 sticky top-0 z-[1] py-1 bg-[#0a0a14]/90 backdrop-blur-sm">
            <span
              className="w-2.5 h-2.5 rounded-sm shrink-0"
              style={{ background: category.shades[0].hex }}
            />
            <h2 className="text-xs font-semibold tracking-wide text-white/70">
              {category.label}
            </h2>
            <span className="text-[10px] text-white/25">{items.length}</span>
            <span className="text-[10px] text-white/20 ml-1 hidden sm:inline">
              {category.description}
            </span>
          </div>

          <div className="space-y-1">
            {items.map((playlist, i) => {
              const color = resolvePlaylistColor({
                color: playlist.color,
                vibe: playlist.vibe,
                shade: playlist.shade,
              });
              const dark = isDarkColor(color);
              const shadeMeta = category.shades.find((s) => s.shade === playlist.shade)
                ?? category.shades[0];

              return (
                <motion.button
                  key={playlist.name}
                  type="button"
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.02 }}
                  className="w-full flex items-center gap-3 rounded-lg px-2.5 py-2 text-left hover:bg-white/[0.04] transition-colors group outline-none"
                  onClick={() => onPlaylistClick?.(playlist)}
                >
                  <div
                    className="w-10 h-10 rounded-md shrink-0 flex items-center justify-center"
                    style={{
                      background: color,
                      boxShadow: `0 2px 10px ${color}44`,
                    }}
                  >
                    <Music
                      className="w-4 h-4"
                      style={{ color: dark ? 'rgba(255,255,255,0.85)' : 'rgba(0,0,0,0.65)' }}
                    />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-white/90 truncate">
                      {playlist.name}
                    </div>
                    <div className="text-[11px] text-white/35 truncate">
                      {shadeMeta.label} · {playlist.track_count ?? playlist.track_ids?.length ?? 0}곡
                    </div>
                  </div>

                  {onAssignVibe && (
                    <select
                      className="opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity text-[10px] bg-white/5 border border-white/10 rounded px-1.5 py-1 text-white/60 outline-none max-w-[120px]"
                      value={`${playlist.vibe}:${playlist.shade ?? 0}`}
                      onClick={(e) => e.stopPropagation()}
                      onChange={(e) => {
                        e.stopPropagation();
                        const [vibe, shadeStr] = e.target.value.split(':');
                        onAssignVibe(playlist, vibe as VibeId, Number(shadeStr));
                      }}
                    >
                      {VIBE_CATEGORIES.flatMap((cat) =>
                        cat.shades.map((s) => (
                          <option key={`${cat.id}:${s.shade}`} value={`${cat.id}:${s.shade}`}>
                            {cat.label} · {s.label}
                          </option>
                        ))
                      )}
                    </select>
                  )}

                  <ChevronRight className="w-3.5 h-3.5 text-white/20 group-hover:text-white/40 shrink-0" />
                </motion.button>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
