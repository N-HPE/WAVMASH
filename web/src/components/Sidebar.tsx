'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Home,
  Library,
  ListMusic,
  User as UserIcon,
  Compass,
  Download,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

const NAV_ITEMS = [
  { label: '홈', href: '/', icon: Home },
  { label: '검색', href: '/search', icon: Compass },
  { label: '다운로드', href: '/download', icon: Download },
  { label: '라이브러리', href: '/library', icon: Library },
  { label: '플레이리스트', href: '/playlists', icon: ListMusic },
] as const;

export default function Sidebar() {
  const pathname = usePathname();
  const { user, profile } = useAuth();

  return (
    <aside className="app-sidebar hidden lg:flex flex-col">
      <div className="px-4 py-4 border-b border-border">
        <Link href="/">
          <span className="text-gold-gradient text-lg font-bold tracking-[0.15em] select-none">
            WAVMASH
          </span>
        </Link>
      </div>
      <nav className="flex flex-col gap-1 p-3">
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
              className={`sidebar-nav-item ${isActive ? 'sidebar-nav-item-active' : ''}`}
            >
              <Icon className="h-5 w-5 shrink-0" />
              <span className="truncate">{item.label}</span>
            </Link>
          );
        })}

        {user && (
          <Link
            href={`/profile/${profile?.username || user.id}`}
            className={`sidebar-nav-item ${
              pathname.startsWith('/profile') ? 'sidebar-nav-item-active' : ''
            }`}
          >
            {profile?.avatar_url ? (
              <img
                src={profile.avatar_url}
                alt=""
                className="h-5 w-5 shrink-0 rounded-md object-cover"
              />
            ) : (
              <UserIcon className="h-5 w-5 shrink-0" />
            )}
            <span className="truncate">내 프로필</span>
          </Link>
        )}
      </nav>

      <div className="mt-auto p-4 border-t border-border">
        <p className="text-xs text-muted-foreground leading-relaxed">
          WaveMash — 음악 컬렉션을 공유하고 탐색하세요.
        </p>
      </div>
    </aside>
  );
}
