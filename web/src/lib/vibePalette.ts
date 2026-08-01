/* ──────────────────────────────────────────────
   WaveMash — 플레이리스트 바이브(장르) 색 팔레트
   같은 계열 안에서 shade가 낮을수록 더 대중적/코어,
   높을수록 더 밝고 가벼운(또는 세부) 서브장르.
   ────────────────────────────────────────────── */

export type VibeId =
  | 'pop'
  | 'rnb'
  | 'hiphop'
  | 'house'
  | 'techno'
  | 'bass'
  | 'chill'
  | 'other';

export interface VibeShade {
  /** 0 = 코어/대중, 숫자가 클수록 밝고 가벼운 쪽 */
  shade: number;
  hex: string;
  label: string;
}

export interface VibeCategory {
  id: VibeId;
  label: string;
  description: string;
  shades: VibeShade[];
}

export const VIBE_CATEGORIES: VibeCategory[] = [
  {
    id: 'pop',
    label: 'Pop',
    description: '노란색 — 대중 팝 → 밝고 가벼운 팝',
    shades: [
      { shade: 0, hex: '#E5B820', label: 'Mainstream Pop' },
      { shade: 1, hex: '#F5D045', label: 'Dance Pop' },
      { shade: 2, hex: '#FFE566', label: 'Bright Pop' },
      { shade: 3, hex: '#FFF59D', label: 'Light / Soft Pop' },
    ],
  },
  {
    id: 'rnb',
    label: 'R&B',
    description: '빨간색 — 클래식 R&B → 네오소울',
    shades: [
      { shade: 0, hex: '#8B1A1A', label: 'Classic R&B' },
      { shade: 1, hex: '#C62828', label: 'Contemporary R&B' },
      { shade: 2, hex: '#E53935', label: 'Soul' },
      { shade: 3, hex: '#EF5350', label: 'Neo-Soul' },
    ],
  },
  {
    id: 'hiphop',
    label: 'Hip-Hop',
    description: '검정 — 힙합 → 트랩/드릴',
    shades: [
      { shade: 0, hex: '#111111', label: 'Hip-Hop' },
      { shade: 1, hex: '#2A2A2A', label: 'Boom Bap' },
      { shade: 2, hex: '#3D3D3D', label: 'Trap' },
      { shade: 3, hex: '#555555', label: 'Drill / Alt' },
    ],
  },
  {
    id: 'house',
    label: 'House',
    description: '시안/틸 — 하우스 → 딥/테크하우스',
    shades: [
      { shade: 0, hex: '#0D7377', label: 'House' },
      { shade: 1, hex: '#14919B', label: 'Deep House' },
      { shade: 2, hex: '#28A5C5', label: 'Tech House' },
      { shade: 3, hex: '#7DD3E8', label: 'Organic / Disco House' },
    ],
  },
  {
    id: 'techno',
    label: 'Techno',
    description: '인디고 — 테크노 → 미니멀',
    shades: [
      { shade: 0, hex: '#1A237E', label: 'Techno' },
      { shade: 1, hex: '#283593', label: 'Peak Techno' },
      { shade: 2, hex: '#5C6BC0', label: 'Melodic Techno' },
      { shade: 3, hex: '#9FA8DA', label: 'Minimal / Ambient Techno' },
    ],
  },
  {
    id: 'bass',
    label: 'Bass',
    description: '초록 — 베이스/덥스텝 → DnB',
    shades: [
      { shade: 0, hex: '#1B5E20', label: 'Bass' },
      { shade: 1, hex: '#2E7D32', label: 'Dubstep' },
      { shade: 2, hex: '#43A047', label: 'Bass House' },
      { shade: 3, hex: '#81C784', label: 'Drum & Bass' },
    ],
  },
  {
    id: 'chill',
    label: 'Chill',
    description: '라벤더 — 칠/로파이 → 앰비언트',
    shades: [
      { shade: 0, hex: '#5E35B1', label: 'Chill' },
      { shade: 1, hex: '#7E57C2', label: 'Lo-Fi' },
      { shade: 2, hex: '#9575CD', label: 'Downtempo' },
      { shade: 3, hex: '#B39DDB', label: 'Ambient' },
    ],
  },
  {
    id: 'other',
    label: 'Other',
    description: '뉴트럴 — 미분류 / 믹스',
    shades: [
      { shade: 0, hex: '#6D4C41', label: 'Mix / Other' },
      { shade: 1, hex: '#8D6E63', label: 'Eclectic' },
      { shade: 2, hex: '#A1887F', label: 'Experimental' },
      { shade: 3, hex: '#BCAAA4', label: 'Misc' },
    ],
  },
];

export const VIBE_ORDER: VibeId[] = VIBE_CATEGORIES.map((c) => c.id);

export function getVibeCategory(id: string | null | undefined): VibeCategory {
  return VIBE_CATEGORIES.find((c) => c.id === id) ?? VIBE_CATEGORIES[VIBE_CATEGORIES.length - 1];
}

export function getVibeColor(vibe: string | null | undefined, shade = 0): string {
  const cat = getVibeCategory(vibe);
  const clamped = Math.max(0, Math.min(shade, cat.shades.length - 1));
  return cat.shades[clamped]?.hex ?? cat.shades[0].hex;
}

export function resolvePlaylistColor(opts: {
  color?: string | null;
  vibe?: string | null;
  shade?: number | null;
}): string {
  if (opts.color && /^#[0-9A-Fa-f]{6}$/.test(opts.color)) return opts.color;
  return getVibeColor(opts.vibe, opts.shade ?? 0);
}

export function isDarkColor(hex: string): boolean {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return 0.299 * r + 0.587 * g + 0.114 * b < 140;
}

/** 이름 기반 기본 바이브 추정 (마이그레이션/자동 분류용) */
export function inferVibeFromName(name: string): { vibe: VibeId; shade: number } {
  const n = name.toLowerCase();
  if (/\b(old\s*)?pop\b|dance\s*pop|electropop/.test(n)) {
    if (/old|retro|vintage/.test(n)) return { vibe: 'pop', shade: 1 };
    if (/light|soft|bright|cute/.test(n)) return { vibe: 'pop', shade: 2 };
    return { vibe: 'pop', shade: 0 };
  }
  if (/r&?b|rnb|soul|neo.?soul/.test(n)) return { vibe: 'rnb', shade: 0 };
  if (/hip.?hop|rap|trap|drill/.test(n)) return { vibe: 'hiphop', shade: 0 };
  if (/house|vino|afro.?house|tech.?house/.test(n)) return { vibe: 'house', shade: 0 };
  if (/techno|minimal/.test(n)) return { vibe: 'techno', shade: 0 };
  if (/bass|dubstep|dnb|drum.?and.?bass/.test(n)) return { vibe: 'bass', shade: 0 };
  if (/chill|lo.?fi|lofi|ambient|downtempo/.test(n)) return { vibe: 'chill', shade: 0 };
  return { vibe: 'other', shade: 0 };
}
