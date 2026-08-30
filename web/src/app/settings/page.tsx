'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft, LogOut, Save } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { getSupabase } from '@/lib/supabase';
import { getProfileHref } from '@/lib/profile';
import { Skeleton } from '@/components/ui/skeleton';

export default function SettingsPage() {
  const router = useRouter();
  const { user, profile, loading: authLoading, signOut, refreshProfile } =
    useAuth();
  const [displayName, setDisplayName] = useState('');
  const [bio, setBio] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.replace('/login');
      return;
    }
    setDisplayName(profile?.display_name || '');
    setBio(profile?.bio || '');
  }, [authLoading, user, profile, router]);

  const handleSave = async () => {
    if (!user) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const sb = getSupabase();
      const { error: updateError } = await sb
        .from('profiles')
        .update({
          display_name: displayName.trim() || profile?.display_name || 'User',
          bio: bio.trim(),
        })
        .eq('user_id', user.id);

      if (updateError) throw new Error(updateError.message);
      await refreshProfile();
      setMessage('저장되었습니다.');
    } catch (err) {
      setError(err instanceof Error ? err.message : '저장에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  };

  const handleSignOut = async () => {
    await signOut();
    router.replace('/login');
  };

  if (authLoading || !user) {
    return (
      <div className="max-w-lg mx-auto px-4 py-10 space-y-4">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-24 w-full rounded-xl" />
        <Skeleton className="h-24 w-full rounded-xl" />
      </div>
    );
  }

  const profileHref = getProfileHref(user, profile);

  return (
    <div className="max-w-lg mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center gap-3">
        <Link
          href={profileHref}
          className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-muted-foreground hover:text-white transition-colors border border-white/10"
          aria-label="프로필로 돌아가기"
        >
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <h1 className="text-lg font-bold text-white">설정</h1>
      </div>

      <section className="glass rounded-2xl p-5 border border-white/10 space-y-4">
        <div className="flex items-center gap-3">
          {profile?.avatar_url ? (
            <img
              src={profile.avatar_url}
              alt=""
              className="w-14 h-14 rounded-full object-cover border border-[#d4a853]/40"
            />
          ) : (
            <div className="w-14 h-14 rounded-full bg-white/10 flex items-center justify-center text-sm font-bold text-[#d4a853]">
              {(profile?.display_name || 'WM').slice(0, 2).toUpperCase()}
            </div>
          )}
          <div className="min-w-0">
            <p className="text-sm font-semibold text-white truncate">
              {profile?.display_name || 'User'}
            </p>
            <p className="text-xs text-muted-foreground truncate">
              @{profile?.username}
            </p>
          </div>
        </div>

        <label className="block space-y-1.5">
          <span className="text-[11px] font-medium text-muted-foreground">
            표시 이름
          </span>
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            maxLength={60}
            className="w-full rounded-xl bg-black/40 border border-white/10 px-3 py-2.5 text-sm text-white outline-none focus:border-[#d4a853]/50"
          />
        </label>

        <label className="block space-y-1.5">
          <span className="text-[11px] font-medium text-muted-foreground">
            소개
          </span>
          <textarea
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            maxLength={280}
            rows={3}
            className="w-full rounded-xl bg-black/40 border border-white/10 px-3 py-2.5 text-sm text-white outline-none focus:border-[#d4a853]/50 resize-none"
            placeholder="간단한 소개를 적어보세요."
          />
        </label>

        {message && (
          <p className="text-xs text-emerald-400">{message}</p>
        )}
        {error && <p className="text-xs text-red-400">{error}</p>}

        <button
          type="button"
          onClick={() => void handleSave()}
          disabled={saving}
          className="w-full flex items-center justify-center gap-2 rounded-xl bg-[#d4a853] hover:bg-amber-400 disabled:opacity-60 text-black font-bold text-sm py-2.5 transition-colors"
        >
          <Save className="w-4 h-4" />
          {saving ? '저장 중…' : '저장'}
        </button>
      </section>

      <section className="glass rounded-2xl p-5 border border-white/10 space-y-3">
        <Link
          href="/privacy"
          className="block text-sm text-muted-foreground hover:text-white transition-colors"
        >
          개인정보 처리방침
        </Link>
        <button
          type="button"
          onClick={() => void handleSignOut()}
          className="w-full flex items-center justify-center gap-2 rounded-xl bg-white/5 hover:bg-red-500/15 border border-white/10 hover:border-red-500/30 text-white/80 hover:text-red-300 font-medium text-sm py-2.5 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          로그아웃
        </button>
      </section>
    </div>
  );
}
