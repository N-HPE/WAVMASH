'use client';

/* ──────────────────────────────────────────────
   WaveMash — Player Context (Hybrid Local & YouTube Audio Engine)
   ────────────────────────────────────────────── */

import React, {
  createContext,
  useContext,
  useRef,
  useState,
  useCallback,
  useEffect,
  type ReactNode,
} from 'react';
import type { Track } from '@/lib/types';
import api from '@/lib/api';

export function extractYoutubeId(urlOrId?: string): string | null {
  if (!urlOrId) return null;
  if (/^[a-zA-Z0-9_-]{11}$/.test(urlOrId)) return urlOrId;
  const match = urlOrId.match(
    /(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})/
  );
  return match ? match[1] : null;
}

function trackSpotifyId(track: Track): string {
  const tid = (track.track_id || '').trim();
  if (tid.startsWith('sp:')) return tid.slice(3);
  if (tid && !tid.startsWith('bp:') && !extractYoutubeId(tid)) return tid;
  return (track.external_id || '').trim();
}

function hasPlayableSource(track: Track): boolean {
  if (track.has_file) return true;
  if (extractYoutubeId(track.url || track.external_id || track.track_id)) {
    return true;
  }
  return Boolean(track.preview_url?.trim());
}

async function resolvePlayableTrack(track: Track): Promise<Track> {
  if (hasPlayableSource(track)) return track;

  try {
    const res = await api.resolveCatalogPreview(
      track.title,
      track.artist || track.primary_artist,
      trackSpotifyId(track)
    );
    if (res.youtube_id) {
      return {
        ...track,
        url: res.youtube_url || `https://www.youtube.com/watch?v=${res.youtube_id}`,
        external_id: res.youtube_id,
        preview_url: res.preview_url || track.preview_url,
        platform: 'youtube',
      };
    }
    if (res.preview_url) {
      return { ...track, preview_url: res.preview_url };
    }
  } catch {
    /* keep original */
  }
  return track;
}

interface PlayerState {
  currentTrack: Track | null;
  isPlaying: boolean;
  progress: number;
  duration: number;
  currentTime: number;
  volume: number;
  queue: Track[];
  queueIndex: number;
  engine: 'audio' | 'youtube' | 'idle';
}

interface PlayerContextValue extends PlayerState {
  play: (track: Track, queue?: Track[]) => void;
  pause: () => void;
  resume: () => void;
  togglePlay: () => void;
  next: () => void;
  prev: () => void;
  setVolume: (v: number) => void;
  seekTo: (percent: number) => void;
  addToQueue: (track: Track) => void;
}

const PlayerContext = createContext<PlayerContextValue | null>(null);

declare global {
  interface Window {
    YT: any;
    onYouTubeIframeAPIReady: () => void;
  }
}

