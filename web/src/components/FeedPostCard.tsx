'use client';

/* ──────────────────────────────────────────────
   WaveMash — Instagram-Style Feed Post Card
   앨범 자켓, 바이닐 인터랙션, Digger's Note, 오디오 프리뷰, 댓글/좋아요
   ────────────────────────────────────────────── */

import React, { useState, useRef } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Heart,
  MessageCircle,
  Share2,
  Bookmark,
  Play,
  Pause,
  MoreHorizontal,
  Disc3,
  Send,
  Trash2,
  ExternalLink,
} from 'lucide-react';
import type { Post, PostComment } from '@/lib/types';
import api from '@/lib/api';
import { useCoverGlow } from '@/lib/coverColors';
import { usePlayer } from '@/contexts/PlayerContext';
import ShareVinylCardModal from './ShareVinylCardModal';

interface FeedPostCardProps {
  post: Post;
  currentUserId?: string;
  onDelete?: (postId: string) => void;
  onLikeToggle?: (postId: string, liked: boolean) => void;
}

export default function FeedPostCard({
  post,
  currentUserId,
  onDelete,
  onLikeToggle,
}: FeedPostCardProps) {
  const track = post.track;
  const user = post.user;
  const { currentTrack, isPlaying: globalPlaying, play, togglePlay: globalTogglePlay } = usePlayer();

  const isCurrentTrackPlaying = globalPlaying && currentTrack?.track_id === track?.track_id;

  const [isLiked, setIsLiked] = useState(post.is_liked || false);
  const [likesCount, setLikesCount] = useState(post.likes_count || 0);
  const [isCollected, setIsCollected] = useState(false);
  const [showComments, setShowComments] = useState(false);
  const [comments, setComments] = useState<PostComment[]>([]);
  const [newComment, setNewComment] = useState('');
  const [loadingComments, setLoadingComments] = useState(false);
  const [showShareModal, setShowShareModal] = useState(false);
  const [showMenu, setShowMenu] = useState(false);

  const coverUrl = track ? api.getCoverUrl(track.track_id, 600) : '';
  const glowColor = useCoverGlow(
    track?.track_id || '',
    track?.has_cover || false,
    track?.dominant_color
  );

  // 좋아요 토글 핸들러
  const handleLike = async () => {
    const nextLiked = !isLiked;
    setIsLiked(nextLiked);
    setLikesCount((prev) => (nextLiked ? prev + 1 : Math.max(prev - 1, 0)));

    try {
      const res = await api.togglePostLike(post.id);
      setLikesCount(res.likes_count);
      setIsLiked(res.liked);
      onLikeToggle?.(post.id, res.liked);
    } catch {
      // 롤백
      setIsLiked(!nextLiked);
      setLikesCount((prev) => (!nextLiked ? prev + 1 : Math.max(prev - 1, 0)));
    }
  };

  // 컬렉션 담기 핸들러
  const handleCollect = async () => {
    if (!track) return;
    setIsCollected(!isCollected);
    try {
      if (!isCollected) {
        await api.collectTrack(track.track_id);
      } else {
        await api.uncollectTrack(track.track_id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // 앨범 커버 클릭 시 통합 플레이어로 자동 재생
  const handleCoverClick = () => {
    if (!track) return;
    if (currentTrack?.track_id === track.track_id) {
      globalTogglePlay();
    } else {
      play(track);
    }
  };


  // 댓글 목록 조회
  const toggleCommentSection = async () => {
    const next = !showComments;
    setShowComments(next);
    if (next && comments.length === 0) {
      setLoadingComments(true);
      try {
        const list = await api.getPostComments(post.id);
        setComments(list);
      } catch (err) {
        console.error(err);
      } finally {
        setLoadingComments(false);
      }
    }
  };

  // 댓글 작성
  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newComment.trim()) return;

    const text = newComment.trim();
    setNewComment('');

    try {
      const comment = await api.addPostComment(post.id, text);
      setComments((prev) => [...prev, comment]);
    } catch (err) {
      console.error(err);
    }
  };

  if (!track) return null;

  const isOwner = currentUserId && post.user_id === currentUserId;

  return (
    <>
      <article className="w-full max-w-xl mx-auto rounded-2xl bg-[#0f111e]/90 border border-white/[0.08] shadow-2xl overflow-hidden mb-8 backdrop-blur-xl transition-all duration-300 hover:border-white/15">
        {/* ── 1. Post Header ── */}
        <div className="flex items-center justify-between px-4 py-3.5 border-b border-white/[0.06]">
          <Link
            href={`/profile/${user?.username || 'unknown'}`}
            className="flex items-center gap-3 group"
          >
            <div className="relative w-10 h-10 rounded-full p-[1.5px] bg-gradient-to-tr from-[#d4a853] to-amber-300">
              <div className="w-full h-full rounded-full overflow-hidden bg-black/60 flex items-center justify-center">
                {user?.avatar_url ? (
                  <img
                    src={user.avatar_url}
                    alt={user.display_name || user.username}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <span className="text-sm font-bold text-[#d4a853]">
                    {(user?.display_name || user?.username || 'D').charAt(0).toUpperCase()}
                  </span>
                )}
              </div>
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-semibold text-white group-hover:text-[#d4a853] transition-colors">
                  {user?.display_name || user?.username || 'Collector'}
                </span>
                <span className="text-xs text-muted-foreground">@{user?.username || 'digger'}</span>
              </div>
              <span className="text-[10px] text-muted-foreground block">
                {new Date(post.created_at).toLocaleDateString('ko-KR', {
                  month: 'short',
                  day: 'numeric',
                })}
              </span>
            </div>
          </Link>

          {/* Right Menu */}
          <div className="relative">
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="p-1.5 rounded-full hover:bg-white/10 text-muted-foreground hover:text-white transition-colors"
            >
              <MoreHorizontal className="w-5 h-5" />
            </button>

            {showMenu && (
              <div className="absolute right-0 top-8 z-30 w-44 rounded-xl bg-[#181829] border border-white/10 shadow-2xl py-1 text-xs backdrop-blur-xl">
                <button
                  onClick={() => {
                    setShowShareModal(true);
                    setShowMenu(false);
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-white hover:bg-white/10 text-left"
                >
                  <Share2 className="w-4 h-4 text-[#d4a853]" />
                  인스타 스토리 카드 생성
                </button>
                <Link
                  href={`/track/${track.track_id}`}
                  className="w-full flex items-center gap-2 px-3 py-2 text-white hover:bg-white/10 text-left"
                >
                  <ExternalLink className="w-4 h-4" />
                  트랙 상세 보기
                </Link>
                {isOwner && (
                  <button
                    onClick={() => {
                      onDelete?.(post.id);
                      setShowMenu(false);
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-red-400 hover:bg-red-500/10 text-left"
                  >
                    <Trash2 className="w-4 h-4" />
                    포스트 삭제
                  </button>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ── 2. Vinyl & Cover Showcase (Visual + Audio) ── */}
        <div
          className="relative aspect-square w-full overflow-hidden bg-[#080811] flex items-center justify-center group cursor-pointer"
          style={{ '--glow-color': glowColor } as React.CSSProperties}
          onClick={handleCoverClick}
        >
          {/* Ambient Glow */}
          <div
            className="absolute inset-0 opacity-40 blur-3xl transition-opacity duration-700 pointer-events-none"
            style={{ backgroundColor: glowColor }}
          />

          {/* Vinyl Disc Slipout */}
          <div
            className={`absolute z-10 w-4/5 h-4/5 rounded-full bg-black border-4 border-[#222] shadow-2xl flex items-center justify-center transition-all duration-700 ${
              isCurrentTrackPlaying
                ? 'right-4 rotate-180 animate-spin'
                : 'right-10 group-hover:right-6'
            }`}
            style={{ animationDuration: '4s' }}
          >
            <div className="w-28 h-28 rounded-full border border-white/20 bg-gradient-to-tr from-[#2a1b0a] to-[#d4a853]/40 flex items-center justify-center">
              <div className="w-8 h-8 rounded-full bg-black border border-white/20" />
            </div>
          </div>

          {/* Album Cover Art */}
          <div className="relative z-20 w-4/5 h-4/5 rounded-2xl overflow-hidden shadow-2xl border border-white/15 bg-[#141424]">
            {track.has_cover ? (
              <img
                src={coverUrl}
                alt={track.title}
                className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                loading="lazy"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center bg-white/5">
                <Disc3 className="w-20 h-20 text-white/20" />
              </div>
            )}

            {/* Center Play Overlay */}
            <div className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity">
              <div className="w-14 h-14 rounded-full bg-[#d4a853] text-black flex items-center justify-center shadow-xl transform group-hover:scale-110 transition-transform">
                {isCurrentTrackPlaying ? (
                  <Pause className="w-6 h-6 fill-current" />
                ) : (
                  <Play className="w-6 h-6 fill-current ml-1" />
                )}
              </div>
            </div>

            {/* Corner Badges */}
            <div className="absolute top-3 left-3 flex gap-1.5 z-30">
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-black/60 text-[#d4a853] border border-[#d4a853]/30 backdrop-blur-md">
                {track.format || 'WAV'}
              </span>
            </div>

            <div className="absolute bottom-3 right-3 flex gap-1.5 z-30">
              {track.bpm > 0 && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-black/70 text-white backdrop-blur-md">
                  {Math.round(track.bpm)} BPM
                </span>
              )}
              {track.key && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-black/70 text-white backdrop-blur-md">
                  {track.key}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* ── 3. Post Interaction Bar ── */}
        <div className="px-4 pt-3.5 pb-2">
          <div className="flex items-center justify-between mb-2.5">
            <div className="flex items-center gap-4">
              {/* Like Button */}
              <motion.button
                whileTap={{ scale: 0.85 }}
                onClick={handleLike}
                className="flex items-center gap-1.5 text-white/90 hover:text-red-500 transition-colors"
              >
                <Heart
                  className={`w-6 h-6 transition-colors ${
                    isLiked ? 'fill-red-500 text-red-500' : 'text-white/80'
                  }`}
                />
                <span className="text-xs font-semibold">{likesCount}</span>
              </motion.button>

              {/* Comment Button */}
              <button
                onClick={toggleCommentSection}
                className="flex items-center gap-1.5 text-white/80 hover:text-[#d4a853] transition-colors"
              >
                <MessageCircle className="w-6 h-6" />
                <span className="text-xs font-semibold">{post.comments_count || comments.length}</span>
              </button>

              {/* Share Story Card Button */}
              <button
                onClick={() => setShowShareModal(true)}
                className="p-1 rounded-full text-white/80 hover:text-[#d4a853] transition-colors"
                title="인스타 스토리 카드 생성"
              >
                <Share2 className="w-5 h-5" />
              </button>
            </div>

            {/* Collect / Bookmark Button */}
            <motion.button
              whileTap={{ scale: 0.85 }}
              onClick={handleCollect}
              className={`flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium border transition-all ${
                isCollected
                  ? 'bg-[#d4a853]/20 border-[#d4a853] text-[#d4a853]'
                  : 'bg-white/5 border-white/10 text-white/80 hover:bg-white/10'
              }`}
            >
              <Bookmark className={`w-3.5 h-3.5 ${isCollected ? 'fill-current' : ''}`} />
              {isCollected ? '소장됨' : '디깅 (소장)'}
            </motion.button>
          </div>

          {/* ── 4. Track Info & Digger's Note ── */}
          <div className="space-y-1.5">
            <div className="flex items-baseline gap-2">
              <h3 className="font-bold text-sm text-white hover:text-[#d4a853] transition-colors">
                <Link href={`/track/${track.track_id}`}>{track.title}</Link>
              </h3>
              <span className="text-xs text-muted-foreground">{track.artist}</span>
            </div>

            {/* Digger's Note / Caption */}
            {post.caption && (
              <p className="text-sm text-white/90 leading-relaxed pt-0.5">
                <span className="font-semibold text-[#d4a853] mr-1.5">
                  @{user?.username || 'digger'}
                </span>
                {post.caption}
              </p>
            )}

            {/* Tags */}
            {post.tags && post.tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {post.tags.map((tag) => (
                  <span
                    key={tag}
                    className="text-[11px] text-[#d4a853]/80 hover:text-[#d4a853] cursor-pointer"
                  >
                    #{tag}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* ── 5. Comments Section ── */}
          {showComments && (
            <div className="mt-3 pt-3 border-t border-white/[0.06] space-y-2.5">
              {loadingComments ? (
                <p className="text-xs text-muted-foreground text-center py-2">댓글 불러오는 중...</p>
              ) : comments.length === 0 ? (
                <p className="text-xs text-muted-foreground text-center py-2">첫 번째 감상평을 남겨보세요!</p>
              ) : (
                <div className="space-y-2 max-h-48 overflow-y-auto pr-1 scrollbar-thin">
                  {comments.map((c) => (
                    <div key={c.id} className="text-xs flex items-start gap-2">
                      <span className="font-semibold text-white/90 shrink-0">
                        @{c.user?.username || 'user'}:
                      </span>
                      <span className="text-white/70 leading-tight">{c.content}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Comment Input */}
              <form onSubmit={handleAddComment} className="flex items-center gap-2 pt-1">
                <input
                  type="text"
                  placeholder="디깅 감상평 또는 코멘트 작성..."
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white placeholder:text-muted-foreground focus:outline-none focus:border-[#d4a853]"
                />
                <button
                  type="submit"
                  disabled={!newComment.trim()}
                  className="p-1.5 rounded-lg bg-[#d4a853] text-black disabled:opacity-30 transition-opacity"
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </form>
            </div>
          )}
        </div>
      </article>

      {/* Share Vinyl Card Modal */}
      <ShareVinylCardModal
        isOpen={showShareModal}
        onClose={() => setShowShareModal(false)}
        track={track}
        user={user}
        caption={post.caption}
      />
    </>
  );
}
