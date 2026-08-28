'use client';

/* 이번 달 디깅 커버 9장 → 정사각 공유 카드 */

import { useMemo, useRef, useState } from 'react';
import { Download, Share2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { Track } from '@/lib/types';
import api from '@/lib/api';

interface DigShareCardProps {
  tracks: Track[];
  onClose: () => void;
}

export default function DigShareCard({ tracks, onClose }: DigShareCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [busy, setBusy] = useState(false);

  const nine = useMemo(() => {
    return tracks.filter((t) => t.has_cover || t.thumbnail_url).slice(0, 9);
  }, [tracks]);

  const monthLabel = useMemo(() => {
    const d = new Date();
    return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')} DIG`;
  }, []);

  const exportPng = async () => {
    if (!cardRef.current || nine.length === 0) return;
    setBusy(true);
    try {
      const html2canvas = (await import('html2canvas')).default;
      const canvas = await html2canvas(cardRef.current, {
        scale: 2,
        useCORS: true,
        backgroundColor: '#12100e',
      });
      const link = document.createElement('a');
      link.download = `wavemash-dig-${monthLabel.replace(/\s+/g, '-').toLowerCase()}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-md space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-medium flex items-center gap-2">
            <Share2 className="h-4 w-4 text-[#d4a853]" />
            Dig Share Card
          </h2>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div
          ref={cardRef}
          className="aspect-square w-full p-5 flex flex-col"
          style={{
            background:
              'radial-gradient(ellipse at 30% 20%, #2a2218 0%, #12100e 55%, #0a0908 100%)',
          }}
        >
          <div className="flex items-end justify-between mb-4">
            <div>
              <p className="text-[10px] tracking-[0.35em] text-[#c4a574]/80">WAVEMASH</p>
              <p className="text-lg font-semibold text-[#f0e6d2] mt-1">{monthLabel}</p>
            </div>
            <p className="text-[10px] text-[#c4a574]/60">{nine.length} covers</p>
          </div>
          <div className="grid grid-cols-3 gap-2 flex-1">
            {Array.from({ length: 9 }).map((_, i) => {
              const t = nine[i];
              return (
                <div
                  key={t?.track_id || i}
                  className="aspect-square overflow-hidden rounded-sm bg-black/40"
                >
                  {t ? (
                    <img
                      src={api.getCoverUrl(t.track_id, 320)}
                      alt=""
                      className="h-full w-full object-cover"
                      crossOrigin="anonymous"
                    />
                  ) : (
                    <div className="h-full w-full bg-white/5" />
                  )}
                </div>
              );
            })}
          </div>
          <p className="mt-4 text-[10px] text-center tracking-widest text-[#c4a574]/50">
            COLLECT · SHOWCASE
          </p>
        </div>

        <Button
          className="w-full gap-2 bg-primary text-primary-foreground"
          disabled={busy || nine.length === 0}
          onClick={exportPng}
        >
          <Download className="h-4 w-4" />
          {busy ? '렌더링 중...' : '정사각 PNG 저장'}
        </Button>
      </div>
    </div>
  );
}
