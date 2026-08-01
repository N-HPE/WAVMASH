'use client';

/* ──────────────────────────────────────────────
   WaveMash — 플레이리스트 상세 (트랙 리스트)
   ────────────────────────────────────────────── */

import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  ExternalLink,
  Music,
  RefreshCw,
  X,
  Play,
  AlertCircle,
} from 'lucide-react';
import api from '@/lib/api';
import type { Playlist, Track } from '@/lib/types';
import { usePlayer } from '@/contexts/PlayerContext';
import { resolvePlaylistColor, isDarkColor, getVibeCategory } from '@/lib/vibePalette';

type PlaylistTrack = Track & { missing?: boolean };

interface PlaylistDetailPanelProps {
  playlist: Playlist;
  onClose: () => void;
  onSyncComplete?: () => void;
}

export default function PlaylistDetailPanel({
  playlist,
  onClose,
  onSyncComplete,
}: PlaylistDetailPanelProps) {
  const [tracks, setTracks] = useState<PlaylistTrack[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const { play } = usePlayer();

  const color = resolvePlaylistColor({
    color: playlist.color,
    vibe: playlist.vibe,
    shade: playlist.shade,
  });
  const dark = isDarkColor(color);
  const vibeLabel = getVibeCategory(playlist.vibe).label;
  const isSpotify = playlist.source === 'spotify' || !!playlist.sync_id;

  const loadTracks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getPlaylistTracks(playlist.name);
      setTracks(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '트랙을 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  }, [playlist.name]);

  useEffect(() => {
    loadTracks();
  }, [loadTracks]);

  const handleSync = async () => {
    if (!playlist.sync_id) return;
    setSyncing(true);
    try {
      await api.triggerSpotifySync(playlist.sync_id);
      await loadTracks();
      onSyncComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : '동기화 실패');
    } finally {
      setSyncing(false);
    }
  };

  const playable = tracks.filter((t) => t.has_file && !t.missing);

  return (
    <motion.div
      initial={{ opacity: 0, x: 24 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 24 }}
      className="h-full flex flex-col glass rounded-xl overflow-hidden border border-white/8"
    >
      {/* Header */}
      <div
        className="relative px-5 pt-5 pb-4 shrink-0"
        style={{
          background: `linear-gradient(135deg, ${color}cc, ${color}55 60%, transparent)`,
        }}
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute top-3 right-3 p-1.5 rounded-md bg-black/20 hover:bg-black/40 text-white/80"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="flex items-start gap-4 pr-8">
          <div
            className="w-16 h-16 rounded-lg flex items-center justify-center shrink-0 shadow-lg"
            style={{ background: color }}
          >
            <Music
              className="w-7 h-7"
              style={{ color: dark ? 'rgba(255,255,255,0.9)' : 'rgba(0,0,0,0.7)' }}
            />
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="text-lg font-semibold text-white truncate drop-shadow">
              {playlist.name}
            </h2>
            <p className="text-xs text-white/70 mt-0.5">
              {vibeLabel} · {tracks.length || playlist.track_count}곡
              {playlist.missing_count ? ` · 누락 ${playlist.missing_count}` : ''}
            </p>

            <div className="flex flex-wrap items-center gap-2 mt-2">
              {isSpotify ? (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#1DB954]/25 text-[#1DB954] border border-[#1DB954]/40">
                  Spotify 동기화
                </span>
              ) : (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-white/60 border border-white/15">
                  Local
                </span>
              )}
              {playlist.sync_status === 'partial' && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  부분 동기화
                </span>
              )}
              {playlist.spotify_count != null && (
                <span className="text-[10px] text-white/50">
                  Spotify {playlist.spotify_count} · 로컬 {playlist.local_count ?? tracks.length}
                </span>
              )}
            </div>

            {playlist.spotify_url && (
              <a
                href={playlist.spotify_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 mt-2 text-[11px] text-white/60 hover:text-[#1DB954] truncate max-w-full"
              >
                <ExternalLink className="h-3 w-3 shrink-0" />
                <span className="truncate">{playlist.spotify_url}</span>
              </a>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 mt-4">
          <button
            type="button"
            disabled={!playable.length}
            onClick={() => playable[0] && play(playable[0], playable)}
            className="flex items-center gap-1.5 rounded-lg bg-white/95 text-black px-3 py-1.5 text-xs font-semibold disabled:opacity-40"
          >
            <Play className="h-3.5 w-3.5 fill-current" />
            재생
          </button>
          {isSpotify && playlist.sync_id && (
            <button
              type="button"
              onClick={handleSync}
              disabled={syncing}
              className="flex items-center gap-1.5 rounded-lg bg-white/15 hover:bg-white/25 text-white px-3 py-1.5 text-xs disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${syncing ? 'animate-spin' : ''}`} />
              {syncing ? '동기화 중...' : '다시 동기화'}
            </button>
          )}
        </div>
      </div>

      {/* Track list */}
      <div className="flex-1 min-h-0 overflow-y-auto px-2 py-2">
        {loading ? (
          <p className="text-center text-xs text-white/30 py-8">불러오는 중...</p>
        ) : error ? (
          <div className="flex items-center gap-2 text-red-400 text-xs p-4">
            <AlertCircle className="h-4 w-4" />
            {error}
          </div>
        ) : tracks.length === 0 ? (
          <p className="text-center text-xs text-white/30 py-8">
            곡이 없습니다. Spotify 동기화를 실행해 보세요.
          </p>
        ) : (
          <div className="space-y-0.5">
            {tracks.map((track, i) => (
              <button
                key={track.track_id || i}
                type="button"
                disabled={!!track.missing || !track.has_file}
                onClick={() => track.has_file && play(track, playable)}
                className="w-full flex items-center gap-3 rounded-lg px-2.5 py-2 text-left hover:bg-white/[0.04] disabled:opacity-40 disabled:hover:bg-transparent group"
              >
                <span className="w-5 text-[10px] text-white/25 tabular-nums text-right shrink-0">
                  {i + 1}
                </span>
                <div className="w-9 h-9 rounded bg-white/5 overflow-hidden shrink-0">
                  {track.has_cover ? (
                    <img
                      src={api.getCoverUrl(track.track_id, 80)}
                      alt=""
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <Music className="w-3.5 h-3.5 text-white/20" />
                    </div>
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-sm text-white/90 truncate">{track.title}</div>
                  <div className="text-[11px] text-white/35 truncate">
                    {track.artist}
                    {track.missing ? ' · 파일 없음' : ''}
                  </div>
                </div>
                {track.bpm ? (
                  <span className="text-[10px] text-white/25 tabular-nums shrink-0">
                    {track.bpm}
                  </span>
                ) : null}
              </button>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}
