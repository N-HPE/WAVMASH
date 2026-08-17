'use client';

/* ──────────────────────────────────────────────
   WaveMash — Shareable Vinyl Story Card Modal
   인스타 스토리(9:16) 규격의 바이럴 오디오 티켓 카드 생성기
   ────────────────────────────────────────────── */

import React, { useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Download, Copy, Check, Sparkles, Disc3 } from 'lucide-react';
import type { Track, UserProfile } from '@/lib/types';
import api from '@/lib/api';

interface ShareVinylCardModalProps {
  isOpen: boolean;
  onClose: () => void;
  track: Track;
  user?: UserProfile | null;
  caption?: string;
}

export default function ShareVinylCardModal({
  isOpen,
  onClose,
  track,
  user,
  caption,
}: ShareVinylCardModalProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  if (!isOpen) return null;

  const coverUrl = api.getCoverUrl(track.track_id, 600);
  const collectorName = user?.display_name || user?.username || 'WAVMASH DIGGER';

  const handleDownload = async () => {
    setIsExporting(true);
    try {
      // Dynamic import to prevent SSR issues
      const html2canvas = (await import('html2canvas')).default;
      if (cardRef.current) {
        const canvas = await html2canvas(cardRef.current, {
          scale: 2,
          useCORS: true,
          backgroundColor: '#0a0a14',
        });
        const link = document.createElement('a');
        link.download = `wavemash-${track.title.toLowerCase().replace(/\s+/g, '-')}-story.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
      }
    } catch (err) {
      console.error('Failed to generate image:', err);
    } finally {
      setIsExporting(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(
      `🎧 "${track.title}" by ${track.artist}\nCollected on WAVMASH • ${track.bpm ? `${Math.round(track.bpm)} BPM` : ''} ${track.key || ''}\n${window.location.origin}/track/${track.track_id}`
    );
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative max-w-sm w-full bg-[#0e0e1a] border border-white/10 rounded-2xl overflow-hidden shadow-2xl p-6 flex flex-col items-center"
        >
          {/* Close Button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-muted-foreground hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-2 mb-4 text-xs font-semibold uppercase tracking-wider text-[#d4a853]">
            <Sparkles className="w-4 h-4" />
            Instagram Story Card
          </div>

          {/* ── 9:16 Instagram Story Preview Card ── */}
          <div
            ref={cardRef}
            className="w-[280px] h-[480px] rounded-2xl p-5 flex flex-col justify-between relative overflow-hidden bg-gradient-to-b from-[#181829] via-[#0d0d18] to-[#08080f] border border-white/15 shadow-2xl"
          >
            {/* Background Ambient Glow */}
            <div
              className="absolute -top-20 -left-20 w-48 h-48 rounded-full blur-3xl opacity-30 pointer-events-none"
              style={{ backgroundColor: track.dominant_color || '#d4a853' }}
            />
            <div
              className="absolute -bottom-20 -right-20 w-48 h-48 rounded-full blur-3xl opacity-20 pointer-events-none"
              style={{ backgroundColor: '#60a5fa' }}
            />

            {/* Top Branding */}
            <div className="relative z-10 flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Disc3 className="w-4 h-4 text-[#d4a853] animate-spin" style={{ animationDuration: '6s' }} />
                <span className="text-[11px] font-black tracking-widest text-white/90 uppercase">WAVMASH</span>
              </div>
              <span className="text-[9px] px-2 py-0.5 rounded-full bg-white/10 text-white/80 border border-white/10 font-mono">
                {track.format || 'LOSSLESS WAV'}
              </span>
            </div>

            {/* Center: Vinyl & Cover Visual */}
            <div className="relative z-10 my-auto flex flex-col items-center">
              <div className="relative w-44 h-44 group">
                {/* Vinyl Disc Sticking Out */}
                <div className="absolute -right-6 top-1/2 -translate-y-1/2 w-40 h-40 rounded-full bg-black border-2 border-white/10 shadow-xl flex items-center justify-center">
                  <div className="w-16 h-16 rounded-full border border-white/10 flex items-center justify-center bg-[#d4a853]/20">
                    <div className="w-5 h-5 rounded-full bg-black" />
                  </div>
                </div>

                {/* Album Cover */}
                <div className="relative z-10 w-44 h-44 rounded-xl overflow-hidden shadow-2xl border border-white/20 bg-[#121220]">
                  {track.has_cover ? (
                    <img
                      src={coverUrl}
                      alt={track.title}
                      className="w-full h-full object-cover"
                      crossOrigin="anonymous"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center bg-white/5">
                      <Disc3 className="w-12 h-12 text-white/20" />
                    </div>
                  )}
                </div>
              </div>

              {/* Track Title & Artist */}
              <div className="mt-4 text-center w-full px-2">
                <h4 className="font-bold text-base text-white truncate leading-tight">{track.title}</h4>
                <p className="text-xs text-white/70 truncate mt-0.5">{track.artist}</p>
              </div>

              {/* Audio Meta Tags */}
              <div className="flex items-center justify-center gap-1.5 mt-2.5">
                {track.bpm > 0 && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#d4a853]/20 text-[#d4a853] border border-[#d4a853]/30 font-semibold">
                    {Math.round(track.bpm)} BPM
                  </span>
                )}
                {track.key && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/10 text-white/90 border border-white/10">
                    {track.key}
                  </span>
                )}
                {track.genre && (
                  <span className="text-[10px] px-2 py-0.5 rounded bg-white/10 text-white/80 border border-white/10 truncate max-w-[90px]">
                    {track.genre}
                  </span>
                )}
              </div>

              {caption && (
                <p className="mt-3 text-[11px] text-white/80 italic text-center line-clamp-2 px-3 bg-white/5 py-1.5 rounded-lg border border-white/5">
                  &ldquo;{caption}&rdquo;
                </p>
              )}
            </div>

            {/* Bottom: Digger Verification */}
            <div className="relative z-10 pt-2 border-t border-white/10 flex items-center justify-between text-[10px] text-white/60">
              <div>
                <span className="text-white/40 block text-[8px] uppercase">COLLECTED BY</span>
                <span className="font-semibold text-white/90">@{collectorName}</span>
              </div>
              <div className="text-right">
                <span className="text-white/40 block text-[8px] uppercase">ARCHIVE ID</span>
                <span className="font-mono text-[#d4a853]">#{track.track_id.slice(0, 6)}</span>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-3 mt-6 w-full">
            <button
              onClick={handleDownload}
              disabled={isExporting}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-[#d4a853] text-black font-semibold text-sm hover:bg-[#e0b764] transition-all active:scale-95 disabled:opacity-50 shadow-lg shadow-[#d4a853]/20"
            >
              <Download className="w-4 h-4" />
              {isExporting ? '생성 중...' : '이미지 저장'}
            </button>
            <button
              onClick={handleCopy}
              className="flex items-center justify-center p-2.5 rounded-xl bg-white/10 hover:bg-white/15 text-white transition-all active:scale-95 border border-white/10"
              title="링크 복사"
            >
              {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
