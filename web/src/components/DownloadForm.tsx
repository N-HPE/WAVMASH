'use client';

/* ──────────────────────────────────────────────
   WaveMash — Download Form
   ────────────────────────────────────────────── */

import { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Download,
  ClipboardPaste,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';
import { useDownload } from '@/contexts/DownloadContext';

function detectPlatform(url: string): 'youtube' | 'spotify' | null {
  if (/youtu(\.be|be\.com)/i.test(url)) return 'youtube';
  if (/spotify\.com/i.test(url)) return 'spotify';
  return null;
}

function PlatformIcon({ platform }: { platform: 'youtube' | 'spotify' | null }) {
  if (platform === 'youtube') {
    return (
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="#FF0000">
        <path d="M23.498 6.186a2.994 2.994 0 0 0-2.112-2.12C19.505 3.546 12 3.546 12 3.546s-7.505 0-9.386.52A2.994 2.994 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a2.994 2.994 0 0 0 2.112 2.12c1.881.52 9.386.52 9.386.52s7.505 0 9.386-.52a2.994 2.994 0 0 0 2.112-2.12C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
      </svg>
    );
  }
  if (platform === 'spotify') {
    return (
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="#1DB954">
        <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z" />
      </svg>
    );
  }
  return null;
}

const STAGE_LABELS: Record<string, string> = {
  listing: '목록 확인',
  downloading: '오디오 다운로드',
  converting: '오디오 변환',
  cover: '앨범 커버 · 태그',
  metadata: 'BPM · Key 추출',
  done: '완료',
};

function FormatToggle({
  value,
  onChange,
  disabled,
}: {
  value: 'wav' | 'mp3';
  onChange: (v: 'wav' | 'mp3') => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex rounded-lg border border-border bg-secondary/30 p-0.5 text-xs">
      <button
        type="button"
        disabled={disabled}
        onClick={() => onChange('wav')}
        className={`flex-1 rounded-md px-3 py-1.5 transition-colors ${
          value === 'wav'
            ? 'bg-primary text-primary-foreground'
            : 'text-muted-foreground hover:text-foreground'
        }`}
      >
        Master · WAV
      </button>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onChange('mp3')}
        className={`flex-1 rounded-md px-3 py-1.5 transition-colors ${
          value === 'mp3'
            ? 'bg-primary text-primary-foreground'
            : 'text-muted-foreground hover:text-foreground'
        }`}
      >
        Mobile · MP3
      </button>
    </div>
  );
}

