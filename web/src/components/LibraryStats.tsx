'use client';

/* ──────────────────────────────────────────────
   WaveMash — Library Stats Dashboard
   ────────────────────────────────────────────── */

import { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { Disc3, Users, Library } from 'lucide-react';
import type { LibraryStats } from '@/lib/types';

/* ── Animated Counter ── */

function AnimatedNumber({ value, duration = 1.2 }: { value: number; duration?: number }) {
  const [display, setDisplay] = useState(0);
  const startTimeRef = useRef<number | null>(null);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    if (value === 0) {
      setDisplay(0);
      return;
    }

    const animate = (timestamp: number) => {
      if (!startTimeRef.current) startTimeRef.current = timestamp;
      const elapsed = timestamp - startTimeRef.current;
      const progress = Math.min(elapsed / (duration * 1000), 1);

      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(Math.round(eased * value));

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate);
      }
    };

    startTimeRef.current = null;
    rafRef.current = requestAnimationFrame(animate);

    return () => cancelAnimationFrame(rafRef.current);
  }, [value, duration]);

  return <>{display.toLocaleString()}</>;
}

/* ── Stats Cards ── */

const STAT_ITEMS = [
  { key: 'total_tracks' as const, label: '총 트랙', Icon: Disc3 },
  { key: 'total_artists' as const, label: '아티스트', Icon: Users },
  { key: 'total_albums' as const, label: '앨범', Icon: Library },
];

interface LibraryStatsProps {
  stats: LibraryStats;
}

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

export default function LibraryStatsView({ stats }: LibraryStatsProps) {
  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      {/* ── Stat Cards ── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {STAT_ITEMS.map(({ key, label, Icon }) => (
          <motion.div
            key={key}
            variants={item}
            className="glass rounded-xl p-6 relative overflow-hidden"
          >
            {/* Background icon */}
            <Icon className="absolute top-4 right-4 h-8 w-8 text-[#d4a853]/10" />

            <div className="relative">
              <p className="text-gold-gradient text-4xl font-bold tabular-nums">
                <AnimatedNumber value={stats[key]} />
              </p>
              <p className="mt-1 text-sm text-muted-foreground">{label}</p>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
