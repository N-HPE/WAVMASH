'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Search,
  Disc3,
  Loader2,
  Sparkles,
  Zap,
  Moon,
  Crown,
  Check,
} from 'lucide-react';
import api from '@/lib/api';
import type { CatalogAlbum, MasterAlbumCreate } from '@/lib/types';

interface CollectAlbumModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAlbumCollected: () => void;
  defaultArtisan?: 'nova' | 'echo' | 'yachi' | 'personal';
}

const ARTISANS = [
  {
    id: 'nova',
    label: 'Nova',
    desc: '클럽 · 일렉트로닉 · UKG',
    icon: Zap,
    color: 'border-violet-500/40 bg-violet-500/10 text-violet-300',
    activeColor: 'bg-violet-600 text-white border-violet-400',
  },
  {
    id: 'echo',
    label: 'Echo',
    desc: '인디 · R&B · 힙합 · 컬처',
    icon: Sparkles,
    color: 'border-rose-500/40 bg-rose-500/10 text-rose-300',
    activeColor: 'bg-rose-600 text-white border-rose-400',
  },
  {
    id: 'yachi',
    label: 'Yachi',
    desc: '미니멀 · 재즈 · 오디오필',
    icon: Moon,
    color: 'border-cyan-500/40 bg-cyan-500/10 text-cyan-300',
    activeColor: 'bg-cyan-600 text-white border-cyan-400',
  },
  {
    id: 'personal',
    label: '내 명반',
    desc: '나만의 올타임 클래식',
    icon: Crown,
    color: 'border-[#d4a853]/40 bg-[#d4a853]/10 text-[#d4a853]',
    activeColor: 'bg-[#d4a853] text-black border-amber-300',
  },
] as const;