export default function DownloadForm({
  variant = 'inline',
}: {
  variant?: 'inline' | 'stacked';
}) {
  const [url, setUrl] = useState('');
  const [platform, setPlatform] = useState<'youtube' | 'spotify' | null>(null);
  const { active, progress, error, completedTracks, startDownload, clear, exportFormat, setExportFormat } =
    useDownload();

  useEffect(() => {
    setPlatform(detectPlatform(url));
  }, [url]);

  const handlePaste = useCallback(async () => {
    try {
      const text = await navigator.clipboard.readText();
      setUrl(text);
    } catch {
      // Clipboard not available
    }
  }, []);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!url.trim() || active) return;
      await startDownload(url.trim(), exportFormat);
    },
    [url, active, startDownload, exportFormat]
  );

  const handleReset = useCallback(() => {
    setUrl('');
    clear();
  }, [clear]);

  const pct = progress
    ? Math.round(Math.min(100, Math.max(0, progress.progress * 100)))
    : 0;
  const isDone = progress?.status === 'completed';
  const hasCount =
    typeof progress?.current === 'number' &&
    typeof progress?.total === 'number' &&
    (progress.total ?? 0) > 0;

  return (
    <div className="w-full">
      <form onSubmit={handleSubmit}>
        {variant === 'stacked' ? (
          <div className="space-y-3">
            <FormatToggle
              value={exportFormat}
              onChange={setExportFormat}
              disabled={active}
            />
            <div className="flex items-center gap-2 rounded-lg border border-border bg-secondary/40 px-3 py-2 min-w-0">
              <div className="shrink-0">
                {platform ? (
                  <PlatformIcon platform={platform} />
                ) : (
                  <Download className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="Spotify / YouTube Music / YouTube URL 붙여넣기..."
                disabled={active}
                className="flex-1 min-w-0 bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none disabled:opacity-50"
              />
            </div>
            <div className="flex flex-col sm:flex-row gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={handlePaste}
                disabled={active}
                className="sm:flex-1 gap-2"
              >
                <ClipboardPaste className="h-4 w-4" />
                클립보드 붙여넣기
              </Button>
              <Button
                type="submit"
                disabled={!url.trim() || active}
                className="sm:flex-1 bg-primary text-primary-foreground hover:bg-primary/90 gap-2"
              >
                {active ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Download className="h-4 w-4" />
                )}
                {active
                  ? '변환 중...'
                  : exportFormat === 'mp3'
                    ? 'MP3 다운로드'
                    : 'WAV 다운로드'}
              </Button>
            </div>
            <p className="text-[10px] text-muted-foreground">
              파일에 아티스트·제목·커버·BPM·Camelot이 베이킹됩니다. 서버에는 메타만
              남고 오디오는 다운로드 후 삭제됩니다.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            <FormatToggle
              value={exportFormat}
              onChange={setExportFormat}
              disabled={active}
            />
            <div className="relative flex flex-col sm:flex-row sm:items-center gap-2 glass rounded-xl p-2 min-w-0">
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <div className="shrink-0 pl-1">
                  {platform ? (
                    <PlatformIcon platform={platform} />
                  ) : (
                    <Download className="h-5 w-5 text-muted-foreground" />
                  )}
                </div>
                <input
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="YouTube 또는 Spotify URL..."
                  disabled={active}
                  className="flex-1 min-w-0 bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none h-10 disabled:opacity-50"
                />
              </div>
              <div className="flex items-center gap-2 shrink-0 self-end sm:self-auto">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={handlePaste}
                  disabled={active}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <ClipboardPaste className="h-4 w-4" />
                </Button>
                <Button
                  type="submit"
                  disabled={!url.trim() || active}
                  className="bg-primary text-primary-foreground hover:bg-primary/90 rounded-lg px-4 sm:px-5"
                >
                  {active ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      <Download className="h-4 w-4 sm:mr-1.5" />
                      <span className="hidden sm:inline">
                        {exportFormat === 'mp3' ? 'MP3' : 'WAV'}
                      </span>
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        )}
      </form>

      <AnimatePresence mode="wait">
        {(active || (progress && !isDone && !error)) && progress && (
          <motion.div
            key="progress"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mt-4 glass rounded-xl p-4 space-y-3"
          >
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm text-white/80">
                    {STAGE_LABELS[progress.stage || ''] || '진행 중'}
                  </span>
                  {hasCount && (
                    <span className="text-[11px] tabular-nums text-white/40">
                      {progress.current}/{progress.total}곡
                      {typeof progress.remaining === 'number' && progress.remaining > 0
                        ? ` · 남은 ${progress.remaining}`
                        : ''}
                    </span>
                  )}
                </div>
                <p className="text-xs text-muted-foreground mt-1 truncate">
                  {progress.message}
                </p>
                {progress.track_title && (
                  <p className="text-[11px] text-white/35 mt-0.5 truncate">
                    {progress.track_artist ? `${progress.track_artist} — ` : ''}
                    {progress.track_title}
                  </p>
                )}
              </div>
              <span className="text-sm text-gold-gradient font-medium tabular-nums shrink-0">
                {pct}%
              </span>
            </div>
            <div className="h-2 w-full rounded-full bg-white/5 overflow-hidden">
              <motion.div
                className="h-full rounded-full"
                style={{
                  background: 'linear-gradient(90deg, #d4a853, #f5c542)',
                }}
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 0.3, ease: 'easeOut' }}
              />
            </div>
            <p className="text-[10px] text-white/25">
              커버 · BPM · Key 추출까지 포함되어 시간이 걸릴 수 있습니다. 하단 바에서도 진행 상황을 확인할 수 있어요.
            </p>
          </motion.div>
        )}

        {isDone && (
          <motion.div
            key="success"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="mt-4 glass rounded-xl p-4"
          >
            <div className="flex items-center gap-4">
              {completedTracks[0] && (
                <div className="h-16 w-16 flex-shrink-0 overflow-hidden rounded-lg bg-white/5">
                  <img
                    src={api.getCoverUrl(completedTracks[0].track_id)}
                    alt={completedTracks[0].title}
                    className="h-full w-full object-cover"
                  />
                </div>
              )}
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <CheckCircle2 className="h-4 w-4 text-green-400 flex-shrink-0" />
                  <span className="text-sm text-green-400">
                    다운로드 완료!
                    {completedTracks.length > 1
                      ? ` (${completedTracks.length}곡)`
                      : ''}{' '}
                    — 파일이 기기로 저장됩니다
                  </span>
                </div>
                {completedTracks[0] && (
                  <>
                    <p className="truncate text-sm font-medium">
                      {completedTracks[0].title}
                      {completedTracks.length > 1
                        ? ` 외 ${completedTracks.length - 1}곡`
                        : ''}
                    </p>
                    <p className="truncate text-xs text-muted-foreground">
                      {completedTracks[0].artist}
                    </p>
                  </>
                )}
                {!completedTracks.length && (
                  <p className="text-xs text-muted-foreground">{progress?.message}</p>
                )}
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleReset}
                className="flex-shrink-0"
              >
                새로 다운로드
              </Button>
            </div>
          </motion.div>
        )}

        {error && (
          <motion.div
            key="error"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mt-4 rounded-xl p-4"
            style={{
              background: 'rgba(239, 68, 68, 0.08)',
              border: '1px solid rgba(239, 68, 68, 0.2)',
            }}
          >
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-red-400">다운로드 오류</p>
                <p className="text-xs text-red-400/70 mt-1">{error}</p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleReset}
                className="text-red-400 hover:text-red-300 flex-shrink-0"
              >
                다시 시도
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
