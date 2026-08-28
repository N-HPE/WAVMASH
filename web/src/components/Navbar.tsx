'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Menu,
  X,
  User as UserIcon,
  Home,
  Library,
  ListMusic,
  Compass,
  LogOut,
  Disc3,
  Download,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { FormEvent, useEffect, useRef, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { getProfileHref } from '@/lib/profile';

const NAV_ITEMS = [
  { label: '홈', href: '/', icon: Home },
  { label: '검색', href: '/search', icon: Compass },
  { label: '다운로드', href: '/download', icon: Download },
  { label: '라이브러리', href: '/library', icon: Library },
  { label: '플레이리스트', href: '/playlists', icon: ListMusic },
] as const;

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [query, setQuery] = useState('');
  const { user, profile, signOut } = useAuth();
  const profileHref = getProfileHref(user, profile);
  const menuRef = useRef<HTMLDivElement>(null);

  const isLoginPage = pathname.startsWith('/login');
  const isLegalPage = pathname.startsWith('/privacy');

  const avatarUrl =
    profile?.avatar_url ||
    (user?.user_metadata?.avatar_url as string | undefined) ||
    (user?.user_metadata?.picture as string | undefined) ||
    '';
  const displayName =
    profile?.display_name ||
    (user?.user_metadata?.full_name as string | undefined) ||
    (user?.user_metadata?.name as string | undefined) ||
    user?.email ||
    'User';
  const username = profile?.username || 'me';

  useEffect(() => {
    if (!menuOpen) return;
    const onPointerDown = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMenuOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [menuOpen]);

  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  const handleSearch = (e: FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    if (q) router.push(`/search?q=${encodeURIComponent(q)}`);
  };

  const go = (href: string) => {
    setMenuOpen(false);
    router.push(href);
  };

  const handleSignOut = async () => {
    setMenuOpen(false);
    await signOut();
    router.push('/');
  };

  if (isLoginPage || isLegalPage) {
    return (
      <header className="fixed top-0 left-0 right-0 z-50 h-14 border-b border-border bg-background/95 backdrop-blur-md">
        <div className="mx-auto flex h-full max-w-3xl items-center justify-between px-4">
          <Link href="/">
            <span className="text-gold-gradient text-lg font-bold tracking-[0.15em] select-none">
              WAVMASH
            </span>
          </Link>
          {isLegalPage && (
            <span className="text-xs text-white/40">Privacy Policy</span>
          )}
        </div>
      </header>
    );
  }

  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-14 border-b border-border bg-background/95 backdrop-blur-md">
      <div className="flex h-full items-center gap-3 px-4 lg:pl-[calc(240px+1rem)]">
        <Link href="/" className="flex-shrink-0 lg:hidden">
          <span className="text-gold-gradient text-lg font-bold tracking-[0.1em] select-none">
            W
          </span>
        </Link>

        <form onSubmit={handleSearch} className="flex-1 max-w-xl mx-auto">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="아티스트, 곡 검색..."
              className="w-full h-9 rounded-full bg-secondary border border-border pl-9 pr-4 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:ring-1 focus:ring-[#d4a853]/40 transition-shadow"
            />
          </div>
        </form>

        <div className="flex items-center gap-1 shrink-0">
          {user ? (
            <div className="relative" ref={menuRef}>
              <button
                type="button"
                aria-label="계정 메뉴"
                aria-expanded={menuOpen}
                onClick={() => setMenuOpen((v) => !v)}
                className="rounded-lg overflow-hidden w-9 h-9 flex items-center justify-center hover:bg-secondary transition-colors cursor-pointer ring-1 ring-white/10"
              >
                {avatarUrl ? (
                  <img
                    src={avatarUrl}
                    alt=""
                    className="w-full h-full object-cover"
                    referrerPolicy="no-referrer"
                  />
                ) : (
                  <div className="w-full h-full bg-secondary flex items-center justify-center text-xs font-semibold text-[#d4a853]">
                    {displayName.charAt(0).toUpperCase() || (
                      <UserIcon className="w-4 h-4" />
                    )}
                  </div>
                )}
              </button>

              <AnimatePresence>
                {menuOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: -6, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -6, scale: 0.98 }}
                    transition={{ duration: 0.15 }}
                    className="absolute right-0 top-[calc(100%+8px)] z-[60] w-64 rounded-xl border border-white/10 bg-[#12121c]/98 shadow-2xl backdrop-blur-xl overflow-hidden"
                  >
                    <div className="flex items-center gap-3 px-4 py-3 border-b border-white/8">
                      <div className="w-11 h-11 rounded-full overflow-hidden bg-secondary shrink-0 ring-1 ring-[#d4a853]/40">
                        {avatarUrl ? (
                          <img
                            src={avatarUrl}
                            alt=""
                            className="w-full h-full object-cover"
                            referrerPolicy="no-referrer"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-sm font-bold text-[#d4a853]">
                            {displayName.charAt(0).toUpperCase()}
                          </div>
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-white truncate">
                          {displayName}
                        </p>
                        <p className="text-xs text-white/45 truncate">
                          @{username}
                        </p>
                        {user.email && (
                          <p className="text-[10px] text-white/30 truncate mt-0.5">
                            {user.email}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="p-1.5">
                      <button
                        type="button"
                        onClick={() => go(profileHref)}
                        className="w-full flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-white/85 hover:bg-white/8 cursor-pointer text-left"
                      >
                        <UserIcon className="w-4 h-4 text-[#d4a853]" />
                        내 프로필
                      </button>
                      <button
                        type="button"
                        onClick={() => go('/playlists')}
                        className="w-full flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-white/85 hover:bg-white/8 cursor-pointer text-left"
                      >
                        <Disc3 className="w-4 h-4 text-white/50" />
                        플레이리스트
                      </button>
                      <button
                        type="button"
                        onClick={() => go('/library')}
                        className="w-full flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-white/85 hover:bg-white/8 cursor-pointer text-left"
                      >
                        <Library className="w-4 h-4 text-white/50" />
                        라이브러리
                      </button>
                      <button
                        type="button"
                        onClick={() => go('/download')}
                        className="w-full flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-white/85 hover:bg-white/8 cursor-pointer text-left"
                      >
                        <Download className="w-4 h-4 text-white/50" />
                        다운로드
                      </button>
                    </div>

                    <div className="border-t border-white/8 p-1.5">
                      <button
                        type="button"
                        onClick={() => void handleSignOut()}
                        className="w-full flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-red-400 hover:bg-red-500/10 cursor-pointer text-left"
                      >
                        <LogOut className="w-4 h-4" />
                        로그아웃
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ) : (
            <Link href="/login">
              <Button
                variant="ghost"
                size="sm"
                className="text-sm text-[#d4a853] hover:text-[#b58c3f]"
              >
                로그인
              </Button>
            </Link>
          )}

          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden text-muted-foreground"
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            {mobileOpen ? (
              <X className="h-5 w-5" />
            ) : (
              <Menu className="h-5 w-5" />
            )}
          </Button>
        </div>
      </div>

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            className="lg:hidden absolute top-14 left-0 right-0 border-b border-border bg-background/98 backdrop-blur-xl"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
          >
            <nav className="flex flex-col py-2">
              {NAV_ITEMS.map((item) => {
                const isActive =
                  item.href === '/'
                    ? pathname === '/'
                    : pathname.startsWith(item.href);
                const Icon = item.icon;

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileOpen(false)}
                    className={`flex items-center gap-3 px-5 py-3 text-sm font-medium transition-colors ${
                      isActive
                        ? 'text-[#d4a853] bg-secondary/50'
                        : 'text-muted-foreground hover:text-foreground hover:bg-secondary/30'
                    }`}
                  >
                    <Icon className="h-5 w-5" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