export default function CollectAlbumModal({
  isOpen,
  onClose,
  onAlbumCollected,
  defaultArtisan = 'nova',
}: CollectAlbumModalProps) {
  const [query, setQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<CatalogAlbum[]>([]);
  const [selectedAlbum, setSelectedAlbum] = useState<CatalogAlbum | null>(null);
  const [artisan, setArtisan] = useState<'nova' | 'echo' | 'yachi' | 'personal'>(
    defaultArtisan
  );
  const [curatorNote, setCuratorNote] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const q = query.trim();
    if (!q) return;

    setSearching(true);
    try {
      const res = await api.searchCatalog(q);
      const foundAlbums = res.albums || [];
      setResults(foundAlbums);
    } catch (err) {
      console.error('Failed to search albums:', err);
    } finally {
      setSearching(false);
    }
  };

  const handleCollect = async () => {
    if (!selectedAlbum || saving) return;
    setSaving(true);
    try {
      const payload: MasterAlbumCreate = {
        id: selectedAlbum.id,
        title: selectedAlbum.name,
        artist: selectedAlbum.artist,
        cover_url: selectedAlbum.thumbnail_url,
        year: (selectedAlbum.release_date || '').slice(0, 4),
        genre: selectedAlbum.album_type === 'single' ? 'Single' : 'Album',
        total_tracks: selectedAlbum.total_tracks,
        spotify_url: selectedAlbum.spotify_url,
        artisan: artisan,
        curator_note:
          curatorNote.trim() || `${selectedAlbum.artist}의 대표 명반`,
      };

      await api.collectMasterAlbum(payload);
      onAlbumCollected();
      onClose();
      // Reset state
      setSelectedAlbum(null);
      setQuery('');
      setResults([]);
      setCuratorNote('');
    } catch (err) {
      console.error('Failed to collect album:', err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-xl max-h-[90vh] overflow-y-auto bg-[#13131c] border-white/10 text-white">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#d4a853]/15 text-[#d4a853]">
              <Disc3 className="h-4 w-4" />
            </span>
            <DialogTitle className="text-lg font-bold">
              명반 수집하기 (Collect Album)
            </DialogTitle>
          </div>
          <DialogDescription className="text-xs text-muted-foreground">
            Spotify 음악 카탈로그에서 명반을 검색하고, 아티산의 추천 이유와 함께
            내 바이닐 보관소에 저장합니다.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Step 1: Album Search */}
          {!selectedAlbum ? (
            <div className="space-y-3">
              <form onSubmit={handleSearch} className="flex gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    type="search"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="앨범 이름 또는 아티스트명 (예: Daft Punk, Blonde, 류이치 사카모토)"
                    className="pl-9 bg-secondary/50 border-border text-sm text-white focus-visible:ring-[#d4a853]"
                  />
                </div>
                <Button
                  type="submit"
                  disabled={searching || !query.trim()}
                  className="bg-[#d4a853] text-black hover:bg-[#b58c3f] font-semibold shrink-0"
                >
                  {searching ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    '검색'
                  )}
                </Button>
              </form>

              {/* Search Results */}
              <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                {searching ? (
                  <div className="py-12 text-center text-xs text-muted-foreground">
                    <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2 text-[#d4a853]" />
                    명반 카탈로그를 탐색 중...
                  </div>
                ) : results.length > 0 ? (
                  results.map((al) => (
                    <div
                      key={al.id}
                      onClick={() => setSelectedAlbum(al)}
                      className="flex items-center gap-3 p-2.5 rounded-xl border border-white/5 hover:border-[#d4a853]/50 bg-secondary/20 hover:bg-secondary/40 transition-all cursor-pointer group"
                    >
                      <div className="h-12 w-12 rounded-lg overflow-hidden bg-black/40 shrink-0 border border-white/10 shadow">
                        {al.thumbnail_url ? (
                          <img
                            src={al.thumbnail_url}
                            alt=""
                            className="h-full w-full object-cover group-hover:scale-105 transition-transform"
                          />
                        ) : (
                          <Disc3 className="h-6 w-6 m-auto text-zinc-600" />
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-white truncate group-hover:text-[#d4a853] transition-colors">
                          {al.name}
                        </p>
                        <p className="text-xs text-muted-foreground truncate">
                          {al.artist} · {(al.release_date || '').slice(0, 4)} ·{' '}
                          {al.total_tracks}곡
                        </p>
                      </div>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-xs text-[#d4a853] opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        선택
                      </Button>
                    </div>
                  ))
                ) : query && !searching ? (
                  <div className="py-8 text-center text-xs text-muted-foreground">
                    검색된 앨범이 없습니다. 다른 키워드로 검색해 보세요.
                  </div>
                ) : null}
              </div>
            </div>
          ) : (
            /* Step 2: Configure Artisan & Review */
            <div className="space-y-4">
              {/* Selected Album Preview Card */}
              <div className="flex items-center justify-between p-3 rounded-xl border border-[#d4a853]/40 bg-[#d4a853]/5">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="h-14 w-14 rounded-lg overflow-hidden shrink-0 border border-white/10 shadow-md">
                    <img
                      src={selectedAlbum.thumbnail_url}
                      alt=""
                      className="h-full w-full object-cover"
                    />
                  </div>
                  <div className="min-w-0 flex-1">
                    <span className="text-[10px] text-[#d4a853] font-semibold uppercase">
                      선택된 명반
                    </span>
                    <h4 className="text-sm font-bold text-white truncate">
                      {selectedAlbum.name}
                    </h4>
                    <p className="text-xs text-muted-foreground truncate">
                      {selectedAlbum.artist} ·{' '}
                      {(selectedAlbum.release_date || '').slice(0, 4)}
                    </p>
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setSelectedAlbum(null)}
                  className="text-xs text-muted-foreground hover:text-white"
                >
                  변경
                </Button>
              </div>

              {/* Artisan Choice */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-zinc-300 block">
                  어떤 아티산의 큐레이션으로 수집할까요?
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {ARTISANS.map((a) => {
                    const Icon = a.icon;
                    const isSelected = artisan === a.id;
                    return (
                      <button
                        key={a.id}
                        type="button"
                        onClick={() => setArtisan(a.id as any)}
                        className={`flex items-start gap-2.5 p-3 rounded-xl border text-left transition-all cursor-pointer ${
                          isSelected
                            ? a.activeColor + ' shadow-lg'
                            : 'border-white/10 bg-secondary/20 hover:bg-secondary/40 text-zinc-300'
                        }`}
                      >
                        <Icon className="h-4 w-4 shrink-0 mt-0.5" />
                        <div className="min-w-0">
                          <p className="text-xs font-bold leading-tight">
                            {a.label}
                          </p>
                          <p className="text-[10px] opacity-80 truncate mt-0.5">
                            {a.desc}
                          </p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Curator Note / Review */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-zinc-300 block">
                  명반 추천 코멘트 / 헌사 (Liner Note)
                </label>
                <Textarea
                  value={curatorNote}
                  onChange={(e) => setCuratorNote(e.target.value)}
                  placeholder="예: 프렌치 터치 하우스의 정점. 인트로의 신스 루프부터 마지막 트랙까지 완벽한 사운드스케이프."
                  className="bg-secondary/40 border-border text-sm text-white resize-none h-20 placeholder:text-zinc-500"
                />
              </div>

              {/* Submit Button */}
              <div className="flex items-center justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={onClose}
                  className="text-xs text-muted-foreground hover:text-white"
                >
                  취소
                </Button>
                <Button
                  type="button"
                  onClick={handleCollect}
                  disabled={saving}
                  className="bg-[#d4a853] text-black hover:bg-[#b58c3f] font-bold text-xs"
                >
                  {saving ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />
                  ) : (
                    <Check className="h-3.5 w-3.5 mr-1.5" />
                  )}
                  명반 라이브러리에 저장
                </Button>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
