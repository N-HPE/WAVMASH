'use client';

/* ──────────────────────────────────────────────
   WaveMash — Navigation Bar
   ────────────────────────────────────────────── */

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Menu, X, User as UserIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

const NAV_ITEMS = [
  { label: '대시보드', href: '/' },
  { label: '라이브러리', href: '/library' },
  { label: '플레이리스트', href: '/playlists' },
  { label: '다운로드', href: '/download' },
] as const;

export default function Navbar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user, profile, signOut } = useAuth();

  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-16 glass-strong">
      <div className="mx-auto flex h-full max-w-7xl items-center justify-between px-4 sm:px-6">
        {/* ── Logo ── */}
        <Link href="/" className="flex-shrink-0">
          <span className="text-gold-gradient text-xl font-bold tracking-[0.2em] select-none">
            WAVMASH
          </span>
        </Link>

        {/* ── Desktop Nav ── */}
        <nav className="hidden md:flex items-center gap-1">
          {NAV_ITEMS.map((item) => {
            const isActive =
              item.href === '/'
                ? pathname === '/'
                : pathname.startsWith(item.href);

            return (
              <Link key={item.href} href={item.href}>
                <motion.div
                  className="relative px-4 py-2 text-sm font-medium transition-colors"
                  style={{
                    color: isActive
                      ? '#d4a853'
                      : 'rgba(255, 255, 255, 0.6)',
                  }}
                  whileHover={{ color: '#d4a853' }}
                >
                  {item.label}
                  {isActive && (
                    <motion.div
                      className="absolute bottom-0 left-2 right-2 h-[2px] rounded-full"
                      style={{
                        background:
                          'linear-gradient(90deg, transparent, #d4a853, transparent)',
                      }}
                      layoutId="nav-underline"
                      transition={{
                        type: 'spring',
                        stiffness: 380,
                        damping: 30,
                      }}
                    />
                  )}
                </motion.div>
              </Link>
            );
          })}
        </nav>

        {/* ── Right Actions ── */}
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            className="text-muted-foreground hover:text-foreground"
          >
            <Search className="h-4 w-4" />
          </Button>

          {user ? (
            <DropdownMenu>
              <DropdownMenuTrigger className="rounded-full overflow-hidden w-8 h-8 ml-2 flex items-center justify-center hover:opacity-80 transition-opacity cursor-pointer">
                  {profile?.avatar_url ? (
                    <img src={profile.avatar_url} alt="Avatar" className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full bg-white/10 flex items-center justify-center text-xs rounded-full">
                      {profile?.display_name?.charAt(0).toUpperCase() || <UserIcon className="w-4 h-4" />}
                    </div>
                  )}
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56 glass-strong border-white/10 bg-black/80 backdrop-blur-xl">
                <DropdownMenuLabel className="font-normal">
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium leading-none">{profile?.display_name || user.email}</p>
                    <p className="text-xs leading-none text-muted-foreground">
                      @{profile?.username || 'user'}
                    </p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator className="bg-white/10" />
                <DropdownMenuItem className="hover:bg-white/10 focus:bg-white/10 cursor-pointer">
                  <Link href={`/profile/${profile?.username || user.id}`} className="w-full">내 프로필</Link>
                </DropdownMenuItem>
                <DropdownMenuItem className="hover:bg-white/10 focus:bg-white/10 cursor-pointer">
                  설정
                </DropdownMenuItem>
                <DropdownMenuSeparator className="bg-white/10" />
                <DropdownMenuItem className="text-red-400 hover:bg-white/10 focus:bg-white/10 focus:text-red-400 cursor-pointer" onClick={() => signOut()}>
                  로그아웃
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Link href="/login">
              <Button variant="ghost" className="ml-2 text-sm text-[#d4a853] hover:text-[#b58c3f] hover:bg-white/5">
                로그인
              </Button>
            </Link>
          )}

          {/* Mobile hamburger */}
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden text-muted-foreground hover:text-foreground ml-1"
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

      {/* ── Bottom Gold Line ── */}
      <div
        className="absolute bottom-0 left-0 right-0 h-px"
        style={{
          background:
            'linear-gradient(90deg, transparent 0%, #d4a853 50%, transparent 100%)',
          opacity: 0.4,
        }}
      />

      {/* ── Mobile Nav Overlay ── */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            className="md:hidden absolute top-16 left-0 right-0 glass-strong border-t border-white/5 bg-background/95 backdrop-blur-xl"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
          >
            <nav className="flex flex-col py-2">
              {NAV_ITEMS.map((item) => {
                const isActive =
                  item.href === '/'
                    ? pathname === '/'
                    : pathname.startsWith(item.href);

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileOpen(false)}
                    className={`px-6 py-3 text-sm font-medium transition-colors ${
                      isActive
                        ? 'text-[#d4a853]'
                        : 'text-white/60 hover:text-white/90'
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
              
              {!user && (
                <Link
                  href="/login"
                  onClick={() => setMobileOpen(false)}
                  className="px-6 py-3 text-sm font-medium text-[#d4a853] transition-colors"
                >
                  로그인
                </Link>
              )}
            </nav>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
