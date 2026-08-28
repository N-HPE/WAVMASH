'use client';

import { PlayCircle, Music2, ListMusic } from 'lucide-react';
import DownloadForm from '@/components/DownloadForm';

const INFO_CARDS = [
  {
    icon: PlayCircle,
    title: 'YouTube',
    description: '영상 URL을 붙여넣으면 최고 품질 WAV로 저장합니다.',
    color: '#FF0000',
  },
  {
    icon: Music2,
    title: 'Spotify',
    description: '트랙·앨범·플레이리스트 링크만 넣으면 메타데이터까지 자동 추출합니다.',
    color: '#1DB954',
  },
  {
    icon: ListMusic,
    title: '보관소 정리',
    description: '커버 · BPM · Key를 추출해 나만의 로컬 음악 보관소로 정리합니다.',
    color: '#d4a853',
  },
];

export default function DownloadPage() {
  return (
    <div className="py-4 space-y-4">
      <div className="feed-card p-6 text-center">
        <h1 className="text-2xl font-bold mb-2">
          <span className="text-gold-gradient">음악</span> 다운로드
        </h1>
        <p className="text-muted-foreground text-sm mb-6">
          Spotify 플리 링크를 넣으면 곡을 받아 커버·BPM·Key까지 자동으로 정리합니다
        </p>
        <DownloadForm />
      </div>

      <div className="feed-card p-4">
        <h2 className="text-sm font-semibold mb-4 px-1">다운로드 방법</h2>
        <div className="space-y-3">
          {INFO_CARDS.map((card) => (
            <div
              key={card.title}
              className="flex items-start gap-3 rounded-md p-3 hover:bg-white/[0.02] transition-colors"
            >
              <div
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
                style={{ backgroundColor: card.color + '15' }}
              >
                <card.icon className="h-5 w-5" style={{ color: card.color }} />
              </div>
              <div>
                <h3 className="text-sm font-medium mb-0.5">{card.title}</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {card.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
