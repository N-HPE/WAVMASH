'use client';

/* ──────────────────────────────────────────────
   WaveMash — Track Card (Album + LP Vinyl + Instant Play + WM Heart Like)
   앨범 커버 클릭 시 YouTube/Audio 즉시 자동 재생 & WM 내부 좋아요 실시간 전파
   ────────────────────────────────────────────── */

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Music, Play, Pause, Heart, Disc3 } from 'lucide-react';

import api from '@/lib/api';
import { useCoverGlow } from '@/lib/coverColors';
import { usePlayer } from '@/contexts/PlayerContext';
import { useAuth } from '@/contexts/AuthContext';
import type { Track } from '@/lib/types';

interface TrackCardProps {
  track: Track;
  index?: number;
}

export default function TrackCard({ track, index = 0 }: TrackCardProps) {
  const { user } = useAuth();
  const { currentTrack, isPlaying: globalPlaying, play, togglePlay: globalTogglePlay } = usePlayer();
  const isCurrentTrackPlaying = globalPlaying && currentTrack?.track_id === track.track_id;

  const [isLiked, setIsLiked] = useState(false);
  const [likesCount, setLikesCount] = useState(0);
  const [imgError, setImgError] = useState(false);

  const glowColor = useCoverGlow(
    track.track_id,
    track.has_cover,
    track.dominant_color
  );

  const coverUrl = api.getCoverUrl(track.track_id, 320);

  // 트랙 좋아요 상태 로드
  useEffect(() => {
    let isMounted = true;
    api
      .getTrackSocialStatus(track.track_id)
      .then((status) => {
        if (isMounted) {
          setIsLiked(status.liked);
          setLikesCount(status.likes_count);
        }
      })
      .catch(() => {});
    return () => {
      isMounted = false;
    };
  }, [track.track_id, user]);

  const handlePlayClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (currentTrack?.track_id === track.track_id) {
      globalTogglePlay();
    } else {
      play(track);
    }
  };

  const handleLikeClick = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    // Optimistic UI
    const prevLiked = isLiked;
    const prevCount = likesCount;
    setIsLiked(!prevLiked);
    setLikesCount(prevLiked ? Math.max(prevCount - 1, 0) : prevCount + 1);

    try {
      const res = await api.toggleTrackLike(track.track_id, {
        title: track.title,
        artist: track.artist,
        cover_url: coverUrl,
      });
      setIsLiked(res.liked);
      setLikesCount(res.likes_count);
    } catch (err) {
      setIsLiked(prevLiked);
      setLikesCount(prevCount);
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

            {/* Top Right Heart Like Button */}
            <button
              onClick={handleLikeClick}
              className={`absolute top-2 right-2 z-30 p-1.5 rounded-full backdrop-blur-md transition-all active:scale-75 ${
                isLiked
                  ? 'bg-red-500/80 text-white shadow-lg shadow-red-500/30'
                  : 'bg-black/50 text-white/70 hover:text-white hover:bg-black/70'
              }`}
              title={isLiked ? '좋아요 취소' : 'WM에서 좋아요 (친구와 공유)'}
            >
              <Heart className={`w-3.5 h-3.5 ${isLiked ? 'fill-current' : ''}`} />
            </button>

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

          {/* ── Track Info & Metrics ── */}
          <div className="p-3 flex items-center justify-between gap-2">
            <Link href={`/track/${track.track_id}`} className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-foreground group-hover:text-[#d4a853] transition-colors">
                {track.title}
              </p>
              <p className="truncate text-xs text-muted-foreground">
                {track.artist}
              </p>
            </Link>

            <div className="flex items-center gap-2 shrink-0 text-[10px] font-mono">
              {likesCount > 0 && (
                <span className="text-red-400 flex items-center gap-0.5" title={`좋아요 ${likesCount}개`}>
                  <Heart className="w-2.5 h-2.5 fill-current" />
                  {likesCount}
                </span>
              )}
              {((track as any).collector_count > 0 || likesCount === 0) && (
                <span className="text-[#d4a853]/80 flex items-center gap-0.5" title="소장 횟수">
                  <Disc3 className="w-2.5 h-2.5" />
                  {(track as any).collector_count || 1}
                </span>
              )}
            </div>
          </div>

        </div>
      </div>
    </motion.div>
  );
}
