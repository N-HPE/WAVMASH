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

export type ExportFormat = 'wav' | 'mp3';

interface DownloadContextValue {
  active: boolean;
  activeUrl: string | null;
  progress: DownloadProgress | null;
  error: string | null;
  completedTracks: Track[];
  exportFormat: ExportFormat;
  setExportFormat: (f: ExportFormat) => void;
  startDownload: (url: string, format?: ExportFormat) => Promise<void>;
  clear: () => void;
}

const DownloadContext = createContext<DownloadContextValue | null>(null);

function preferMobileMp3(): boolean {
  if (typeof navigator === 'undefined') return false;
  return /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
}

export function DownloadProvider({ children }: { children: ReactNode }) {
  const [progress, setProgress] = useState<DownloadProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState(false);
  const [activeUrl, setActiveUrl] = useState<string | null>(null);
  const [completedTracks, setCompletedTracks] = useState<Track[]>([]);
  const [exportFormat, setExportFormat] = useState<ExportFormat>(() =>
    preferMobileMp3() ? 'mp3' : 'wav'
  );
  const cleanupRef = useRef<(() => void) | null>(null);
  const exportingRef = useRef(false);

  const clear = useCallback(() => {
    cleanupRef.current?.();
    cleanupRef.current = null;
    setProgress(null);
    setError(null);
    setActive(false);
    setActiveUrl(null);
    setCompletedTracks([]);
  }, []);

  const startDownload = useCallback(
    async (url: string, format?: ExportFormat) => {
      const trimmed = url.trim();
      if (!trimmed) return;

      cleanupRef.current?.();
      const fmt = format || exportFormat;
      setActive(true);
      setActiveUrl(trimmed);
      setError(null);
      setCompletedTracks([]);
      setProgress({
        job_id: '',
        status: 'pending',
        progress: 0,
        message: '다운로드 시작 중...',
        stage: 'listing',
        format: fmt,
      });

      try {
        const { job_id } = await api.startDownload(trimmed, fmt);
        setProgress((prev) =>
          prev
            ? {
                ...prev,
                job_id,
                status: 'downloading',
                message: '서버에 연결됨... (동시 변환 1개 제한)',
              }
            : prev
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
            setActiveUrl(null);
            cleanupRef.current = null;

            tracks.forEach((t) => {
              api
                .recordTrackDownload(t.track_id, {
                  title: t.title,
                  artist: t.artist,
                  cover_url: api.getCoverUrl(t.track_id, 320),
                })
                .catch(() => {});
            });

            // 태그 베이킹된 파일을 브라우저로 즉시 저장 (서버는 이후 GC)
            const exports = data.exports || [];
            if (exports.length && !exportingRef.current) {
              exportingRef.current = true;
              void (async () => {
                try {
                  for (const ex of exports) {
                    await api.downloadExportBlob(
                      job_id,
                      ex.track_id,
                      ex.export_name
                    );
                    // 브라우저가 연속 다운로드를 막지 않도록 짧은 간격
                    await new Promise((r) => setTimeout(r, 400));
                  }
                } catch (err) {
                  console.warn('Auto export failed', err);
                  setError(
                    err instanceof Error
                      ? err.message
                      : '파일 저장에 실패했습니다. 다시 시도하세요.'
                  );
                } finally {
                  exportingRef.current = false;
                }
              })();
            }
          }

          if (data.status === 'failed') {
            setError(data.error || data.message || '알 수 없는 오류가 발생했습니다.');
            setActive(false);
            setActiveUrl(null);
            cleanupRef.current = null;
          }
        });
      } catch (err) {
        setError(
          err instanceof Error ? err.message : '다운로드를 시작할 수 없습니다.'
        );
        setActive(false);
        setActiveUrl(null);
        setProgress(null);
      }
    },
    [exportFormat]
  );

  const value = useMemo(
    () => ({
      active,
      activeUrl,
      progress,
      error,
      completedTracks,
      exportFormat,
      setExportFormat,
      startDownload,
      clear,
    }),
    [
      active,
      activeUrl,
      progress,
      error,
      completedTracks,
      exportFormat,
      startDownload,
      clear,
    ]
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
