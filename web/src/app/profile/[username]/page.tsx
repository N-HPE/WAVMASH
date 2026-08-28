'use client';

/* ──────────────────────────────────────────────
   WaveMash — Private Music Diary & Visual Album Showcase Profile
   나만의 감성 사진 + 음악 다이어리 & 바이닐 앨범 쇼룸
   ────────────────────────────────────────────── */

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  Grid,
  List,
  Disc3,
  Heart,
  Bookmark,
  Share2,
  Settings,
  Plus,
  Play,
  Pause,
  Download,
  Music,
  Lock,
  Globe,
  BookOpen,
  Image as ImageIcon,
} from 'lucide-react';
import api from '@/lib/api';
import { usePlayer } from '@/contexts/PlayerContext';
import { useAuth } from '@/contexts/AuthContext';
import { isOwnProfileSegment } from '@/lib/profile';
import type { UserProfile, Track, Post, HighlightItem } from '@/lib/types';
import FeedPostCard from '@/components/FeedPostCard';
import NowSpinningWidget from '@/components/NowSpinningWidget';
import FeedStoryHighlights from '@/components/FeedStoryHighlights';
import ShareVinylCardModal from '@/components/ShareVinylCardModal';
import CreatePostModal from '@/components/CreatePostModal';
import { Skeleton } from '@/components/ui/skeleton';

