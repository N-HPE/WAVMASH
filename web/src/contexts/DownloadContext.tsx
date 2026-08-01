'use client';

/* ──────────────────────────────────────────────
   WaveMash — 글로벌 다운로드 진행 상태
   ────────────────────────────────────────────── */

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import api from '@/lib/api';
import type { DownloadProgress, Track } from '@/lib/types';

interface DownloadContextValue {
  active: boolean;
  progress: DownloadProgress | null;
  error: string | null;
  completedTracks: Track[];
  startDownload: (url: string) => Promise<void>;
  clear: () => void;
}

const DownloadContext = createContext<DownloadContextValue | null>(null);

export function DownloadProvider({ children }: { children: ReactNode }) {
  const [progress, setProgress] = useState<DownloadProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState(false);
  const [completedTracks, setCompletedTracks] = useState<Track[]>([]);
  const cleanupRef = useRef<(() => void) | null>(null);

  const clear = useCallback(() => {
    cleanupRef.current?.();
    cleanupRef.current = null;
    setProgress(null);
    setError(null);
    setActive(false);
    setCompletedTracks([]);
  }, []);

  const startDownload = useCallback(async (url: string) => {
    cleanupRef.current?.();
    setActive(true);
    setError(null);
    setCompletedTracks([]);
    setProgress({
      job_id: '',
      status: 'pending',
      progress: 0,
      message: '다운로드 시작 중...',
      stage: 'listing',
    });

    try {
      const { job_id } = await api.startDownload(url.trim());
      setProgress((prev) =>
        prev ? { ...prev, job_id, status: 'downloading', message: '서버에 연결됨...' } : prev
      );

      cleanupRef.current = api.subscribeDownloadProgress(job_id, (data) => {
        setProgress(data);

        if (data.status === 'completed') {
          const tracks = data.tracks?.length
            ? data.tracks
            : data.track
              ? [data.track]
              : [];
          setCompletedTracks(tracks);
          setActive(false);
          cleanupRef.current = null;
        }

        if (data.status === 'failed') {
          setError(data.error || data.message || '알 수 없는 오류가 발생했습니다.');
          setActive(false);
          cleanupRef.current = null;
        }
      });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : '다운로드를 시작할 수 없습니다.'
      );
      setActive(false);
      setProgress(null);
    }
  }, []);

  const value = useMemo(
    () => ({ active, progress, error, completedTracks, startDownload, clear }),
    [active, progress, error, completedTracks, startDownload, clear]
  );

  return (
    <DownloadContext.Provider value={value}>{children}</DownloadContext.Provider>
  );
}

export function useDownload() {
  const ctx = useContext(DownloadContext);
  if (!ctx) {
    throw new Error('useDownload must be used within DownloadProvider');
  }
  return ctx;
}
