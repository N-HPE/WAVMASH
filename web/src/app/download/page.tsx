'use client';

/* ──────────────────────────────────────────────
   WaveMash — 다운로드 (Download Page)
   ────────────────────────────────────────────── */

import { motion } from 'framer-motion';
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

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.3 },
  },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

export default function DownloadPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 sm:px-6 py-12">
      {/* ── Header ── */}
      <motion.div
        className="text-center mb-10"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="text-3xl font-light mb-2">
          <span className="text-gold-gradient font-bold">음악</span> 다운로드
        </h1>
        <p className="text-muted-foreground text-sm">
          Spotify 플리 링크를 넣으면 곡을 받아 커버·BPM·Key까지 자동으로 정리합니다
        </p>
      </motion.div>

      {/* ── Download Form ── */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
      >
        <DownloadForm />
      </motion.div>

      {/* ── Info Cards ── */}
      <motion.div
        className="mt-16"
        variants={container}
        initial="hidden"
        animate="show"
      >
        <h2 className="text-lg font-medium mb-6 text-center">다운로드 방법</h2>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {INFO_CARDS.map((card) => (
            <motion.div
              key={card.title}
              variants={item}
              className="glass rounded-xl p-6 text-center hover-lift"
            >
              <div
                className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl"
                style={{ backgroundColor: card.color + '15' }}
              >
                <card.icon
                  className="h-6 w-6"
                  style={{ color: card.color }}
                />
              </div>
              <h3 className="text-sm font-medium mb-2">{card.title}</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {card.description}
              </p>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
