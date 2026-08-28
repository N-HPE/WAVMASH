'use client';

/* ──────────────────────────────────────────────
   WaveMash — Mobile Bottom Navigation Bar
   인스타그램 스타일의 모바일 하단 5버튼 네비게이션
   ────────────────────────────────────────────── */

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Flame, Compass, Library, Download, User } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { getProfileHref } from '@/lib/profile';

export default function MobileBottomNav() {
  const pathname = usePathname();
  const { user, profile } = useAuth();

  if (pathname.startsWith('/login') || pathname.startsWith('/privacy')) {
    return null;
  }

  const profileHref = getProfileHref(user, profile);

  const NAV_BUTTONS = [
    { label: '홈', href: '/', icon: Flame },
    { label: '검색', href: '/search', icon: Compass },
    { label: '다운로드', href: '/download', icon: Download },
    { label: '라이브러리', href: '/library', icon: Library },
    { label: '프로필', href: profileHref, icon: User },
  ];

  return (
    <div className="md:hidden fixed bottom-0 left-0 right-0 z-40 h-16 glass-strong bg-[#090912]/95 border-t border-white/10 px-2 flex items-center justify-around">
      {NAV_BUTTONS.map((item) => {
        const Icon = item.icon;
        const isActive =
          item.href === '/'
            ? pathname === '/'
            : pathname.startsWith(item.href);

        return (
          <Link
            key={item.href}
            href={item.href}
            className="flex flex-col items-center justify-center w-14 h-full gap-1 text-[10px] transition-all"
          >
            <Icon
              className={`w-5 h-5 transition-transform ${
                isActive ? 'text-[#d4a853] scale-110' : 'text-white/50 hover:text-white/80'
              }`}
            />
            <span
              className={`font-medium ${
                isActive ? 'text-[#d4a853] font-bold' : 'text-white/50'
              }`}
            >
              {item.label}
            </span>
          </Link>
        );
      })}
    </div>
  );
}
