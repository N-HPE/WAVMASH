import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { TooltipProvider } from '@/components/ui/tooltip';
import Navbar from '@/components/Navbar';
import AppShell from '@/components/AppShell';
import { PlayerProvider } from '@/contexts/PlayerContext';
import { DownloadProvider } from '@/contexts/DownloadContext';
import { AuthProvider } from '@/contexts/AuthContext';
import MiniPlayer from '@/components/MiniPlayer';
import DownloadProgressBar from '@/components/DownloadProgressBar';
import MobileBottomNav from '@/components/MobileBottomNav';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: 'WaveMash — 디거들의 바이닐 & 무손실 음악 쇼케이스',
  description:
    '내가 소장한 명곡과 바이닐/WAV 컬렉션을 자랑하고, 친구들과 피드로 디깅하며 소통하는 음악 소셜 플랫폼.',
  keywords: ['음악', '컬렉션', '바이닐', 'WAV', '디깅', '소셜', 'Lossless'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="ko"
      className={`${inter.variable} dark`}
      suppressHydrationWarning
    >
      <head>
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"
        />
      </head>
      <body className="min-h-screen bg-background text-foreground font-sans antialiased">
        <AuthProvider>
          <TooltipProvider delay={300}>
            <PlayerProvider>
              <DownloadProvider>
                <Navbar />
                <main className="pb-28 sm:pb-24">
                  <AppShell>{children}</AppShell>
                </main>
                <DownloadProgressBar />
                <MiniPlayer />
                <MobileBottomNav />
              </DownloadProvider>
            </PlayerProvider>
          </TooltipProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
