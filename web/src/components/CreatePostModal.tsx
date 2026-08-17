'use client';

/* ──────────────────────────────────────────────
   WaveMash — Create Post Modal (Digger's Note)
   내 소장 트랙 선택 및 감성 코멘트/태그 피드 작성 모달
   ────────────────────────────────────────────── */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Search, Disc3, Sparkles, Plus, Check } from 'lucide-react';
import type { Track, Post } from '@/lib/types';
import api from '@/lib/api';

interface CreatePostModalProps {
  isOpen: boolean;
  onClose: () => void;
  onPostCreated?: (post: Post) => void;
  initialTrack?: Track | null;
}

const PRESET_TAGS = ['Vinyl', 'FrenchTouch', 'DeepHouse', 'LateNight', 'ClubBanger', '90sGroove', 'LosslessWAV', 'RareFind'];

export default function CreatePostModal({
  isOpen,
  onClose,
  onPostCreated,
  initialTrack,
}: CreatePostModalProps) {
  const [tracks, setTracks] = useState<Track[]>([]);
  const [selectedTrack, setSelectedTrack] = useState<Track | null>(initialTrack || null);
  const [searchQuery, setSearchQuery] = useState('');
  const [caption, setCaption] = useState('');
  const [tags, setTags] = useState<string[]>(['Vinyl']);
  const [customTag, setCustomTag] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [loadingTracks, setLoadingTracks] = useState(false);

  useEffect(() => {
    if (initialTrack) {
      setSelectedTrack(initialTrack);
    }
  }, [initialTrack]);

  useEffect(() => {
    if (isOpen && tracks.length === 0) {
      setLoadingTracks(true);
      api
        .getTracks({ limit: 50 })
        .then((res) => setTracks(res))
        .catch(console.error)
        .finally(() => setLoadingTracks(false));
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const filteredTracks = tracks.filter(
    (t) =>
      t.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.artist.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const toggleTag = (tag: string) => {
    if (tags.includes(tag)) {
      setTags(tags.filter((t) => t !== tag));
    } else {
      setTags([...tags, tag]);
    }
  };

  const handleAddCustomTag = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && customTag.trim()) {
      e.preventDefault();
      const cleaned = customTag.trim().replace(/^#/, '');
      if (!tags.includes(cleaned)) {
        setTags([...tags, cleaned]);
      }
      setCustomTag('');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTrack || submitting) return;

    setSubmitting(true);
    try {
      const newPost = await api.createPost({
        track_id: selectedTrack.track_id,
        caption: caption.trim(),
        tags,
      });
      // 트랙 정보 병합
      newPost.track = selectedTrack;
      onPostCreated?.(newPost);
      onClose();
      // Reset form
      setCaption('');
      setSelectedTrack(null);
    } catch (err) {
      console.error('Failed to create post:', err);
      alert('포스트 게시에 실패했습니다.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative max-w-lg w-full bg-[#0e0e1a] border border-white/10 rounded-2xl overflow-hidden shadow-2xl p-6"
        >
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-muted-foreground hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-2 mb-6 text-sm font-semibold text-[#d4a853]">
            <Sparkles className="w-4 h-4" />
            내 컬렉션 소장곡 자랑하기
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* ── 1. Select Track ── */}
            <div>
              <label className="block text-xs font-semibold text-white/80 uppercase tracking-wider mb-2">
                소장 트랙 선택
              </label>

              {selectedTrack ? (
                <div className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-[#d4a853]/40">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-lg overflow-hidden bg-black/40 border border-white/10 shrink-0">
                      {selectedTrack.has_cover ? (
                        <img
                          src={api.getCoverUrl(selectedTrack.track_id, 120)}
                          alt={selectedTrack.title}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <Disc3 className="w-6 h-6 text-[#d4a853]" />
                        </div>
                      )}
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-white truncate max-w-[240px]">
                        {selectedTrack.title}
                      </h4>
                      <p className="text-xs text-muted-foreground truncate">{selectedTrack.artist}</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setSelectedTrack(null)}
                    className="text-xs text-[#d4a853] hover:underline"
                  >
                    변경
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="relative">
                    <Search className="absolute left-3 top-2.5 w-4 h-4 text-muted-foreground" />
                    <input
                      type="text"
                      placeholder="내 라이브러리 트랙 검색..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full bg-white/5 border border-white/10 rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder:text-muted-foreground focus:outline-none focus:border-[#d4a853]"
                    />
                  </div>

                  <div className="max-h-40 overflow-y-auto space-y-1 pr-1 scrollbar-thin">
                    {loadingTracks ? (
                      <p className="text-xs text-muted-foreground text-center py-4">트랙 불러오는 중...</p>
                    ) : filteredTracks.length === 0 ? (
                      <p className="text-xs text-muted-foreground text-center py-4">검색된 트랙이 없습니다.</p>
                    ) : (
                      filteredTracks.slice(0, 10).map((t) => (
                        <div
                          key={t.track_id}
                          onClick={() => setSelectedTrack(t)}
                          className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/10 cursor-pointer transition-colors"
                        >
                          <div className="w-8 h-8 rounded bg-black/40 overflow-hidden shrink-0">
                            {t.has_cover ? (
                              <img
                                src={api.getCoverUrl(t.track_id, 80)}
                                alt={t.title}
                                className="w-full h-full object-cover"
                              />
                            ) : (
                              <Disc3 className="w-full h-full p-1 text-white/40" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-semibold text-white truncate">{t.title}</p>
                            <p className="text-[10px] text-muted-foreground truncate">{t.artist}</p>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* ── 2. Digger's Note (Caption) ── */}
            <div>
              <label className="block text-xs font-semibold text-white/80 uppercase tracking-wider mb-2">
                디거스 노트 (Digger&apos;s Note / 감성 코멘트)
              </label>
              <textarea
                rows={3}
                placeholder="이 트랙을 소장하게 된 이유나 감상평을 남겨보세요. (예: 90년대 프렌치 하우스의 정점, 새벽 드라이브 필수 트랙)"
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-xs text-white placeholder:text-muted-foreground focus:outline-none focus:border-[#d4a853] resize-none"
              />
            </div>

            {/* ── 3. Tags ── */}
            <div>
              <label className="block text-xs font-semibold text-white/80 uppercase tracking-wider mb-2">
                태그 선택
              </label>
              <div className="flex flex-wrap gap-1.5 mb-2">
                {PRESET_TAGS.map((tag) => {
                  const active = tags.includes(tag);
                  return (
                    <button
                      type="button"
                      key={tag}
                      onClick={() => toggleTag(tag)}
                      className={`text-[11px] px-2.5 py-1 rounded-full border transition-all ${
                        active
                          ? 'bg-[#d4a853] text-black border-[#d4a853] font-semibold'
                          : 'bg-white/5 text-white/70 border-white/10 hover:bg-white/10'
                      }`}
                    >
                      #{tag}
                    </button>
                  );
                })}
              </div>
              <input
                type="text"
                placeholder="+ 직접 태그 추가 (입력 후 Enter)"
                value={customTag}
                onChange={(e) => setCustomTag(e.target.value)}
                onKeyDown={handleAddCustomTag}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white placeholder:text-muted-foreground focus:outline-none focus:border-[#d4a853]"
              />
            </div>

            {/* ── Submit Button ── */}
            <button
              type="submit"
              disabled={!selectedTrack || submitting}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-[#d4a853] to-amber-400 text-black font-bold text-sm hover:opacity-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-[#d4a853]/20 flex items-center justify-center gap-2"
            >
              <Check className="w-4 h-4" />
              {submitting ? '게시 중...' : '피드에 자랑하기'}
            </button>
          </form>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
