'use client';

import Link from 'next/link';
import { ArrowRight, Download } from 'lucide-react';
import DownloadForm from '@/components/DownloadForm';

export default function DownloadPage() {
  return (
    <div className="py-4 space-y-4">
      <div className="feed-card p-5 sm:p-6">
        <div className="mb-5">
          <h1 className="text-xl font-bold mb-1">음원 다운로드</h1>
          <p className="text-sm text-muted-foreground">
            Spotify 플레이리스트·트랙, YouTube / YouTube Music URL을 붙여넣으세요.
            플리는 곡 목록을 확인한 뒤 선택한 트랙만 WAV/MP3로 받습니다.
          </p>
        </div>

        <DownloadForm variant="stacked" />

        <div className="mt-4 flex flex-wrap gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-md bg-secondary px-2.5 py-1 text-xs text-muted-foreground">
            <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="#1DB954">
              <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02z" />
            </svg>
            Spotify 플리 / 트랙 / 앨범
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-md bg-secondary px-2.5 py-1 text-xs text-muted-foreground">
            <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="#FF0000">
              <path d="M23.498 6.186a2.994 2.994 0 0 0-2.112-2.12C19.505 3.546 12 3.546 12 3.546s-7.505 0-9.386.52A2.994 2.994 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a2.994 2.994 0 0 0 2.112 2.12c1.881.52 9.386.52 9.386.52s7.505 0 9.386-.52a2.994 2.994 0 0 0 2.112-2.12C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
            </svg>
            YouTube · YouTube Music
          </span>
        </div>
      </div>

      <div className="flex items-center justify-between px-1">
        <p className="text-xs text-muted-foreground">받은 곡은 라이브러리에 쌓입니다.</p>
        <Link
          href="/library?sort_by=recent"
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-[#d4a853] transition-colors"
        >
          <Download className="h-3 w-3" />
          라이브러리
          <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
    </div>
  );
}
