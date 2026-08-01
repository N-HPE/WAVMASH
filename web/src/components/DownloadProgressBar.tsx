'use client';

/* ──────────────────────────────────────────────
   WaveMash — 하단 다운로드 진행 패널
   ────────────────────────────────────────────── */

import { motion, AnimatePresence } from 'framer-motion';
import {
  Loader2,
  CheckCircle2,
  AlertCircle,
  X,
  Music,
} from 'lucide-react';
import { useDownload } from '@/contexts/DownloadContext';
import { usePlayer } from '@/contexts/PlayerContext';

const STAGE_LABELS: Record<string, string> = {
  listing: '목록 확인',
  downloading: '오디오 다운로드',
  converting: 'WAV 변환',
  cover: '앨범 커버',
  metadata: 'BPM · Key 추출',
  done: '완료',
  error: '오류',
};

export default function DownloadProgressBar() {
  const { active, progress, error, completedTracks, clear } = useDownload();
  const { currentTrack } = usePlayer();

  const show =
    active ||
    !!error ||
    (progress?.status === 'completed' && !!progress) ||
    (progress?.status === 'failed' && !!progress);

  if (!show || !progress) return null;

  const pct = Math.round(Math.min(100, Math.max(0, (progress.progress ?? 0) * 100)));
  const stageLabel = STAGE_LABELS[progress.stage || ''] || progress.stage || '';
  const isDone = progress.status === 'completed';
  const isFailed = progress.status === 'failed' || !!error;
  const hasCount =
    typeof progress.current === 'number' &&
    typeof progress.total === 'number' &&
    progress.total > 0;

  // MiniPlayer가 있으면 그 위에 붙임
  const bottomOffset = currentTrack ? 80 : 0;

  return (
    <AnimatePresence>
      <motion.div
        key="download-bar"
        initial={{ y: 40, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 40, opacity: 0 }}
        className="fixed left-0 right-0 z-40 px-3 sm:px-6"
        style={{ bottom: bottomOffset + 12 }}
      >
        <div
          className="mx-auto max-w-3xl rounded-xl border border-white/10 shadow-2xl overflow-hidden"
          style={{
            background: isFailed
              ? 'rgba(40, 12, 12, 0.94)'
              : isDone
                ? 'rgba(12, 28, 18, 0.94)'
                : 'rgba(12, 12, 22, 0.94)',
            backdropFilter: 'blur(16px)',
          }}
        >
          {/* progress strip */}
          {!isDone && !isFailed && (
            <div className="h-1 w-full bg-white/5">
              <motion.div
                className="h-full"
                style={{
                  background: 'linear-gradient(90deg, #d4a853, #f5c542)',
                }}
                initial={false}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 0.35, ease: 'easeOut' }}
              />
            </div>
          )}

          <div className="flex items-start gap-3 px-4 py-3">
            <div className="mt-0.5 shrink-0">
              {isFailed ? (
                <AlertCircle className="h-5 w-5 text-red-400" />
              ) : isDone ? (
                <CheckCircle2 className="h-5 w-5 text-green-400" />
              ) : (
                <Loader2 className="h-5 w-5 text-[#d4a853] animate-spin" />
              )}
            </div>

            <div className="min-w-0 flex-1 space-y-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-medium text-white/90">
                  {isFailed
                    ? '다운로드 실패'
                    : isDone
                      ? `다운로드 완료${completedTracks.length ? ` · ${completedTracks.length}곡` : ''}`
                      : '다운로드 진행 중'}
                </span>
                {!isDone && !isFailed && (
                  <span className="text-xs tabular-nums text-[#d4a853] font-semibold">
                    {pct}%
                  </span>
                )}
                {stageLabel && !isDone && !isFailed && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/8 text-white/50">
                    {stageLabel}
                  </span>
                )}
              </div>

              <p className="text-xs text-white/50 truncate">
                {isFailed ? error || progress.error || progress.message : progress.message}
              </p>

              {(progress.track_title || hasCount) && !isFailed && (
                <div className="flex items-center gap-2 text-[11px] text-white/35 flex-wrap">
                  {progress.track_title && (
                    <span className="inline-flex items-center gap-1 truncate max-w-[240px]">
                      <Music className="h-3 w-3 shrink-0" />
                      <span className="truncate">
                        {progress.track_artist ? `${progress.track_artist} — ` : ''}
                        {progress.track_title}
                      </span>
                    </span>
                  )}
                  {hasCount && (
                    <span className="tabular-nums shrink-0">
                      {progress.current}/{progress.total}곡
                      {typeof progress.remaining === 'number' && progress.remaining > 0
                        ? ` · 남은 ${progress.remaining}곡`
                        : ''}
                      {typeof progress.skipped === 'number' && progress.skipped > 0
                        ? ` · 스킵 ${progress.skipped}`
                        : ''}
                    </span>
                  )}
                </div>
              )}
            </div>

            <button
              type="button"
              onClick={clear}
              className="shrink-0 p-1 rounded-md text-white/30 hover:text-white/70 hover:bg-white/5 transition-colors"
              aria-label="닫기"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
