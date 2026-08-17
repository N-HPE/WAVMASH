'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { getSupabase } from '@/lib/supabase';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { motion } from 'framer-motion';

export default function LoginPage() {
  const router = useRouter();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (isLogin) {
        const { error } = await getSupabase().auth.signInWithPassword({
          email,
          password,
        });
        if (error) throw error;
      } else {
        const { error } = await getSupabase().auth.signUp({
          email,
          password,
        });
        if (error) throw error;
        // Optional: show a message to check email if confirm is required
      }
      router.push('/');
    } catch (err: any) {
      setError(err.message || '인증에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleOAuth = async (provider: 'google') => {
    try {
      const { error } = await getSupabase().auth.signInWithOAuth({
        provider,
        options: {
          redirectTo: `${window.location.origin}/`,
        },
      });
      if (error) throw error;
    } catch (err: any) {
      setError(err.message || 'OAuth 로그인에 실패했습니다.');
    }
  };

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-64px)] px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md p-8 rounded-2xl glass-strong border border-white/[0.06] bg-white/[0.03]"
      >
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold mb-2">
            {isLogin ? 'WAVMASH 로그인' : 'WAVMASH 회원가입'}
          </h1>
          <p className="text-muted-foreground text-sm">
            {isLogin
              ? '음악 컬렉션을 관리하고 친구들과 공유하세요'
              : 'WAVMASH에 가입하고 컬렉션을 시작하세요'}
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-md bg-red-500/10 border border-red-500/20 text-red-500 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Input
              type="email"
              placeholder="이메일"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="bg-black/20 border-white/10"
            />
          </div>
          <div>
            <Input
              type="password"
              placeholder="비밀번호"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="bg-black/20 border-white/10"
            />
          </div>

          <Button
            type="submit"
            disabled={loading}
            className="w-full bg-[#d4a853] hover:bg-[#b58c3f] text-black font-semibold"
          >
            {loading ? '처리 중...' : isLogin ? '로그인' : '회원가입'}
          </Button>
        </form>

        <div className="mt-6">
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-white/10" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-[#0a0a0a] px-2 text-muted-foreground">
                또는
              </span>
            </div>
          </div>

          <div className="mt-6">
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOAuth('google')}
              className="w-full border-white/10 hover:bg-white/5"
            >
              Google로 계속하기
            </Button>
          </div>
        </div>

        <div className="mt-6 text-center text-sm text-muted-foreground">
          {isLogin ? '계정이 없으신가요?' : '이미 계정이 있으신가요?'}
          <button
            onClick={() => setIsLogin(!isLogin)}
            className="ml-2 text-[#d4a853] hover:underline"
          >
            {isLogin ? '회원가입' : '로그인'}
          </button>
        </div>
      </motion.div>
    </div>
  );
}
