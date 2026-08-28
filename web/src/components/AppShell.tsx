'use client';

import { usePathname } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import RightPanel from '@/components/RightPanel';

const STANDALONE_ROUTES = ['/login'];
const HIDE_RIGHT_PANEL_ROUTES = ['/', '/profile'];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isStandalone = STANDALONE_ROUTES.some((r) => pathname.startsWith(r));
  const hideRightPanel = HIDE_RIGHT_PANEL_ROUTES.some(
    (r) => r === '/' ? pathname === '/' : pathname.startsWith(r)
  );

  if (isStandalone) {
    return <>{children}</>;
  }

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="app-main">
        <div className={`app-content ${pathname === '/' ? 'app-content-wide' : ''}`}>
          {children}
        </div>
        {!hideRightPanel && <RightPanel />}
      </div>
    </div>
  );
}
