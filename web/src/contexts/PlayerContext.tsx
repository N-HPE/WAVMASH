'use client';

/* ──────────────────────────────────────────────
   WaveMash — Player Context
   듀얼 데크(A/B) 엔진: 곡이 끝나기 전에 다음 곡을 미리 띄워
   DJ처럼 크로스페이드로 이어 붙인다.
   ────────────────────────────────────────────── */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
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
  if (tid.startsWith('bp:')) return '';
  if (tid && !extractYoutubeId(tid)) return tid;
  return (track.external_id || '').trim();
}

function trackYoutubeId(track: Track): string | null {
  return (
    extractYoutubeId(track.url) ||
    extractYoutubeId(track.external_id) ||
    extractYoutubeId(track.track_id)
  );
}

function hasPlayableSource(track: Track): boolean {
  if (track.has_file) return true;
  if (trackYoutubeId(track)) return true;
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
        url:
          res.youtube_url || `https://www.youtube.com/watch?v=${res.youtube_id}`,
        external_id: res.youtube_id,
        preview_url: res.preview_url || track.preview_url,
        platform: 'youtube',
      };
    }
    if (res.preview_url) {
      return { ...track, preview_url: res.preview_url };
    }
  } catch {
    /* 해석 실패 — 호출자가 건너뛴다 */
  }
  return track;
}

const DJ_STORAGE_KEY = 'wavemash.dj.v1';
/** DJ 모드 기본 크로스페이드 길이(초) */
const DEFAULT_CROSSFADE = 6;
/** 수동 전환(다음/이전) 시 짧은 페이드로 클릭음 방지 */
const MANUAL_FADE = 0.45;
/** 크로스페이드 없이 이어붙일 때의 선행 트리거(초) */
const HARD_CUT_LEAD = 0.4;
const RAMP_INTERVAL_MS = 50;

type DeckId = 'a' | 'b';

interface Deck {
  id: DeckId;
  domId: string;
  yt: YTPlayer | null;
  ytReady: boolean;
  pendingYtId: string | null;
  needUnmute: boolean;
  audio: HTMLAudioElement | null;
  mode: 'yt' | 'audio' | 'idle';
  track: Track | null;
  /** 0..1 — 마스터 볼륨에 곱해지는 데크 게인 */
  gain: number;
  onPlaying: (() => void) | null;
}

interface YTPlayer {
  loadVideoById?: (opts: { videoId: string; startSeconds?: number }) => void;
  playVideo?: () => void;
  pauseVideo?: () => void;
  stopVideo?: () => void;
  seekTo?: (sec: number, allowSeekAhead: boolean) => void;
  mute?: () => void;
  unMute?: () => void;
  setVolume?: (v: number) => void;
  getCurrentTime?: () => number;
  getDuration?: () => number;
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
  /** DJ 모드: 곡 끝에서 자동 크로스페이드 */
  autoMix: boolean;
  crossfadeSec: number;
  /** 두 곡이 겹쳐 흐르는 중 */
  isMixing: boolean;
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
  setAutoMix: (on: boolean) => void;
  setCrossfadeSec: (sec: number) => void;
}

const PlayerContext = createContext<PlayerContextValue | null>(null);

declare global {
  interface Window {
    YT?: {
      Player: new (
        el: string,
        opts: Record<string, unknown>
      ) => YTPlayer;
    };
    onYouTubeIframeAPIReady?: () => void;
  }
}

function makeDeck(id: DeckId): Deck {
  return {
    id,
    domId: `wavemash-yt-deck-${id}`,
    yt: null,
    ytReady: false,
    pendingYtId: null,
    needUnmute: false,
    audio: null,
    mode: 'idle',
    track: null,
    gain: 0,
    onPlaying: null,
  };
}

