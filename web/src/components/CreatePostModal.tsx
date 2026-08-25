'use client';

/* ──────────────────────────────────────────────
   WaveMash — Create Music Diary & Photo Album Modal
   나만의 음악 다이어리 & 뮤직플레잉 앨범 생성 모달
   - 프라이버시(🔒 나만 보기 / 🌐 전체 공개) 선택
   - 브라우저 초경량 이미지 압축 (150KB 이하)
   - 사진 + 어울리는 음악(유튜브/트랙) 조합
   ────────────────────────────────────────────── */

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Search,
  Disc3,
  Sparkles,
  Plus,
  Check,
  Image as ImageIcon,
  Upload,
  Link as LinkIcon,
  Music,
  Trash2,
  Play,
  Loader2,
  Lock,
  Globe,
  BookOpen,
} from 'lucide-react';
import type { Track, Post } from '@/lib/types';
import api from '@/lib/api';
import { compressImage } from '@/lib/imageCompressor';

interface CreatePostModalProps {
  isOpen: boolean;
  onClose: () => void;
  onPostCreated?: (post: Post) => void;
  initialTrack?: Track | null;
}

const PRESET_TAGS = [
  '나만의기록',
  'NightDrive',
  'CafeVibes',
  'VinylMood',
  'DeepGroove',
  'AnalogSound',
  'DailyDiary',
  'DiggerChoice',
];

