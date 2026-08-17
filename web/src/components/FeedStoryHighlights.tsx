'use client';

/* ──────────────────────────────────────────────
   WaveMash — Feed Story Highlights Bar
   인스타그램 감성의 상단 원형 스토리 큐레이션 서클 바
   ────────────────────────────────────────────── */

import React from 'react';
import { motion } from 'framer-motion';
import { Plus, Flame, Disc, Sparkles, Moon, Radio } from 'lucide-react';
import type { HighlightItem } from '@/lib/types';

interface FeedStoryHighlightsProps {
  highlights?: HighlightItem[];
  onSelectHighlight?: (highlight: HighlightItem) => void;
  onOpenCreate?: () => void;
  selectedId?: string | null;
}

const DEFAULT_STORIES = [
  { id: 'trending', title: '🔥 이달의 디깅', icon: Flame, color: 'from-amber-500 to-red-500' },
  { id: 'vinyl_grail', title: '💽 바이닐 명반', icon: Disc, color: 'from-[#d4a853] to-amber-600' },
  { id: 'club_bangers', title: '⚡️ 클럽 뱅어', icon: Sparkles, color: 'from-purple-500 to-indigo-600' },
  { id: 'night_drive', title: '🌙 심야 드라이브', icon: Moon, color: 'from-blue-600 to-cyan-500' },
  { id: 'lossless_only', title: '🎧 24bit WAV', icon: Radio, color: 'from-emerald-500 to-teal-600' },
];

export default function FeedStoryHighlights({
  highlights = [],
  onSelectHighlight,
  onOpenCreate,
  selectedId,
}: FeedStoryHighlightsProps) {
  return (
    <div className="w-full overflow-x-auto pb-3 pt-1 scrollbar-none">
      <div className="flex items-center gap-4 px-2 sm:px-0 min-w-max">
        {/* ── 1. Create Story / Add Collection Button ── */}
        <div className="flex flex-col items-center gap-1.5 cursor-pointer group" onClick={onOpenCreate}>
          <div className="relative w-16 h-16 rounded-full p-[2px] border-2 border-dashed border-white/20 group-hover:border-[#d4a853] transition-all flex items-center justify-center bg-white/[0.02]">
            <div className="w-full h-full rounded-full bg-white/5 flex items-center justify-center group-hover:bg-[#d4a853]/10 transition-colors">
              <Plus className="w-6 h-6 text-muted-foreground group-hover:text-[#d4a853] transition-transform group-hover:scale-110" />
            </div>
          </div>
          <span className="text-[11px] font-medium text-muted-foreground group-hover:text-white transition-colors">
            자랑하기
          </span>
        </div>

        {/* ── 2. Preset Curation Highlights ── */}
        {DEFAULT_STORIES.map((story) => {
          const Icon = story.icon;
          const isSelected = selectedId === story.id;
          return (
            <motion.div
              key={story.id}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="flex flex-col items-center gap-1.5 cursor-pointer group"
              onClick={() =>
                onSelectHighlight?.({
                  id: story.id,
                  user_id: 'system',
                  title: story.title,
                  track_ids: [],
                  created_at: new Date().toISOString(),
                })
              }
            >
              <div
                className={`relative w-16 h-16 rounded-full p-[2.5px] bg-gradient-to-tr ${
                  story.color
                } shadow-lg transition-all ${
                  isSelected ? 'ring-2 ring-white ring-offset-2 ring-offset-[#0a0a14]' : 'opacity-90 group-hover:opacity-100'
                }`}
              >
                <div className="w-full h-full rounded-full bg-[#0e0e1a] flex items-center justify-center p-1 border border-black/50">
                  <Icon className="w-6 h-6 text-white group-hover:scale-110 transition-transform" />
                </div>
              </div>
              <span className="text-[11px] font-medium text-white/80 group-hover:text-white transition-colors">
                {story.title}
              </span>
            </motion.div>
          );
        })}

        {/* ── 3. User Custom Highlights ── */}
        {highlights.map((hl) => (
          <motion.div
            key={hl.id}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="flex flex-col items-center gap-1.5 cursor-pointer group"
            onClick={() => onSelectHighlight?.(hl)}
          >
            <div
              className={`relative w-16 h-16 rounded-full p-[2px] bg-gradient-to-tr from-[#d4a853] to-amber-300 ${
                selectedId === hl.id ? 'ring-2 ring-white ring-offset-2 ring-offset-[#0a0a14]' : ''
              }`}
            >
              <div className="w-full h-full rounded-full overflow-hidden bg-black/60 flex items-center justify-center">
                {hl.cover_url ? (
                  <img src={hl.cover_url} alt={hl.title} className="w-full h-full object-cover" />
                ) : (
                  <Disc className="w-6 h-6 text-[#d4a853]" />
                )}
              </div>
            </div>
            <span className="text-[11px] font-medium text-white/80 group-hover:text-white truncate max-w-[68px]">
              {hl.title}
            </span>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
