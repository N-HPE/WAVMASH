'use client';

/* ──────────────────────────────────────────────
   WaveMash — 트랙 상세 (Track Detail)
   ────────────────────────────────────────────── */

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  Play,
  Music,
  Disc3,
  Clock,
  Tag,
  Calendar,
  Gauge,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import api from '@/lib/api';
import type { Track } from '@/lib/types';
import { usePlayer } from '@/contexts/PlayerContext';
import { requestCoverColor } from '@/lib/coverColors';

interface MetaCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
}

function MetaCard({ icon, label, value }: MetaCardProps) {
  if (!value || value === '0' || value === 'Unknown') return null;
  return (
    <div className="glass rounded-xl p-4 flex items-center gap-3">
      <div className="text-[#d4a853]/40">{icon}</div>
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-sm font-medium">{value}</p>
      </div>
    </div>
  );
}

export default function TrackDetailPage() {
  const params = useParams();
  const router = useRouter();
  const trackId = params.id as string;
  const { play } = usePlayer();

  const [track, setTrack] = useState<Track | null>(null);
  const [glowColor, setGlowColor] = useState('#d4a85326');
  const [loading, setLoading] = useState(true);
  const [imgError, setImgError] = useState(false);

  useEffect(() => {
    if (!trackId) return;

    let cancelled = false;

    (async () => {
      try {
        const trackData = await api.getTrack(trackId);
        if (cancelled) return;
        setTrack(trackData);

        const color =
          trackData.dominant_color ||
          (await requestCoverColor(trackId, trackData.dominant_color)) ||
          '#d4a853';
        if (!cancelled) setGlowColor(color);
      } catch {
        // ignore
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [trackId]);

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-4 sm:px-6 py-8 space-y-6">
        <Skeleton className="h-8 w-32 skeleton-shimmer" />
        <div className="flex flex-col sm:flex-row gap-8">
          <Skeleton className="h-[300px] w-[300px] rounded-2xl skeleton-shimmer flex-shrink-0" />
          <div className="flex-1 space-y-4">
            <Skeleton className="h-10 w-3/4 skeleton-shimmer" />
            <Skeleton className="h-6 w-1/2 skeleton-shimmer" />
            <div className="grid grid-cols-2 gap-3">
              {[...Array(6)].map((_, i) => (
                <Skeleton key={i} className="h-16 rounded-xl skeleton-shimmer" />
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!track) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="glass rounded-xl p-8 text-center">
          <p className="text-muted-foreground">트랙을 찾을 수 없습니다.</p>
          <Button variant="ghost" className="mt-4" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            돌아가기
          </Button>
        </div>
      </div>
    );
  }

  const coverUrl = api.getCoverUrl(track.track_id);

  return (
    <div className="mx-auto max-w-4xl px-4 sm:px-6 py-8">
      {/* ── Back Button ── */}
      <motion.div
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
      >
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.back()}
          className="mb-6 text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          돌아가기
        </Button>
      </motion.div>

      {/* ── Hero ── */}
      <div className="flex flex-col sm:flex-row gap-8">
        {/* Cover */}
        <motion.div
          className="flex-shrink-0 self-center sm:self-start"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          <div
            className="cover-glow relative"
            style={{ '--glow-color': glowColor + '40' } as React.CSSProperties}
          >
            {track.has_cover && !imgError ? (
              <img
                src={coverUrl}
                alt={track.title}
                className="h-[300px] w-[300px] rounded-2xl object-cover shadow-2xl"
                onError={() => setImgError(true)}
              />
            ) : (
              <div className="flex h-[300px] w-[300px] items-center justify-center rounded-2xl bg-gradient-to-br from-[#1a1a2e] to-[#0a0a14] shadow-2xl">
                <Music className="h-20 w-20 text-white/10" />
              </div>
            )}
          </div>
        </motion.div>

        {/* Info */}
        <motion.div
          className="flex-1 min-w-0"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <h1 className="text-3xl font-light mb-1 break-words">
            {track.title}
          </h1>
          <p className="text-lg text-muted-foreground mb-6">{track.artist}</p>

          {/* Play button */}
          <Button
            size="lg"
            className="bg-primary text-primary-foreground hover:bg-primary/90 mb-8 gap-2"
            onClick={() => play(track)}
          >
            <Play className="h-5 w-5" />
            재생
          </Button>

          {/* Metadata grid */}
          <div className="grid grid-cols-2 gap-3">
            <MetaCard
              icon={<Gauge className="h-5 w-5" />}
              label="BPM"
              value={track.bpm > 0 ? String(Math.round(track.bpm)) : ''}
            />
            <MetaCard
              icon={<Music className="h-5 w-5" />}
              label="키"
              value={track.key}
            />
            <MetaCard
              icon={<Disc3 className="h-5 w-5" />}
              label="카멜롯"
              value={track.camelot_key}
            />
            <MetaCard
              icon={<Tag className="h-5 w-5" />}
              label="장르"
              value={track.genre}
            />
            <MetaCard
              icon={<Calendar className="h-5 w-5" />}
              label="연도"
              value={track.year}
            />
            <MetaCard
              icon={<Clock className="h-5 w-5" />}
              label="플랫폼"
              value={track.platform}
            />
          </div>

          {/* Album info */}
          {track.album && (
            <motion.div
              className="mt-6 glass rounded-xl p-4"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
            >
              <p className="text-xs text-muted-foreground mb-1">앨범</p>
              <p className="text-sm font-medium">{track.album}</p>
            </motion.div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
