import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { TooltipProvider } from '@/components/ui/tooltip';
import Navbar from '@/components/Navbar';
import { PlayerProvider } from '@/contexts/PlayerContext';
import { DownloadProvider } from '@/contexts/DownloadContext';
import { AuthProvider } from '@/contexts/AuthContext';
import MiniPlayer from '@/components/MiniPlayer';
import DownloadProgressBar from '@/components/DownloadProgressBar';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: 'WaveMash — 프리미엄 음반 컬렉션',
  description:
    '고품질 음악을 다운로드하고 관리하세요. YouTube와 Spotify에서 최고의 음질로 컬렉션을 구축합니다.',
  keywords: ['음악', '컬렉션', '다운로드', 'YouTube', 'Spotify'],
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
                <main className="pt-16 pb-28">{children}</main>
                <DownloadProgressBar />
                <MiniPlayer />
              </DownloadProvider>
            </PlayerProvider>
          </TooltipProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
