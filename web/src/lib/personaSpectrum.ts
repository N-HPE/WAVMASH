/**
 * Nexus persona identity spectrum — Echo (black) → Yachi (white).
 * Keep in sync with NEXUS `config/artisan_playlists.json` → persona_spectrum.
 * Genre vibePalette.ts stays for WAVMASH chart classification (빨주노초…).
 */

export interface PersonaSpectrumEntry {
  artisanKey: string;
  name: string;
  playlist: string;
  color: string;
  chartBuckets: string[];
}

/** Dark → light tab / identity order */
export const PERSONA_SPECTRUM: PersonaSpectrumEntry[] = [
  {
    artisanKey: 'echo',
    name: 'Echo',
    playlist: 'ECHO',
    color: '#0A0A0A',
    chartBuckets: ['blue', 'indigo', 'violet'],
  },
  {
    artisanKey: 'stock',
    name: 'Midas',
    playlist: 'MIDAS',
    color: '#1C1C1C',
    chartBuckets: ['red'],
  },
  {
    artisanKey: 'sports',
    name: 'Paolo',
    playlist: 'PAOLO',
    color: '#1B4332',
    chartBuckets: ['green', 'violet'],
  },
  {
    artisanKey: 'fashion',
    name: 'Rocky',
    playlist: 'ROCKY',
    color: '#9B2226',
    chartBuckets: ['red', 'orange'],
  },
  {
    artisanKey: 'business',
    name: 'Hermes',
    playlist: 'HERMES',
    color: '#005F73',
    chartBuckets: ['blue', 'indigo'],
  },
  {
    artisanKey: 'music',
    name: 'Nova',
    playlist: 'NOVA',
    color: '#6B5344',
    chartBuckets: ['yellow', 'green'],
  },
  {
    artisanKey: 'now',
    name: 'Nau',
    playlist: 'Nau',
    color: '#CA8A04',
    chartBuckets: ['yellow'],
  },
  {
    artisanKey: 'health',
    name: 'Galen',
    playlist: 'GALEN',
    color: '#6D28D9',
    chartBuckets: ['green', 'indigo'],
  },
  {
    artisanKey: 'art',
    name: 'Leo',
    playlist: 'LEO',
    color: '#A78BFA',
    chartBuckets: ['green'],
  },
  {
    artisanKey: 'media',
    name: 'Ari',
    playlist: 'ARI',
    color: '#FB7185',
    chartBuckets: ['red', 'orange'],
  },
  {
    artisanKey: 'macro',
    name: 'Mac',
    playlist: 'Mac',
    color: '#E9D5FF',
    chartBuckets: ['green', 'indigo'],
  },
  {
    artisanKey: 'yachi',
    name: 'Yachi',
    playlist: 'YACHI',
    color: '#FAFAFA',
    chartBuckets: ['blue', 'indigo'],
  },
];

export function personaColor(artisanKey: string): string | undefined {
  return PERSONA_SPECTRUM.find((p) => p.artisanKey === artisanKey)?.color;
}
