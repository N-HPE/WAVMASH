'use client';

/* ──────────────────────────────────────────────
   WaveMash — Account-level YouTube Sync & Database Manager
   유튜브 재생목록/좋아요 음악 계정별 DB 영구 저장, 스마트 정제, 스트리밍 및 WAV 소장
   ────────────────────────────────────────────── */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  RefreshCw,
  Folder,
  Heart,
  Play,
  Pause,
  Download,
  Check,
  Disc3,
  ExternalLink,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Database,
  CloudCheck,
  CheckCircle2,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { usePlayer } from '@/contexts/PlayerContext';
import {
  fetchMyYouTubePlaylists,
  fetchPlaylistItems,
  fetchLikedVideos,
  type YouTubePlaylist,
  type YouTubePlaylistItem,
} from '@/lib/youtube';
import api from '@/lib/api';

function YouTubeIcon({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
    </svg>
  );
}

export default function YouTubeSyncManager() {
  const { user, googleAccessToken, signInWithGoogle } = useAuth();
  const { currentTrack, isPlaying, play, togglePlay } = usePlayer();

  const [playlists, setPlaylists] = useState<YouTubePlaylist[]>([]);
  const [selectedPlaylist, setSelectedPlaylist] = useState<YouTubePlaylist | null>(null);
  const [playlistItems, setPlaylistItems] = useState<YouTubePlaylistItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncingDb, setSyncingDb] = useState(false);
  const [dbSavedNotice, setDbSavedNotice] = useState(false);
  const [loadingItems, setLoadingItems] = useState(false);
  const [downloadingIds, setDownloadingIds] = useState<string[]>([]);
  const [downloadedIds, setDownloadedIds] = useState<string[]>([]);

  // 1. Initial Load: DB에서 계정별 저장된 플리 먼저 불러오기 (캐시/오프라인 지원)
  const loadSavedFromDb = async () => {
    if (!user) return;
    try {
      const saved = await api.getSavedYouTubePlaylists(user.id);
      if (saved && saved.length > 0) {
        const mapped: YouTubePlaylist[] = saved.map((s: any) => ({
          id: s.id,
          title: s.title,
          description: s.description || '',
          thumbnailUrl: s.thumbnail_url || '',
          itemCount: s.item_count || 0,
        }));
        setPlaylists(mapped);
      }
    } catch (err) {
      console.warn('Could not load saved YouTube playlists from DB:', err);
    }
  };

  // 2. Fetch Live Playlists from YouTube API & Auto Sync to DB
  const loadAndSyncPlaylists = async () => {
    if (!googleAccessToken) return;
    setLoading(true);
    try {
      const livePlaylists = await fetchMyYouTubePlaylists(googleAccessToken);
      if (livePlaylists && livePlaylists.length > 0) {
        setPlaylists(livePlaylists);
        // 백그라운드에서 DB로 영구 저장 (Sync to Supabase DB)
        syncPlaylistsToDatabase(livePlaylists);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // 3. Sync Playlists & Top Items to Supabase Database
  const syncPlaylistsToDatabase = async (targetPlaylists: YouTubePlaylist[]) => {
    if (!user || !googleAccessToken) return;
    setSyncingDb(true);
    try {
      const payload: any[] = [];
      for (const pl of targetPlaylists.slice(0, 10)) {
        let items: YouTubePlaylistItem[] = [];
        try {
          items = await fetchPlaylistItems(googleAccessToken, pl.id);
        } catch {
          items = [];
        }

        payload.push({
          id: pl.id,
          title: pl.title,
          description: pl.description || '',
          thumbnailUrl: pl.thumbnailUrl || '',
          itemCount: pl.itemCount || items.length,
          tracks: items.map((t) => ({
            videoId: t.videoId,
            rawTitle: t.title,
            artist: t.artist,
            cleanTitle: t.cleanTitle,
            channelTitle: t.channelTitle,
            thumbnailUrl: t.thumbnailUrl,
            duration: t.duration || '',
          })),
        });
      }

      if (payload.length > 0) {
        await api.syncUserYouTubePlaylists(payload);
        setDbSavedNotice(true);
        setTimeout(() => setDbSavedNotice(false), 4000);
      }
    } catch (err) {
      console.error('Failed to sync to database:', err);
    } finally {
      setSyncingDb(false);
    }
  };

  useEffect(() => {
    if (user) {
      loadSavedFromDb();
    }
    if (googleAccessToken) {
      loadAndSyncPlaylists();
    }
  }, [user, googleAccessToken]);

  // 4. Select Playlist & Load Videos (DB First, then Live API)
  const handleSelectPlaylist = async (pl: YouTubePlaylist) => {
    setSelectedPlaylist(pl);
    setLoadingItems(true);

    try {
      // A. DB에 저장된 트랙이 있는지 먼저 확인
      if (user && pl.id !== 'liked-videos') {
        const savedTracks = await api.getSavedYouTubePlaylistTracks(pl.id, user.id);
        if (savedTracks && savedTracks.length > 0) {
          setPlaylistItems(
            savedTracks.map((st: any) => ({
              id: st.id,
              videoId: st.video_id,
              title: st.raw_title,
              artist: st.artist,
              cleanTitle: st.clean_title,
              channelTitle: st.channel_title,
              thumbnailUrl: st.thumbnail_url,
              publishedAt: st.created_at,
            }))
          );
          setLoadingItems(false);
          return;
        }
      }

      // B. DB에 없거나 실시간 조회가 필요할 때
      if (googleAccessToken) {
        if (pl.id === 'liked-videos') {
          const items = await fetchLikedVideos(googleAccessToken);
          setPlaylistItems(items);
        } else {
          const items = await fetchPlaylistItems(googleAccessToken, pl.id);
          setPlaylistItems(items);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingItems(false);
    }
  };

  // 5. Play YouTube Item in unified player
  const handlePlayItem = (item: YouTubePlaylistItem) => {
    const trackMock: any = {
      track_id: item.videoId,
      title: item.cleanTitle,
      artist: item.artist,
      primary_artist: item.artist,
      album: selectedPlaylist?.title || 'YouTube Collection',
      genre: 'YouTube',
      year: item.publishedAt ? item.publishedAt.slice(0, 4) : '',
      bpm: 0,
      key: '',
      camelot_key: '',
      energy_level: 0,
      platform: 'YouTube',
      url: `https://www.youtube.com/watch?v=${item.videoId}`,
      thumbnail_url: item.thumbnailUrl,
      has_cover: true,
      has_file: false,
      format: 'YOUTUBE_STREAM',
    };

    if (currentTrack?.track_id === item.videoId) {
      togglePlay();
    } else {
      play(trackMock);
    }
  };

  // 6. Download / Collect Single Track as Lossless WAV
  const handleDownloadTrack = async (item: YouTubePlaylistItem) => {
    const videoUrl = `https://www.youtube.com/watch?v=${item.videoId}`;
    setDownloadingIds((prev) => [...prev, item.videoId]);

    try {
      await api.startDownload(videoUrl);
      setDownloadedIds((prev) => [...prev, item.videoId]);
    } catch (err) {
      console.error('Download start failed:', err);
    } finally {
      setDownloadingIds((prev) => prev.filter((id) => id !== item.videoId));
    }
  };

  // ── A. Not Logged in or No YouTube Token ──
  if (!user || (!googleAccessToken && playlists.length === 0)) {
    return (
      <div className="glass rounded-2xl p-8 border border-white/10 text-center max-w-2xl mx-auto space-y-6">
        <div className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/30 flex items-center justify-center mx-auto text-red-500 shadow-xl">
          <YouTubeIcon className="w-8 h-8" />
        </div>

        <div className="space-y-2">
          <h3 className="text-xl font-bold text-white">
            개인별 YouTube 재생목록 계정 DB 영구 연동
          </h3>
          <p className="text-xs text-muted-foreground max-w-md mx-auto leading-relaxed">
            Google 계정으로 로그인하면 내 유튜브에 저장된 플레이리스트들이
            <strong>내 전용 클라우드 데이터베이스에 안전하게 구축 및 저장</strong>되어
            언제든 즉각 로드되고 고음질 WAV로 소장할 수 있습니다.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2">
          <button
            onClick={signInWithGoogle}
            className="w-full sm:w-auto px-6 py-3 rounded-xl bg-red-600 hover:bg-red-500 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-red-600/30 transition-all active:scale-95 cursor-pointer"
          >
            <YouTubeIcon className="w-5 h-5 fill-current" />
            Google 계정으로 YouTube 플리 연동
          </button>
        </div>

        <div className="flex items-center justify-center gap-4 text-[11px] text-muted-foreground/80 pt-2 border-t border-white/5">
          <span className="flex items-center gap-1">
            <Database className="w-3.5 h-3.5 text-blue-400" />
            계정별 독립 DB 구축
          </span>
          <span>•</span>
          <span className="flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5 text-green-400" />
            안전한 읽기 권한
          </span>
        </div>
      </div>
    );
  }

  // ── B. Logged in with Synced YouTube Data ──
  return (
    <div className="space-y-6">
      {/* Top Header Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass p-4 rounded-2xl border border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-red-500/15 border border-red-500/30 flex items-center justify-center text-red-500 shrink-0">
            <YouTubeIcon className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              내 YouTube 플레이리스트 ({playlists.length}개)
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-500/20 text-green-400 font-mono flex items-center gap-1">
                <Database className="w-2.5 h-2.5" />
                DB SYNCED
              </span>
            </h3>
            <p className="text-xs text-muted-foreground">
              계정별 데이터베이스에 안전하게 보관되어 빠른 스트리밍 및 소장이 가능합니다.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {syncingDb && (
            <span className="text-[11px] text-[#d4a853] flex items-center gap-1 animate-pulse">
              <RefreshCw className="w-3 h-3 animate-spin" /> DB 동기화 중...
            </span>
          )}
          {dbSavedNotice && (
            <span className="text-[11px] text-green-400 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" /> DB 저장 완료!
            </span>
          )}
          <button
            onClick={loadAndSyncPlaylists}
            disabled={loading || syncingDb}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 text-white text-xs font-semibold border border-white/10 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading || syncingDb ? 'animate-spin' : ''}`} />
            동기화 갱신
          </button>
        </div>
      </div>

      {/* Playlists Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
        {/* Preset: Liked Videos */}
        <div
          onClick={() =>
            handleSelectPlaylist({
              id: 'liked-videos',
              title: '❤️ 좋아요 표시한 음악',
              description: '내가 좋아요를 누른 음악 영상 목록',
              thumbnailUrl: '',
              itemCount: 50,
            })
          }
          className={`glass rounded-xl p-3 border transition-all cursor-pointer group flex flex-col justify-between ${
            selectedPlaylist?.id === 'liked-videos'
              ? 'border-red-500 ring-2 ring-red-500/20 bg-red-500/10'
              : 'border-white/10 hover:border-white/20'
          }`}
        >
          <div className="aspect-square rounded-lg bg-gradient-to-tr from-red-600 to-amber-500 flex items-center justify-center mb-2 shadow-lg group-hover:scale-105 transition-transform">
            <Heart className="w-8 h-8 text-white fill-current" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-white truncate">좋아요 표시한 음악</h4>
            <p className="text-[10px] text-muted-foreground">YouTube Liked</p>
          </div>
        </div>

        {/* User Playlists */}
        {playlists.map((pl) => {
          const isSelected = selectedPlaylist?.id === pl.id;
          return (
            <div
              key={pl.id}
              onClick={() => handleSelectPlaylist(pl)}
              className={`glass rounded-xl p-3 border transition-all cursor-pointer group flex flex-col justify-between ${
                isSelected
                  ? 'border-[#d4a853] ring-2 ring-[#d4a853]/20 bg-[#d4a853]/10'
                  : 'border-white/10 hover:border-white/20'
              }`}
            >
              <div className="aspect-square rounded-lg overflow-hidden bg-black/40 mb-2 relative group-hover:scale-105 transition-transform">
                {pl.thumbnailUrl ? (
                  <img src={pl.thumbnailUrl} alt={pl.title} className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <Folder className="w-8 h-8 text-white/30" />
                  </div>
                )}
                <span className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/70 text-[9px] font-mono text-white">
                  {pl.itemCount}곡
                </span>
              </div>
              <div>
                <h4 className="text-xs font-bold text-white truncate group-hover:text-[#d4a853] transition-colors">
                  {pl.title}
                </h4>
                <p className="text-[10px] text-muted-foreground truncate">
                  {pl.itemCount}개의 트랙
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected Playlist Track List */}
      {selectedPlaylist && (
        <div className="glass rounded-2xl p-5 border border-white/10 space-y-4">
          <div className="flex items-center justify-between border-b border-white/10 pb-3">
            <div>
              <h4 className="text-base font-bold text-white flex items-center gap-2">
                <Disc3 className="w-4 h-4 text-[#d4a853]" />
                {selectedPlaylist.title}
              </h4>
              <p className="text-xs text-muted-foreground">
                총 {playlistItems.length}개의 음악 트랙이 DB에 정제 및 보관되어 있습니다.
              </p>
            </div>
          </div>

          {loadingItems ? (
            <div className="py-12 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-[#d4a853]" />
              유튜브 트랙 목록 및 메타데이터를 불러오는 중...
            </div>
          ) : playlistItems.length === 0 ? (
            <div className="py-12 text-center text-xs text-muted-foreground">
              재생목록에 포함된 영상이 없습니다.
            </div>
          ) : (
            <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1 scrollbar-thin">
              {playlistItems.map((item) => {
                const isPlayingThis = isPlaying && currentTrack?.track_id === item.videoId;
                const isDownloading = downloadingIds.includes(item.videoId);
                const isDownloaded = downloadedIds.includes(item.videoId);

                return (
                  <div
                    key={item.id || item.videoId}
                    className={`flex items-center justify-between p-3 rounded-xl border transition-all ${
                      isPlayingThis
                        ? 'bg-[#d4a853]/15 border-[#d4a853]/40'
                        : 'bg-white/[0.02] border-white/5 hover:bg-white/[0.05]'
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      {/* Play Button Thumbnail */}
                      <div
                        onClick={() => handlePlayItem(item)}
                        className="relative w-12 h-12 rounded-lg overflow-hidden bg-black/50 shrink-0 cursor-pointer group"
                      >
                        <img
                          src={item.thumbnailUrl}
                          alt={item.title}
                          className="w-full h-full object-cover"
                        />
                        <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                          {isPlayingThis ? (
                            <Pause className="w-5 h-5 text-[#d4a853] fill-current" />
                          ) : (
                            <Play className="w-5 h-5 text-[#d4a853] fill-current ml-0.5" />
                          )}
                        </div>
                      </div>

                      {/* Cleaned Track Info */}
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <h5
                            className="text-xs font-bold text-white truncate hover:text-[#d4a853] cursor-pointer"
                            onClick={() => handlePlayItem(item)}
                          >
                            {item.cleanTitle}
                          </h5>
                          {isPlayingThis && (
                            <span className="flex h-2 w-2 relative">
                              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#d4a853] opacity-75"></span>
                              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#d4a853]"></span>
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-muted-foreground truncate">
                          {item.artist}
                        </p>
                      </div>
                    </div>

                    {/* Actions: Instant Play + Lossless Download */}
                    <div className="flex items-center gap-2 shrink-0 ml-3">
                      <button
                        onClick={() => handlePlayItem(item)}
                        className={`p-2 rounded-lg text-xs font-semibold flex items-center gap-1 transition-all ${
                          isPlayingThis
                            ? 'bg-[#d4a853] text-black font-bold'
                            : 'bg-white/10 hover:bg-white/15 text-white'
                        }`}
                      >
                        {isPlayingThis ? <Pause className="w-3.5 h-3.5 fill-current" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                        <span className="hidden sm:inline">{isPlayingThis ? '재생 중' : '재생'}</span>
                      </button>

                      <button
                        onClick={() => handleDownloadTrack(item)}
                        disabled={isDownloading || isDownloaded}
                        className={`p-2 rounded-lg text-xs font-semibold flex items-center gap-1 border transition-all ${
                          isDownloaded
                            ? 'bg-green-500/20 border-green-500/40 text-green-400'
                            : 'bg-white/5 border-white/10 hover:bg-[#d4a853]/20 hover:border-[#d4a853]/40 text-white/90 hover:text-[#d4a853]'
                        }`}
                        title="24bit 무손실 WAV로 보관함에 소장"
                      >
                        {isDownloaded ? (
                          <>
                            <Check className="w-3.5 h-3.5" />
                            <span className="hidden sm:inline">소장됨</span>
                          </>
                        ) : isDownloading ? (
                          <>
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                            <span className="hidden sm:inline">소장 중...</span>
                          </>
                        ) : (
                          <>
                            <Download className="w-3.5 h-3.5" />
                            <span className="hidden sm:inline">WAV 소장</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
