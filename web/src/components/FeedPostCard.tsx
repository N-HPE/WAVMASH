'use client';

/* ──────────────────────────────────────────────
   WaveMash — Instagram-Style Music & Photo Post Card
   인스타 감성: 감성 사진 비주얼, 바이닐 오디오 스트리밍, 내 플리에 담기(소장), YouTube 바로가기
   ────────────────────────────────────────────── */

import React, { useState } from 'react';
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
  Plus,
  Check,
  Sparkles,
  Music,
} from 'lucide-react';
import type { Post, PostComment } from '@/lib/types';
import api from '@/lib/api';
import { useCoverGlow } from '@/lib/coverColors';
import { usePlayer } from '@/contexts/PlayerContext';
import ShareVinylCardModal from './ShareVinylCardModal';
import AddToPlaylistModal from './AddToPlaylistModal';

interface FeedPostCardProps {
  post: Post;
  currentUserId?: string;
  onDelete?: (postId: string) => void;
  onLikeToggle?: (postId: string, liked: boolean) => void;
}

function formatCount(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1).replace(/\.0$/, '') + 'M';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1).replace(/\.0$/, '') + 'k';
  }
  return num.toString();
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

  const isCurrentTrackPlaying = Boolean(track && globalPlaying && currentTrack?.track_id === track?.track_id);

  const [isLiked, setIsLiked] = useState(post.is_liked || false);
  const [likesCount, setLikesCount] = useState(post.likes_count || 0);
  const [sharesCount, setSharesCount] = useState(post.shares_count || 0);
  const [downloadsCount, setDownloadsCount] = useState(post.downloads_count || 0);

  const [showComments, setShowComments] = useState(false);
  const [comments, setComments] = useState<PostComment[]>([]);
  const [newComment, setNewComment] = useState('');
  const [loadingComments, setLoadingComments] = useState(false);
  const [showShareModal, setShowShareModal] = useState(false);
  const [showAddToPlaylistModal, setShowAddToPlaylistModal] = useState(false);
  const [showMenu, setShowMenu] = useState(false);

  const coverUrl = track ? api.getCoverUrl(track.track_id, 600) : '';
  const glowColor = useCoverGlow(
    track?.track_id || '',
    track?.has_cover || false,
    track?.dominant_color
  );

  // 1. 좋아요 토글 핸들러
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
      setIsLiked(!nextLiked);
      setLikesCount((prev) => (!nextLiked ? prev + 1 : Math.max(prev - 1, 0)));
    }
  };

  // 2. 공유 핸들러 (스토리 모달 열기 + 카운트 증가)
  const handleShare = async () => {
    setShowShareModal(true);
    try {
      const res = await api.sharePost(post.id);
      setSharesCount(res.shares_count);
    } catch (err) {
      console.warn(err);
    }
  };

  // 3. 앨범/음악 클릭 시 통합 플레이어로 자동 재생
  const handleMusicPlay = () => {
    if (!track) return;
    if (currentTrack?.track_id === track.track_id) {
      globalTogglePlay();
    } else {
      play(track);
    }
  };

  // 4. 댓글 목록 조회
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

  // 5. 댓글 작성
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

  const isOwner = Boolean(currentUserId && user?.user_id === currentUserId);
  const youtubeLink = track ? (track.url || `https://www.youtube.com/watch?v=${track.track_id}`) : null;

  return (
    <>
      <motion.article
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="glass-strong rounded-3xl overflow-hidden border border-white/10 shadow-2xl bg-[#0b0b14]/85 backdrop-blur-xl"
      >
        {/* ── 1. Post Header (Digger Profile) ── */}
        <div className="flex items-center justify-between p-4 border-b border-white/5">
          <Link
            href={`/profile/${user?.username || 'user'}`}
            className="flex items-center gap-3 group"
          >
            <div className="relative w-10 h-10 rounded-full border border-[#d4a853]/60 p-0.5 shadow-md">
              {user?.avatar_url ? (
                <img
                  src={user.avatar_url}
                  alt={user.display_name}
                  className="w-full h-full rounded-full object-cover"
                />
              ) : (
                <div className="w-full h-full rounded-full bg-gradient-to-tr from-[#2a1a08] to-[#d4a853]/30 flex items-center justify-center font-bold text-xs text-[#d4a853]">
                  {user?.username?.slice(0, 2).toUpperCase() || 'WM'}
                </div>
              )}
            </div>
            <div>
              <h4 className="font-bold text-sm text-white group-hover:text-[#d4a853] transition-colors leading-tight">
                {user?.display_name || user?.username || '디거'}
              </h4>
              <p className="text-[11px] text-muted-foreground font-mono">
                @{user?.username || 'digger'}
              </p>
            </div>
          </Link>

          <div className="relative">
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="p-2 text-white/60 hover:text-white rounded-full hover:bg-white/5 transition-colors cursor-pointer"
            >
              <MoreHorizontal className="w-5 h-5" />
            </button>

            {showMenu && (
              <div className="absolute right-0 top-full mt-1 w-44 rounded-xl bg-[#181828] border border-white/10 shadow-2xl py-1 z-50 text-xs font-medium backdrop-blur-lg">
                <button
                  onClick={() => {
                    handleShare();
                    setShowMenu(false);
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-white hover:bg-white/10 text-left cursor-pointer"
                >
                  <Share2 className="w-4 h-4 text-[#d4a853]" />
                  스토리 카드 생성
                </button>
                {track && (
                  <Link
                    href={`/track/${track.track_id}`}
                    className="w-full flex items-center gap-2 px-3 py-2 text-white hover:bg-white/10 text-left"
                  >
                    <ExternalLink className="w-4 h-4" />
                    트랙 상세 보기
                  </Link>
                )}
                {isOwner && (
                  <button
                    onClick={() => {
                      onDelete?.(post.id);
                      setShowMenu(false);
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-red-400 hover:bg-red-500/10 text-left cursor-pointer"
                  >
                    <Trash2 className="w-4 h-4" />
                    포스트 삭제
                  </button>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ── 2. Photo & Music Visual Media Area ── */}
        <div className="relative w-full overflow-hidden bg-[#080811] flex flex-col justify-center">
          {post.image_url ? (
            /* 2-A. User Uploaded Photo Showcase */
            <div className="relative aspect-square w-full overflow-hidden bg-black group">
              <img
                src={post.image_url}
                alt="Feed Post"
                className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
              />

              {/* Floating Music Badge on Photo */}
              {track && (
                <div
                  onClick={handleMusicPlay}
                  className="absolute bottom-4 left-4 right-4 p-3 rounded-2xl glass-strong border border-white/20 shadow-2xl flex items-center justify-between gap-3 cursor-pointer group/music hover:border-[#d4a853]/60 transition-all backdrop-blur-md"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="relative w-10 h-10 rounded-xl overflow-hidden bg-black/60 shrink-0">
                      {track.has_cover ? (
                        <img
                          src={track.thumbnail_url || api.getCoverUrl(track.track_id, 160)}
                          alt={track.title}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <Disc3 className="w-5 h-5 text-[#d4a853]" />
                        </div>
                      )}
                      <div className="absolute inset-0 bg-black/30 flex items-center justify-center">
                        {isCurrentTrackPlaying ? (
                          <Pause className="w-4 h-4 text-[#d4a853] fill-current" />
                        ) : (
                          <Play className="w-4 h-4 text-white fill-current ml-0.5" />
                        )}
                      </div>
                    </div>

                    <div className="min-w-0">
                      <p className="text-xs font-bold text-white truncate group-hover/music:text-[#d4a853] transition-colors">
                        {track.title}
                      </p>
                      <p className="text-[10px] text-muted-foreground truncate">
                        {track.artist}
                      </p>
                    </div>
                  </div>

                  <span className="text-[10px] font-mono font-semibold px-2.5 py-1 rounded-full bg-[#d4a853] text-black shadow-md shrink-0 flex items-center gap-1">
                    <Disc3 className={`w-3 h-3 ${isCurrentTrackPlaying ? 'animate-spin' : ''}`} />
                    {isCurrentTrackPlaying ? '재생 중' : '음악 듣기'}
                  </span>
                </div>
              )}
            </div>
          ) : track ? (
            /* 2-B. Vinyl Slipout Showcase (when no photo uploaded) */
            <div
              className="relative aspect-square w-full overflow-hidden bg-[#080811] flex items-center justify-center group cursor-pointer"
              style={{ '--glow-color': glowColor } as React.CSSProperties}
              onClick={handleMusicPlay}
            >
              {/* Ambient Glow */}
              <div
                className="absolute inset-0 opacity-40 blur-3xl transition-opacity duration-700 pointer-events-none"
                style={{ backgroundColor: glowColor }}
              />

              {/* Vinyl Disc Slipout Animation */}
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
              </div>
            </div>
          ) : null}
        </div>

        {/* ── 3. Instagram Style Metrics & Collection Action Bar ── */}
        <div className="px-4 pt-3.5 pb-2">
          <div className="flex items-center justify-between mb-2.5">
            <div className="flex items-center gap-5">
              {/* ① Like Counter */}
              <motion.button
                whileTap={{ scale: 0.8 }}
                onClick={handleLike}
                className="flex items-center gap-1.5 text-white/90 hover:text-red-500 transition-colors group cursor-pointer"
                title="좋아요"
              >
                <Heart
                  className={`w-6 h-6 transition-transform group-hover:scale-110 ${
                    isLiked ? 'fill-red-500 text-red-500' : 'text-white/80'
                  }`}
                />
                <span className="text-xs font-bold font-mono">
                  {formatCount(likesCount)}
                </span>
              </motion.button>

              {/* ② Comment Counter */}
              <button
                onClick={toggleCommentSection}
                className="flex items-center gap-1.5 text-white/80 hover:text-[#d4a853] transition-colors group cursor-pointer"
                title="댓글"
              >
                <MessageCircle className="w-6 h-6 group-hover:scale-110 transition-transform" />
                <span className="text-xs font-bold font-mono">
                  {formatCount(post.comments_count || comments.length)}
                </span>
              </button>

              {/* ③ Share Counter */}
              <motion.button
                whileTap={{ scale: 0.8 }}
                onClick={handleShare}
                className="flex items-center gap-1.5 text-white/80 hover:text-[#d4a853] transition-colors group cursor-pointer"
                title="인스타 스토리 카드 공유"
              >
                <Share2 className="w-5 h-5 group-hover:scale-110 transition-transform" />
                <span className="text-xs font-bold font-mono">
                  {formatCount(sharesCount)}
                </span>
              </motion.button>
            </div>

            {/* Quick Action Hub: [내 플리에 담기(소장)] + [유튜브 바로가기] */}
            <div className="flex items-center gap-2">
              {track && (
                <button
                  onClick={() => setShowAddToPlaylistModal(true)}
                  className="px-3 py-1.5 rounded-full bg-[#d4a853]/15 hover:bg-[#d4a853] text-[#d4a853] hover:text-black border border-[#d4a853]/40 text-xs font-bold transition-all flex items-center gap-1 cursor-pointer shadow-md"
                  title="내 플레이리스트에 담기"
                >
                  <Plus className="w-3.5 h-3.5" />
                  플리에 소장
                </button>
              )}

              {youtubeLink && (
                <a
                  href={youtubeLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-2 rounded-full bg-white/5 hover:bg-white/10 text-white/70 hover:text-white border border-white/10 transition-colors"
                  title="유튜브에서 바로 보기"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              )}
            </div>
          </div>

          {/* ── 4. Track Info & Digger's Story Note ── */}
          <div className="space-y-1.5 pt-1">
            {track && (
              <div className="flex items-baseline gap-2">
                <h3 className="font-bold text-sm text-white hover:text-[#d4a853] transition-colors">
                  <Link href={`/track/${track.track_id}`}>{track.title}</Link>
                </h3>
                <span className="text-xs text-muted-foreground">{track.artist}</span>
              </div>
            )}

            {/* Digger's Note / Caption */}
            {post.caption && (
              <p className="text-sm text-white/90 leading-relaxed pt-0.5">
                <span className="font-semibold text-[#d4a853] mr-1.5">
                  @{user?.username || 'digger'}
                </span>
                {post.caption}
              </p>
            )}

            {/* Hashtags */}
            {post.tags && post.tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {post.tags.map((tag) => (
                  <span
                    key={tag}
                    className="text-xs text-[#d4a853]/80 hover:text-[#d4a853] cursor-pointer"
                  >
                    #{tag}
                  </span>
                ))}
              </div>
            )}

            <div className="text-[10px] text-muted-foreground/60 font-mono pt-1">
              {new Date(post.created_at).toLocaleDateString('ko-KR', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
              })}
            </div>
          </div>
        </div>

        {/* ── 5. Comments Section ── */}
        <AnimatePresence>
          {showComments && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="border-t border-white/5 bg-black/30 p-4 space-y-3"
            >
              {loadingComments ? (
                <div className="text-center py-4 text-xs text-muted-foreground">
                  댓글을 불러오는 중...
                </div>
              ) : comments.length === 0 ? (
                <div className="text-center py-3 text-xs text-muted-foreground">
                  첫 번째 Digger 댓글을 남겨보세요!
                </div>
              ) : (
                <div className="space-y-2.5 max-h-48 overflow-y-auto pr-1 scrollbar-thin">
                  {comments.map((c) => (
                    <div key={c.id} className="text-xs flex items-start gap-2">
                      <span className="font-bold text-[#d4a853] shrink-0">
                        @{c.user?.username || 'digger'}:
                      </span>
                      <span className="text-white/80 leading-relaxed break-all">
                        {c.content}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* Comment Input */}
              <form onSubmit={handleAddComment} className="flex gap-2 pt-2">
                <input
                  type="text"
                  placeholder="댓글 달기..."
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-white placeholder:text-muted-foreground outline-none focus:border-[#d4a853]/50"
                />
                <button
                  type="submit"
                  disabled={!newComment.trim()}
                  className="px-3 py-2 rounded-xl bg-[#d4a853] text-black font-semibold text-xs disabled:opacity-40 hover:bg-[#b58c3f] transition-colors"
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </form>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.article>

      {/* ── 6. 9:16 Instagram Story Card Modal ── */}
      {showShareModal && track && (
        <ShareVinylCardModal
          isOpen={showShareModal}
          onClose={() => setShowShareModal(false)}
          track={track}
          user={user}
        />
      )}

      {/* ── 7. Add to Playlist (소장하기) Modal ── */}
      {showAddToPlaylistModal && track && (
        <AddToPlaylistModal
          isOpen={showAddToPlaylistModal}
          onClose={() => setShowAddToPlaylistModal(false)}
          track={track}
        />
      )}
    </>
  );
}
