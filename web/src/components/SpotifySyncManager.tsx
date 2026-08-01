'use client';

/* ──────────────────────────────────────────────
   WaveMash — Spotify Playlist Auto-Sync Manager
   ────────────────────────────────────────────── */

import { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  RefreshCw,
  Plus,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Music2,
  ExternalLink,
  ShieldAlert,
} from 'lucide-react';
import api from '@/lib/api';
import type { SpotifySyncConfig, SpotifySyncResult } from '@/lib/types';

interface SpotifySyncManagerProps {
  onSyncComplete?: () => void;
}

export default function SpotifySyncManager({ onSyncComplete }: SpotifySyncManagerProps) {
  const [configs, setConfigs] = useState<SpotifySyncConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [urlInput, setUrlInput] = useState('');
  const [autoSync, setAutoSync] = useState(true);
  const [deleteSync, setDeleteSync] = useState(true);

  const [adding, setAdding] = useState(false);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const loadConfigs = useCallback(async () => {
    try {
      const data = await api.getSpotifySyncConfigs();
      setConfigs(data);
    } catch (err) {
      console.error('Failed to load Spotify sync configs:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConfigs();
  }, [loadConfigs]);

  // Auto-poll configs while background sync is running
  useEffect(() => {
    const isSyncing = configs.some((c) => c.status === 'syncing' || c.status === 'pending');
    if (!isSyncing) return;

    const interval = setInterval(() => {
      loadConfigs();
      onSyncComplete?.();
    }, 3000);
    return () => clearInterval(interval);
  }, [configs, loadConfigs, onSyncComplete]);

  const handleAddPlaylist = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!urlInput.trim()) return;

    setAdding(true);
    setStatusMsg(null);
    try {
      await api.addSpotifySyncConfig(urlInput.trim(), autoSync, deleteSync);
      setUrlInput('');
      setStatusMsg({ type: 'success', text: '스포티파이 동기화 플레이리스트가 등록되었습니다. 초기 동기화가 진행됩니다.' });
      await loadConfigs();
      onSyncComplete?.();
    } catch (err) {
      setStatusMsg({
        type: 'error',
        text: err instanceof Error ? err.message : '플레이리스트 등록에 실패했습니다.',
      });
    } finally {
      setAdding(false);
    }
  };

  const handleToggleAutoSync = async (cfg: SpotifySyncConfig) => {
    try {
      const updated = await api.updateSpotifySyncConfig(cfg.id, {
        auto_sync_enabled: !cfg.auto_sync_enabled,
      });
      setConfigs((prev) => prev.map((c) => (c.id === cfg.id ? updated : c)));
    } catch (err) {
      console.error('Failed to toggle auto sync:', err);
    }
  };

  const handleToggleDeleteSync = async (cfg: SpotifySyncConfig) => {
    try {
      const updated = await api.updateSpotifySyncConfig(cfg.id, {
        sync_deletions: !cfg.sync_deletions,
      });
      setConfigs((prev) => prev.map((c) => (c.id === cfg.id ? updated : c)));
    } catch (err) {
      console.error('Failed to toggle delete sync:', err);
    }
  };

  const handleDeleteConfig = async (configId: string) => {
    if (!confirm('이 스포티파이 플레이리스트 동기화 설정을 삭제하시겠습니까?')) return;
    try {
      await api.deleteSpotifySyncConfig(configId);
      setConfigs((prev) => prev.filter((c) => c.id !== configId));
      setStatusMsg({ type: 'success', text: '동기화 설정이 삭제되었습니다.' });
      onSyncComplete?.();
    } catch (err) {
      setStatusMsg({
        type: 'error',
        text: err instanceof Error ? err.message : '설정 삭제에 실패했습니다.',
      });
    }
  };

  const handleTriggerSync = async (configId: string) => {
    setSyncingId(configId);
    setStatusMsg(null);
    try {
      const res: SpotifySyncResult = await api.triggerSpotifySync(configId);
      let text = `'${res.name}' 동기화 완료! (스포티파이 총 ${res.total_spotify_tracks}곡)`;
      if (res.downloaded > 0) text += ` · ${res.downloaded}곡 신규 다운로드`;
      if (res.deleted > 0) text += ` · ${res.deleted}곡 및 빈 폴더 정리 완료`;
      if (res.downloaded === 0 && res.deleted === 0) text += ` · 변경사항 없음 (최신 상태)`;

      setStatusMsg({ type: 'success', text });
      await loadConfigs();
      onSyncComplete?.();
    } catch (err) {
      setStatusMsg({
        type: 'error',
        text: err instanceof Error ? err.message : '동기화 실행 중 오류가 발생했습니다.',
      });
    } finally {
      setSyncingId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* ── Add Sync Form ── */}
      <div className="glass rounded-xl p-6 relative overflow-hidden">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Music2 className="h-5 w-5 text-[#d4a853]" />
            <h3 className="text-lg font-medium">스포티파이 플레이리스트 동기화 등록</h3>
          </div>
          <span className="text-xs text-muted-foreground bg-white/5 px-2.5 py-1 rounded-full border border-white/10">
            자동 감지 & 삭제 연동
          </span>
        </div>

        <form onSubmit={handleAddPlaylist} className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              placeholder="https://open.spotify.com/playlist/..."
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              className="flex-1 rounded-lg bg-black/40 border border-white/10 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-[#d4a853]/60 transition-colors"
            />
            <button
              type="submit"
              disabled={adding || !urlInput.trim()}
              className="flex items-center justify-center gap-2 rounded-lg bg-[#d4a853] px-5 py-2.5 text-sm font-medium text-black transition-transform hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100 cursor-pointer"
            >
              {adding ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Plus className="h-4 w-4" />
              )}
              동기화 등록
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-6 pt-1 text-xs text-muted-foreground">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={autoSync}
                onChange={(e) => setAutoSync(e.target.checked)}
                className="rounded accent-[#d4a853] h-4 w-4 cursor-pointer"
              />
              <span>자동 동기화 활성화</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer select-none text-[#f87171]">
              <input
                type="checkbox"
                checked={deleteSync}
                onChange={(e) => setDeleteSync(e.target.checked)}
                className="rounded accent-red-500 h-4 w-4 cursor-pointer"
              />
              <span className="flex items-center gap-1">
                <ShieldAlert className="h-3.5 w-3.5" />
                삭제 동기화 (스포티파이에서 삭제 시 WAVMASH 음원/폴더 완전 삭제)
              </span>
            </label>
          </div>
        </form>
      </div>

      {/* ── Status Message ── */}
      <AnimatePresence>
        {statusMsg && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className={`flex items-center gap-2 rounded-lg p-4 text-sm ${
              statusMsg.type === 'success'
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                : 'bg-red-500/10 text-red-400 border border-red-500/20'
            }`}
          >
            {statusMsg.type === 'success' ? (
              <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
            ) : (
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
            )}
            <span>{statusMsg.text}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Synced Playlists List ── */}
      <div className="space-y-3">
        <h4 className="text-sm font-medium text-muted-foreground px-1">
          등록된 동기화 플레이리스트 ({configs.length})
        </h4>

        {loading ? (
          <div className="glass rounded-xl p-8 text-center text-sm text-muted-foreground">
            동기화 목록 불러오는 중...
          </div>
        ) : configs.length === 0 ? (
          <div className="glass rounded-xl p-8 text-center text-sm text-muted-foreground">
            등록된 스포티파이 동기화 플레이리스트가 없습니다. 위 입력창에 링크를 넣어 등록해 보세요.
          </div>
        ) : (
          <div className="grid gap-3">
            {configs.map((cfg) => {
              const isSyncing = syncingId === cfg.id;
              return (
                <div
                  key={cfg.id}
                  className="glass rounded-xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 border border-white/5 hover:border-white/10 transition-colors"
                >
                  <div className="min-w-0 space-y-1">
                    <div className="flex items-center gap-2">
                      <h5 className="font-medium text-sm truncate">{cfg.name}</h5>
                      <a
                        href={cfg.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-muted-foreground hover:text-foreground transition-colors"
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                      <span>곡 수: {cfg.track_count}곡</span>
                      <span>•</span>
                      <span>
                        마지막 동기화: {cfg.last_synced_at || '동기화 기록 없음'}
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-3">
                    {/* Controls */}
                    <button
                      onClick={() => handleToggleAutoSync(cfg)}
                      className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors cursor-pointer ${
                        cfg.auto_sync_enabled
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                          : 'bg-white/5 text-muted-foreground border-white/10'
                      }`}
                    >
                      자동동기화 {cfg.auto_sync_enabled ? 'ON' : 'OFF'}
                    </button>

                    <button
                      onClick={() => handleToggleDeleteSync(cfg)}
                      className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors cursor-pointer ${
                        cfg.sync_deletions
                          ? 'bg-red-500/10 text-red-400 border-red-500/30'
                          : 'bg-white/5 text-muted-foreground border-white/10'
                      }`}
                    >
                      삭제연동 {cfg.sync_deletions ? 'ON' : 'OFF'}
                    </button>

                    {/* Sync Now Button */}
                    <button
                      onClick={() => handleTriggerSync(cfg.id)}
                      disabled={isSyncing}
                      className="flex items-center gap-1.5 rounded-lg bg-white/10 hover:bg-white/15 px-3.5 py-1.5 text-xs font-medium text-foreground transition-colors disabled:opacity-50 cursor-pointer"
                    >
                      <RefreshCw
                        className={`h-3.5 w-3.5 ${isSyncing ? 'animate-spin text-[#d4a853]' : ''}`}
                      />
                      {isSyncing ? '동기화 중...' : '지금 동기화'}
                    </button>

                    {/* Delete Config */}
                    <button
                      onClick={() => handleDeleteConfig(cfg.id)}
                      className="p-1.5 rounded-lg text-muted-foreground hover:text-red-400 transition-colors cursor-pointer"
                      title="동기화 설정 삭제"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
