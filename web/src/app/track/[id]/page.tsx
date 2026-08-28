'use client';

/* ──────────────────────────────────────────────
   WaveMash — 트랙 상세 (Track Detail)
   ────────────────────────────────────────────── */

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
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
    <div className="rounded-md border border-border bg-secondary/30 p-3 flex items-center gap-3">
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

        void requestCoverColor(trackId, trackData.dominant_color);
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
      <div className="py-4 space-y-4">
        <Skeleton className="h-8 w-32 skeleton-shimmer" />
        <Skeleton className="h-64 rounded-lg skeleton-shimmer" />
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
    <div className="py-4 space-y-4">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => router.back()}
        className="text-muted-foreground hover:text-foreground -ml-2"
      >
        <ArrowLeft className="h-4 w-4 mr-2" />
        돌아가기
      </Button>

      <div className="feed-card p-4 sm:p-6">
        <div className="flex gap-4 sm:gap-6">
          <div className="shrink-0">
            {track.has_cover && !imgError ? (
              <img
                src={coverUrl}
                alt={track.title}
                className="h-32 w-32 sm:h-40 sm:w-40 rounded-lg object-cover"
                onError={() => setImgError(true)}
              />
            ) : (
              <div className="flex h-32 w-32 sm:h-40 sm:w-40 items-center justify-center rounded-lg bg-secondary">
                <Music className="h-12 w-12 text-white/10" />
              </div>
            )}
          </div>

          <div className="flex-1 min-w-0">
            <h1 className="text-xl sm:text-2xl font-bold mb-1 break-words">
              {track.title}
            </h1>
            <p className="text-muted-foreground mb-4">{track.artist}</p>

            <Button
              size="sm"
              className="bg-primary text-primary-foreground hover:bg-primary/90 gap-2"
              onClick={() => play(track)}
            >
              <Play className="h-4 w-4" />
              재생
            </Button>
          </div>
        </div>

        <div className="mt-6 pt-4 border-t border-border grid grid-cols-2 gap-2">
          <MetaCard
            icon={<Gauge className="h-4 w-4" />}
            label="BPM"
            value={track.bpm > 0 ? String(Math.round(track.bpm)) : ''}
          />
          <MetaCard
            icon={<Music className="h-4 w-4" />}
            label="키"
            value={track.key}
          />
          <MetaCard
            icon={<Disc3 className="h-4 w-4" />}
            label="카멜롯"
            value={track.camelot_key}
          />
          <MetaCard
            icon={<Tag className="h-4 w-4" />}
            label="장르"
            value={track.genre}
          />
          <MetaCard
            icon={<Calendar className="h-4 w-4" />}
            label="연도"
            value={track.year}
          />
          <MetaCard
            icon={<Clock className="h-4 w-4" />}
            label="플랫폼"
            value={track.platform}
          />
        </div>

        {track.album && (
          <div className="mt-4 pt-4 border-t border-border">
            <p className="text-xs text-muted-foreground mb-1">앨범</p>
            <p className="text-sm font-medium">{track.album}</p>
          </div>
        )}
      </div>
    </div>
  );
}
