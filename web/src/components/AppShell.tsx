'use client';

import { usePathname } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import RightPanel from '@/components/RightPanel';

const STANDALONE_ROUTES = ['/login'];
const WIDE_ROUTES = ['/search', '/artist'];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isStandalone = STANDALONE_ROUTES.some((r) => pathname.startsWith(r));
  const isWide = WIDE_ROUTES.some((r) => pathname.startsWith(r));

  if (isStandalone) {
    return <>{children}</>;
  }

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="app-main">
        <div className={`app-content ${isWide ? 'app-content-wide' : ''}`}>
          {children}
        </div>
        {!isWide && <RightPanel />}
      </div>
    </div>
  );
}
