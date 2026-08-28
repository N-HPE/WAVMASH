'use client';

/* Vinyl crate / harmonic digger views for cover-centric archive */

import Link from 'next/link';
import { motion } from 'framer-motion';
import type { Track } from '@/lib/types';
import api from '@/lib/api';

/** Camelot wheel neighbors (same energy + ±1) + relative major/minor */
const CAMELOT_NEIGHBORS: Record<string, string[]> = (() => {
  const map: Record<string, string[]> = {};
  for (let n = 1; n <= 12; n++) {
    for (const letter of ['A', 'B'] as const) {
      const key = `${n}${letter}`;
      const prev = `${n === 1 ? 12 : n - 1}${letter}`;
      const next = `${n === 12 ? 1 : n + 1}${letter}`;
      const relative = `${n}${letter === 'A' ? 'B' : 'A'}`;
      map[key] = [key, prev, next, relative];
    }
  }
  return map;
})();

export function normalizeCamelot(raw?: string | null): string {
  if (!raw) return '';
  const m = String(raw)
    .trim()
    .toUpperCase()
    .match(/^(\d{1,2})\s*([AB])$/);
  if (!m) return '';
  const n = parseInt(m[1], 10);
  if (n < 1 || n > 12) return '';
  return `${n}${m[2]}`;
}

export function isHarmonicCompatible(a?: string | null, b?: string | null): boolean {
  const ca = normalizeCamelot(a);
  const cb = normalizeCamelot(b);
  if (!ca || !cb) return false;
  return (CAMELOT_NEIGHBORS[ca] || []).includes(cb);
}

export function bpmNear(a?: string | number | null, b?: string | number | null, tol = 6): boolean {
  const na = typeof a === 'number' ? a : parseFloat(String(a || ''));
  const nb = typeof b === 'number' ? b : parseFloat(String(b || ''));
  if (!Number.isFinite(na) || !Number.isFinite(nb) || na <= 0 || nb <= 0) return true;
  return Math.abs(na - nb) <= tol || Math.abs(na * 2 - nb) <= tol || Math.abs(na - nb * 2) <= tol;
}

export function CrateGrid({ tracks }: { tracks: Track[] }) {
  return (
    <div
      className="feed-card p-4"
      style={{
        background:
          'linear-gradient(165deg, rgba(40,28,18,0.9), rgba(18,14,12,0.95)), repeating-linear-gradient(90deg, transparent, transparent 47px, rgba(0,0,0,0.15) 48px)',
      }}
    >
      <p className="text-[11px] uppercase tracking-[0.2em] text-[#c4a574]/70 mb-3">
        Vinyl Crate
      </p>
      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2 sm:gap-3">
        {tracks.map((track, i) => (
          <motion.div
            key={track.track_id}
            initial={{ opacity: 0, y: 12, rotateX: 8 }}
            animate={{ opacity: 1, y: 0, rotateX: 0 }}
            transition={{ delay: Math.min(i * 0.03, 0.4), type: 'spring', stiffness: 260 }}
            style={{ perspective: 600 }}
          >
            <Link
              href={`/track/${track.track_id}`}
              className="group block relative"
              style={{ transformStyle: 'preserve-3d' }}
            >
              <div
                className="aspect-square overflow-hidden rounded-sm shadow-[0_8px_20px_rgba(0,0,0,0.45)] transition-transform duration-300 group-hover:-translate-y-2 group-hover:rotate-[-2deg]"
                style={{
                  boxShadow:
                    'inset 0 0 0 1px rgba(255,255,255,0.08), 0 10px 24px rgba(0,0,0,0.5)',
                }}
              >
                <img
                  src={api.getCoverUrl(track.track_id, 320)}
                  alt={track.title}
                  className="h-full w-full object-cover"
                  loading="lazy"
                />
              </div>
              <div className="mt-1.5 min-w-0">
                <p className="truncate text-[11px] font-medium leading-tight">{track.title}</p>
                <p className="truncate text-[10px] text-muted-foreground">{track.artist}</p>
              </div>
            </Link>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

export function HarmonicCrate({
  tracks,
  anchor,
  onSelectAnchor,
}: {
  tracks: Track[];
  anchor: Track | null;
  onSelectAnchor: (t: Track) => void;
}) {
  const compatible = anchor
    ? tracks.filter(
        (t) =>
          t.track_id !== anchor.track_id &&
          isHarmonicCompatible(anchor.camelot_key || anchor.key, t.camelot_key || t.key) &&
          bpmNear(anchor.bpm, t.bpm)
      )
    : [];

  return (
    <div className="space-y-3">
      <div className="feed-card p-4">
        <p className="text-[11px] uppercase tracking-[0.2em] text-[#c4a574]/70 mb-2">
          Harmonic Crate
        </p>
        <p className="text-xs text-muted-foreground mb-3">
          앨범을 고르면 BPM·Camelot이 맞는 믹싱 후보만 보여줍니다.
        </p>
        <div className="flex gap-2 overflow-x-auto pb-1">
          {tracks.slice(0, 24).map((t) => {
            const selected = anchor?.track_id === t.track_id;
            return (
              <button
                key={t.track_id}
                type="button"
                onClick={() => onSelectAnchor(t)}
                className={`shrink-0 w-16 transition-opacity ${selected ? 'opacity-100' : 'opacity-60 hover:opacity-100'}`}
              >
                <img
                  src={api.getCoverUrl(t.track_id, 160)}
                  alt=""
                  className={`aspect-square w-full object-cover rounded-sm ${selected ? 'ring-2 ring-[#d4a853]' : ''}`}
                />
              </button>
            );
          })}
        </div>
        {anchor && (
          <p className="mt-3 text-sm">
            <span className="text-[#d4a853]">{anchor.title}</span>
            <span className="text-muted-foreground text-xs ml-2">
              {anchor.bpm ? `${anchor.bpm} BPM` : ''}{' '}
              {anchor.camelot_key || anchor.key || ''}
            </span>
          </p>
        )}
      </div>

      {anchor && (
        <CrateGrid tracks={compatible.length ? compatible : []} />
      )}
      {anchor && compatible.length === 0 && (
        <p className="text-center text-xs text-muted-foreground py-8">
          호환 키가 있는 소장곡이 아직 없습니다.
        </p>
      )}
    </div>
  );
}
