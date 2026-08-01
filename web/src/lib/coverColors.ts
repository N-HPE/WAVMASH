/* ──────────────────────────────────────────────
   WaveMash — Cover color resolver
   카드 N개가 동시에 마운트돼도 요청을 하나로 합치고
   IndexedDB → 메모리 → 배치 API 순으로 조회합니다.
   ────────────────────────────────────────────── */

'use client';

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { getCachedColors, setCachedColors } from '@/lib/colorCache';

const memoryCache = new Map<string, string>();
const DEFAULT_GLOW = 'rgba(212, 168, 83, 0.15)';

let pendingIds = new Set<string>();
let flushTimer: ReturnType<typeof setTimeout> | null = null;
const waiters = new Map<string, Array<(color: string | null) => void>>();

function hexToGlow(hex: string): string {
  const h = hex.replace('#', '');
  if (h.length !== 6) return DEFAULT_GLOW;
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  if (Number.isNaN(r) || Number.isNaN(g) || Number.isNaN(b)) return DEFAULT_GLOW;
  return `rgba(${r}, ${g}, ${b}, 0.15)`;
}

function resolveWaiters(trackId: string, color: string | null) {
  const cbs = waiters.get(trackId);
  if (!cbs) return;
  waiters.delete(trackId);
  for (const cb of cbs) cb(color);
}

async function flushBatch() {
  flushTimer = null;
  const ids = Array.from(pendingIds);
  pendingIds = new Set();
  if (!ids.length) return;

  // 1) IndexedDB
  const local = await getCachedColors(ids);
  const stillMissing: string[] = [];
  for (const id of ids) {
    const cached = local.get(id) ?? memoryCache.get(id);
    if (cached) {
      memoryCache.set(id, cached);
      resolveWaiters(id, cached);
    } else {
      stillMissing.push(id);
    }
  }

  if (!stillMissing.length) return;

  // 2) 서버 배치 API
  try {
    const colors = await api.getCoverColors(stillMissing);
    await setCachedColors(colors);
    for (const id of stillMissing) {
      const color = colors[id] ?? null;
      if (color) memoryCache.set(id, color);
      resolveWaiters(id, color);
    }
  } catch {
    for (const id of stillMissing) {
      resolveWaiters(id, null);
    }
  }
}

function scheduleFlush() {
  if (flushTimer) return;
  // 같은 틱에 마운트된 카드들을 한 요청으로 합침
  flushTimer = setTimeout(() => {
    void flushBatch();
  }, 16);
}

/**
 * 색상 HEX를 가져옵니다. seed가 있으면 즉시 캐시에 넣고 반환합니다.
 */
export function requestCoverColor(
  trackId: string,
  seed?: string | null
): Promise<string | null> {
  if (seed) {
    memoryCache.set(trackId, seed);
    void setCachedColors({ [trackId]: seed });
    return Promise.resolve(seed);
  }

  const mem = memoryCache.get(trackId);
  if (mem) return Promise.resolve(mem);

  return new Promise((resolve) => {
    const list = waiters.get(trackId) ?? [];
    list.push(resolve);
    waiters.set(trackId, list);
    pendingIds.add(trackId);
    scheduleFlush();
  });
}

/** 메모리에 이미 있는 색상 (동기) */
export function peekCoverColor(trackId: string): string | null {
  return memoryCache.get(trackId) ?? null;
}

/**
 * 트랙 카드용 훅 — seed(API dominant_color) → 캐시 → 배치 fetch
 */
export function useCoverGlow(
  trackId: string,
  hasCover: boolean,
  seedColor?: string | null
): string {
  const initial =
    (seedColor && hexToGlow(seedColor)) ||
    (peekCoverColor(trackId) && hexToGlow(peekCoverColor(trackId)!)) ||
    DEFAULT_GLOW;

  const [glow, setGlow] = useState(initial);

  useEffect(() => {
    if (!hasCover) {
      setGlow(DEFAULT_GLOW);
      return;
    }

    if (seedColor) {
      memoryCache.set(trackId, seedColor);
      void setCachedColors({ [trackId]: seedColor });
      setGlow(hexToGlow(seedColor));
      return;
    }

    let cancelled = false;
    requestCoverColor(trackId).then((color) => {
      if (!cancelled && color) setGlow(hexToGlow(color));
    });
    return () => {
      cancelled = true;
    };
  }, [trackId, hasCover, seedColor]);

  return glow;
}

/**
 * 단일 HEX 색상 훅 (트랙 상세 페이지용)
 */
export function useCoverColor(
  trackId: string,
  seedColor?: string | null
): string {
  const [color, setColor] = useState(seedColor || peekCoverColor(trackId) || '#d4a853');

  useEffect(() => {
    let cancelled = false;
    requestCoverColor(trackId, seedColor).then((c) => {
      if (!cancelled && c) setColor(c);
    });
    return () => {
      cancelled = true;
    };
  }, [trackId, seedColor]);

  return color;
}
