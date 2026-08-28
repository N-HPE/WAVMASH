'use client';

/* ──────────────────────────────────────────────
   WaveMash — Login Page (Google OAuth)
   ────────────────────────────────────────────── */

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, Disc3, ShieldCheck, Users, Flame } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

export default function LoginPage() {
  const { signInWithGoogle } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGoogleLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      await signInWithGoogle();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Google 로그인에 실패했습니다.';
      setError(message);
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
        <div className="absolute -top-24 -left-24 w-60 h-60 rounded-full bg-[#d4a853] opacity-20 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -right-24 w-60 h-60 rounded-full bg-blue-600 opacity-15 blur-3xl pointer-events-none" />

        <div className="space-y-3 relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#d4a853]/15 border border-[#d4a853]/30 text-[#d4a853] text-xs font-semibold uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5" />
            Digger&apos;s Audio Social Hub
          </div>

          <h1 className="text-3xl sm:text-4xl font-black text-white tracking-tight">
            WAVMASH <span className="text-gold-gradient">LOGIN</span>
          </h1>

          <p className="text-xs sm:text-sm text-muted-foreground max-w-sm mx-auto leading-relaxed">
            Google 계정으로 간편하게 로그인하고, 프로필·피드·컬렉션을
            저장하세요.
          </p>
        </div>

        <div className="grid grid-cols-3 gap-2 py-2 relative z-10">
          <div className="glass p-3 rounded-xl border border-white/5 flex flex-col items-center gap-1 text-center">
            <Users className="w-5 h-5 text-blue-400" />
            <span className="text-[11px] font-bold text-white">프로필</span>
            <span className="text-[9px] text-muted-foreground">컬렉션 공유</span>
          </div>

          <div className="glass p-3 rounded-xl border border-white/5 flex flex-col items-center gap-1 text-center">
            <Disc3 className="w-5 h-5 text-[#d4a853]" />
            <span className="text-[11px] font-bold text-white">24bit WAV</span>
            <span className="text-[9px] text-muted-foreground">무손실 아카이빙</span>
          </div>

          <div className="glass p-3 rounded-xl border border-white/5 flex flex-col items-center gap-1 text-center">
            <Flame className="w-5 h-5 text-amber-500" />
            <span className="text-[11px] font-bold text-white">피드</span>
            <span className="text-[9px] text-muted-foreground">바이닐 쇼룸</span>
          </div>
        </div>

        {error && (
          <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
            {error}
          </div>
        )}

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
            <span>{loading ? '로그인 중...' : 'Google 계정으로 로그인'}</span>
          </button>
        </div>

        <div className="flex items-center justify-center gap-2 text-[11px] text-muted-foreground/70 relative z-10 pt-2 border-t border-white/5">
          <ShieldCheck className="w-4 h-4 text-green-400" />
          <span>이메일과 프로필 정보만 사용합니다.</span>
        </div>
      </motion.div>
    </div>
  );
}
