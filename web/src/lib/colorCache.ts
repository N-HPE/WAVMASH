/* ──────────────────────────────────────────────
   WaveMash — Cover color IndexedDB cache
   브라우저 로컬에 색상을 영속 저장해 재방문 시
   네트워크 없이 즉시 글로우를 복원합니다.
   ────────────────────────────────────────────── */

const DB_NAME = 'wavemash-cache';
const DB_VERSION = 1;
const STORE = 'cover_colors';

export interface CachedColor {
  track_id: string;
  color: string;
  updated_at: number;
}

let dbPromise: Promise<IDBDatabase> | null = null;

function openDb(): Promise<IDBDatabase> {
  if (typeof indexedDB === 'undefined') {
    return Promise.reject(new Error('IndexedDB unavailable'));
  }
  if (!dbPromise) {
    dbPromise = new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onerror = () => reject(req.error ?? new Error('IndexedDB open failed'));
      req.onsuccess = () => resolve(req.result);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(STORE)) {
          db.createObjectStore(STORE, { keyPath: 'track_id' });
        }
      };
    });
  }
  return dbPromise;
}

function withStore<T>(
  mode: IDBTransactionMode,
  fn: (store: IDBObjectStore) => IDBRequest<T>
): Promise<T> {
  return openDb().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const tx = db.transaction(STORE, mode);
        const store = tx.objectStore(STORE);
        const req = fn(store);
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error ?? new Error('IndexedDB request failed'));
      })
  );
}

export async function getCachedColors(
  trackIds: string[]
): Promise<Map<string, string>> {
  const result = new Map<string, string>();
  if (!trackIds.length) return result;

  try {
    const db = await openDb();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, 'readonly');
      const store = tx.objectStore(STORE);
      let pending = trackIds.length;
      if (pending === 0) {
        resolve();
        return;
      }
      for (const id of trackIds) {
        const req = store.get(id);
        req.onsuccess = () => {
          const row = req.result as CachedColor | undefined;
          if (row?.color) result.set(id, row.color);
          pending -= 1;
          if (pending === 0) resolve();
        };
        req.onerror = () => {
          pending -= 1;
          if (pending === 0) resolve();
        };
      }
      tx.onerror = () => reject(tx.error ?? new Error('IndexedDB tx failed'));
    });
  } catch {
    // IndexedDB 실패 시 빈 맵 반환 (네트워크 폴백)
  }
  return result;
}

export async function setCachedColors(
  colors: Record<string, string | null | undefined>
): Promise<void> {
  const entries = Object.entries(colors).filter(
    (entry): entry is [string, string] => Boolean(entry[1])
  );
  if (!entries.length) return;

  try {
    const db = await openDb();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      const store = tx.objectStore(STORE);
      const now = Date.now();
      for (const [track_id, color] of entries) {
        store.put({ track_id, color, updated_at: now } satisfies CachedColor);
      }
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error ?? new Error('IndexedDB write failed'));
    });
  } catch {
    // ignore
  }
}

export async function getCachedColor(trackId: string): Promise<string | null> {
  try {
    const row = await withStore<CachedColor | undefined>('readonly', (store) =>
      store.get(trackId)
    );
    return row?.color ?? null;
  } catch {
    return null;
  }
}
