'use client';

/* ──────────────────────────────────────────────
   WaveMash — Friend Activity Feed Widget
   친구가 어떤 곡을 다운받거나 좋아요를 눌렀는지 실시간 피드 공유
   ────────────────────────────────────────────── */

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Heart, Download, Disc3, Play, Pause, User, Sparkles, RefreshCw } from 'lucide-react';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import { usePlayer } from '@/contexts/PlayerContext';
import api from '@/lib/api';

interface ActivityItem {
  id: string;
  user_id: string;
  action_type: string; // 'liked_track' | 'downloaded_track' | 'added_track'
  target_id: string;
  metadata: {
    track_id?: string;
    title?: string;
    artist?: string;
    cover_url?: string;
  };
  created_at: string;
  profiles?: {
    username: string;
    display_name: string;
    avatar_url: string;
  };
}

export default function FriendActivityFeed() {
  const { user } = useAuth();
  const { currentTrack, isPlaying, play, togglePlay } = usePlayer();
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchFeed = async () => {
    try {
      const data = await api.getActivityFeed();
      if (Array.isArray(data)) {
        setActivities(data);
      }
    } catch (err) {
      console.warn('Activity feed fetch note:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFeed();
    // 30초마다 자동 갱신
    const interval = setInterval(fetchFeed, 30000);
    return () => clearInterval(interval);
  }, []);

  const handlePlayActivityTrack = (act: ActivityItem) => {
    const trackId = act.metadata.track_id || act.target_id;
    if (!trackId) return;

    if (currentTrack?.track_id === trackId) {
      togglePlay();
      return;
    }

    const mockTrack: any = {
      track_id: trackId,
      title: act.metadata.title || 'Untitled Track',
      artist: act.metadata.artist || 'Unknown Artist',
      primary_artist: act.metadata.artist || 'Unknown Artist',
      album: 'Friend Digging Feed',
      genre: 'Digging',
      year: new Date(act.created_at).getFullYear().toString(),
      bpm: 0,
      key: '',
      camelot_key: '',
      energy_level: 0,
      platform: 'YouTube',
      url: `https://www.youtube.com/watch?v=${trackId}`,
      thumbnail_url: act.metadata.cover_url || api.getCoverUrl(trackId, 320),
      has_cover: true,
      has_file: false,
    };

    play(mockTrack);
  };

  return (
    <div className="glass rounded-2xl p-4 border border-white/10 space-y-3">
      <div className="flex items-center justify-between border-b border-white/10 pb-2.5">
        <h3 className="text-xs font-bold text-white flex items-center gap-1.5 uppercase tracking-wider">
          <Sparkles className="w-3.5 h-3.5 text-[#d4a853]" />
          친구들의 실시간 디깅 활동
        </h3>
        <button
          onClick={fetchFeed}
          className="text-muted-foreground hover:text-white transition-colors cursor-pointer"
          title="새로고침"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {loading ? (
        <div className="py-6 text-center text-xs text-muted-foreground">
          실시간 활동 불러오는 중...
        </div>
      ) : activities.length === 0 ? (
        <div className="py-6 text-center text-xs text-muted-foreground space-y-1">
          <p>아직 친구들의 최근 활동이 없습니다.</p>
          <p className="text-[11px] text-white/40">곡에 좋아요를 누르거나 다운로드해 보세요!</p>
        </div>
      ) : (
        <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1 scrollbar-thin">
          {activities.map((act) => {
            const trackId = act.metadata.track_id || act.target_id;
            const isPlayingThis = isPlaying && currentTrack?.track_id === trackId;
            const userDisplay =
              act.profiles?.display_name || act.profiles?.username || 'WAVMASH 디거';
            const username = act.profiles?.username || 'user';
            const isLiked = act.action_type === 'liked_track';
            const isDownloaded =
              act.action_type === 'downloaded_track' || act.action_type === 'added_track';

            return (
              <motion.div
                key={act.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className={`p-2.5 rounded-xl border transition-all flex items-center gap-3 ${
                  isPlayingThis
                    ? 'bg-[#d4a853]/15 border-[#d4a853]/40'
                    : 'bg-white/[0.02] border-white/5 hover:bg-white/[0.05]'
                }`}
              >
                {/* Track Thumbnail & Play Button */}
                <div
                  onClick={() => handlePlayActivityTrack(act)}
                  className="relative w-11 h-11 rounded-lg overflow-hidden bg-black/50 shrink-0 cursor-pointer group"
                >
                  <img
                    src={act.metadata.cover_url || api.getCoverUrl(trackId, 160)}
                    alt={act.metadata.title || 'Track'}
                    className="w-full h-full object-cover"
                    onError={(e: any) => {
                      e.target.src =
                        'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=300&q=80';
                    }}
                  />
                  <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                    {isPlayingThis ? (
                      <Pause className="w-4 h-4 text-[#d4a853] fill-current" />
                    ) : (
                      <Play className="w-4 h-4 text-[#d4a853] fill-current ml-0.5" />
                    )}
                  </div>
                </div>

                {/* Activity Text */}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5 text-[11px] truncate">
                    <Link
                      href={`/profile/${username}`}
                      className="font-bold text-white hover:text-[#d4a853] truncate transition-colors"
                    >
                      {userDisplay}
                    </Link>
                    <span className="text-muted-foreground/70">님이</span>
                    {isLiked ? (
                      <span className="inline-flex items-center gap-0.5 text-red-400 font-semibold shrink-0">
                        <Heart className="w-3 h-3 fill-current" /> 좋아요
                      </span>
                    ) : isDownloaded ? (
                      <span className="inline-flex items-center gap-0.5 text-[#d4a853] font-semibold shrink-0">
                        <Download className="w-3 h-3" /> 소장(다운로드)
                      </span>
                    ) : (
                      <span className="text-muted-foreground shrink-0">활동</span>
                    )}
                  </div>

                  <p
                    className="text-xs font-semibold text-white/90 truncate hover:text-[#d4a853] cursor-pointer mt-0.5"
                    onClick={() => handlePlayActivityTrack(act)}
                  >
                    {act.metadata.title || '알 수 없는 곡'}
                  </p>
                  <p className="text-[10px] text-muted-foreground truncate">
                    {act.metadata.artist || 'Unknown Artist'}
                  </p>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
