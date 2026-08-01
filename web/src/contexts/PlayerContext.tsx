'use client';

/* ──────────────────────────────────────────────
   WaveMash — Player Context
   ────────────────────────────────────────────── */

import {
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

/* ── Types ── */

interface PlayerState {
  currentTrack: Track | null;
  isPlaying: boolean;
  progress: number;       // 0–100
  duration: number;       // seconds
  currentTime: number;    // seconds
  volume: number;         // 0–1
  queue: Track[];
  queueIndex: number;
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

export function PlayerProvider({ children }: { children: ReactNode }) {
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const [state, setState] = useState<PlayerState>({
    currentTrack: null,
    isPlaying: false,
    progress: 0,
    duration: 0,
    currentTime: 0,
    volume: 0.8,
    queue: [],
    queueIndex: -1,
  });

  // Lazily create the Audio element (client-side only)
  const getAudio = useCallback(() => {
    if (!audioRef.current && typeof window !== 'undefined') {
      audioRef.current = new Audio();
      audioRef.current.volume = state.volume;
    }
    return audioRef.current;
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /* ── Playback Controls ── */

  const play = useCallback(
    (track: Track, queue?: Track[]) => {
      const audio = getAudio();
      if (!audio) return;

      const streamUrl = api.getStreamUrl(track.track_id);
      audio.src = streamUrl;
      audio.play().catch(() => {});

      const newQueue = queue || [track];
      const idx = newQueue.findIndex((t) => t.track_id === track.track_id);

      setState((prev) => ({
        ...prev,
        currentTrack: track,
        isPlaying: true,
        progress: 0,
        currentTime: 0,
        queue: newQueue,
        queueIndex: idx >= 0 ? idx : 0,
      }));
    },
    [getAudio]
  );

  const pause = useCallback(() => {
    getAudio()?.pause();
    setState((prev) => ({ ...prev, isPlaying: false }));
  }, [getAudio]);

  const resume = useCallback(() => {
    getAudio()?.play().catch(() => {});
    setState((prev) => ({ ...prev, isPlaying: true }));
  }, [getAudio]);

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

  const setVolume = useCallback(
    (v: number) => {
      const clamped = Math.max(0, Math.min(1, v));
      const audio = getAudio();
      if (audio) audio.volume = clamped;
      setState((prev) => ({ ...prev, volume: clamped }));
    },
    [getAudio]
  );

  const seekTo = useCallback(
    (percent: number) => {
      const audio = getAudio();
      if (!audio || !audio.duration) return;
      audio.currentTime = (percent / 100) * audio.duration;
    },
    [getAudio]
  );

  const addToQueue = useCallback((track: Track) => {
    setState((prev) => ({
      ...prev,
      queue: [...prev.queue, track],
    }));
  }, []);

  /* ── Audio Event Listeners ── */

  useEffect(() => {
    const audio = getAudio();
    if (!audio) return;

    const onTimeUpdate = () => {
      const dur = audio.duration || 0;
      const cur = audio.currentTime || 0;
      setState((prev) => ({
        ...prev,
        currentTime: cur,
        duration: dur,
        progress: dur > 0 ? (cur / dur) * 100 : 0,
      }));
    };

    const onEnded = () => {
      // Auto-play next
      setState((prev) => {
        const { queue, queueIndex } = prev;
        if (queue.length > 1) {
          const nextIdx = (queueIndex + 1) % queue.length;
          // Schedule next track play
          setTimeout(() => play(queue[nextIdx], queue), 0);
        }
        return { ...prev, isPlaying: false };
      });
    };

    const onLoadedMetadata = () => {
      setState((prev) => ({
        ...prev,
        duration: audio.duration || 0,
      }));
    };

    const onError = (e: Event) => {
      console.error('Audio playback error:', e);
      setState((prev) => ({ ...prev, isPlaying: false }));
    };

    audio.addEventListener('timeupdate', onTimeUpdate);
    audio.addEventListener('ended', onEnded);
    audio.addEventListener('loadedmetadata', onLoadedMetadata);
    audio.addEventListener('error', onError);

    return () => {
      audio.removeEventListener('timeupdate', onTimeUpdate);
      audio.removeEventListener('ended', onEnded);
      audio.removeEventListener('loadedmetadata', onLoadedMetadata);
      audio.removeEventListener('error', onError);
    };
  }, [getAudio, play]);

  /* ── Context Value ── */

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
    <PlayerContext.Provider value={value}>{children}</PlayerContext.Provider>
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