export function PlayerProvider({ children }: { children: ReactNode }) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const ytPlayerRef = useRef<any>(null);
  const isYtReadyRef = useRef(false);
  const pendingYtIdRef = useRef<string | null>(null);
  const unmuteAfterPlayRef = useRef(false);
  const volumeRef = useRef(0.8);
  const playRef = useRef<(track: Track, queue?: Track[]) => void>(() => {});
  const playTrackRef = useRef<
    (track: Track, queue?: Track[], opts?: { fromAuto?: boolean }) => void
  >(() => {});
  const advanceRef = useRef<() => void>(() => {});
  const tickerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const resolveCacheRef = useRef<Map<string, Track>>(new Map());
  const prefetchingRef = useRef<Set<string>>(new Set());
  const playGenRef = useRef(0);
  /** loadVideoById 직후 스퓨리어스 ENDED 무시 */
  const ignoreEndedUntilRef = useRef(0);

  const [state, setState] = useState<PlayerState>({
    currentTrack: null,
    isPlaying: false,
    progress: 0,
    duration: 0,
    currentTime: 0,
    volume: 0.8,
    queue: [],
    queueIndex: -1,
    engine: 'idle',
  });
  const stateRef = useRef(state);
  stateRef.current = state;

  const startYtVideo = useCallback((ytId: string) => {
    const player = ytPlayerRef.current;
    if (!player?.loadVideoById || !isYtReadyRef.current) {
      pendingYtIdRef.current = ytId;
      return false;
    }
    try {
      // 자동재생 정책 우회: mute → play → PLAYING 후 unmute
      unmuteAfterPlayRef.current = true;
      if (player.mute) player.mute();
      player.loadVideoById({ videoId: ytId, startSeconds: 0 });
      if (player.playVideo) player.playVideo();
      pendingYtIdRef.current = null;
      return true;
    } catch (err) {
      console.warn('YT loadVideoById failed:', err);
      pendingYtIdRef.current = ytId;
      return false;
    }
  }, []);

  const bindAudioEnded = useCallback((audio: HTMLAudioElement) => {
    if ((audio as HTMLAudioElement & { __wmEndedBound?: boolean }).__wmEndedBound) {
      return;
    }
    (audio as HTMLAudioElement & { __wmEndedBound?: boolean }).__wmEndedBound =
      true;
    audio.addEventListener('ended', () => {
      advanceRef.current();
    });
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    let pollTimer: ReturnType<typeof setInterval> | null = null;

    function initYtPlayer() {
      if (ytPlayerRef.current || !window.YT?.Player) return;
      const el = document.getElementById('wavemash-hidden-yt-player');
      if (!el) return;

      try {
        ytPlayerRef.current = new window.YT.Player('wavemash-hidden-yt-player', {
          height: '180',
          width: '320',
          playerVars: {
            playsinline: 1,
            controls: 0,
            disablekb: 1,
            fs: 0,
            rel: 0,
            modestbranding: 1,
            origin: window.location.origin,
          },
          events: {
            onReady: () => {
              isYtReadyRef.current = true;
              try {
                ytPlayerRef.current?.setVolume?.(volumeRef.current * 100);
              } catch {
                /* ignore */
              }
              if (pendingYtIdRef.current) {
                startYtVideo(pendingYtIdRef.current);
              }
            },
            onStateChange: (event: { data: number }) => {
              // 1 PLAYING, 2 PAUSED, 0 ENDED
              if (event.data === 1) {
                if (unmuteAfterPlayRef.current) {
                  unmuteAfterPlayRef.current = false;
                  try {
                    ytPlayerRef.current?.unMute?.();
                    ytPlayerRef.current?.setVolume?.(volumeRef.current * 100);
                  } catch {
                    /* ignore */
                  }
                }
                setState((prev) => ({ ...prev, isPlaying: true }));
              } else if (event.data === 2) {
                setState((prev) => ({ ...prev, isPlaying: false }));
              } else if (event.data === 0) {
                if (Date.now() < ignoreEndedUntilRef.current) return;
                setState((prev) => ({ ...prev, isPlaying: false }));
                setTimeout(() => advanceRef.current(), 0);
              }
            },
            onError: (e: { data?: number }) => {
              console.warn('YouTube Player error:', e?.data ?? e);
              unmuteAfterPlayRef.current = false;
              const prev = stateRef.current;
              const fallback = prev.currentTrack?.preview_url?.trim();
              if (fallback) {
                try {
                  if (!audioRef.current) {
                    audioRef.current = new Audio();
                    audioRef.current.volume = volumeRef.current;
                    bindAudioEnded(audioRef.current);
                  }
                  const audio = audioRef.current;
                  audio.src = fallback;
                  void audio.play().catch(() => {});
                  setState((s) => ({
                    ...s,
                    isPlaying: true,
                    engine: 'audio',
                  }));
                  return;
                } catch {
                  /* fall through */
                }
              }
              // 재생 불가 시 다음 곡으로
              setTimeout(() => advanceRef.current(), 0);
            },
          },
        });
      } catch (err) {
        console.warn('Failed to init YT player:', err);
      }
    }

    function ensureYtApi() {
      if (window.YT?.Player) {
        initYtPlayer();
        return;
      }
      if (!document.querySelector('script[src*="youtube.com/iframe_api"]')) {
        const tag = document.createElement('script');
        tag.src = 'https://www.youtube.com/iframe_api';
        document.head.appendChild(tag);
      }
      const prev = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => {
        if (typeof prev === 'function') prev();
        initYtPlayer();
      };
      pollTimer = setInterval(() => {
        if (window.YT?.Player) {
          if (pollTimer) clearInterval(pollTimer);
          initYtPlayer();
        }
      }, 200);
    }

    ensureYtApi();

    return () => {
      if (pollTimer) clearInterval(pollTimer);
    };
  }, [startYtVideo, bindAudioEnded]);

  const getAudio = useCallback(() => {
    if (!audioRef.current && typeof window !== 'undefined') {
      audioRef.current = new Audio();
      audioRef.current.volume = volumeRef.current;
      bindAudioEnded(audioRef.current);
    } else if (audioRef.current) {
      bindAudioEnded(audioRef.current);
    }
    return audioRef.current;
  }, [bindAudioEnded]);

  useEffect(() => {
    if (state.isPlaying) {
      tickerRef.current = setInterval(() => {
        if (state.engine === 'youtube' && ytPlayerRef.current?.getCurrentTime) {
          try {
            const cur = ytPlayerRef.current.getCurrentTime() || 0;
            const dur = ytPlayerRef.current.getDuration() || 0;
            setState((prev) => ({
              ...prev,
              currentTime: cur,
              duration: dur,
              progress: dur > 0 ? (cur / dur) * 100 : 0,
            }));
          } catch {
            /* ignore */
          }
        } else if (state.engine === 'audio' && audioRef.current) {
          const cur = audioRef.current.currentTime || 0;
          const dur = audioRef.current.duration || 0;
          setState((prev) => ({
            ...prev,
            currentTime: cur,
            duration: dur,
            progress: dur > 0 ? (cur / dur) * 100 : 0,
          }));
        }
      }, 500);
    } else if (tickerRef.current) {
      clearInterval(tickerRef.current);
    }

    return () => {
      if (tickerRef.current) clearInterval(tickerRef.current);
    };
  }, [state.isPlaying, state.engine]);

  const playNow = useCallback(
    (track: Track, queue?: Track[]) => {
      const newQueue = queue || [track];
      const idx = newQueue.findIndex((t) => t.track_id === track.track_id);
      const ytId = extractYoutubeId(
        track.url || track.external_id || track.track_id
      );
      const previewUrl = track.preview_url?.trim();

      if (track.has_file) {
        pendingYtIdRef.current = null;
        if (ytPlayerRef.current?.pauseVideo) {
          try {
            ytPlayerRef.current.pauseVideo();
          } catch {
            /* ignore */
          }
        }
        const audio = getAudio();
        if (audio) {
          audio.src = api.getStreamUrl(track.track_id);
          void audio.play().catch(() => {});
        }
        setState((prev) => ({
          ...prev,
          currentTrack: track,
          isPlaying: true,
          progress: 0,
          currentTime: 0,
          queue: newQueue,
          queueIndex: idx >= 0 ? idx : 0,
          engine: 'audio',
        }));
        return;
      }

      if (ytId) {
        if (audioRef.current) audioRef.current.pause();
        ignoreEndedUntilRef.current = Date.now() + 1800;
        setState((prev) => ({
          ...prev,
          currentTrack: track,
          isPlaying: true,
          progress: 0,
          currentTime: 0,
          queue: newQueue,
          queueIndex: idx >= 0 ? idx : 0,
          engine: 'youtube',
        }));
        if (!startYtVideo(ytId)) {
          let tries = 0;
          const timer = setInterval(() => {
            tries += 1;
            if (startYtVideo(ytId) || tries >= 40) clearInterval(timer);
          }, 250);
        }
        return;
      }

      if (previewUrl) {
        pendingYtIdRef.current = null;
        if (ytPlayerRef.current?.pauseVideo) {
          try {
            ytPlayerRef.current.pauseVideo();
          } catch {
            /* ignore */
          }
        }
        const audio = getAudio();
        if (audio) {
          audio.src = previewUrl;
          void audio.play().catch(() => {});
        }
        setState((prev) => ({
          ...prev,
          currentTrack: track,
          isPlaying: true,
          progress: 0,
          currentTime: 0,
          queue: newQueue,
          queueIndex: idx >= 0 ? idx : 0,
          engine: 'audio',
        }));
        return;
      }

      pendingYtIdRef.current = null;
      if (audioRef.current) audioRef.current.pause();
      if (ytPlayerRef.current?.pauseVideo) {
        try {
          ytPlayerRef.current.pauseVideo();
        } catch {
          /* ignore */
        }
      }
      setState((prev) => ({
        ...prev,
        currentTrack: track,
        isPlaying: false,
        progress: 0,
        currentTime: 0,
        duration: 0,
        queue: newQueue,
        queueIndex: idx >= 0 ? idx : 0,
        engine: 'idle',
      }));
    },
    [getAudio, startYtVideo]
  );

  const mergeResolvedIntoQueue = useCallback(
    (queue: Track[], resolved: Track): Track[] =>
      queue.map((t) => (t.track_id === resolved.track_id ? resolved : t)),
    []
  );

  const playTrack = useCallback(
    (track: Track, queue?: Track[], opts?: { fromAuto?: boolean }) => {
      const gen = ++playGenRef.current;
      const baseQueue =
        queue ||
        (stateRef.current.queue.length > 0
          ? stateRef.current.queue
          : [track]);

      const cached = resolveCacheRef.current.get(track.track_id);
      const starter = cached && hasPlayableSource(cached) ? cached : track;

      if (hasPlayableSource(starter)) {
        playNow(starter, mergeResolvedIntoQueue(baseQueue, starter));
        return;
      }

      // UI는 바로 전환, 소스는 백그라운드 해석
      const idx = baseQueue.findIndex((t) => t.track_id === track.track_id);
      setState((prev) => ({
        ...prev,
        currentTrack: track,
        isPlaying: true,
        progress: 0,
        currentTime: 0,
        duration: 0,
        queue: baseQueue,
        queueIndex: idx >= 0 ? idx : 0,
        engine: 'idle',
      }));

      void (async () => {
        const resolved = await resolvePlayableTrack(track);
        if (gen !== playGenRef.current) return;

        if (hasPlayableSource(resolved)) {
          resolveCacheRef.current.set(resolved.track_id, resolved);
          playNow(resolved, mergeResolvedIntoQueue(baseQueue, resolved));
          return;
        }

        // 해석 실패 → 다음 곡으로 (자동 연속 재생)
        if (opts?.fromAuto !== false) {
          const q = stateRef.current.queue;
          const i = stateRef.current.queueIndex;
          if (i + 1 < q.length) {
            playTrackRef.current(q[i + 1], q, { fromAuto: true });
            return;
          }
        }
        setState((prev) => ({ ...prev, isPlaying: false, engine: 'idle' }));
      })();
    },
    [playNow, mergeResolvedIntoQueue]
  );

  playRef.current = (track, queue) => playTrack(track, queue);
  playTrackRef.current = playTrack;

  const advance = useCallback(() => {
    const { queue, queueIndex } = stateRef.current;
    if (!queue.length || queueIndex < 0) {
      setState((prev) => ({ ...prev, isPlaying: false }));
      return;
    }
    const nextIdx = queueIndex + 1;
    if (nextIdx >= queue.length) {
      // 큐 끝에서 정지 (반복 없음)
      setState((prev) => ({ ...prev, isPlaying: false, progress: 100 }));
      return;
    }
    playTrackRef.current(queue[nextIdx], queue, { fromAuto: true });
  }, []);

  advanceRef.current = advance;

  // 다음 1~2곡 YouTube 미리 해석 (끊김 최소화)
  useEffect(() => {
    const { queue, queueIndex } = state;
    if (queueIndex < 0 || !queue.length) return;

    const targets = [queue[queueIndex + 1], queue[queueIndex + 2]].filter(
      Boolean
    ) as Track[];

    for (const t of targets) {
      if (hasPlayableSource(t)) continue;
      if (resolveCacheRef.current.has(t.track_id)) continue;
      if (prefetchingRef.current.has(t.track_id)) continue;
      prefetchingRef.current.add(t.track_id);
      void resolvePlayableTrack(t)
        .then((resolved) => {
          if (!hasPlayableSource(resolved)) return;
          resolveCacheRef.current.set(resolved.track_id, resolved);
          setState((prev) => ({
            ...prev,
            queue: prev.queue.map((row) =>
              row.track_id === resolved.track_id ? resolved : row
            ),
          }));
        })
        .finally(() => {
          prefetchingRef.current.delete(t.track_id);
        });
    }
  }, [state.queue, state.queueIndex]);

  const play = useCallback(
    (track: Track, queue?: Track[]) => {
      playTrack(track, queue);
    },
    [playTrack]
  );

  const pause = useCallback(() => {
    if (state.engine === 'youtube') {
      try {
        ytPlayerRef.current?.pauseVideo();
      } catch {
        /* ignore */
      }
    } else {
      audioRef.current?.pause();
    }
    setState((prev) => ({ ...prev, isPlaying: false }));
  }, [state.engine]);

  const resume = useCallback(() => {
    if (state.engine === 'youtube') {
      try {
        unmuteAfterPlayRef.current = true;
        ytPlayerRef.current?.mute?.();
        ytPlayerRef.current?.playVideo();
      } catch {
        /* ignore */
      }
    } else if (state.engine === 'audio') {
      void audioRef.current?.play().catch(() => {});
    } else if (state.currentTrack) {
      playTrack(state.currentTrack, state.queue);
      return;
    }
    setState((prev) => ({ ...prev, isPlaying: true }));
  }, [state.engine, state.currentTrack, state.queue, playTrack]);

  const togglePlay = useCallback(() => {
    if (state.isPlaying) pause();
    else resume();
  }, [state.isPlaying, pause, resume]);

  const next = useCallback(() => {
    const { queue, queueIndex } = stateRef.current;
    if (queue.length === 0) return;
    const nextIdx = queueIndex + 1;
    if (nextIdx >= queue.length) {
      // 수동 next는 처음으로
      playTrack(queue[0], queue);
      return;
    }
    playTrack(queue[nextIdx], queue);
  }, [playTrack]);

  const prev = useCallback(() => {
    const { queue, queueIndex, currentTime } = stateRef.current;
    if (queue.length === 0) return;
    // 3초 이상 재생 중이면 곡 처음으로
    if (currentTime > 3) {
      if (stateRef.current.engine === 'youtube') {
        try {
          ytPlayerRef.current?.seekTo(0, true);
        } catch {
          /* ignore */
        }
      } else if (audioRef.current) {
        audioRef.current.currentTime = 0;
      }
      setState((s) => ({ ...s, currentTime: 0, progress: 0 }));
      return;
    }
    const prevIdx = (queueIndex - 1 + queue.length) % queue.length;
    playTrack(queue[prevIdx], queue);
  }, [playTrack]);

  const setVolume = useCallback((v: number) => {
    const clamped = Math.max(0, Math.min(1, v));
    volumeRef.current = clamped;
    if (audioRef.current) audioRef.current.volume = clamped;
    try {
      ytPlayerRef.current?.setVolume?.(clamped * 100);
    } catch {
      /* ignore */
    }
    setState((prev) => ({ ...prev, volume: clamped }));
  }, []);

  const seekTo = useCallback(
    (percent: number) => {
      const targetSec = (percent / 100) * state.duration;
      if (state.engine === 'youtube') {
        try {
          ytPlayerRef.current?.seekTo(targetSec, true);
        } catch {
          /* ignore */
        }
      } else if (audioRef.current) {
        audioRef.current.currentTime = targetSec;
      }
      setState((prev) => ({
        ...prev,
        progress: percent,
        currentTime: targetSec,
      }));
    },
    [state.duration, state.engine]
  );

  const addToQueue = useCallback((track: Track) => {
    setState((prev) => ({
      ...prev,
      queue: [...prev.queue, track],
    }));
  }, []);

  const value: PlayerContextValue = {
    ...state,
    play,
    pause,
    resume,
    togglePlay,
    next,
    prev,
    setVolume,
    seekTo,
    addToQueue,
  };

  return (
    <PlayerContext.Provider value={value}>
      {children}
      {/* Off-screen but real-sized — 1×1 / opacity-0 breaks YT playback */}
      <div
        id="wavemash-hidden-yt-player-container"
        className="pointer-events-none fixed bottom-0 right-0 z-[-1] h-[180px] w-[320px] overflow-hidden"
        style={{ opacity: 0.01 }}
        aria-hidden
      >
        <div id="wavemash-hidden-yt-player" />
      </div>
    </PlayerContext.Provider>
  );
}

export function usePlayer(): PlayerContextValue {
  const ctx = useContext(PlayerContext);
  if (!ctx) {
    throw new Error('usePlayer must be used within a PlayerProvider');
  }
  return ctx;
}
