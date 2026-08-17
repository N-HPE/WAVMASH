'use client';

/* ──────────────────────────────────────────────
   WaveMash — Instagram-Style Audio Feed & Showcase
   인스타 감성의 음악 소장 및 컬렉션 자랑 피드 메인 페이지
   ────────────────────────────────────────────── */

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  Sparkles,
  Flame,
  Disc3,
  Plus,
  ArrowRight,
  TrendingUp,
  Music2,
  Compass,
} from 'lucide-react';
import api from '@/lib/api';
import type { Post, Track, LibraryStats, ChartEntry } from '@/lib/types';
import FeedStoryHighlights from '@/components/FeedStoryHighlights';
import FeedPostCard from '@/components/FeedPostCard';
import CreatePostModal from '@/components/CreatePostModal';
import NowSpinningWidget from '@/components/NowSpinningWidget';
import FriendActivityFeed from '@/components/FriendActivityFeed';
import DownloadForm from '@/components/DownloadForm';
import { Skeleton } from '@/components/ui/skeleton';


export default function FeedDashboardPage() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [stats, setStats] = useState<LibraryStats | null>(null);
  const [chart, setChart] = useState<ChartEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'feed' | 'trending'>('feed');
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedTag, setSelectedTag] = useState<string | null>(null);

  // 초기 데이터 로딩
  useEffect(() => {
    async function loadInitialData() {
      setLoading(true);
      try {
        const [postsRes, statsRes, chartRes] = await Promise.allSettled([
          api.getPosts(),
          api.getLibraryStats(),
          api.getMostCollectedChart(),
        ]);

        let fetchedPosts: Post[] = [];
        if (postsRes.status === 'fulfilled' && postsRes.value?.length > 0) {
          fetchedPosts = postsRes.value;
        }

        let loadedStats: LibraryStats | null = null;
        if (statsRes.status === 'fulfilled') {
          loadedStats = statsRes.value;
          setStats(loadedStats);
        }

        if (chartRes.status === 'fulfilled') {
          setChart(chartRes.value);
        }

        // 실제 DB에 등록된 진짜 포스트만 설정 (가짜 데이터 없음)
        setPosts(fetchedPosts);


      } catch (err) {
        console.error('Failed to load feed data:', err);
      } finally {
        setLoading(false);
      }
    }

    loadInitialData();
  }, []);

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

  // 상단 하이라이트 클릭 시 필터링
  const handleSelectHighlight = (hl: any) => {
    if (hl.id === 'trending') {
      setSelectedTag(null);
      setActiveTab('trending');
    } else {
      setSelectedTag(hl.title.replace(/^[^\w\s가-힣]+/, '').trim());
      setActiveTab('feed');
    }
  };

  const featuredTrack = stats?.recent_tracks?.[0] || posts[0]?.track || null;

  const filteredPosts = selectedTag
    ? posts.filter(
        (p) =>
          p.tags.some((t) => t.toLowerCase().includes(selectedTag.toLowerCase())) ||
          p.track?.genre?.toLowerCase().includes(selectedTag.toLowerCase())
      )
    : posts;

  return (
    <div className="mx-auto max-w-7xl px-3 sm:px-6 py-6 space-y-8">
      {/* ── 1. Instagram Story Highlights ── */}
      <section className="pt-1">
        <FeedStoryHighlights
          onOpenCreate={() => setIsCreateOpen(true)}
          onSelectHighlight={handleSelectHighlight}
          selectedId={selectedTag}
        />
      </section>

      {/* ── 2. Main 2-Column Responsive Layout ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* ── LEFT / CENTER FEED (lg: col 1-7 or 1-8) ── */}
        <main className="lg:col-span-7 xl:col-span-8 space-y-6">
          {/* Feed Controls Header */}
          <div className="flex items-center justify-between border-b border-white/10 pb-3">
            <div className="flex items-center gap-6">
              <button
                onClick={() => {
                  setActiveTab('feed');
                  setSelectedTag(null);
                }}
                className={`flex items-center gap-2 text-sm font-bold pb-1 transition-all ${
                  activeTab === 'feed' && !selectedTag
                    ? 'text-white border-b-2 border-[#d4a853]'
                    : 'text-muted-foreground hover:text-white'
                }`}
              >
                <Flame className="w-4 h-4 text-[#d4a853]" />
                디거스 피드 (Feed)
              </button>

              <button
                onClick={() => setActiveTab('trending')}
                className={`flex items-center gap-2 text-sm font-bold pb-1 transition-all ${
                  activeTab === 'trending'
                    ? 'text-white border-b-2 border-[#d4a853]'
                    : 'text-muted-foreground hover:text-white'
                }`}
              >
                <TrendingUp className="w-4 h-4 text-[#60a5fa]" />
                명예의 전당 (Top Digs)
              </button>
            </div>

            {/* Quick Share Trigger */}
            <button
              onClick={() => setIsCreateOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gradient-to-r from-[#d4a853] to-amber-400 text-black text-xs font-bold shadow-lg shadow-[#d4a853]/20 hover:opacity-90 active:scale-95 transition-all"
            >
              <Plus className="w-3.5 h-3.5" />
              자랑하기
            </button>
          </div>

          {/* Active Tag Notice */}
          {selectedTag && (
            <div className="flex items-center justify-between px-4 py-2 rounded-xl bg-[#d4a853]/10 border border-[#d4a853]/30 text-xs">
              <span className="text-[#d4a853] font-medium">
                #{selectedTag} 태그 큐레이션 피드
              </span>
              <button
                onClick={() => setSelectedTag(null)}
                className="text-muted-foreground hover:text-white"
              >
                전체 피드 보기
              </button>
            </div>
          )}

          {/* Feed Content */}
          {loading ? (
            <div className="space-y-6">
              {[...Array(3)].map((_, i) => (
                <div
                  key={i}
                  className="rounded-2xl bg-white/[0.02] border border-white/5 p-4 space-y-4 max-w-xl mx-auto"
                >
                  <div className="flex items-center gap-3">
                    <Skeleton className="w-10 h-10 rounded-full" />
                    <div className="space-y-1.5 flex-1">
                      <Skeleton className="w-24 h-4" />
                      <Skeleton className="w-16 h-3" />
                    </div>
                  </div>
                  <Skeleton className="w-full aspect-square rounded-xl" />
                  <Skeleton className="w-3/4 h-4" />
                </div>
              ))}
            </div>
          ) : activeTab === 'feed' ? (
            filteredPosts.length > 0 ? (
              <div className="space-y-8">
                {filteredPosts.map((post) => (
                  <FeedPostCard
                    key={post.id}
                    post={post}
                    onDelete={handleDeletePost}
                  />
                ))}
              </div>
            ) : (
              <div className="glass rounded-2xl p-12 text-center max-w-xl mx-auto space-y-4">
                <Disc3 className="w-12 h-12 text-muted-foreground mx-auto animate-spin" style={{ animationDuration: '8s' }} />
                <h3 className="font-bold text-white text-base">아직 등록된 소장곡 피드가 없습니다</h3>
                <p className="text-xs text-muted-foreground">
                  내가 소장한 명곡을 첫 번째로 피드에 자랑해보세요!
                </p>
                <button
                  onClick={() => setIsCreateOpen(true)}
                  className="px-5 py-2 rounded-xl bg-[#d4a853] text-black font-semibold text-xs shadow-lg"
                >
                  첫 포스트 작성하기
                </button>
              </div>
            )
          ) : (
            /* Trending Chart View */
            <div className="space-y-4 max-w-xl mx-auto">
              <h3 className="text-sm font-semibold text-white/80 mb-3 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-[#d4a853]" />
                가장 많은 디거들이 소장한 트랙 (Most Collected)
              </h3>
              {(chart.length > 0 ? chart : (stats?.recent_tracks || []).slice(0, 10)).map((item: any, idx) => (
                <div
                  key={item.track_id}
                  className="glass flex items-center justify-between p-3 rounded-xl hover:border-[#d4a853]/40 transition-all group"
                >
                  <div className="flex items-center gap-4">
                    <span className="font-mono text-base font-black text-white/40 group-hover:text-[#d4a853] w-6 text-center">
                      {idx + 1}
                    </span>
                    <div className="w-12 h-12 rounded-lg bg-black/40 overflow-hidden border border-white/10 shrink-0">
                      <img
                        src={api.getCoverUrl(item.track_id, 120)}
                        alt={item.title}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <div>
                      <Link href={`/track/${item.track_id}`}>
                        <h4 className="text-sm font-bold text-white truncate max-w-[200px] sm:max-w-[280px] group-hover:text-[#d4a853] transition-colors">
                          {item.title}
                        </h4>
                      </Link>
                      <p className="text-xs text-muted-foreground truncate">{item.artist}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-mono text-[#d4a853] font-semibold block">
                      {item.collector_count || 10 + idx * 3} Digs
                    </span>
                    <span className="text-[10px] text-muted-foreground">소장자</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </main>

        {/* ── RIGHT SIDEBAR (lg: col 8-12) ── */}
        <aside className="lg:col-span-5 xl:col-span-4 space-y-6">
          {/* 1. Real-time Friend Activity Feed */}
          <FriendActivityFeed />

          {/* 2. Now Spinning Turntable Deck */}
          <NowSpinningWidget track={featuredTrack} collectorName="KYO" />

          {/* 3. Quick Download & Archive Form */}
          <div className="glass rounded-2xl p-5 border border-white/10 space-y-3">

            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2">
                <Music2 className="w-4 h-4 text-[#d4a853]" />
                빠른 음원 소장 (Download)
              </h3>
              <span className="text-[10px] text-muted-foreground font-mono">WAV/Lossless</span>
            </div>
            <DownloadForm />
          </div>

          {/* 3. Genre Exploration Tags */}
          {stats && Object.keys(stats.genres).length > 0 && (
            <div className="glass rounded-2xl p-5 border border-white/10 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2">
                  <Compass className="w-4 h-4 text-[#d4a853]" />
                  장르별 디깅 (Genres)
                </h3>
                <Link
                  href="/library"
                  className="text-[10px] text-muted-foreground hover:text-[#d4a853] flex items-center gap-0.5"
                >
                  전체
                  <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(stats.genres)
                  .sort(([, a], [, b]) => b - a)
                  .slice(0, 10)
                  .map(([genre, count]) => (
                    <Link key={genre} href={`/library?genre=${encodeURIComponent(genre)}`}>
                      <span className="text-xs px-3 py-1 rounded-full bg-white/5 hover:bg-[#d4a853]/20 border border-white/10 hover:border-[#d4a853]/40 text-white/80 hover:text-[#d4a853] transition-all inline-flex items-center gap-1.5">
                        {genre}
                        <span className="text-[10px] opacity-40 font-mono">{count}</span>
                      </span>
                    </Link>
                  ))}
              </div>
            </div>
          )}
        </aside>
      </div>

      {/* ── Create Post Modal ── */}
      <CreatePostModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onPostCreated={handlePostCreated}
      />
    </div>
  );
}
