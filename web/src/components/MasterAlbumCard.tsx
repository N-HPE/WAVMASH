'use client';

import { useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  Disc3,
  Play,
  Trash2,
  Zap,
  Sparkles,
  Moon,
  Crown,
  ExternalLink,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { MasterAlbum } from '@/lib/types';

interface MasterAlbumCardProps {
  album: MasterAlbum;
  onDelete?: (id: string) => void;
  onPlay?: (album: MasterAlbum) => void;
}

const ARTISAN_CONFIG = {
  nova: {
    label: 'Nova',
    title: "Nova's Pick",
    icon: Zap,
    color: 'text-violet-400 border-violet-500/30 bg-violet-500/10',
    dot: 'bg-violet-400',
  },
  echo: {
    label: 'Echo',
    title: "Echo's Pick",
    icon: Sparkles,
    color: 'text-rose-400 border-rose-500/30 bg-rose-500/10',
    dot: 'bg-rose-400',
  },
  yachi: {
    label: 'Yachi',
    title: "Yachi's Pick",
    icon: Moon,
    color: 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10',
    dot: 'bg-cyan-400',
  },
  personal: {
    label: '내 명반',
    title: 'Personal Classic',
    icon: Crown,
    color: 'text-[#d4a853] border-[#d4a853]/30 bg-[#d4a853]/10',
    dot: 'bg-[#d4a853]',
  },
} as const;

export default function MasterAlbumCard({
  album,
  onDelete,
  onPlay,
}: MasterAlbumCardProps) {
  const [isHovered, setIsHovered] = useState(false);
  const artisanMeta =
    ARTISAN_CONFIG[album.artisan] || ARTISAN_CONFIG.personal;
  const Icon = artisanMeta.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="group relative flex flex-col rounded-2xl border border-white/8 bg-[#14141e]/90 hover:border-[#d4a853]/30 p-4 transition-all duration-300 hover:shadow-2xl hover:shadow-[#d4a853]/5"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* ── LP Vinyl Sleeve Container ── */}
      <div className="relative aspect-square w-full rounded-xl overflow-hidden bg-black/60 shadow-lg border border-white/5 mb-3.5">
        {/* Vinyl Disc sliding out on hover */}
        <motion.div
          animate={{ x: isHovered ? '28%' : '0%' }}
          transition={{ type: 'spring', stiffness: 220, damping: 22 }}
          className="absolute inset-y-1 right-1 w-full rounded-full bg-gradient-to-tr from-zinc-950 via-zinc-800 to-zinc-950 border border-zinc-700/60 shadow-2xl flex items-center justify-center pointer-events-none z-0"
        >
          {/* Vinyl Grooves */}
          <div className="w-[82%] h-[82%] rounded-full border border-white/5 flex items-center justify-center">
            <div className="w-[66%] h-[66%] rounded-full border border-white/10 flex items-center justify-center">
              <div className="w-[45%] h-[45%] rounded-full bg-[#181822] border border-[#d4a853]/40 flex items-center justify-center shadow-inner">
                <div className="w-2.5 h-2.5 rounded-full bg-black border border-zinc-500" />
              </div>
            </div>
          </div>
        </motion.div>

        {/* Front Album Jacket Cover */}
        <div className="relative z-10 w-full h-full rounded-xl overflow-hidden shadow-md bg-zinc-900">
          {album.cover_url ? (
            <img
              src={album.cover_url}
              alt={album.title}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-zinc-600">
              <Disc3 className="h-12 w-12" />
            </div>
          )}

          {/* Action Overlay */}
          <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-3">
            <Link href={`/album/${encodeURIComponent(album.id)}`}>
              <button
                type="button"
                className="h-11 w-11 rounded-full bg-[#d4a853] flex items-center justify-center text-black shadow-lg transform transition-transform hover:scale-110 cursor-pointer"
                title="앨범 트랙 보기"
              >
                <Play className="h-5 w-5 fill-black ml-0.5" />
              </button>
            </Link>
          </div>
        </div>
      </div>

      {/* ── Metadata & Artisan Badge ── */}
      <div className="flex-1 flex flex-col justify-between space-y-2">
        <div>
          {/* Artisan Pill */}
          <div className="flex items-center justify-between gap-1 mb-1.5">
            <span
              className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[11px] font-semibold ${artisanMeta.color}`}
            >
              <Icon className="h-3 w-3" />
              {artisanMeta.title}
            </span>

            {album.genre && (
              <span className="text-[10px] text-zinc-500 truncate max-w-[100px]">
                {album.genre}
              </span>
            )}
          </div>

          {/* Title & Artist */}
          <Link
            href={`/album/${encodeURIComponent(album.id)}`}
            className="block group/link"
          >
            <h3 className="font-bold text-sm text-white truncate group-hover/link:text-[#d4a853] transition-colors">
              {album.title}
            </h3>
          </Link>
          <p className="text-xs text-zinc-400 truncate mt-0.5">
            {album.artist}
            {album.year ? ` · ${album.year}` : ''}
            {album.total_tracks ? ` · ${album.total_tracks}곡` : ''}
          </p>

          {/* Curator Note / Liner Note */}
          {album.curator_note && (
            <p className="text-[11px] text-zinc-300/90 italic line-clamp-2 mt-2 pl-2 border-l-2 border-[#d4a853]/40 leading-relaxed">
              &ldquo;{album.curator_note}&rdquo;
            </p>
          )}
        </div>

        {/* Footer Actions */}
        <div className="pt-2 flex items-center justify-between border-t border-white/5 text-xs text-muted-foreground">
          <Link
            href={`/album/${encodeURIComponent(album.id)}`}
            className="inline-flex items-center gap-1 text-[#d4a853] hover:underline text-[11px]"
          >
            트랙 보기 <ExternalLink className="h-3 w-3" />
          </Link>

          {onDelete && (
            <button
              type="button"
              onClick={() => onDelete(album.id)}
              className="text-zinc-500 hover:text-red-400 p-1 rounded transition-colors cursor-pointer"
              title="명반 삭제"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>
    </motion.div>
  );
}
