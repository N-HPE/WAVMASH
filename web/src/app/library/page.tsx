'use client';

import { useEffect, useState, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Disc3,
  Plus,
  RotateCcw,
  Zap,
  Sparkles,
  Moon,
  Crown,
  Layers,
  Loader2,
  Trash2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';
import type { MasterAlbum } from '@/lib/types';
import MasterAlbumCard from '@/components/MasterAlbumCard';
import CollectAlbumModal from '@/components/CollectAlbumModal';

type ArtisanTab = 'all' | 'nova' | 'echo' | 'yachi' | 'personal';

const ARTISAN_TABS: Array<{
  id: ArtisanTab;
  label: string;
  subtitle: string;
  icon: any;
  color: string;
}> = [
  {
    id: 'all',
    label: '전체 명반',
    subtitle: '모든 아티산 & 셀렉션',
    icon: Layers,
    color: 'text-white',
  },
  {
    id: 'nova',
    label: 'Nova',
    subtitle: '클럽 · 일렉트로닉 · UKG',
    icon: Zap,
    color: 'text-violet-400',
  },
  {
    id: 'echo',
    label: 'Echo',
    subtitle: '인디 · R&B · 힙합',
    icon: Sparkles,
    color: 'text-rose-400',
  },
  {
    id: 'yachi',
    label: 'Yachi',
    subtitle: '미니멀 · 재즈 · 오디오필',
    icon: Moon,
    color: 'text-cyan-400',
  },
  {
    id: 'personal',
    label: '내 명반',
    subtitle: '개인 소장 클래식',
    icon: Crown,
    color: 'text-[#d4a853]',
  },
];

export default function LibraryPage() {
  const [albums, setAlbums] = useState<MasterAlbum[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<ArtisanTab>('all');
  const [search, setSearch] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [resetting, setResetting] = useState(false);

  const fetchAlbums = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.getMasterAlbums(activeTab, search || undefined);
      setAlbums(data || []);
    } catch (err) {
      console.error('Failed to load master albums:', err);
    } finally {
      setLoading(false);
    }
  }, [activeTab, search]);

  useEffect(() => {
    fetchAlbums();
  }, [fetchAlbums]);

  // Counts per tab
  const counts = useMemo(() => {
    return {
      all: albums.length,
      nova: albums.filter((a) => a.artisan === 'nova').length,
      echo: albums.filter((a) => a.artisan === 'echo').length,
      yachi: albums.filter((a) => a.artisan === 'yachi').length,
      personal: albums.filter((a) => a.artisan === 'personal').length,
    };
  }, [albums]);

  const handleDeleteAlbum = async (albumId: string) => {
    try {
      await api.deleteMasterAlbum(albumId);
      setAlbums((prev) => prev.filter((a) => a.id !== albumId));
    } catch (err) {
      console.error('Failed to delete album:', err);
    }
  };

  const handleResetToDefaults = async () => {
    if (!confirm('라이브러리를 기본 아티산 추천 명반 세트로 초기화하시겠습니까?')) {
      return;
    }
    setResetting(true);
    try {
      // Clear legacy single tracks as requested
      await api.clearLegacyTracks().catch(() => {});
      const res = await api.resetMasterAlbums();
      setAlbums(res);
      setActiveTab('all');
    } catch (err) {
      console.error('Reset failed:', err);
    } finally {
      setResetting(false);
    }
  };

  const currentTabMeta =
    ARTISAN_TABS.find((t) => t.id === activeTab) || ARTISAN_TABS[0];

  return (
    <div className="w-full max-w-7xl mx-auto py-6 px-2 sm:px-6 space-y-6">
      {/* ── Top Header ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border/60 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-[#d4a853]/15 text-[#d4a853]">
              <Disc3 className="h-5 w-5" />
            </span>
            <h1 className="text-2xl font-bold tracking-tight text-white">
              명반 라이브러리
            </h1>
            <span className="rounded-full bg-[#d4a853]/10 px-2.5 py-0.5 text-xs font-semibold text-[#d4a853] border border-[#d4a853]/20">
              Masterpiece Vault
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Nexus 아티산들과 내가 엄선한 바이닐 명반 아카이브입니다. 앨범 단위로
            수집하고 트랙을 청음합니다.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2.5">
          <Button
            size="sm"
            variant="outline"
            onClick={handleResetToDefaults}
            disabled={resetting}
            className="h-9 text-xs border-border hover:bg-secondary text-muted-foreground hover:text-white"
            title="초기화 및 추천 명반 복구"
          >
            {resetting ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />
            ) : (
              <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
            )}
            초기화
          </Button>

          <Button
            size="sm"
            onClick={() => setIsModalOpen(true)}
            className="h-9 bg-[#d4a853] text-black hover:bg-[#b58c3f] font-bold text-xs shadow-lg shadow-[#d4a853]/20"
          >
            <Plus className="h-4 w-4 mr-1.5 stroke-[2.5]" />
            명반 수집하기
          </Button>
        </div>
      </div>

      {/* ── Search & Artisan Tabs ── */}
      <div className="space-y-3">
        {/* Search Bar */}
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="수집한 명반, 아티스트, 큐레이터 노트 검색..."
            className="pl-9 bg-secondary/40 border-border text-sm text-white focus-visible:ring-[#d4a853]"
          />
        </div>

        {/* Artisan Tabs Strip */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
          {ARTISAN_TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            const count = counts[tab.id] ?? 0;

            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition-all border cursor-pointer ${
                  isActive
                    ? 'bg-[#1a1a27] border-[#d4a853]/50 text-white shadow-md'
                    : 'border-white/5 bg-secondary/20 text-muted-foreground hover:text-white hover:bg-secondary/40'
                }`}
              >
                <Icon
                  className={`h-3.5 w-3.5 ${
                    isActive ? tab.color : 'text-muted-foreground'
                  }`}
                />
                <span>{tab.label}</span>
                <span
                  className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                    isActive
                      ? 'bg-[#d4a853]/20 text-[#d4a853]'
                      : 'bg-white/5 text-zinc-400'
                  }`}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Album Grid ── */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-24 gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-[#d4a853]" />
          <p className="text-xs text-muted-foreground">명반 컬렉션을 불러오는 중...</p>
        </div>
      ) : albums.length === 0 ? (
        /* Empty State */
        <div className="rounded-2xl border border-dashed border-border/80 p-16 text-center bg-secondary/10">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-secondary/60 text-[#d4a853] mb-4">
            <Disc3 className="h-7 w-7" />
          </div>
          <h3 className="text-base font-semibold text-white">
            {activeTab === 'all'
              ? '수집된 명반이 없습니다'
              : `${currentTabMeta.label} 탭에 수집된 명반이 없습니다`}
          </h3>
          <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
            Spotify 음악 카탈로그에서 명반을 검색하고, 아티산의 추천 이유와 함께
            소장해 보세요.
          </p>
          <div className="mt-6 flex items-center justify-center gap-3">
            <Button
              onClick={() => setIsModalOpen(true)}
              className="bg-[#d4a853] text-black hover:bg-[#b58c3f] font-semibold text-xs"
            >
              <Plus className="h-4 w-4 mr-1.5" />
              지금 명반 수집하기
            </Button>
          </div>
        </div>
      ) : (
        <motion.div
          layout
          className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5"
        >
          <AnimatePresence>
            {albums.map((album) => (
              <MasterAlbumCard
                key={album.id}
                album={album}
                onDelete={handleDeleteAlbum}
              />
            ))}
          </AnimatePresence>
        </motion.div>
      )}

      {/* ── Collect Album Modal ── */}
      <CollectAlbumModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onAlbumCollected={fetchAlbums}
        defaultArtisan={activeTab === 'all' ? 'nova' : activeTab}
      />
    </div>
  );
}