export default function CreatePostModal({
  isOpen,
  onClose,
  onPostCreated,
  initialTrack,
}: CreatePostModalProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Photo & Compression state
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [isCompressing, setIsCompressing] = useState(false);

  // Privacy Visibility state ('public' | 'private')
  const [visibility, setVisibility] = useState<'public' | 'private'>('public');

  // Music state
  const [tracks, setTracks] = useState<Track[]>([]);
  const [selectedTrack, setSelectedTrack] = useState<Track | null>(initialTrack || null);
  const [youtubeUrlInput, setYoutubeUrlInput] = useState('');
  const [isYoutubeMatching, setIsYoutubeMatching] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [musicTab, setMusicTab] = useState<'library' | 'youtube'>('library');

  // Text & tags state
  const [caption, setCaption] = useState('');
  const [tags, setTags] = useState<string[]>(['나만의기록']);
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

  // Handle Photo Select & Client-Side Auto Compression (초경량 압축)
  const handlePhotoSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsCompressing(true);
    try {
      // 1200px, 82% 퀄리티로 브라우저에서 98% 용량 다이어트 압축
      const compressedBase64 = await compressImage(file, 1200, 0.82);
      setPhotoPreview(compressedBase64);
    } catch (err) {
      console.error(err);
      alert('사진 압축에 실패했습니다.');
    } finally {
      setIsCompressing(false);
    }
  };

  // Handle YouTube URL Direct Match
  const handleMatchYouTube = async () => {
    const url = youtubeUrlInput.trim();
    if (!url) return;

    setIsYoutubeMatching(true);
    try {
      let videoId = '';
      const match = url.match(/(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})/);
      if (match) {
        videoId = match[1];
      } else if (/^[\w-]{11}$/.test(url)) {
        videoId = url;
      }

      if (!videoId) {
        alert('유효한 유튜브 영상 링크를 입력해주세요.');
        setIsYoutubeMatching(false);
        return;
      }

      const matchedTrack: Track = {
        track_id: videoId,
        title: 'YouTube Track',
        artist: 'Curation',
        primary_artist: 'Curation',
        album: 'YouTube Music',
        genre: 'Mood',
        year: new Date().getFullYear().toString(),
        bpm: 0,
        key: '',
        camelot_key: '',
        energy_level: 0,
        platform: 'YouTube',
        url: `https://www.youtube.com/watch?v=${videoId}`,
        thumbnail_url: `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`,
        has_cover: true,
        has_file: false,
      };

      setSelectedTrack(matchedTrack);
      setYoutubeUrlInput('');
    } catch (err) {
      console.error(err);
      alert('유튜브 곡 매칭에 실패했습니다.');
    } finally {
      setIsYoutubeMatching(false);
    }
  };

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
    if ((!selectedTrack && !photoPreview) || submitting) return;

    setSubmitting(true);
    try {
      const newPost = await api.createPost({
        track_id: selectedTrack?.track_id,
        image_url: photoPreview || '',
        caption: caption.trim(),
        tags,
        visibility,
      });

      newPost.track = selectedTrack || undefined;
      newPost.image_url = photoPreview || undefined;
      newPost.visibility = visibility;

      onPostCreated?.(newPost);
      onClose();

      // Reset form
      setCaption('');
      setPhotoPreview(null);
      setSelectedTrack(null);
      setVisibility('public');
    } catch (err) {
      console.error('Failed to create post:', err);
      alert('포스트 게시에 실패했습니다.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md overflow-y-auto">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative max-w-lg w-full bg-[#0d0d17] border border-white/15 rounded-3xl overflow-hidden shadow-2xl p-6 my-8"
        >
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-5 right-5 text-muted-foreground hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>

          {/* Modal Header */}
          <div className="flex items-center justify-between mb-5 pr-8">
            <div className="flex items-center gap-2 text-sm font-bold text-[#d4a853]">
              <BookOpen className="w-4 h-4" />
              뮤직플레잉 앨범 & 음악 다이어리 작성
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* ── 0. Privacy Visibility Toggle (프라이버시 설정) ── */}
            <div className="p-3 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-white flex items-center gap-1.5">
                  {visibility === 'public' ? (
                    <>
                      <Globe className="w-3.5 h-3.5 text-[#d4a853]" /> 전체 공개 (피드 공유)
                    </>
                  ) : (
                    <>
                      <Lock className="w-3.5 h-3.5 text-blue-400" /> 나만 보기 (프라이빗 다이어리)
                    </>
                  )}
                </span>
                <p className="text-[10px] text-muted-foreground mt-0.5">
                  {visibility === 'public'
                    ? '피드에 공개되어 친구들과 감성을 나눕니다.'
                    : '오직 나만의 프로필 다이어리에 안전하게 보관됩니다.'}
                </p>
              </div>

              <div className="flex rounded-xl bg-black/40 p-1 border border-white/10">
                <button
                  type="button"
                  onClick={() => setVisibility('public')}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    visibility === 'public'
                      ? 'bg-[#d4a853] text-black font-bold shadow'
                      : 'text-muted-foreground hover:text-white'
                  }`}
                >
                  공개
                </button>
                <button
                  type="button"
                  onClick={() => setVisibility('private')}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    visibility === 'private'
                      ? 'bg-blue-500 text-white font-bold shadow'
                      : 'text-muted-foreground hover:text-white'
                  }`}
                >
                  비공개
                </button>
              </div>
            </div>

            {/* ── 1. Photo Upload Section (브라우저 자동 98% 압축) ── */}
            <div>
              <label className="block text-xs font-bold text-white/90 uppercase tracking-wider mb-2 flex items-center justify-between">
                <span>📸 감성 사진 업로드</span>
                <span className="text-[10px] text-green-400 font-mono font-medium">
                  {isCompressing ? '초경량 압축 중...' : '자동 경량화 압축'}
                </span>
              </label>

              <input
                type="file"
                ref={fileInputRef}
                accept="image/*"
                onChange={handlePhotoSelect}
                className="hidden"
              />

              {photoPreview ? (
                <div className="relative aspect-video sm:aspect-[16/10] rounded-2xl overflow-hidden bg-black/50 border border-white/15 group">
                  <img
                    src={photoPreview}
                    alt="Upload Preview"
                    className="w-full h-full object-cover"
                  />
                  <button
                    type="button"
                    onClick={() => setPhotoPreview(null)}
                    className="absolute top-3 right-3 p-1.5 rounded-full bg-black/70 text-red-400 hover:bg-red-500 hover:text-white transition-colors shadow-lg"
                    title="사진 삭제"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-white/15 hover:border-[#d4a853]/60 rounded-2xl p-5 text-center cursor-pointer transition-all bg-white/[0.02] hover:bg-white/[0.05] group"
                >
                  {isCompressing ? (
                    <div className="py-3 flex flex-col items-center gap-2">
                      <Loader2 className="w-6 h-6 text-[#d4a853] animate-spin" />
                      <span className="text-xs text-muted-foreground">사진을 가볍게 압축하고 있습니다...</span>
                    </div>
                  ) : (
                    <>
                      <div className="w-10 h-10 rounded-full bg-[#d4a853]/15 text-[#d4a853] flex items-center justify-center mx-auto mb-2 group-hover:scale-110 transition-transform">
                        <ImageIcon className="w-5 h-5" />
                      </div>
                      <p className="text-xs font-semibold text-white mb-0.5">
                        어울리는 감성 사진 추가
                      </p>
                      <p className="text-[10px] text-muted-foreground">
                        LP판, 일상 사진, 여행 무드샷을 가볍게 업로드하세요
                      </p>
                    </>
                  )}
                </div>
              )}
            </div>

            {/* ── 2. Match Music / Track (어울리는 음악 선택) ── */}
            <div>
              <label className="block text-xs font-bold text-white/90 uppercase tracking-wider mb-2 flex items-center justify-between">
                <span>🎵 사진에 어울리는 BGM 음악 매칭</span>
                <span className="text-[10px] text-[#d4a853] font-semibold">필수</span>
              </label>

              {selectedTrack ? (
                <div className="flex items-center justify-between p-3 rounded-2xl bg-white/5 border border-[#d4a853]/40">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-12 h-12 rounded-xl overflow-hidden bg-black/50 border border-white/10 shrink-0">
                      {selectedTrack.has_cover ? (
                        <img
                          src={selectedTrack.thumbnail_url || api.getCoverUrl(selectedTrack.track_id, 120)}
                          alt={selectedTrack.title}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <Disc3 className="w-6 h-6 text-[#d4a853]" />
                        </div>
                      )}
                    </div>
                    <div className="min-w-0">
                      <h4 className="text-xs font-bold text-white truncate">
                        {selectedTrack.title}
                      </h4>
                      <p className="text-[11px] text-muted-foreground truncate">
                        {selectedTrack.artist}
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setSelectedTrack(null)}
                    className="text-xs text-[#d4a853] hover:underline shrink-0 font-semibold cursor-pointer ml-2"
                  >
                    변경
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  {/* Tab Selector */}
                  <div className="flex rounded-xl bg-white/5 p-1 border border-white/10">
                    <button
                      type="button"
                      onClick={() => setMusicTab('library')}
                      className={`flex-1 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                        musicTab === 'library'
                          ? 'bg-[#d4a853] text-black shadow-md'
                          : 'text-muted-foreground hover:text-white'
                      }`}
                    >
                      내 라이브러리 곡
                    </button>
                    <button
                      type="button"
                      onClick={() => setMusicTab('youtube')}
                      className={`flex-1 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                        musicTab === 'youtube'
                          ? 'bg-[#d4a853] text-black shadow-md'
                          : 'text-muted-foreground hover:text-white'
                      }`}
                    >
                      유튜브 링크로 추가
                    </button>
                  </div>

                  {musicTab === 'youtube' ? (
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <LinkIcon className="absolute left-3 top-2.5 w-4 h-4 text-muted-foreground" />
                        <input
                          type="text"
                          placeholder="YouTube 영상 링크 또는 ID 입력..."
                          value={youtubeUrlInput}
                          onChange={(e) => setYoutubeUrlInput(e.target.value)}
                          className="w-full bg-white/5 border border-white/10 rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder:text-muted-foreground focus:outline-none focus:border-[#d4a853]"
                        />
                      </div>
                      <button
                        type="button"
                        onClick={handleMatchYouTube}
                        disabled={!youtubeUrlInput.trim() || isYoutubeMatching}
                        className="px-4 py-2 rounded-xl bg-[#d4a853] text-black font-bold text-xs hover:bg-amber-400 transition-colors disabled:opacity-50 flex items-center gap-1 cursor-pointer"
                      >
                        {isYoutubeMatching ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : '매칭'}
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <div className="relative">
                        <Search className="absolute left-3 top-2.5 w-4 h-4 text-muted-foreground" />
                        <input
                          type="text"
                          placeholder="소장 트랙 검색..."
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          className="w-full bg-white/5 border border-white/10 rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder:text-muted-foreground focus:outline-none focus:border-[#d4a853]"
                        />
                      </div>

                      <div className="max-h-36 overflow-y-auto space-y-1 pr-1 scrollbar-thin">
                        {loadingTracks ? (
                          <p className="text-xs text-muted-foreground text-center py-4">트랙 불러오는 중...</p>
                        ) : filteredTracks.length === 0 ? (
                          <p className="text-xs text-muted-foreground text-center py-4">
                            검색된 트랙이 없습니다. 유튜브 탭에서 링크로 바로 매칭해보세요!
                          </p>
                        ) : (
                          filteredTracks.slice(0, 10).map((t) => (
                            <div
                              key={t.track_id}
                              onClick={() => setSelectedTrack(t)}
                              className="flex items-center gap-3 p-2 rounded-xl hover:bg-white/10 cursor-pointer transition-colors"
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
              )}
            </div>

            {/* ── 3. Digger's Note (Caption) ── */}
            <div>
              <label className="block text-xs font-bold text-white/90 uppercase tracking-wider mb-2">
                ✍️ 다이어리 코멘트 (Digger&apos;s Note)
              </label>
              <textarea
                rows={2}
                placeholder="이 사진과 음악에 얽힌 이야기나 오늘의 감상을 편안하게 기록해보세요."
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-2xl p-3 text-xs text-white placeholder:text-muted-foreground focus:outline-none focus:border-[#d4a853] resize-none leading-relaxed"
              />
            </div>

            {/* ── 4. Tags ── */}
            <div>
              <label className="block text-xs font-bold text-white/90 uppercase tracking-wider mb-2">
                무드 태그
              </label>
              <div className="flex flex-wrap gap-1.5 mb-2">
                {PRESET_TAGS.map((tag) => {
                  const active = tags.includes(tag);
                  return (
                    <button
                      type="button"
                      key={tag}
                      onClick={() => toggleTag(tag)}
                      className={`text-[11px] px-2.5 py-1 rounded-full border transition-all cursor-pointer ${
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
              disabled={(!selectedTrack && !photoPreview) || submitting || isCompressing}
              className="w-full py-3.5 rounded-2xl bg-gradient-to-r from-[#d4a853] to-amber-400 text-black font-bold text-sm hover:opacity-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-xl shadow-[#d4a853]/20 flex items-center justify-center gap-2 cursor-pointer"
            >
              <Check className="w-4 h-4" />
              {submitting
                ? '저장 중...'
                : visibility === 'public'
                  ? '피드에 공개하기'
                  : '🔒 나만의 다이어리에 저장하기'}
            </button>
          </form>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