export function PlayerProvider({ children }: { children: ReactNode }) {
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
    autoMix: true,
    crossfadeSec: DEFAULT_CROSSFADE,
    isMixing: false,
  });

  const stateRef = useRef(state);
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  const decksRef = useRef<Record<DeckId, Deck>>({
    a: makeDeck('a'),
    b: makeDeck('b'),
  });
  const activeIdRef = useRef<DeckId>('a');
  const masterVolRef = useRef(0.8);
  const autoMixRef = useRef(true);
  const crossfadeRef = useRef(DEFAULT_CROSSFADE);
  const transitioningRef = useRef(false);
  const rampRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const watcherRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const playGenRef = useRef(0);
  const resolveCacheRef = useRef<Map<string, Track>>(new Map());
  const prefetchingRef = useRef<Set<string>>(new Set());
  const startAtIndexRef = useRef<
    (queue: Track[], idx: number, fadeSec: number) => Promise<void>
  >(async () => {});

  /* ── DJ 설정 로드 (hydration 이후) ── */
  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(DJ_STORAGE_KEY);
      if (!raw) return;
      const saved = JSON.parse(raw) as {
        autoMix?: boolean;
        crossfadeSec?: number;
      };
      const autoMix = saved.autoMix !== false;
      const crossfadeSec =
        typeof saved.crossfadeSec === 'number'
          ? Math.max(0, Math.min(15, saved.crossfadeSec))
          : DEFAULT_CROSSFADE;
      autoMixRef.current = autoMix;
      crossfadeRef.current = crossfadeSec;
      setState((prev) => ({ ...prev, autoMix, crossfadeSec }));
    } catch {
      /* 기본값 유지 */
    }
  }, []);

  const persistDj = useCallback((autoMix: boolean, crossfadeSec: number) => {
    try {
      window.localStorage.setItem(
        DJ_STORAGE_KEY,
        JSON.stringify({ autoMix, crossfadeSec })
      );
    } catch {
      /* 저장 실패는 무시 */
    }
  }, []);

  /* ── 데크 기본 조작 ── */

  const applyGain = useCallback((deck: Deck) => {
    const v = Math.max(0, Math.min(1, masterVolRef.current * deck.gain));
    if (deck.mode === 'yt') {
      try {
        deck.yt?.setVolume?.(Math.round(v * 100));
      } catch {
        /* ignore */
      }
    } else if (deck.mode === 'audio' && deck.audio) {
      deck.audio.volume = v;
    }
  }, []);

  const setDeckGain = useCallback(
    (id: DeckId, gain: number) => {
      const deck = decksRef.current[id];
      deck.gain = Math.max(0, Math.min(1, gain));
      applyGain(deck);
    },
    [applyGain]
  );

  const stopDeck = useCallback((id: DeckId) => {
    const deck = decksRef.current[id];
    deck.onPlaying = null;
    deck.pendingYtId = null;
    deck.needUnmute = false;
    try {
      deck.yt?.stopVideo?.();
    } catch {
      /* ignore */
    }
    if (deck.audio) {
      try {
        deck.audio.pause();
      } catch {
        /* ignore */
      }
    }
    deck.mode = 'idle';
    deck.track = null;
    deck.gain = 0;
  }, []);

  const clearRamp = useCallback(() => {
    if (rampRef.current) {
      clearInterval(rampRef.current);
      rampRef.current = null;
    }
  }, []);

  /** 등파워 곡선으로 fromId → toId 크로스페이드 */
  const runCrossfade = useCallback(
    (fromId: DeckId, toId: DeckId, seconds: number) => {
      if (rampRef.current) return;
      if (fromId === toId) {
        setDeckGain(toId, 1);
        transitioningRef.current = false;
        return;
      }
      const steps = Math.max(4, Math.round((seconds * 1000) / RAMP_INTERVAL_MS));
      let i = 0;
      setState((prev) => ({ ...prev, isMixing: true }));
      rampRef.current = setInterval(() => {
        i += 1;
        const t = Math.min(1, i / steps);
        setDeckGain(fromId, Math.cos((t * Math.PI) / 2));
        setDeckGain(toId, Math.sin((t * Math.PI) / 2));
        if (t >= 1) {
          clearRamp();
          stopDeck(fromId);
          setDeckGain(toId, 1);
          transitioningRef.current = false;
          setState((prev) => ({ ...prev, isMixing: false }));
        }
      }, RAMP_INTERVAL_MS);
    },
    [clearRamp, setDeckGain, stopDeck]
  );

  const ensureDeckAudio = useCallback(
    (deck: Deck): HTMLAudioElement => {
      if (!deck.audio) {
        const audio = new Audio();
        audio.preload = 'auto';
        audio.addEventListener('ended', () => {
          if (activeIdRef.current !== deck.id) return;
          if (transitioningRef.current) return;
          void startAtIndexRef.current(
            stateRef.current.queue,
            stateRef.current.queueIndex + 1,
            0
          );
        });
        deck.audio = audio;
      }
      return deck.audio;
    },
    []
  );

  /**
   * 데크에 트랙을 올리고 재생을 시작한다.
   * gain 0으로 올리면 소리 없이 시작하므로 크로스페이드 인이 가능하다.
   */
  const loadDeck = useCallback(
    (id: DeckId, track: Track, gain: number): boolean => {
      const deck = decksRef.current[id];
      const ytId = trackYoutubeId(track);
      const previewUrl = track.preview_url?.trim();

      deck.track = track;
      deck.gain = Math.max(0, Math.min(1, gain));
      deck.onPlaying = null;

      if (track.has_file) {
        try {
          deck.yt?.stopVideo?.();
        } catch {
          /* ignore */
        }
        deck.mode = 'audio';
        const audio = ensureDeckAudio(deck);
        audio.volume = masterVolRef.current * deck.gain;
        audio.src = api.getStreamUrl(track.track_id);
        void audio.play().catch(() => {});
        return true;
      }

      if (ytId) {
        if (deck.audio) {
          try {
            deck.audio.pause();
          } catch {
            /* ignore */
          }
        }
        deck.mode = 'yt';
        // 자동재생 정책: mute → play → PLAYING 시 volume 설정 후 unmute
        deck.needUnmute = true;
        if (!deck.yt || !deck.ytReady) {
          deck.pendingYtId = ytId;
          return true;
        }
        try {
          deck.yt.mute?.();
          deck.yt.loadVideoById?.({ videoId: ytId, startSeconds: 0 });
          deck.yt.playVideo?.();
          deck.pendingYtId = null;
          return true;
        } catch {
          deck.pendingYtId = ytId;
          return true;
        }
      }

      if (previewUrl) {
        try {
          deck.yt?.stopVideo?.();
        } catch {
          /* ignore */
        }
        deck.mode = 'audio';
        const audio = ensureDeckAudio(deck);
        audio.volume = masterVolRef.current * deck.gain;
        audio.src = previewUrl;
        void audio.play().catch(() => {});
        return true;
      }

      deck.mode = 'idle';
      deck.track = null;
      return false;
    },
    [ensureDeckAudio]
  );

  const deckTime = useCallback((deck: Deck): { cur: number; dur: number } => {
    if (deck.mode === 'yt' && deck.yt) {
      try {
        return {
          cur: deck.yt.getCurrentTime?.() || 0,
          dur: deck.yt.getDuration?.() || 0,
        };
      } catch {
        return { cur: 0, dur: 0 };
      }
    }
    if (deck.mode === 'audio' && deck.audio) {
      const dur = deck.audio.duration;
      return {
        cur: deck.audio.currentTime || 0,
        dur: Number.isFinite(dur) ? dur : 0,
      };
    }
    return { cur: 0, dur: 0 };
  }, []);

  /* ── 재생 코어 ── */

  /**
   * queue[idx]부터 재생. 재생 불가한 곡은 앞으로 건너뛴다.
   * fadeSec > 0 이면 현재 데크에서 새 데크로 크로스페이드.
   */
  const startAtIndex = useCallback(
    async (queue: Track[], idx: number, fadeSec: number): Promise<void> => {
      const gen = ++playGenRef.current;
      let workingQueue = queue;

      for (let cursor = idx; cursor < workingQueue.length; cursor += 1) {
        const queued = workingQueue[cursor];
        let track = resolveCacheRef.current.get(queued.track_id) || queued;

        if (!hasPlayableSource(track)) {
          // 해석 중에도 어떤 곡으로 넘어갔는지 UI에 먼저 보여준다
          setState((prev) => ({
            ...prev,
            currentTrack: track,
            queue: workingQueue,
            queueIndex: cursor,
            isPlaying: true,
            progress: 0,
            currentTime: 0,
            duration: 0,
          }));

          const resolved = await resolvePlayableTrack(track);
          if (gen !== playGenRef.current) return;

          if (!hasPlayableSource(resolved)) {
            continue; // 이 곡은 재생 불가 → 다음 곡
          }
          resolveCacheRef.current.set(resolved.track_id, resolved);
          track = resolved;
          workingQueue = workingQueue.map((t) =>
            t.track_id === resolved.track_id ? resolved : t
          );
        }

        const fromId = activeIdRef.current;
        const fromDeck = decksRef.current[fromId];
        const fromBusy = fromDeck.mode !== 'idle';
        const toId: DeckId = fromBusy ? (fromId === 'a' ? 'b' : 'a') : fromId;
        const fade = fromBusy ? fadeSec : 0;

        clearRamp();
        if (fade <= 0 && fromBusy) {
          stopDeck(fromId);
        }

        const ok = loadDeck(toId, track, fade > 0 ? 0 : 1);
        if (!ok) continue;

        activeIdRef.current = toId;
        transitioningRef.current = fade > 0;

        setState((prev) => ({
          ...prev,
          currentTrack: track,
          queue: workingQueue,
          queueIndex: cursor,
          isPlaying: true,
          progress: 0,
          currentTime: 0,
          duration: 0,
          engine: decksRef.current[toId].mode === 'yt' ? 'youtube' : 'audio',
          isMixing: fade > 0,
        }));

        if (fade > 0) {
          // 새 데크가 실제로 소리를 내기 시작하면 페이드 시작
          decksRef.current[toId].onPlaying = () =>
            runCrossfade(fromId, toId, fade);
          // 버퍼링이 길어도 전환이 멈추지 않도록 안전장치
          setTimeout(() => {
            if (
              gen === playGenRef.current &&
              transitioningRef.current &&
              !rampRef.current
            ) {
              runCrossfade(fromId, toId, fade);
            }
          }, 1500);
        } else {
          setDeckGain(toId, 1);
        }
        return;
      }

      // 재생할 수 있는 곡이 없음
      if (gen !== playGenRef.current) return;
      transitioningRef.current = false;
      setState((prev) => ({ ...prev, isPlaying: false, isMixing: false }));
    },
    [clearRamp, loadDeck, runCrossfade, setDeckGain, stopDeck]
  );

  useEffect(() => {
    startAtIndexRef.current = startAtIndex;
  }, [startAtIndex]);

  /* ── 플레이어 준비 전에 걸린 영상을 뒤늦게 시작 ── */
  useEffect(() => {
    const timer = setInterval(() => {
      for (const id of ['a', 'b'] as DeckId[]) {
        const deck = decksRef.current[id];
        if (!deck.pendingYtId || !deck.ytReady || !deck.yt) continue;
        const videoId = deck.pendingYtId;
        deck.pendingYtId = null;
        try {
          deck.needUnmute = true;
          deck.yt.mute?.();
          deck.yt.loadVideoById?.({ videoId, startSeconds: 0 });
          deck.yt.playVideo?.();
        } catch {
          deck.pendingYtId = videoId;
        }
      }
    }, 400);
    return () => clearInterval(timer);
  }, []);

  /* ── YouTube IFrame API + 두 데크 초기화 ── */

  useEffect(() => {
    if (typeof window === 'undefined') return;
    let pollTimer: ReturnType<typeof setInterval> | null = null;

    const handleStateChange = (id: DeckId, data: number) => {
      const deck = decksRef.current[id];
      if (data === 1) {
        if (deck.needUnmute) {
          deck.needUnmute = false;
          try {
            deck.yt?.setVolume?.(
              Math.round(masterVolRef.current * deck.gain * 100)
            );
            deck.yt?.unMute?.();
          } catch {
            /* ignore */
          }
        }
        const cb = deck.onPlaying;
        deck.onPlaying = null;
        cb?.();
        if (activeIdRef.current === id) {
          setState((prev) => ({ ...prev, isPlaying: true }));
        }
      } else if (data === 2) {
        if (activeIdRef.current === id && !transitioningRef.current) {
          setState((prev) => ({ ...prev, isPlaying: false }));
        }
      } else if (data === 0) {
        // 시간 기반 전환이 이미 처리했으면 무시, 아니면 폴백으로 다음 곡
        if (activeIdRef.current !== id) return;
        if (transitioningRef.current) return;
        void startAtIndexRef.current(
          stateRef.current.queue,
          stateRef.current.queueIndex + 1,
          0
        );
      }
    };

    const handleError = (id: DeckId) => {
      const deck = decksRef.current[id];
      const fallback = deck.track?.preview_url?.trim();
      if (fallback) {
        deck.mode = 'audio';
        const audio = ensureDeckAudio(deck);
        audio.volume = masterVolRef.current * deck.gain;
        audio.src = fallback;
        void audio.play().catch(() => {});
        const cb = deck.onPlaying;
        deck.onPlaying = null;
        cb?.();
        return;
      }
      if (activeIdRef.current !== id) return;
      // 이 곡은 못 틀음 → 다음 곡으로
      transitioningRef.current = false;
      void startAtIndexRef.current(
        stateRef.current.queue,
        stateRef.current.queueIndex + 1,
        0
      );
    };

    function initDeckPlayer(id: DeckId) {
      const deck = decksRef.current[id];
      if (deck.yt || !window.YT?.Player) return;
      if (!document.getElementById(deck.domId)) return;
      try {
        deck.yt = new window.YT.Player(deck.domId, {
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
              deck.ytReady = true;
              try {
                deck.yt?.setVolume?.(
                  Math.round(masterVolRef.current * deck.gain * 100)
                );
              } catch {
                /* ignore */
              }
              if (deck.pendingYtId) {
                const pending = deck.pendingYtId;
                deck.pendingYtId = null;
                try {
                  deck.yt?.mute?.();
                  deck.yt?.loadVideoById?.({
                    videoId: pending,
                    startSeconds: 0,
                  });
                  deck.yt?.playVideo?.();
                  deck.needUnmute = true;
                } catch {
                  /* ignore */
                }
              }
            },
            onStateChange: (e: { data: number }) =>
              handleStateChange(id, e.data),
            onError: () => handleError(id),
          },
        });
      } catch (err) {
        console.warn(`YT deck ${id} init failed:`, err);
      }
    }

    function initDecks() {
      initDeckPlayer('a');
      initDeckPlayer('b');
    }

    if (window.YT?.Player) {
      initDecks();
    } else {
      if (!document.querySelector('script[src*="youtube.com/iframe_api"]')) {
        const tag = document.createElement('script');
        tag.src = 'https://www.youtube.com/iframe_api';
        document.head.appendChild(tag);
      }
      const prevHook = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => {
        prevHook?.();
        initDecks();
      };
      pollTimer = setInterval(() => {
        if (window.YT?.Player) {
          if (pollTimer) clearInterval(pollTimer);
          initDecks();
        }
      }, 200);
    }

    return () => {
      if (pollTimer) clearInterval(pollTimer);
    };
  }, [ensureDeckAudio]);

  /* ── 진행률 감시 + 곡 끝 자동 전환 ──
     ENDED 이벤트는 숨겨진 iframe에서 종종 늦거나 누락되므로
     남은 시간을 직접 보고 다음 곡을 미리 띄운다. */
  useEffect(() => {
    watcherRef.current = setInterval(() => {
      const activeId = activeIdRef.current;
      const deck = decksRef.current[activeId];
      if (deck.mode === 'idle') return;

      const { cur, dur } = deckTime(deck);
      setState((prev) => {
        if (
          Math.abs(prev.currentTime - cur) < 0.05 &&
          Math.abs(prev.duration - dur) < 0.05
        ) {
          return prev;
        }
        return {
          ...prev,
          currentTime: cur,
          duration: dur,
          progress: dur > 0 ? Math.min(100, (cur / dur) * 100) : 0,
        };
      });

      if (transitioningRef.current) return;
      if (!stateRef.current.isPlaying) return;
      if (dur <= 0 || cur <= 0.5) return;

      const fade = autoMixRef.current
        ? Math.min(crossfadeRef.current, dur * 0.35)
        : 0;
      const lead = fade > 0 ? fade : HARD_CUT_LEAD;
      if (dur - cur > lead) return;

      const { queue, queueIndex } = stateRef.current;
      if (queueIndex < 0 || queueIndex + 1 >= queue.length) return;

      void startAtIndex(queue, queueIndex + 1, fade);
    }, 250);

    return () => {
      if (watcherRef.current) clearInterval(watcherRef.current);
    };
  }, [deckTime, startAtIndex]);

  /* ── 다음 곡 미리 해석 (전환 시 끊김 방지) ── */
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

  /* ── 공개 API ── */

  const play = useCallback(
    (track: Track, queue?: Track[]) => {
      const baseQueue = queue?.length ? queue : [track];
      const idx = baseQueue.findIndex((t) => t.track_id === track.track_id);
      clearRamp();
      transitioningRef.current = false;
      setState((prev) => ({ ...prev, isMixing: false }));
      void startAtIndex(baseQueue, idx >= 0 ? idx : 0, MANUAL_FADE);
    },
    [clearRamp, startAtIndex]
  );

  const pause = useCallback(() => {
    const deck = decksRef.current[activeIdRef.current];
    if (deck.mode === 'yt') {
      try {
        deck.yt?.pauseVideo?.();
      } catch {
        /* ignore */
      }
    } else if (deck.mode === 'audio') {
      deck.audio?.pause();
    }
    setState((prev) => ({ ...prev, isPlaying: false }));
  }, []);

  const resume = useCallback(() => {
    const deck = decksRef.current[activeIdRef.current];
    if (deck.mode === 'yt') {
      try {
        deck.yt?.playVideo?.();
      } catch {
        /* ignore */
      }
    } else if (deck.mode === 'audio' && deck.audio) {
      void deck.audio.play().catch(() => {});
    } else {
      const { currentTrack, queue, queueIndex } = stateRef.current;
      if (currentTrack) {
        void startAtIndex(
          queue.length ? queue : [currentTrack],
          queueIndex >= 0 ? queueIndex : 0,
          0
        );
        return;
      }
    }
    setState((prev) => ({ ...prev, isPlaying: true }));
  }, [startAtIndex]);

  const togglePlay = useCallback(() => {
    if (stateRef.current.isPlaying) pause();
    else resume();
  }, [pause, resume]);

  const next = useCallback(() => {
    const { queue, queueIndex } = stateRef.current;
    if (!queue.length) return;
    clearRamp();
    transitioningRef.current = false;
    const nextIdx = queueIndex + 1 >= queue.length ? 0 : queueIndex + 1;
    void startAtIndex(queue, nextIdx, MANUAL_FADE);
  }, [clearRamp, startAtIndex]);

  const prev = useCallback(() => {
    const { queue, queueIndex, currentTime } = stateRef.current;
    if (!queue.length) return;

    // 3초 넘게 재생했으면 곡 처음으로
    if (currentTime > 3) {
      const deck = decksRef.current[activeIdRef.current];
      if (deck.mode === 'yt') {
        try {
          deck.yt?.seekTo?.(0, true);
        } catch {
          /* ignore */
        }
      } else if (deck.audio) {
        deck.audio.currentTime = 0;
      }
      setState((s) => ({ ...s, currentTime: 0, progress: 0 }));
      return;
    }

    clearRamp();
    transitioningRef.current = false;
    const prevIdx = (queueIndex - 1 + queue.length) % queue.length;
    void startAtIndex(queue, prevIdx, MANUAL_FADE);
  }, [clearRamp, startAtIndex]);

  const setVolume = useCallback(
    (v: number) => {
      const clamped = Math.max(0, Math.min(1, v));
      masterVolRef.current = clamped;
      applyGain(decksRef.current.a);
      applyGain(decksRef.current.b);
      setState((prev) => ({ ...prev, volume: clamped }));
    },
    [applyGain]
  );

  const seekTo = useCallback(
    (percent: number) => {
      const { duration } = stateRef.current;
      const targetSec = (percent / 100) * duration;
      const deck = decksRef.current[activeIdRef.current];
      if (deck.mode === 'yt') {
        try {
          deck.yt?.seekTo?.(targetSec, true);
        } catch {
          /* ignore */
        }
      } else if (deck.audio) {
        deck.audio.currentTime = targetSec;
      }
      setState((prev) => ({
        ...prev,
        progress: percent,
        currentTime: targetSec,
      }));
    },
    []
  );

  const addToQueue = useCallback((track: Track) => {
    setState((prev) => ({ ...prev, queue: [...prev.queue, track] }));
  }, []);

  const setAutoMix = useCallback(
    (on: boolean) => {
      autoMixRef.current = on;
      setState((prev) => {
        persistDj(on, prev.crossfadeSec);
        return { ...prev, autoMix: on };
      });
    },
    [persistDj]
  );

  const setCrossfadeSec = useCallback(
    (sec: number) => {
      const clamped = Math.max(0, Math.min(15, sec));
      crossfadeRef.current = clamped;
      setState((prev) => {
        persistDj(prev.autoMix, clamped);
        return { ...prev, crossfadeSec: clamped };
      });
    },
    [persistDj]
  );

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
    setAutoMix,
    setCrossfadeSec,
  };

  return (
    <PlayerContext.Provider value={value}>
      {children}
      {/* 화면 밖이지만 실제 크기 유지 — 1×1 / opacity:0 은 YT 재생을 막는다 */}
      <div
        className="pointer-events-none fixed bottom-0 right-0 z-[-1] h-[180px] w-[320px] overflow-hidden"
        style={{ opacity: 0.01 }}
        aria-hidden
      >
        <div id="wavemash-yt-deck-a" />
        <div id="wavemash-yt-deck-b" />
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
