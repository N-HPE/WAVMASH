'use client';

/* ──────────────────────────────────────────────
   WaveMash — Login / Google & YouTube Connect Page
   구글 계정 1초 로그인 & YouTube 플레이리스트 자동 연동
   ────────────────────────────────────────────── */

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Sparkles, Disc3, ShieldCheck, ArrowRight, Music, Flame } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

function YouTubeIcon({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
    </svg>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const { user, signInWithGoogle } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGoogleLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      await signInWithGoogle();
    } catch (err: any) {
      setError(err.message || 'Google 로그인에 실패했습니다.');
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-80px)] px-4 py-10">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        className="w-full max-w-lg p-8 sm:p-10 rounded-3xl bg-[#0e0e1a]/95 border border-white/10 shadow-2xl backdrop-blur-2xl text-center space-y-8 relative overflow-hidden"
      >
        {/* Background Ambient Glow */}
        <div className="absolute -top-24 -left-24 w-60 h-60 rounded-full bg-[#d4a853] opacity-20 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -right-24 w-60 h-60 rounded-full bg-red-600 opacity-15 blur-3xl pointer-events-none" />

        {/* ── 1. Branding Header ── */}
        <div className="space-y-3 relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#d4a853]/15 border border-[#d4a853]/30 text-[#d4a853] text-xs font-semibold uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5" />
            Digger&apos;s Audio Social Hub
          </div>

          <h1 className="text-3xl sm:text-4xl font-black text-white tracking-tight">
            WAVMASH <span className="text-gold-gradient">LOGIN</span>
          </h1>

          <p className="text-xs sm:text-sm text-muted-foreground max-w-sm mx-auto leading-relaxed">
            구글 계정으로 1초 만에 시작하고, 내 <strong className="text-white">YouTube 재생목록</strong>을
            가져와 세련된 바이닐 컬렉션으로 소장하세요.
          </p>
        </div>

        {/* ── 2. Feature Highlights Pill Bar ── */}
        <div className="grid grid-cols-3 gap-2 py-2 relative z-10">
          <div className="glass p-3 rounded-xl border border-white/5 flex flex-col items-center gap-1 text-center">
            <YouTubeIcon className="w-5 h-5 text-red-500" />
            <span className="text-[11px] font-bold text-white">YouTube 연동</span>
            <span className="text-[9px] text-muted-foreground">좋아요/플리 자동 분석</span>
          </div>


          <div className="glass p-3 rounded-xl border border-white/5 flex flex-col items-center gap-1 text-center">
            <Disc3 className="w-5 h-5 text-[#d4a853]" />
            <span className="text-[11px] font-bold text-white">24bit WAV 소장</span>
            <span className="text-[9px] text-muted-foreground">무손실 아카이빙</span>
          </div>

          <div className="glass p-3 rounded-xl border border-white/5 flex flex-col items-center gap-1 text-center">
            <Flame className="w-5 h-5 text-amber-500" />
            <span className="text-[11px] font-bold text-white">인스타 쇼룸</span>
            <span className="text-[9px] text-muted-foreground">3x3 바이닐 피드</span>
          </div>
        </div>

        {error && (
          <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
            {error}
          </div>
        )}

        {/* ── 3. Google One-Click Login Button ── */}
        <div className="space-y-3 relative z-10">
          <button
            onClick={handleGoogleLogin}
            disabled={loading}
            className="w-full py-4 px-6 rounded-2xl bg-white text-black hover:bg-neutral-200 font-bold text-sm flex items-center justify-center gap-3 shadow-xl hover:shadow-2xl transition-all active:scale-95 disabled:opacity-50 cursor-pointer"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
              />
            </svg>
            <span>{loading ? '연결 중...' : 'Google 계정으로 시작 & YouTube 플리 연동'}</span>
          </button>
        </div>

        {/* ── 4. Privacy Footer Note ── */}
        <div className="flex items-center justify-center gap-2 text-[11px] text-muted-foreground/70 relative z-10 pt-2 border-t border-white/5">
          <ShieldCheck className="w-4 h-4 text-green-400" />
          <span>YouTube 데이터는 읽기 전용으로 안전하게 동기화됩니다.</span>
        </div>
      </motion.div>
    </div>
  );
}
