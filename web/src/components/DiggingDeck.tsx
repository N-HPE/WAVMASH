'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Play,
  Pause,
  ChevronRight,
  ChevronLeft,
  Flame,
  Check,
  X,
  Download,
  Sparkles,
  Headphones,
  Music2,
  Volume2,
  VolumeX,
  Layers,
  ListFilter,
  Disc3,
  Loader2,
  FolderPlus,
  RefreshCw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';
import type { InboxItem, InboxStats } from '@/lib/types';

const QUICK_CRATES = [
  'Peak Time',
  'Deep House',
  'Warmup',
  'Melodic & Vocal',
  'Afterhours',
];

export default function DiggingDeck() {
  const [items, setItems] = useState<InboxItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<InboxStats | null>(null);
  const [viewMode, setViewMode] = useState<'deck' | 'list'>('deck');

  // Audio Playback
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(30);
  const [currentTime, setCurrentTime] = useState(0);
  const [isMuted, setIsMuted] = useState(false);
  const [resolvingYt, setResolvingYt] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [batchDownloading, setBatchDownloading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<'inbox' | 'keep' | 'pass' | 'all'>('inbox');

  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Load items & stats
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [inboxRes, statsRes] = await Promise.all([
        api.getInbox(statusFilter, undefined, 0, 50),
        api.getInboxStats(),
      ]);
      setItems(inboxRes.items || []);
      setStats(statsRes);
      setCurrentIndex(0);
    } catch (err) {
      console.error('Failed to load inbox data:', err);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const currentItem = items[currentIndex] as InboxItem | undefined;

  // Stop previous audio when changing track
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setIsPlaying(false);
    setProgress(0);
    setCurrentTime(0);

    // Auto-play when new track appears in deck mode
    if (currentItem?.preview_url) {
      const timer = setTimeout(() => {
        if (audioRef.current) {
          audioRef.current.src = currentItem.preview_url || '';
          audioRef.current
            .play()
            .then(() => setIsPlaying(true))
            .catch(() => setIsPlaying(false));
        }
      }, 150);
      return () => clearTimeout(timer);
    }
  }, [currentItem]);

  // Audio events
  const handleTimeUpdate = () => {
    if (!audioRef.current) return;
    const cur = audioRef.current.currentTime;
    const dur = audioRef.current.duration || 30;
    setCurrentTime(cur);
    setDuration(dur);
    setProgress((cur / dur) * 100);
  };

  const handleAudioEnded = () => {
    setIsPlaying(false);
    setProgress(100);
  };

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      if (currentItem?.preview_url) {
        audioRef.current.src = currentItem.preview_url;
        audioRef.current
          .play()
          .then(() => setIsPlaying(true))
          .catch(() => setIsPlaying(false));
      }
    }
  };

  // Keep action
  const handleKeep = async (targetCrate?: string, triggerDownload = true) => {
    if (!currentItem || actionLoading) return;
    setActionLoading(true);
    try {
      await api.keepInboxItem(currentItem.id, targetCrate, triggerDownload);
      // Remove from current list if looking at inbox
      if (statusFilter === 'inbox') {
        const nextItems = items.filter((_, idx) => idx !== currentIndex);
        setItems(nextItems);
        if (currentIndex >= nextItems.length) {
          setCurrentIndex(Math.max(0, nextItems.length - 1));
        }
      }
      const newStats = await api.getInboxStats();
      setStats(newStats);
    } catch (err) {
      console.error('Keep failed:', err);
    } finally {
      setActionLoading(false);
    }
  };

  // Pass action
  const handlePass = async () => {
    if (!currentItem || actionLoading) return;
    setActionLoading(true);
    try {
      await api.passInboxItem(currentItem.id);
      if (statusFilter === 'inbox') {
        const nextItems = items.filter((_, idx) => idx !== currentIndex);
        setItems(nextItems);
        if (currentIndex >= nextItems.length) {
          setCurrentIndex(Math.max(0, nextItems.length - 1));
        }
      }
      const newStats = await api.getInboxStats();
      setStats(newStats);
    } catch (err) {
      console.error('Pass failed:', err);
    } finally {
      setActionLoading(false);
    }
  };

  // Batch download
  const handleBatchDownload = async () => {
    try {
      setBatchDownloading(true);
      await api.batchDownloadKept();
      await loadData();
    } catch (err) {
      console.error('Batch download failed:', err);
    } finally {
      setBatchDownloading(false);
    }
  };

  // Seed sample tracks from charts if inbox is empty
  const handleSeedFromCharts = async () => {
    try {
      setLoading(true);
      const res = await api.getSpotifyChart('blue-house', 10);
      const tracks = (res as any)?.tracks || [];
      if (tracks.length > 0) {
        const itemsToPush = tracks.map((t: any) => ({
          track_id: t.id || t.track_id,
          title: t.title,
          artist: t.artist,
          album: t.album,
          genre: 'House / Dance',
          thumbnail_url: t.thumbnail_url,
          preview_url: t.preview_url,
          spotify_url: t.spotify_url,
          curator: 'nexus_nova',
          curator_note: 'Nova가 엄선한 이번 주 하우스 & 댄스 차트 픽',
        }));
        await api.pushToInbox(itemsToPush);
        await loadData();
      }
    } catch (err) {
      console.error('Failed to seed charts:', err);
    } finally {
      setLoading(false);
    }
  };

  // Global Keyboard Shortcuts
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      // Don't intercept typing in inputs
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      if (e.code === 'Space') {
        e.preventDefault();
        togglePlay();
      } else if (e.code === 'KeyD' || e.code === 'ArrowRight') {
        e.preventDefault();
        if (e.shiftKey) {
          handleKeep(undefined, true);
        } else {
          handleKeep();
        }
      } else if (e.code === 'KeyA' || e.code === 'ArrowLeft') {
        e.preventDefault();
        handlePass();
      } else if (e.code === 'Digit1') {
        e.preventDefault();
        handleKeep(QUICK_CRATES[0]);
      } else if (e.code === 'Digit2') {
        e.preventDefault();
        handleKeep(QUICK_CRATES[1]);
      } else if (e.code === 'Digit3') {
        e.preventDefault();
        handleKeep(QUICK_CRATES[2]);
      } else if (e.code === 'Digit4') {
        e.preventDefault();
        handleKeep(QUICK_CRATES[3]);
      } else if (e.code === 'Digit5') {
        e.preventDefault();
        handleKeep(QUICK_CRATES[4]);
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  });

  return (
    <div className="w-full max-w-5xl mx-auto space-y-6">
      {/* Hidden Audio Element */}
      <audio
        ref={audioRef}
        onTimeUpdate={handleTimeUpdate}
        onEnded={handleAudioEnded}
        muted={isMuted}
      />

      {/* ── Top Header & Stats Bar ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/60 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#d4a853]/15 text-[#d4a853]">
              <Headphones className="h-4 w-4" />
            </span>
            <h1 className="text-xl font-bold tracking-tight text-white">
              Digging Room
            </h1>
            <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs font-semibold text-emerald-400 border border-emerald-500/20">
              Nexus Connected
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            중앙통제실(Nexus)과 차트에서 유입된 트랙을 초고속으로 청음하고 선별합니다.
          </p>
        </div>

        {/* Stats Pill Strip */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1.5 rounded-lg border border-border/70 bg-secondary/40 px-3 py-1.5 text-xs">
            <span className="text-muted-foreground">인박스 대기:</span>
            <span className="font-bold text-[#d4a853]">
              {stats?.inbox_count ?? 0}곡
            </span>
          </div>

          <div className="flex items-center gap-1.5 rounded-lg border border-border/70 bg-secondary/40 px-3 py-1.5 text-xs">
            <span className="text-muted-foreground">소장(Keep):</span>
            <span className="font-bold text-emerald-400">
              {stats?.kept_count ?? 0}곡
            </span>
          </div>

          <div className="flex items-center gap-1.5 rounded-lg border border-border/70 bg-secondary/40 px-3 py-1.5 text-xs">
            <span className="text-muted-foreground">전환율:</span>
            <span className="font-bold text-white">
              {stats?.keep_rate_pct ?? 0}%
            </span>
          </div>

          {(stats?.kept_count ?? 0) > 0 && (
            <Button
              size="sm"
              variant="outline"
              onClick={handleBatchDownload}
              disabled={batchDownloading}
              className="h-8 text-xs border-[#d4a853]/40 text-[#d4a853] hover:bg-[#d4a853]/10"
            >
              {batchDownloading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />
              ) : (
                <Download className="h-3.5 w-3.5 mr-1.5" />
              )}
              Keep 곡 일괄 다운로드
            </Button>
          )}
        </div>
      </div>

      {/* ── Sub Navigation & Mode Toggle ── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1 bg-secondary/40 p-1 rounded-lg border border-border/50 text-xs">
          <button
            onClick={() => setStatusFilter('inbox')}
            className={`px-3 py-1 rounded-md font-medium transition-colors ${
              statusFilter === 'inbox'
                ? 'bg-[#d4a853] text-black font-semibold'
                : 'text-muted-foreground hover:text-white'
            }`}
          >
            대기 중 ({stats?.inbox_count ?? 0})
          </button>
          <button
            onClick={() => setStatusFilter('keep')}
            className={`px-3 py-1 rounded-md font-medium transition-colors ${
              statusFilter === 'keep'
                ? 'bg-emerald-500 text-black font-semibold'
                : 'text-muted-foreground hover:text-white'
            }`}
          >
            소장됨 ({stats?.kept_count ?? 0})
          </button>
          <button
            onClick={() => setStatusFilter('pass')}
            className={`px-3 py-1 rounded-md font-medium transition-colors ${
              statusFilter === 'pass'
                ? 'bg-zinc-700 text-white font-semibold'
                : 'text-muted-foreground hover:text-white'
            }`}
          >
            패스됨 ({stats?.passed_count ?? 0})
          </button>
          <button
            onClick={() => setStatusFilter('all')}
            className={`px-3 py-1 rounded-md font-medium transition-colors ${
              statusFilter === 'all'
                ? 'bg-white/20 text-white font-semibold'
                : 'text-muted-foreground hover:text-white'
            }`}
          >
            전체
          </button>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setViewMode(viewMode === 'deck' ? 'list' : 'deck')}
            className="h-8 text-xs text-muted-foreground hover:text-white"
          >
            {viewMode === 'deck' ? (
              <>
                <ListFilter className="h-3.5 w-3.5 mr-1.5" /> 리스트 뷰
              </>
            ) : (
              <>
                <Layers className="h-3.5 w-3.5 mr-1.5" /> 덱 포커스 뷰
              </>
            )}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={loadData}
            className="h-8 w-8 p-0 text-muted-foreground hover:text-white"
            title="새로고침"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* ── Content View ── */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-[#d4a853]" />
          <p className="text-sm text-muted-foreground">인박스 트랙을 불러오는 중...</p>
        </div>
      ) : items.length === 0 ? (
        /* Empty State */
        <div className="rounded-2xl border border-dashed border-border/80 p-12 text-center bg-secondary/10">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-secondary/60 text-muted-foreground mb-4">
            <Disc3 className="h-7 w-7 text-[#d4a853]" />
          </div>
          <h3 className="text-base font-semibold text-white">
            인박스에 대기 중인 트랙이 없습니다
          </h3>
          <p className="text-sm text-muted-foreground mt-1 max-w-md mx-auto">
            Nexus 중앙통제실에서 추천을 보내거나, 아래 버튼을 눌러 최신 하우스/댄스
            차트 트랙을 인박스로 가져와 바로 디깅해 보세요!
          </p>
          <div className="mt-6 flex items-center justify-center gap-3">
            <Button
              onClick={handleSeedFromCharts}
              className="bg-[#d4a853] text-black hover:bg-[#b58c3f] font-semibold"
            >
              <Sparkles className="h-4 w-4 mr-2" />
              최신 차트 10곡 인박스에 채우기
            </Button>
          </div>
        </div>
      ) : viewMode === 'deck' && currentItem ? (
        /* ── Deck Mode (Focus Audition) ── */
        <div className="relative">
          {/* Track Counter Indicator */}
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-2 px-1">
            <span>
              트랙 {currentIndex + 1} / {items.length}
            </span>
            <span className="flex items-center gap-1 text-[#d4a853]">
              <Flame className="h-3.5 w-3.5" /> 핫키 활성화: A(패스) · D(킵) · Space(재생) · 1~5(크레이트)
            </span>
          </div>

          <motion.div
            key={currentItem.id}
            initial={{ opacity: 0, scale: 0.98, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.98, y: -10 }}
            transition={{ duration: 0.2 }}
            className="rounded-2xl border border-white/10 bg-gradient-to-b from-[#181824] to-[#12121a] p-6 sm:p-8 shadow-2xl backdrop-blur-xl relative overflow-hidden"
          >
            {/* Vinyl Glow Gradient in Background */}
            <div className="absolute top-0 right-0 -mr-20 -mt-20 w-80 h-80 rounded-full bg-[#d4a853]/5 blur-3xl pointer-events-none" />

            <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
              {/* Left Column: Large Vinyl Artwork + Play Overlay */}
              <div className="md:col-span-5 flex flex-col items-center justify-center">
                <div className="relative group w-56 h-56 sm:w-64 sm:h-64 rounded-2xl overflow-hidden shadow-2xl border border-white/10 bg-black/60">
                  {currentItem.thumbnail_url ? (
                    <img
                      src={currentItem.thumbnail_url}
                      alt={currentItem.title}
                      className={`w-full h-full object-cover transition-transform duration-700 ${
                        isPlaying ? 'scale-105 rotate-1' : 'scale-100'
                      }`}
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center bg-zinc-900 text-zinc-600">
                      <Music2 className="h-16 w-16" />
                    </div>
                  )}

                  {/* Pulsing Play Button Overlay */}
                  <button
                    onClick={togglePlay}
                    className="absolute inset-0 flex items-center justify-center bg-black/40 hover:bg-black/30 transition-colors"
                  >
                    <div className="h-16 w-16 rounded-full bg-[#d4a853] flex items-center justify-center text-black shadow-lg transform transition-transform hover:scale-110">
                      {isPlaying ? (
                        <Pause className="h-7 w-7 fill-black" />
                      ) : (
                        <Play className="h-7 w-7 fill-black ml-1" />
                      )}
                    </div>
                  </button>
                </div>
              </div>

              {/* Right Column: Track Details, Nexus Liner Note, Waveform, Quick Crates */}
              <div className="md:col-span-7 flex flex-col justify-between space-y-4">
                <div>
                  {/* Curator Note Banner */}
                  {currentItem.curator_note && (
                    <div className="inline-flex items-center gap-2 rounded-lg bg-[#d4a853]/10 border border-[#d4a853]/30 px-3 py-1.5 text-xs text-[#d4a853] mb-3">
                      <Sparkles className="h-3.5 w-3.5 shrink-0" />
                      <span className="font-semibold">Nova&apos;s Liner Note:</span>
                      <span className="text-zinc-200 truncate">
                        {currentItem.curator_note}
                      </span>
                    </div>
                  )}

                  {/* Title & Artist */}
                  <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white leading-tight">
                    {currentItem.title}
                  </h2>
                  <p className="text-lg font-medium text-[#d4a853] mt-0.5">
                    {currentItem.artist}
                  </p>
                  {currentItem.album && (
                    <p className="text-xs text-muted-foreground mt-0.5">
                      앨범: {currentItem.album}
                    </p>
                  )}

                  {/* Genre / Key / BPM Pills */}
                  <div className="flex items-center gap-2 mt-3 flex-wrap">
                    {currentItem.genre && (
                      <span className="rounded-md bg-white/5 border border-white/10 px-2.5 py-1 text-xs text-zinc-300">
                        {currentItem.genre}
                      </span>
                    )}
                    {currentItem.bpm && (
                      <span className="rounded-md bg-white/5 border border-white/10 px-2.5 py-1 text-xs font-mono text-zinc-300">
                        {currentItem.bpm} BPM
                      </span>
                    )}
                    {currentItem.camelot_key && (
                      <span className="rounded-md bg-[#d4a853]/20 border border-[#d4a853]/40 px-2.5 py-1 text-xs font-mono font-semibold text-[#d4a853]">
                        {currentItem.camelot_key}
                      </span>
                    )}
                  </div>
                </div>

                {/* Audio Progress Scrubber */}
                <div className="space-y-1 pt-2">
                  <div
                    onClick={(e) => {
                      if (!audioRef.current || !audioRef.current.duration) return;
                      const rect = e.currentTarget.getBoundingClientRect();
                      const pct = (e.clientX - rect.left) / rect.width;
                      audioRef.current.currentTime = pct * audioRef.current.duration;
                    }}
                    className="h-2 w-full bg-zinc-800 rounded-full overflow-hidden cursor-pointer relative"
                  >
                    <div
                      className="h-full bg-gradient-to-r from-[#d4a853] to-amber-300 rounded-full transition-all duration-100"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[11px] font-mono text-zinc-400">
                    <span>
                      {Math.floor(currentTime / 60)}:
                      {Math.floor(currentTime % 60)
                        .toString()
                        .padStart(2, '0')}
                    </span>
                    <span>
                      {currentItem.preview_url ? '30초 미리듣기' : '미리듣기 없음'}
                    </span>
                    <span>
                      {Math.floor(duration / 60)}:
                      {Math.floor(duration % 60)
                        .toString()
                        .padStart(2, '0')}
                    </span>
                  </div>
                </div>

                {/* Quick Crate Assignment Buttons */}
                <div className="pt-2">
                  <span className="text-xs text-zinc-400 block mb-1.5">
                    단축키로 크레이트 분류 (1 ~ 5):
                  </span>
                  <div className="flex items-center gap-1.5 flex-wrap">
                    {QUICK_CRATES.map((crate, idx) => (
                      <button
                        key={crate}
                        onClick={() => handleKeep(crate)}
                        className="rounded-md bg-white/5 hover:bg-[#d4a853]/20 border border-white/10 hover:border-[#d4a853]/40 px-2.5 py-1 text-xs text-zinc-300 hover:text-white transition-all cursor-pointer"
                      >
                        <span className="text-[#d4a853] font-bold mr-1">{idx + 1}.</span>
                        {crate}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Primary Action Buttons */}
                <div className="flex items-center gap-3 pt-3">
                  <Button
                    size="lg"
                    variant="outline"
                    onClick={handlePass}
                    disabled={actionLoading}
                    className="flex-1 h-12 border-red-500/40 text-red-400 hover:bg-red-500/10 hover:text-red-300 font-semibold"
                  >
                    <X className="h-5 w-5 mr-1.5" />
                    패스 (A)
                  </Button>

                  <Button
                    size="lg"
                    onClick={() => handleKeep()}
                    disabled={actionLoading}
                    className="flex-1 h-12 bg-[#d4a853] text-black hover:bg-[#b58c3f] font-bold shadow-lg shadow-[#d4a853]/20"
                  >
                    <Check className="h-5 w-5 mr-1.5 stroke-[2.5]" />
                    Keep 소장 (D)
                  </Button>

                  <Button
                    size="lg"
                    variant="secondary"
                    onClick={() => handleKeep(undefined, true)}
                    disabled={actionLoading}
                    className="h-12 px-4 border border-[#d4a853]/30 text-white hover:bg-white/10"
                    title="Keep & 무손실 WAV 즉시 다운로드"
                  >
                    <Download className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Navigation Controls below Deck */}
          <div className="flex items-center justify-between mt-3 px-2">
            <Button
              size="sm"
              variant="ghost"
              disabled={currentIndex === 0}
              onClick={() => setCurrentIndex((i) => Math.max(0, i - 1))}
              className="text-xs text-muted-foreground"
            >
              <ChevronLeft className="h-4 w-4 mr-1" /> 이전 곡
            </Button>
            <Button
              size="sm"
              variant="ghost"
              disabled={currentIndex >= items.length - 1}
              onClick={() => setCurrentIndex((i) => Math.min(items.length - 1, i + 1))}
              className="text-xs text-muted-foreground"
            >
              다음 곡 <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </div>
      ) : (
        /* ── Table / List Mode ── */
        <div className="rounded-xl border border-border/80 overflow-hidden bg-card/60">
          <div className="divide-y divide-border/60">
            {items.map((item, idx) => (
              <div
                key={item.id}
                className={`flex items-center gap-4 px-4 py-3 hover:bg-secondary/40 transition-colors ${
                  currentIndex === idx ? 'bg-secondary/30' : ''
                }`}
              >
                <span className="w-6 text-center font-mono text-xs text-muted-foreground">
                  {idx + 1}
                </span>

                <div className="h-11 w-11 rounded-lg overflow-hidden shrink-0 bg-secondary">
                  {item.thumbnail_url ? (
                    <img
                      src={item.thumbnail_url}
                      alt=""
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="h-full w-full flex items-center justify-center text-muted-foreground">
                      <Music2 className="h-5 w-5" />
                    </div>
                  )}
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="truncate text-sm font-semibold text-white">
                      {item.title}
                    </p>
                    {item.curator_note && (
                      <span className="hidden sm:inline-block rounded bg-[#d4a853]/10 border border-[#d4a853]/20 px-1.5 py-0.5 text-[10px] text-[#d4a853] truncate max-w-[200px]">
                        {item.curator_note}
                      </span>
                    )}
                  </div>
                  <p className="truncate text-xs text-muted-foreground">
                    {item.artist} {item.album ? `· ${item.album}` : ''}
                  </p>
                </div>

                {item.genre && (
                  <span className="hidden md:inline-block text-xs text-zinc-400">
                    {item.genre}
                  </span>
                )}

                <div className="flex items-center gap-1.5 shrink-0">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setCurrentIndex(idx);
                      if (audioRef.current && item.preview_url) {
                        audioRef.current.src = item.preview_url;
                        audioRef.current.play();
                        setIsPlaying(true);
                      }
                    }}
                    className="h-8 w-8 p-0"
                    title="재생"
                  >
                    <Play className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={async () => {
                      await api.passInboxItem(item.id);
                      loadData();
                    }}
                    className="h-8 px-2 text-xs border-red-500/30 text-red-400 hover:bg-red-500/10"
                  >
                    Pass
                  </Button>
                  <Button
                    size="sm"
                    onClick={async () => {
                      await api.keepInboxItem(item.id);
                      loadData();
                    }}
                    className="h-8 px-2 text-xs bg-[#d4a853] text-black hover:bg-[#b58c3f] font-semibold"
                  >
                    Keep
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
