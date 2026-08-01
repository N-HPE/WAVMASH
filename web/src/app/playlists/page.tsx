'use client';

/* ──────────────────────────────────────────────
   WaveMash — 플레이리스트 페이지
   블록 뷰 / 장르별 리스트 토글
   ────────────────────────────────────────────── */

import { useEffect, useState, useCallback } from 'react';
import {
  Plus,
  Sparkles,
  Loader2,
  LayoutGrid,
  List,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import api from '@/lib/api';
import type { Playlist, PlaylistViewMode } from '@/lib/types';
import {
  VIBE_CATEGORIES,
  getVibeColor,
  type VibeId,
} from '@/lib/vibePalette';
import PlaylistGrid from '@/components/PlaylistGrid';
import PlaylistListByGenre from '@/components/PlaylistListByGenre';
import SpotifySyncManager from '@/components/SpotifySyncManager';

const VIEW_STORAGE_KEY = 'wavemash_playlist_view_mode';

export default function PlaylistsPage() {
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newName, setNewName] = useState('');
  const [newVibe, setNewVibe] = useState<VibeId>('pop');
  const [newShade, setNewShade] = useState(0);
  const [creating, setCreating] = useState(false);
  const [autoParsing, setAutoParsing] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [showSync, setShowSync] = useState(false);
  const [viewMode, setViewMode] = useState<PlaylistViewMode>('list');

  useEffect(() => {
    try {
      const saved = localStorage.getItem(VIEW_STORAGE_KEY);
      if (saved === 'block' || saved === 'list') setViewMode(saved);
    } catch { /* ignore */ }
  }, []);

  const changeViewMode = useCallback((mode: PlaylistViewMode) => {
    setViewMode(mode);
    try {
      localStorage.setItem(VIEW_STORAGE_KEY, mode);
    } catch { /* ignore */ }
  }, []);

  const fetchPlaylists = useCallback(async () => {
    try {
      const data = await api.getPlaylists();
      setPlaylists(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : '플레이리스트를 불러올 수 없습니다.'
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchPlaylists(); }, [fetchPlaylists]);

  const handleCreate = useCallback(async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await api.createPlaylist({
        name: newName.trim(),
        vibe: newVibe,
        shade: newShade,
        color: getVibeColor(newVibe, newShade),
      });
      setNewName('');
      setNewVibe('pop');
      setNewShade(0);
      setDialogOpen(false);
      fetchPlaylists();
    } catch { /* */ } finally { setCreating(false); }
  }, [newName, newVibe, newShade, fetchPlaylists]);

  const handleAutoParse = useCallback(async () => {
    setAutoParsing(true);
    try { await api.autoParsePlaylist(); fetchPlaylists(); }
    catch { /* */ } finally { setAutoParsing(false); }
  }, [fetchPlaylists]);

  const handleAssignVibe = useCallback(
    async (playlist: Playlist, vibe: VibeId, shade: number) => {
      try {
        await api.updatePlaylist(playlist.name, {
          vibe,
          shade,
          color: getVibeColor(vibe, shade),
        });
        fetchPlaylists();
      } catch { /* */ }
    },
    [fetchPlaylists],
  );

  const selectedCategory = VIBE_CATEGORIES.find((c) => c.id === newVibe)!;

  if (loading) {
    return (
      <div className="px-4 py-3">
        <Skeleton className="w-full rounded-lg skeleton-shimmer" style={{ height: 'calc(100vh - 140px)' }} />
      </div>
    );
  }

  return (
    <div className="px-4 py-2 flex flex-col" style={{ height: 'calc(100vh - 64px)' }}>

      <div className="flex items-center justify-between mb-2 shrink-0 gap-2">
        <span className="text-[11px] text-white/30 tabular-nums">
          {playlists.length} / 30
          {playlists.filter((p) => p.source === 'spotify' || p.sync_id).length > 0 && (
            <span className="ml-2 text-[#1DB954]/70">
              · Spotify {playlists.filter((p) => p.source === 'spotify' || p.sync_id).length}
            </span>
          )}
        </span>
        <div className="flex items-center gap-1 flex-wrap justify-end">
          {!showSync && (
            <div className="flex items-center gap-0.5 glass rounded-lg p-0.5">
              <Button
                variant={viewMode === 'block' ? 'secondary' : 'ghost'}
                size="icon"
                className="h-6 w-6"
                title="블록 보기"
                onClick={() => changeViewMode('block')}
              >
                <LayoutGrid className="h-3 w-3" />
              </Button>
              <Button
                variant={viewMode === 'list' ? 'secondary' : 'ghost'}
                size="icon"
                className="h-6 w-6"
                title="장르별 리스트"
                onClick={() => changeViewMode('list')}
              >
                <List className="h-3 w-3" />
              </Button>
            </div>
          )}
          <button
            type="button"
            onClick={() => setShowSync(!showSync)}
            className={`text-[10px] transition-colors px-2 py-1 cursor-pointer rounded ${
              showSync
                ? 'text-[#1DB954] bg-[#1DB954]/10'
                : 'text-white/30 hover:text-white/60'
            }`}
          >
            {showSync ? '플리 보기' : 'Spotify 동기화'}
          </button>
          {!showSync && (
            <>
              <Button variant="outline" size="sm" onClick={handleAutoParse} disabled={autoParsing} className="gap-1 h-6 text-[10px] px-2">
                {autoParsing ? <Loader2 className="h-2.5 w-2.5 animate-spin" /> : <Sparkles className="h-2.5 w-2.5" />}
                자동 분류
              </Button>
              <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                <DialogTrigger render={<Button size="sm" className="bg-primary text-primary-foreground gap-1 h-6 text-[10px] px-2" />}>
                  <Plus className="h-2.5 w-2.5" /> 추가
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader><DialogTitle>새 로컬 플레이리스트</DialogTitle></DialogHeader>
                  <div className="space-y-4 pt-2">
                    <p className="text-[11px] text-white/40">
                      로컬 전용 플리입니다. Spotify와 연동하려면 「Spotify 동기화」에서 링크를 등록하세요.
                    </p>
                    <input
                      type="text"
                      value={newName}
                      onChange={(e) => setNewName(e.target.value)}
                      placeholder="플레이리스트 이름..."
                      className="w-full h-10 rounded-lg bg-white/5 border border-white/6 px-3 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:ring-1 focus:ring-[#d4a853]/50"
                      onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                    />

                    <div className="space-y-2">
                      <label className="text-[11px] text-white/40">바이브 / 장르</label>
                      <div className="flex flex-wrap gap-1.5">
                        {VIBE_CATEGORIES.map((cat) => (
                          <button
                            key={cat.id}
                            type="button"
                            onClick={() => { setNewVibe(cat.id); setNewShade(0); }}
                            className={`flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] transition-colors border ${
                              newVibe === cat.id
                                ? 'border-white/30 bg-white/10 text-white/90'
                                : 'border-white/8 text-white/45 hover:border-white/20'
                            }`}
                          >
                            <span
                              className="w-2.5 h-2.5 rounded-sm"
                              style={{ background: cat.shades[0].hex }}
                            />
                            {cat.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label className="text-[11px] text-white/40">톤 (밝기 / 세부)</label>
                      <div className="flex flex-wrap gap-1.5">
                        {selectedCategory.shades.map((s) => (
                          <button
                            key={s.shade}
                            type="button"
                            onClick={() => setNewShade(s.shade)}
                            className={`flex items-center gap-1.5 rounded-md px-2 py-1.5 text-[11px] transition-colors border ${
                              newShade === s.shade
                                ? 'border-white/30 bg-white/10 text-white/90'
                                : 'border-white/8 text-white/45 hover:border-white/20'
                            }`}
                          >
                            <span
                              className="w-4 h-4 rounded"
                              style={{ background: s.hex, boxShadow: `0 0 0 1px ${s.hex}55` }}
                            />
                            {s.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="flex justify-end gap-2">
                      <Button variant="ghost" size="sm" onClick={() => setDialogOpen(false)}>취소</Button>
                      <Button size="sm" onClick={handleCreate} disabled={!newName.trim() || creating} className="bg-primary text-primary-foreground">
                        {creating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : '만들기'}
                      </Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="glass rounded-lg p-3 text-center mb-2 shrink-0">
          <p className="text-xs text-muted-foreground">{error}</p>
        </div>
      )}

      <div className="flex-1 min-h-0">
        {showSync ? (
          <div className="h-full overflow-y-auto max-w-4xl mx-auto pt-2 pb-6">
            <SpotifySyncManager onSyncComplete={fetchPlaylists} />
          </div>
        ) : viewMode === 'block' ? (
          <PlaylistGrid playlists={playlists} onPlaylistClick={(p) => console.log('click', p.name)} />
        ) : (
          <PlaylistListByGenre
            playlists={playlists}
            onPlaylistClick={(p) => console.log('click', p.name)}
            onAssignVibe={handleAssignVibe}
          />
        )}
      </div>
    </div>
  );
}
