'use client';

/* ──────────────────────────────────────────────
   WaveMash — Add Track To Playlist Modal (소장하기)
   마음에 드는 음악을 내 플레이리스트에 즉시 담아 소장하는 모달
   ────────────────────────────────────────────── */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Plus,
  Music,
  Check,
  Disc3,
  Sparkles,
  FolderPlus,
  Loader2,
} from 'lucide-react';
import api from '@/lib/api';
import type { Playlist, Track } from '@/lib/types';
import { useAuth } from '@/contexts/AuthContext';

interface AddToPlaylistModalProps {
  isOpen: boolean;
  onClose: () => void;
  track: Track;
}

export default function AddToPlaylistModal({
  isOpen,
  onClose,
  track,
}: AddToPlaylistModalProps) {
  const { user } = useAuth();
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [isCreatingNew, setIsCreatingNew] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setLoading(true);
      api
        .getPlaylists()
        .then((res) => setPlaylists(res))
        .catch(() => setPlaylists([]))
        .finally(() => setLoading(false));
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleAddToPlaylist = async (playlist: Playlist) => {
    const pId = playlist.id || playlist.name;
    setSavingId(pId);
    try {
      await api.addTrackToPlaylist(pId, track.track_id, {
        title: track.title,
        artist: track.artist,
        cover_url: api.getCoverUrl(track.track_id, 320),
      });
      setSavedId(pId);
      setTimeout(() => {
        onClose();
        setSavedId(null);
        setSavingId(null);
      }, 800);
    } catch (err) {
      console.error(err);
      alert('플레이리스트에 추가하지 못했습니다.');
      setSavingId(null);
    }
  };

  const handleCreateAndAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || creating) return;

    setCreating(true);
    try {
      const created = await api.createPlaylist({
        name: newTitle.trim(),
        title: newTitle.trim(),
        description: newDesc.trim(),
        is_public: true,
      });

      const newId = created.id || created.name;
      await api.addTrackToPlaylist(newId, track.track_id, {
        title: track.title,
        artist: track.artist,
        cover_url: api.getCoverUrl(track.track_id, 320),
      });

      setPlaylists((prev) => [created, ...prev]);
      setSavedId(newId);
      setTimeout(() => {
        onClose();
        setSavedId(null);
        setCreating(false);
        setIsCreatingNew(false);
        setNewTitle('');
      }, 800);
    } catch (err) {
      console.error(err);
      alert('플레이리스트 생성에 실패했습니다.');
      setCreating(false);
    }
  };


  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative max-w-md w-full bg-[#0e0e1a] border border-white/10 rounded-2xl overflow-hidden shadow-2xl p-6"
        >
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-muted-foreground hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>

          {/* Modal Header */}
          <div className="flex items-center gap-2 mb-4 text-sm font-semibold text-[#d4a853]">
            <Sparkles className="w-4 h-4" />
            내 플레이리스트에 소장하기
          </div>

          {/* Track Summary Preview */}
          <div className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10 mb-5">
            <div className="w-12 h-12 rounded-lg bg-black/40 overflow-hidden shrink-0">
              {track.has_cover ? (
                <img
                  src={api.getCoverUrl(track.track_id, 120)}
                  alt={track.title}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <Disc3 className="w-6 h-6 text-[#d4a853]" />
                </div>
              )}
            </div>
            <div className="min-w-0 flex-1">
              <h4 className="text-xs font-bold text-white truncate">{track.title}</h4>
              <p className="text-[11px] text-muted-foreground truncate">{track.artist}</p>
            </div>
          </div>

          {/* Create New Playlist Form Toggle */}
          {isCreatingNew ? (
            <form onSubmit={handleCreateAndAdd} className="space-y-3 mb-4">
              <div>
                <label className="block text-[11px] font-semibold text-white/80 mb-1">
                  새 플레이리스트 이름
                </label>
                <input
                  type="text"
                  placeholder="예: 새벽 드라이브 바이닐 믹스"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  autoFocus
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-white placeholder:text-muted-foreground focus:outline-none focus:border-[#d4a853]"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-white/80 mb-1">
                  설명 (선택)
                </label>
                <input
                  type="text"
                  placeholder="분위기나 무드 설명"
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-white placeholder:text-muted-foreground focus:outline-none focus:border-[#d4a853]"
                />
              </div>
              <div className="flex gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setIsCreatingNew(false)}
                  className="flex-1 py-2 rounded-xl bg-white/5 text-white/70 text-xs font-semibold hover:bg-white/10 transition-colors"
                >
                  취소
                </button>
                <button
                  type="submit"
                  disabled={!newTitle.trim() || creating}
                  className="flex-1 py-2 rounded-xl bg-[#d4a853] text-black text-xs font-bold hover:bg-amber-400 transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
                >
                  {creating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                  생성하고 담기
                </button>
              </div>
            </form>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-white/70">담을 플레이리스트 선택</span>
                <button
                  type="button"
                  onClick={() => setIsCreatingNew(true)}
                  className="text-xs text-[#d4a853] hover:underline flex items-center gap-1 font-semibold cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" /> 새 플리 만들기
                </button>
              </div>

              <div className="max-h-52 overflow-y-auto space-y-1.5 pr-1 scrollbar-thin">
                {loading ? (
                  <div className="text-center py-6 text-xs text-muted-foreground">
                    플레이리스트 불러오는 중...
                  </div>
                ) : playlists.length === 0 ? (
                  <div className="text-center py-6 glass rounded-xl space-y-2">
                    <p className="text-xs text-muted-foreground">생성된 플레이리스트가 없습니다.</p>
                    <button
                      onClick={() => setIsCreatingNew(true)}
                      className="px-3 py-1.5 rounded-lg bg-[#d4a853] text-black text-xs font-semibold inline-flex items-center gap-1"
                    >
                      <Plus className="w-3 h-3" /> 첫 플레이리스트 만들기
                    </button>
                  </div>
                ) : (
                  playlists.map((pl) => {
                    const pId = pl.id || pl.name;
                    const isSaving = savingId === pId;
                    const isSaved = savedId === pId;

                    return (
                      <div
                        key={pId}
                        onClick={() => !isSaving && !isSaved && handleAddToPlaylist(pl)}
                        className={`flex items-center justify-between p-2.5 rounded-xl border transition-all cursor-pointer ${
                          isSaved
                            ? 'bg-green-500/20 border-green-500 text-green-400'
                            : 'bg-white/5 border-white/5 hover:bg-white/10 hover:border-[#d4a853]/40'
                        }`}
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <div className="w-8 h-8 rounded-lg bg-[#1a1a2e] flex items-center justify-center text-[#d4a853] shrink-0">
                            <Music className="w-4 h-4" />
                          </div>
                          <div className="min-w-0">
                            <h5 className="text-xs font-bold text-white truncate">{pl.title || pl.name}</h5>
                            <p className="text-[10px] text-muted-foreground">{pl.track_count || 0}곡 소장됨</p>
                          </div>
                        </div>


                        <div>
                          {isSaved ? (
                            <span className="text-[11px] font-bold text-green-400 flex items-center gap-1">
                              <Check className="w-3.5 h-3.5" /> 소장됨
                            </span>
                          ) : isSaving ? (
                            <Loader2 className="w-4 h-4 text-[#d4a853] animate-spin" />
                          ) : (
                            <Plus className="w-4 h-4 text-white/50 group-hover:text-white" />
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
