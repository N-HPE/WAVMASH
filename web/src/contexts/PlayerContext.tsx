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
  const tickerRef = useRef<ReturnType<typeof setInterval> | null>(null);

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
                setState((prev) => {
                  const { queue, queueIndex } = prev;
                  if (queue.length > 1) {
                    const nextIdx = (queueIndex + 1) % queue.length;
                    setTimeout(() => playRef.current(queue[nextIdx], queue), 0);
                  }
                  return { ...prev, isPlaying: false };
                });
              }
            },
            onError: (e: { data?: number }) => {
              console.warn('YouTube Player error:', e?.data ?? e);
              unmuteAfterPlayRef.current = false;
              setState((prev) => {
                const fallback = prev.currentTrack?.preview_url?.trim();
                if (fallback) {
                  try {
                    if (!audioRef.current) {
                      audioRef.current = new Audio();
                      audioRef.current.volume = volumeRef.current;
                    }
                    const audio = audioRef.current;
                    audio.src = fallback;
                    void audio.play().catch(() => {});
                    return {
                      ...prev,
                      isPlaying: true,
                      engine: 'audio',
                    };
                  } catch {
                    /* fall through */
                  }
                }
                return { ...prev, isPlaying: false, engine: 'idle' };
              });
            },
          },
        });
      } catch (e) {
        console.warn('Failed to init YT player:', e);
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
  }, [startYtVideo]);

  const getAudio = useCallback(() => {
    if (!audioRef.current && typeof window !== 'undefined') {
      audioRef.current = new Audio();
      audioRef.current.volume = volumeRef.current;
    }
    return audioRef.current;
  }, []);

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

  const play = useCallback(
    (track: Track, queue?: Track[]) => {
      const newQueue = queue || [track];
      const idx = newQueue.findIndex((t) => t.track_id === track.track_id);
      const ytId = extractYoutubeId(track.url || track.external_id || track.track_id);
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

      if (previewUrl && !ytId) {
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

      if (ytId) {
        if (audioRef.current) audioRef.current.pause();
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

  playRef.current = play;

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
    } else {
      void audioRef.current?.play().catch(() => {});
    }
    setState((prev) => ({ ...prev, isPlaying: true }));
  }, [state.engine]);

  const togglePlay = useCallback(() => {
    if (state.isPlaying) pause();
    else resume();
  }, [state.isPlaying, pause, resume]);

  const next = useCallback(() => {
    const { queue, queueIndex } = state;
    if (queue.length === 0) return;
    play(queue[(queueIndex + 1) % queue.length], queue);
  }, [state, play]);

  const prev = useCallback(() => {
    const { queue, queueIndex } = state;
    if (queue.length === 0) return;
    play(queue[(queueIndex - 1 + queue.length) % queue.length], queue);
  }, [state, play]);

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