export default function InstagramProfilePage() {
  const params = useParams();
  const username = params.username as string;
  const { user: currentUser, profile: authProfile } = useAuth();
  const { currentTrack, isPlaying, play, togglePlay } = usePlayer();

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [tracks, setTracks] = useState<Track[]>([]);
  const [likedTracks, setLikedTracks] = useState<any[]>([]);
  const [downloadedTracks, setDownloadedTracks] = useState<any[]>([]);
  const [posts, setPosts] = useState<Post[]>([]);
  const [highlights, setHighlights] = useState<HighlightItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewTab, setViewTab] = useState<'diary' | 'grid' | 'likes'>('diary');
  const [shareTrack, setShareTrack] = useState<Track | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const isMyProfile = isOwnProfileSegment(username, currentUser, authProfile);

  useEffect(() => {
    async function loadProfileData() {
      if (!username) return;
      setLoading(true);
      setError(null);

      try {
        let prof: UserProfile | null = null;

        if (isMyProfile && currentUser) {
          try {
            prof = await api.getMyProfile();
          } catch {
            if (authProfile) prof = authProfile;
          }
        } else {
          try {
            prof = await api.getProfile(username);
          } catch {
            prof = null;
          }
        }

        if (!prof && authProfile && (username === authProfile.username || isMyProfile)) {
          prof = authProfile;
        }

        if (!prof) {
          setError('프로필을 찾을 수 없습니다.');
          setProfile(null);
          setLoading(false);
          return;
        }

        setProfile(prof);
        const lookupKey = prof.username || username;

        const [tracksRes, postsRes, hlRes, likesRes, dlRes] = await Promise.allSettled([
          api.getTracks({ limit: 40 }),
          api.getPosts({ username: lookupKey }),
          api.getHighlights(lookupKey),
          api.getUserLikedTracks(lookupKey),
          api.getUserDownloadedTracks(lookupKey),
        ]);

        if (tracksRes.status === 'fulfilled') setTracks(tracksRes.value);
        if (postsRes.status === 'fulfilled') setPosts(postsRes.value);
        if (hlRes.status === 'fulfilled') setHighlights(hlRes.value);
        if (likesRes.status === 'fulfilled') setLikedTracks(likesRes.value);
        if (dlRes.status === 'fulfilled') setDownloadedTracks(dlRes.value);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : '프로필을 불러오지 못했습니다.';
        setError(message);
      } finally {
        setLoading(false);
      }
    }

    loadProfileData();
  }, [username, isMyProfile, currentUser, authProfile]);

  const handlePlayTrack = (trackId: string, title?: string, artist?: string, coverUrl?: string) => {
    if (currentTrack?.track_id === trackId) {
      togglePlay();
      return;
    }

    const name = profile?.username || username;
    const mockTrack: any = {
      track_id: trackId,
      title: title || 'Curated Track',
      artist: artist || name,
      primary_artist: artist || name,
      album: `${name}'s Collection`,
      genre: 'Digging',
      year: new Date().getFullYear().toString(),
      bpm: 0,
      key: '',
      camelot_key: '',
      energy_level: 0,
      platform: 'YouTube',
      url: `https://www.youtube.com/watch?v=${trackId}`,
      thumbnail_url: coverUrl || api.getCoverUrl(trackId, 320),
      has_cover: true,
      has_file: false,
    };

    play(mockTrack);
  };

  const handlePostCreated = (newPost: Post) => {
    setPosts((prev) => [newPost, ...prev]);
  };

  const handleDeletePost = async (postId: string) => {
    try {
      await api.deletePost(postId);
      setPosts((prev) => prev.filter((p) => p.id !== postId));
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
        <div className="flex items-center gap-6">
          <Skeleton className="w-28 h-28 rounded-full" />
          <div className="space-y-3 flex-1">
            <Skeleton className="w-48 h-6" />
            <Skeleton className="w-32 h-4" />
            <Skeleton className="w-64 h-4" />
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="aspect-square rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="max-w-lg mx-auto px-4 py-16 text-center space-y-4">
        <p className="text-sm text-muted-foreground">{error || '프로필을 불러올 수 없습니다.'}</p>
        <Link
          href="/"
          className="inline-block text-sm text-[#d4a853] hover:underline"
        >
          홈으로 돌아가기
        </Link>
      </div>
    );
  }

  const displayUsername = profile.username;
  const featuredTrack = tracks[0] || posts[0]?.track || null;

  return (
    <div className="max-w-4xl mx-auto px-3 sm:px-6 py-6 space-y-8">
      {/* ── 1. Profile Header ── */}
      <section className="glass rounded-3xl p-6 sm:p-8 border border-white/10 relative overflow-hidden">
        <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6 relative z-10">
          {/* Avatar with Vinyl Ring */}
          <div className="relative">
            <div className="w-24 h-24 sm:w-28 sm:h-28 rounded-full border-2 border-[#d4a853] p-1 shadow-xl bg-black">
              {profile?.avatar_url ? (
                <img
                  src={profile.avatar_url}
                  alt={profile.display_name}
                  className="w-full h-full rounded-full object-cover"
                />
              ) : (
                <div className="w-full h-full rounded-full bg-gradient-to-tr from-[#1a1a2e] to-[#0e0e1a] flex items-center justify-center text-xl font-bold text-[#d4a853]">
                  {profile?.username?.slice(0, 2).toUpperCase() || 'WM'}
                </div>
              )}
            </div>
            <span className="absolute bottom-0 right-0 p-1.5 rounded-full bg-[#d4a853] text-black shadow-lg">
              <Disc3 className="w-3.5 h-3.5 animate-spin" style={{ animationDuration: '6s' }} />
            </span>
          </div>

          {/* User Bio & Meta Stats */}
          <div className="flex-1 text-center sm:text-left space-y-3 min-w-0">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h1 className="text-xl sm:text-2xl font-black text-white flex items-center justify-center sm:justify-start gap-2">
                  {profile?.display_name || profile?.username}
                  <span className="text-xs font-mono font-normal px-2 py-0.5 rounded-full bg-[#d4a853]/15 text-[#d4a853] border border-[#d4a853]/30">
                    DIARY ARCHIVE
                  </span>
                </h1>
                <p className="text-xs font-mono text-muted-foreground mt-0.5">
                  @{profile?.username}
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-center gap-2">
                <button
                  onClick={() => setIsCreateOpen(true)}
                  className="px-4 py-1.5 rounded-xl bg-[#d4a853] hover:bg-amber-400 text-black font-bold text-xs transition-colors flex items-center gap-1.5 shadow-lg shadow-[#d4a853]/20 cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  기록 추가
                </button>
                <button className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-white/70 hover:text-white transition-colors border border-white/10">
                  <Settings className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Numbers Strip (Diary Records, Tracks, Likes) */}
            <div className="flex items-center justify-center sm:justify-start gap-6 text-xs py-1">
              <div>
                <strong className="text-[#d4a853] font-bold text-sm block">
                  {posts.length}
                </strong>
                <span className="text-muted-foreground text-[11px]">음악 다이어리</span>
              </div>
              <div>
                <strong className="text-white font-bold text-sm block">
                  {tracks.length}
                </strong>
                <span className="text-muted-foreground text-[11px]">소장 바이닐</span>
              </div>
              <div>
                <strong className="text-red-400 font-bold text-sm block">
                  {likedTracks.length}
                </strong>
                <span className="text-muted-foreground text-[11px]">좋아요</span>
              </div>
            </div>

            <p className="text-xs text-white/80 leading-relaxed max-w-lg">
              {profile?.bio || '사진과 음악을 조합하여 나만의 감성 다이어리와 앨범을 만들어가는 공간입니다.'}
            </p>
          </div>
        </div>
      </section>

      {/* ── 2. Story Highlights ── */}
      <section>
        <FeedStoryHighlights highlights={highlights} />
      </section>

      {/* ── 3. Now Spinning Turntable on Deck ── */}
      {featuredTrack && (
        <section>
          <NowSpinningWidget track={featuredTrack} collectorName={profile?.display_name || displayUsername} />
        </section>
      )}

      {/* ── 4. Showcase View Tabs ── */}
      <div className="border-t border-white/10">
        <div className="flex items-center justify-center gap-6 sm:gap-12 text-xs font-bold uppercase tracking-wider">
          <button
            onClick={() => setViewTab('diary')}
            className={`flex items-center gap-1.5 py-3.5 border-t-2 -mt-[1px] transition-all cursor-pointer ${
              viewTab === 'diary'
                ? 'border-[#d4a853] text-[#d4a853]'
                : 'border-transparent text-muted-foreground hover:text-white'
            }`}
          >
            <BookOpen className="w-4 h-4" />
            뮤직 다이어리 & 앨범 ({posts.length})
          </button>

          <button
            onClick={() => setViewTab('grid')}
            className={`flex items-center gap-1.5 py-3.5 border-t-2 -mt-[1px] transition-all cursor-pointer ${
              viewTab === 'grid'
                ? 'border-[#d4a853] text-[#d4a853]'
                : 'border-transparent text-muted-foreground hover:text-white'
            }`}
          >
            <Grid className="w-4 h-4" />
            소장 바이닐 ({tracks.length})
          </button>

          <button
            onClick={() => setViewTab('likes')}
            className={`flex items-center gap-1.5 py-3.5 border-t-2 -mt-[1px] transition-all cursor-pointer ${
              viewTab === 'likes'
                ? 'border-red-500 text-red-400'
                : 'border-transparent text-muted-foreground hover:text-white'
            }`}
          >
            <Heart className="w-4 h-4" />
            좋아요 ({likedTracks.length})
          </button>
        </div>

        {/* ── 5. Tab Content ── */}
        <div className="mt-4">
          {viewTab === 'diary' ? (
            /* Music Diary Posts List */
            posts.length > 0 ? (
              <div className="space-y-6 max-w-xl mx-auto">
                {posts.map((post) => (
                  <FeedPostCard
                    key={post.id}
                    post={post}
                    currentUserId={currentUser?.id}
                    onDelete={handleDeletePost}
                  />
                ))}
              </div>
            ) : (
              <div className="text-center py-16 text-muted-foreground text-xs glass rounded-2xl space-y-3 max-w-xl mx-auto">
                <BookOpen className="w-10 h-10 text-[#d4a853]/60 mx-auto" />
                <h4 className="text-white font-bold text-sm">아직 기록된 음악 다이어리가 없습니다</h4>
                <p className="text-[11px] text-muted-foreground">
                  어울리는 사진과 음악을 골라 나만의 첫 번째 뮤직 다이어리를 남겨보세요.
                </p>
                <button
                  onClick={() => setIsCreateOpen(true)}
                  className="px-4 py-2 rounded-xl bg-[#d4a853] text-black font-semibold text-xs inline-flex items-center gap-1.5"
                >
                  <Plus className="w-3.5 h-3.5" /> 다이어리 작성하기
                </button>
              </div>
            )
          ) : viewTab === 'grid' ? (
            /* 3x3 Vinyl Album Art Grid */
            tracks.length > 0 ? (
              <div className="grid grid-cols-3 gap-1 sm:gap-3">
                {tracks.map((t) => (
                  <div
                    key={t.track_id}
                    onClick={() => handlePlayTrack(t.track_id, t.title, t.artist, api.getCoverUrl(t.track_id, 320))}
                    className="relative aspect-square rounded-lg overflow-hidden bg-[#111122] group cursor-pointer border border-white/5"
                  >
                    {t.has_cover ? (
                      <img
                        src={api.getCoverUrl(t.track_id, 320)}
                        alt={t.title}
                        className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center bg-white/5">
                        <Disc3 className="w-10 h-10 text-white/20" />
                      </div>
                    )}

                    {/* Hover Overlay */}
                    <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center p-3 text-center gap-2">
                      <p className="text-xs font-bold text-white truncate max-w-full">{t.title}</p>
                      <p className="text-[10px] text-muted-foreground truncate max-w-full">{t.artist}</p>

                      <div className="flex items-center gap-3 text-white text-xs font-semibold mt-1">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setShareTrack(t);
                          }}
                          className="p-1.5 rounded-full bg-white/10 hover:bg-[#d4a853] hover:text-black transition-colors"
                          title="스토리 카드 생성"
                        >
                          <Share2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-16 text-muted-foreground text-xs glass rounded-xl">
                소장된 트랙이 없습니다.
              </div>
            )
          ) : (
            /* Liked Tracks List */
            likedTracks.length > 0 ? (
              <div className="space-y-2 max-w-2xl mx-auto">
                {likedTracks.map((item: any) => {
                  const trackId = item.track_id;
                  const isPlayingThis = isPlaying && currentTrack?.track_id === trackId;

                  return (
                    <div
                      key={item.track_id || item.created_at}
                      className={`flex items-center justify-between p-3 rounded-xl border transition-all ${
                        isPlayingThis
                          ? 'bg-[#d4a853]/15 border-[#d4a853]/40'
                          : 'glass border-white/5 hover:bg-white/[0.04]'
                      }`}
                    >
                      <div className="flex items-center gap-3 min-w-0 flex-1">
                        <div
                          onClick={() => handlePlayTrack(trackId)}
                          className="relative w-12 h-12 rounded-lg overflow-hidden bg-black/50 shrink-0 cursor-pointer group"
                        >
                          <img
                            src={api.getCoverUrl(trackId, 160)}
                            alt="Cover"
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

                        <div className="min-w-0 flex-1">
                          <h5
                            className="text-xs font-bold text-white truncate hover:text-[#d4a853] cursor-pointer"
                            onClick={() => handlePlayTrack(trackId)}
                          >
                            트랙 ID: {trackId}
                          </h5>
                          <span className="text-[10px] text-red-400 font-semibold flex items-center gap-1 mt-0.5">
                            <Heart className="w-3 h-3 fill-current" /> WM에서 좋아요 표시함
                          </span>
                        </div>
                      </div>

                      <button
                        onClick={() => handlePlayTrack(trackId)}
                        className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
                      >
                        {isPlayingThis ? <Pause className="w-3.5 h-3.5 fill-current" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                        <span>{isPlayingThis ? '재생 중' : '듣기'}</span>
                      </button>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-16 text-muted-foreground text-xs glass rounded-xl">
                아직 좋아요를 누른 트랙이 없습니다.
              </div>
            )
          )}
        </div>
      </div>

      {/* Share Vinyl Card Modal */}
      {shareTrack && (
        <ShareVinylCardModal
          isOpen={!!shareTrack}
          onClose={() => setShareTrack(null)}
          track={shareTrack}
          user={profile}
        />
      )}

      {/* Create Diary / Album Modal */}
      <CreatePostModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onPostCreated={handlePostCreated}
      />
    </div>
  );
}
