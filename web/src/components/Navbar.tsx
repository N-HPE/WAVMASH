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
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { FormEvent, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { getProfileHref } from '@/lib/profile';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

const NAV_ITEMS = [
  { label: '홈', href: '/', icon: Home },
  { label: '검색', href: '/search', icon: Compass },
  { label: '라이브러리', href: '/library', icon: Library },
  { label: '플레이리스트', href: '/playlists', icon: ListMusic },
] as const;

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [query, setQuery] = useState('');
  const { user, profile, signOut } = useAuth();
  const profileHref = getProfileHref(user, profile);

  const isLoginPage = pathname.startsWith('/login');
  const isLegalPage = pathname.startsWith('/privacy');

  const handleSearch = (e: FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    if (q) router.push(`/search?q=${encodeURIComponent(q)}`);
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
            <DropdownMenu>
              <DropdownMenuTrigger className="rounded-lg overflow-hidden w-9 h-9 flex items-center justify-center hover:bg-secondary transition-colors cursor-pointer">
                {profile?.avatar_url ? (
                  <img
                    src={profile.avatar_url}
                    alt="Avatar"
                    className="w-full h-full object-cover"
                  />
                ) : user.user_metadata?.picture ? (
                  <img
                    src={user.user_metadata.picture as string}
                    alt="Avatar"
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full bg-secondary flex items-center justify-center text-xs">
                    {profile?.display_name?.charAt(0).toUpperCase() ||
                      user.email?.charAt(0).toUpperCase() || (
                        <UserIcon className="w-4 h-4" />
                      )}
                  </div>
                )}
              </DropdownMenuTrigger>
              <DropdownMenuContent
                align="end"
                className="w-56 border-border bg-popover"
              >
                <DropdownMenuLabel className="font-normal">
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium leading-none">
                      {profile?.display_name || user.email}
                    </p>
                    <p className="text-xs leading-none text-muted-foreground">
                      @{profile?.username || 'me'}
                    </p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  className="cursor-pointer"
                  onClick={() => router.push(profileHref)}
                >
                  내 프로필
                </DropdownMenuItem>
                <DropdownMenuItem className="cursor-pointer">설정</DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  className="text-red-400 focus:text-red-400 cursor-pointer"
                  onClick={() => signOut()}
                >
                  로그아웃
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
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
