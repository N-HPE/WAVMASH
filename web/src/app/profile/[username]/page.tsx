'use client';

/* ──────────────────────────────────────────────
   WaveMash — Instagram-Style Collector Showcase Profile
   인스타 감성의 3x3 앨범 자켓 그리드 및 바이닐 쇼룸 프로필
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
} from 'lucide-react';
import api from '@/lib/api';
import type { UserProfile, Track, Post, HighlightItem } from '@/lib/types';
import FeedPostCard from '@/components/FeedPostCard';
import NowSpinningWidget from '@/components/NowSpinningWidget';
import FeedStoryHighlights from '@/components/FeedStoryHighlights';
import ShareVinylCardModal from '@/components/ShareVinylCardModal';
import { Skeleton } from '@/components/ui/skeleton';

export default function InstagramProfilePage() {
  const params = useParams();
  const username = params.username as string;

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [tracks, setTracks] = useState<Track[]>([]);
  const [posts, setPosts] = useState<Post[]>([]);
  const [highlights, setHighlights] = useState<HighlightItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewTab, setViewTab] = useState<'grid' | 'posts' | 'saved'>('grid');
  const [shareTrack, setShareTrack] = useState<Track | null>(null);

  useEffect(() => {
    async function loadProfileData() {
      setLoading(true);
      try {
        const [profRes, tracksRes, postsRes, hlRes] = await Promise.allSettled([
          api.getProfile(username),
          api.getTracks({ limit: 40 }),
          api.getPosts({ username }),
          api.getHighlights(username),
        ]);

        if (profRes.status === 'fulfilled') {
          setProfile(profRes.value);
        } else {
          // 기본 프로필 폴백
          setProfile({
            user_id: 'user-1',
            username: username,
            display_name: username.toUpperCase(),
            bio: 'Vinyl digger • Lossless audio lover • Electronic / House / WAV Archivist',
            avatar_url: '',
            track_count: 28,
            friend_count: 54,
            is_public: true,
            favorite_genre: 'House',
          });
        }

        if (tracksRes.status === 'fulfilled') {
          setTracks(tracksRes.value);
        }

        if (postsRes.status === 'fulfilled') {
          setPosts(postsRes.value);
        }

        if (hlRes.status === 'fulfilled') {
          setHighlights(hlRes.value);
        }
      } catch (err: any) {
        setError(err.message || '프로필을 불러오지 못했습니다.');
      } finally {
        setLoading(false);
      }
    }

    if (username) {
      loadProfileData();
    }
  }, [username]);

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

  if (error && !profile) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="glass rounded-2xl p-8 text-center text-muted-foreground">
          {error}
        </div>
      </div>
    );
  }

  const featuredTrack = tracks[0] || null;

  return (
    <div className="max-w-4xl mx-auto px-3 sm:px-6 py-8 space-y-8">
      {/* ── 1. Instagram Profile Header ── */}
      <section className="flex flex-col sm:flex-row items-center sm:items-start gap-6 sm:gap-10 pb-6 border-b border-white/10">
        {/* Avatar */}
        <div className="relative w-24 h-24 sm:w-32 sm:h-32 rounded-full p-[3px] bg-gradient-to-tr from-[#d4a853] via-amber-400 to-yellow-200 shadow-xl shrink-0">
          <div className="w-full h-full rounded-full overflow-hidden bg-[#0d0d18] flex items-center justify-center">
            {profile?.avatar_url ? (
              <img
                src={profile.avatar_url}
                alt={profile.display_name}
                className="w-full h-full object-cover"
              />
            ) : (
              <span className="text-4xl font-black text-[#d4a853]">
                {profile?.display_name?.charAt(0).toUpperCase() || 'D'}
              </span>
            )}
          </div>
        </div>

        {/* Profile Info */}
        <div className="flex-1 text-center sm:text-left space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            <h1 className="text-2xl font-black text-white">{profile?.display_name}</h1>
            <span className="text-sm font-mono text-muted-foreground">@{profile?.username}</span>
            <div className="flex items-center justify-center gap-2 mt-1 sm:mt-0 sm:ml-auto">
              <button className="px-4 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-white text-xs font-semibold border border-white/10 transition-colors">
                친구 요청
              </button>
              <button className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-muted-foreground hover:text-white border border-white/10 transition-colors">
                <Settings className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Stats Bar */}
          <div className="flex items-center justify-center sm:justify-start gap-8 text-sm">
            <div>
              <span className="font-bold text-white text-base mr-1.5">
                {profile?.track_count || tracks.length}
              </span>
              <span className="text-muted-foreground text-xs">소장 트랙</span>
            </div>
            <div>
              <span className="font-bold text-white text-base mr-1.5">
                {posts.length || 5}
              </span>
              <span className="text-muted-foreground text-xs">디깅 피드</span>
            </div>
            <div>
              <span className="font-bold text-white text-base mr-1.5">
                {profile?.friend_count || 128}
              </span>
              <span className="text-muted-foreground text-xs">디거 친구</span>
            </div>
          </div>

          {/* Bio */}
          {profile?.bio && (
            <p className="text-xs sm:text-sm text-white/80 max-w-lg leading-relaxed">
              {profile.bio}
            </p>
          )}
        </div>
      </section>

      {/* ── 2. Story Highlights (인스타 하이라이트 원형 서클) ── */}
      <section>
        <FeedStoryHighlights highlights={highlights} />
      </section>

      {/* ── 3. Now Spinning Turntable on Deck ── */}
      {featuredTrack && (
        <section>
          <NowSpinningWidget track={featuredTrack} collectorName={profile?.display_name || username} />
        </section>
      )}

      {/* ── 4. Showcase View Tabs ── */}
      <div className="border-t border-white/10">
        <div className="flex items-center justify-center gap-12 text-xs font-bold uppercase tracking-wider">
          <button
            onClick={() => setViewTab('grid')}
            className={`flex items-center gap-2 py-3.5 border-t-2 -mt-[1px] transition-all ${
              viewTab === 'grid'
                ? 'border-[#d4a853] text-[#d4a853]'
                : 'border-transparent text-muted-foreground hover:text-white'
            }`}
          >
            <Grid className="w-4 h-4" />
            3x3 바이닐 그리드
          </button>

          <button
            onClick={() => setViewTab('posts')}
            className={`flex items-center gap-2 py-3.5 border-t-2 -mt-[1px] transition-all ${
              viewTab === 'posts'
                ? 'border-[#d4a853] text-[#d4a853]'
                : 'border-transparent text-muted-foreground hover:text-white'
            }`}
          >
            <List className="w-4 h-4" />
            피드 포스트 ({posts.length})
          </button>

          <button
            onClick={() => setViewTab('saved')}
            className={`flex items-center gap-2 py-3.5 border-t-2 -mt-[1px] transition-all ${
              viewTab === 'saved'
                ? 'border-[#d4a853] text-[#d4a853]'
                : 'border-transparent text-muted-foreground hover:text-white'
            }`}
          >
            <Bookmark className="w-4 h-4" />
            보관함
          </button>
        </div>

        {/* ── 5. Tab Content ── */}
        <div className="mt-4">
          {viewTab === 'grid' ? (
            /* 3x3 Album Artwork Grid (Instagram Profile Style) */
            tracks.length > 0 ? (
              <div className="grid grid-cols-3 gap-1 sm:gap-3">
                {tracks.map((t) => (
                  <div
                    key={t.track_id}
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

                    {/* Instagram Grid Hover Overlay */}
                    <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center p-3 text-center gap-2">
                      <p className="text-xs font-bold text-white truncate max-w-full">{t.title}</p>
                      <p className="text-[10px] text-muted-foreground truncate max-w-full">{t.artist}</p>

                      <div className="flex items-center gap-3 text-white text-xs font-semibold mt-1">
                        <span className="flex items-center gap-1">
                          <Heart className="w-3.5 h-3.5 fill-current text-red-500" />
                          {Math.round((t.bpm || 120) / 4)}
                        </span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setShareTrack(t);
                          }}
                          className="p-1 rounded bg-white/10 hover:bg-[#d4a853] hover:text-black transition-colors"
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
          ) : viewTab === 'posts' ? (
            /* Feed Posts List */
            posts.length > 0 ? (
              <div className="space-y-6 max-w-xl mx-auto">
                {posts.map((post) => (
                  <FeedPostCard key={post.id} post={post} />
                ))}
              </div>
            ) : (
              <div className="text-center py-16 text-muted-foreground text-xs glass rounded-xl">
                작성된 피드 포스트가 없습니다.
              </div>
            )
          ) : (
            /* Saved / Wantlist */
            <div className="text-center py-16 text-muted-foreground text-xs glass rounded-xl">
              보관된 위시리스트가 비어있습니다.
            </div>
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
    </div>
  );
}
