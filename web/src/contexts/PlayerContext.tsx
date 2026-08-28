'use client';

/* ──────────────────────────────────────────────
   WaveMash — Player Context (Hybrid Local & YouTube Audio Engine)
   앨범 커버 클릭 시 서버 파일 및 YouTube 오디오를 배경에서 자동 스트리밍
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

/* ── YouTube Video ID Extractor ── */
export function extractYoutubeId(urlOrId?: string): string | null {
  if (!urlOrId) return null;
  // If already 11-char ID
  if (/^[a-zA-Z0-9_-]{11}$/.test(urlOrId)) return urlOrId;
  const match = urlOrId.match(
    /(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})/
  );
  return match ? match[1] : null;
}

/* ── Types ── */

interface PlayerState {
  currentTrack: Track | null;
  isPlaying: boolean;
  progress: number; // 0–100
  duration: number; // seconds
  currentTime: number; // seconds
  volume: number; // 0–1
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

/* ── Provider ── */

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
  const tickerRef = useRef<NodeJS.Timeout | null>(null);

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

  // 1. YouTube IFrame API Script Loader
  useEffect(() => {
    if (typeof window === 'undefined') return;

    if (!window.YT) {
      const tag = document.createElement('script');
      tag.src = 'https://www.youtube.com/iframe_api';
      const firstScriptTag = document.getElementsByTagName('script')[0];
      firstScriptTag?.parentNode?.insertBefore(tag, firstScriptTag);

      window.onYouTubeIframeAPIReady = () => {
        initYtPlayer();
      };
    } else if (window.YT && window.YT.Player) {
      initYtPlayer();
    }

    function initYtPlayer() {
      if (ytPlayerRef.current) return;
      try {
        ytPlayerRef.current = new window.YT.Player('wavemash-hidden-yt-player', {
          height: '1',
          width: '1',
          playerVars: {
            playsinline: 1,
            controls: 0,
            disablekb: 1,
            fs: 0,
            rel: 0,
            origin: window.location.origin,
          },
          events: {
            onReady: () => {
              isYtReadyRef.current = true;
              if (ytPlayerRef.current?.setVolume) {
                ytPlayerRef.current.setVolume(state.volume * 100);
              }
            },
            onStateChange: (event: any) => {
              // 1: PLAYING, 2: PAUSED, 0: ENDED
              if (event.data === 1) {
                setState((prev) => ({ ...prev, isPlaying: true }));
              } else if (event.data === 2) {
                setState((prev) => ({ ...prev, isPlaying: false }));
              } else if (event.data === 0) {
                // Auto next
                setState((prev) => {
                  const { queue, queueIndex } = prev;
                  if (queue.length > 1) {
                    const nextIdx = (queueIndex + 1) % queue.length;
                    setTimeout(() => play(queue[nextIdx], queue), 0);
                  }
                  return { ...prev, isPlaying: false };
                });
              }
            },
            onError: (e: any) => {
              console.warn('YouTube Player error:', e);
              setState((prev) => ({ ...prev, isPlaying: false }));
            },
          },
        });
      } catch (e) {
        console.warn('Failed to init YT player:', e);
      }
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 2. Lazily create standard HTML5 Audio Element
  const getAudio = useCallback(() => {
    if (!audioRef.current && typeof window !== 'undefined') {
      audioRef.current = new Audio();
      audioRef.current.volume = state.volume;
    }
    return audioRef.current;
  }, [state.volume]);

  // 3. Playback Progress Ticker (both Audio & YouTube)
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
          } catch {}
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
    } else {
      if (tickerRef.current) clearInterval(tickerRef.current);
    }

    return () => {
      if (tickerRef.current) clearInterval(tickerRef.current);
    };
  }, [state.isPlaying, state.engine]);

  /* ── Playback Controls ── */

  const play = useCallback(
    (track: Track, queue?: Track[]) => {
      const newQueue = queue || [track];
      const idx = newQueue.findIndex((t) => t.track_id === track.track_id);
      const ytId = extractYoutubeId(track.url || track.external_id || track.track_id);
      const previewUrl = track.preview_url?.trim();

      // A. Local WAV file on server
      if (track.has_file) {
        if (ytPlayerRef.current?.pauseVideo) {
          try {
            ytPlayerRef.current.pauseVideo();
          } catch {}
        }

        const audio = getAudio();
        if (audio) {
          audio.src = api.getStreamUrl(track.track_id);
          audio.play().catch(() => {});
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
      }
      // B. Spotify / catalog 30s preview
      else if (previewUrl) {
        if (ytPlayerRef.current?.pauseVideo) {
          try {
            ytPlayerRef.current.pauseVideo();
          } catch {}
        }

        const audio = getAudio();
        if (audio) {
          audio.src = previewUrl;
          audio.play().catch(() => {});
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
      }
      // C. YouTube-based track
      else if (ytId) {
        if (audioRef.current) {
          audioRef.current.pause();
        }

        if (ytPlayerRef.current?.loadVideoById) {
          try {
            ytPlayerRef.current.loadVideoById({
              videoId: ytId,
              startSeconds: 0,
            });
            ytPlayerRef.current.playVideo();
          } catch (err) {
            console.warn('YT loadVideoById failed:', err);
          }
        }

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
      }
      // D. No playable source — still select track for download UI
      else {
        if (audioRef.current) audioRef.current.pause();
        if (ytPlayerRef.current?.pauseVideo) {
          try {
            ytPlayerRef.current.pauseVideo();
          } catch {}
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
      }
    },
    [getAudio]
  );

  const pause = useCallback(() => {
    if (state.engine === 'youtube') {
      try {
        ytPlayerRef.current?.pauseVideo();
      } catch {}
    } else {
      audioRef.current?.pause();
    }
    setState((prev) => ({ ...prev, isPlaying: false }));
  }, [state.engine]);

  const resume = useCallback(() => {
    if (state.engine === 'youtube') {
      try {
        ytPlayerRef.current?.playVideo();
      } catch {}
    } else {
      audioRef.current?.play().catch(() => {});
    }
    setState((prev) => ({ ...prev, isPlaying: true }));
  }, [state.engine]);

  const togglePlay = useCallback(() => {
    if (state.isPlaying) {
      pause();
    } else {
      resume();
    }
  }, [state.isPlaying, pause, resume]);

  const next = useCallback(() => {
    const { queue, queueIndex } = state;
    if (queue.length === 0) return;
    const nextIdx = (queueIndex + 1) % queue.length;
    play(queue[nextIdx], queue);
  }, [state, play]);

  const prev = useCallback(() => {
    const { queue, queueIndex } = state;
    if (queue.length === 0) return;
    const prevIdx = (queueIndex - 1 + queue.length) % queue.length;
    play(queue[prevIdx], queue);
  }, [state, play]);

  const setVolume = useCallback((v: number) => {
    const clamped = Math.max(0, Math.min(1, v));
    if (audioRef.current) audioRef.current.volume = clamped;
    try {
      if (ytPlayerRef.current?.setVolume) {
        ytPlayerRef.current.setVolume(clamped * 100);
      }
    } catch {}
    setState((prev) => ({ ...prev, volume: clamped }));
  }, []);

  const seekTo = useCallback(
    (percent: number) => {
      const targetSec = (percent / 100) * state.duration;
      if (state.engine === 'youtube') {
        try {
          ytPlayerRef.current?.seekTo(targetSec, true);
        } catch {}
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
      {/* ── Background Hidden YouTube Audio Player ── */}
      <div
        id="wavemash-hidden-yt-player-container"
        className="fixed -bottom-10 -right-10 pointer-events-none opacity-0 overflow-hidden w-1 h-1 z-[-1]"
      >
        <div id="wavemash-hidden-yt-player" />
      </div>
    </PlayerContext.Provider>
  );
}

/* ── Hook ── */

export function usePlayer(): PlayerContextValue {
  const ctx = useContext(PlayerContext);
  if (!ctx) {
    throw new Error('usePlayer must be used within a PlayerProvider');
  }
  return ctx;
}
