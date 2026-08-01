import json
import os
import re
import shutil
import sqlite3
import subprocess
import time
import urllib.request
import uuid
from typing import Any

import static_ffmpeg
from mutagen.wave import WAVE
from mutagen.id3 import TIT2, TPE1, TPE2, TALB, TCON, TBPM, TKEY, TDRC, COMM, APIC

from paths import PROJECT_DIR
from env_loader import ensure_env_loaded

ensure_env_loaded()

from paths import default_wav_root  # noqa: E402

WAV_ROOT = default_wav_root()
SINGLES_ALBUM = 'Singles'
UNKNOWN = 'Unknown'

ARCHIVE_JSON_PATH = os.path.join(PROJECT_DIR, 'archive.json')
TRACK_INDEX_DB_PATH = os.path.join(PROJECT_DIR, 'track_index.db')
PLAYLISTS_JSON_PATH = os.path.join(PROJECT_DIR, 'playlists.json')

JSON_SKIP_KEYS = frozenset({'cover_data', 'cover_mime'})

ARCHIVE_CORE_KEYS = frozenset({
    'track_id', 'external_id', 'url', 'platform', 'title', 'artist',
    'primary_artist', 'album', 'genre', 'year', 'format', 'thumbnail_url', 'analysis',
    'mix_data',
})

_INDEX_ROW_KEYS = (
    'track_id', 'artist', 'title', 'bpm', 'key', 'camelot_key',
    'energy_level', 'bpm_source', 'local_path', 'url', 'platform', 'mix_data',
)

DEFAULT_MIX_TRANSITION = {
    'duration_ms': 6000,
    'eq_behavior': 'bass_swap',
    'volume_curve': 'logarithmic',
}

_CAMELOT_WHEEL = {
    'B Major': '1B', 'F# Major': '2B', 'C# Major': '3B', 'G# Major': '4B',
    'D# Major': '5B', 'A# Major': '6B', 'F Major': '7B', 'C Major': '8B',
    'G Major': '9B', 'D Major': '10B', 'A Major': '11B', 'E Major': '12B',
    'G# Minor': '1A', 'D# Minor': '2A', 'A# Minor': '3A', 'F Minor': '4A',
    'C Minor': '5A', 'G Minor': '6A', 'D Minor': '7A', 'A Minor': '8A',
    'E Minor': '9A', 'B Minor': '10A', 'F# Minor': '11A', 'C# Minor': '12A',
}

_KEY_COMPACT_RE = re.compile(r'^([A-Ga-g][#b]?)\s+(Major|Minor)$', re.I)
_ENHARMONIC_COMPACT = {'Db': 'C#', 'Eb': 'D#', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#'}
_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
    re.I,
)


def safe_rename(
    src: str,
    dst: str,
    *,
    max_retries: int = 8,
    delay: float = 0.25,
) -> bool:
    """Rename/move with OneDrive WinError 32 retries; copy+delete fallback."""
    if not src or not dst:
        return False
    if os.path.normcase(os.path.abspath(src)) == os.path.normcase(os.path.abspath(dst)):
        return True

    ensure_parent_dir(dst)
    last_exc: BaseException | None = None

    for attempt in range(max_retries):
        try:
            os.replace(src, dst)
            return True
        except PermissionError as exc:
            last_exc = exc
            winerr = getattr(exc, 'winerror', None)
            if winerr == 32 or 'WinError 32' in str(exc):
                time.sleep(delay * (attempt + 1))
                continue
            break
        except OSError as exc:
            last_exc = exc
            if getattr(exc, 'winerror', None) == 32:
                time.sleep(delay * (attempt + 1))
                continue
            break

    try:
        shutil.copy2(src, dst)
        for attempt in range(max_retries):
            try:
                os.remove(src)
                return True
            except PermissionError as exc:
                last_exc = exc
                if getattr(exc, 'winerror', None) == 32:
                    time.sleep(delay * (attempt + 1))
                    continue
                break
            except OSError as exc:
                last_exc = exc
                if getattr(exc, 'winerror', None) == 32:
                    time.sleep(delay * (attempt + 1))
                    continue
                break
        print(
            f"[Library] 복사 완료, 원본 삭제 실패 (OneDrive 잠금): "
            f"{os.path.basename(src)} — {last_exc}"
        )
        return True
    except OSError as exc:
        print(f"[Library] safe_rename 실패: {os.path.basename(src)} — {last_exc or exc}")
        return False


def _safe_replace_file(src: str, dst: str) -> bool:
    """Backward-compatible alias for safe_rename."""
    return safe_rename(src, dst)

# Split featured / collaborator strings into individual artist names.
_ARTIST_SEP_RE = re.compile(r'\s*[/,;|]\s*')
_FEAT_SPLIT_RE = re.compile(r'\s+(?:feat\.?|ft\.?|featuring)\s+', re.I)
_AND_COLLAB_RE = re.compile(r'\s+&\s+')
_X_COLLAB_RE = re.compile(r'\s+[xX]\s+')
_SPOTIFY_TRACK_ID_RE = re.compile(
    r'(?:open\.)?spotify\.com/track/([a-zA-Z0-9]+)',
    re.IGNORECASE,
)


def split_artists(raw: str) -> list[str]:
    """Return a list of artist names from a tag or metadata string."""
    raw = (raw or '').strip()
    if not raw:
        return [UNKNOWN]

    for splitter in (_ARTIST_SEP_RE.split, _FEAT_SPLIT_RE.split):
        parts = [p.strip() for p in splitter(raw) if p.strip()]
        if len(parts) > 1:
            return parts

    if _AND_COLLAB_RE.search(raw):
        parts = [p.strip() for p in _AND_COLLAB_RE.split(raw) if p.strip()]
        if len(parts) > 1:
            return parts

    if _X_COLLAB_RE.search(raw):
        parts = [p.strip() for p in _X_COLLAB_RE.split(raw) if p.strip()]
        if len(parts) > 1:
            return parts

    return [raw]


def primary_artist(raw: str) -> str:
    """Main artist used for the top-level library folder."""
    parts = split_artists(raw)
    first = parts[0].strip()
    # Recover from collapsed tags like "Dom DollaNelly Furtado" (no separator).
    for prefix in (
        'Dom Dolla', 'Chris Lake', 'Chris Lorenzo', 'Matroda', 'FISHER',
        'San Pacho', 'Wax Motif', 'Sunday Scaries', 'Brad Oberhofer', 'FutureVille',
    ):
        if first.startswith(prefix) and len(first) > len(prefix):
            return sanitize_path_part(prefix, UNKNOWN)
    return sanitize_path_part(first, UNKNOWN)


def display_artists(raw: str) -> str:
    """Human-readable multi-artist string for tags and UI."""
    parts = split_artists(raw)
    if len(parts) <= 1:
        return sanitize_path_part(raw, UNKNOWN)
    return sanitize_path_part(', '.join(parts), UNKNOWN)


def folder_artist(meta: dict) -> str:
    """Artist directory name for on-disk layout."""
    if meta.get('primary_artist'):
        return sanitize_path_part(meta['primary_artist'], UNKNOWN)
    return primary_artist(str(meta.get('artist', '')))


def normalize_artist_meta(meta: dict) -> dict:
    """Ensure meta carries a clean display artist and primary folder artist."""
    meta = dict(meta)
    raw = str(meta.get('artist') or '').strip()
    if meta.get('primary_artist'):
        meta['primary_artist'] = sanitize_path_part(meta['primary_artist'], UNKNOWN)
        if not raw or raw == meta['primary_artist']:
            meta['artist'] = meta['primary_artist']
        else:
            meta['artist'] = display_artists(raw)
        return meta
    if raw:
        meta['artist'] = display_artists(raw)
        meta['primary_artist'] = primary_artist(raw)
    else:
        meta['artist'] = UNKNOWN
        meta['primary_artist'] = UNKNOWN
    return meta


def sanitize_path_part(name, fallback=UNKNOWN):
    cleaned = re.sub(r'[\\/*?:"<>|]', '', (name or '').strip())
    cleaned = re.sub(r'\s+', ' ', cleaned).strip('. ')
    return cleaned or fallback


def parse_artist_title(title, fallback_artist):
    title = (title or '').strip()
    fallback_artist = (fallback_artist or UNKNOWN).strip()
    for sep in (' - ', ' – ', ' — ', ' | '):
        if sep in title:
            artist, track = title.split(sep, 1)
            artist, track = artist.strip(), track.strip()
            if artist and track:
                return artist, track
    return fallback_artist, title or UNKNOWN


_VERSION_MARKERS = [
    (re.compile(r'\bextended\b', re.I), 'Extended'),
    (re.compile(r'\bradio\s*(?:edit|mix|version)\b', re.I), 'Radio Edit'),
    (re.compile(r'\bclub\s*mix\b', re.I), 'Club Mix'),
    (re.compile(r'\boriginal\s*mix\b', re.I), 'Original'),
    (re.compile(r'\bshort\s*(?:edit|version)\b', re.I), 'Short Edit'),
    (re.compile(r'\binstrumental\b', re.I), 'Instrumental'),
    (re.compile(r'\bvip\s*(?:mix|edit)?\b', re.I), 'VIP'),
]

# Markers that get stripped (parenthetical or trailing "- ...") to find the
# shared base title that all versions of one recording have in common.
_VERSION_STRIP = re.compile(
    r'(?:[\(\[\{][^)\]\}]*\b(?:extended|radio|club|original|instrumental|short|vip|edit|mix|version)\b[^)\]\}]*[\)\]\}])'
    r'|(?:\s*[-–—]\s*(?:extended|radio|club|original|instrumental|short|vip)\b.*$)',
    re.I,
)


def split_version(title):
    """Return ``(base_title, version_label)`` for a track title.

    Strips length/edit markers like ``(Extended Mix)`` or ``- Radio Edit`` so the
    base title is shared across versions, and labels the variant ('Original' when
    no marker is present).
    """
    raw = (title or '').strip()
    label = 'Original'
    for rx, name in _VERSION_MARKERS:
        if rx.search(raw):
            label = name
            break
    base = _VERSION_STRIP.sub('', raw)
    base = re.sub(r'\s+', ' ', base).strip(' -–—')
    return (base or raw), label


def version_group_key(artist, title):
    """Stable key shared by all length/edit versions of the same recording."""
    base, _ = split_version(title)
    return re.sub(r'[^a-z0-9]', '', f'{artist or ""}{base}'.lower())


def extract_metadata(info):
    raw_title = info.get('track') or info.get('title') or UNKNOWN
    fallback_artist = (
        info.get('artist')
        or info.get('creator')
        or info.get('channel')
        or info.get('uploader')
        or UNKNOWN
    )
    artist, title = parse_artist_title(raw_title, fallback_artist)

    album = info.get('album') or info.get('album_name')
    if not album and info.get('playlist'):
        album = info.get('playlist_title') or info.get('playlist')
    album = sanitize_path_part(album, SINGLES_ALBUM) if album else SINGLES_ALBUM

    genre = info.get('genre')
    if not genre:
        categories = info.get('categories') or []
        genre = next((c for c in categories if c), None)
    genre = sanitize_path_part(genre, UNKNOWN)

    year = info.get('release_year')
    if not year:
        upload_date = info.get('upload_date') or info.get('release_date') or ''
        if len(str(upload_date)) >= 4:
            year = str(upload_date)[:4]

    thumb_url = info.get('thumbnail') or ''
    for item in reversed(info.get('thumbnails') or []):
        url = item.get('url')
        if url:
            thumb_url = url
            break

    return {
        'id': info.get('id') or 'unknown_id',
        'title': sanitize_path_part(title, UNKNOWN),
        'artist': sanitize_path_part(artist, UNKNOWN),
        'primary_artist': primary_artist(artist),
        'album': album,
        'genre': genre,
        'year': str(year) if year else '',
        'platform': info.get('extractor_key', UNKNOWN),
        'url': info.get('webpage_url') or info.get('original_url') or '',
        'thumbnail_url': thumb_url,
    }


_KEY_HAS_MODE = re.compile(r'\b(Major|Minor)\b', re.I)


def key_has_mode(key: str) -> bool:
    """True when the key string includes Major or Minor (Camelot-ready form)."""
    return bool(_KEY_HAS_MODE.search(str(key or '')))


def upgrade_record_key(rec: dict, *, reanalyze: bool = False) -> bool:
    """Fill in Major/Minor for legacy records; refresh WAV tags and filename.

    Uses ``analysis.key`` when present. Returns True if the record was updated.
    """
    if key_has_mode(str(rec.get('key', ''))):
        return False

    new_key = None
    analysis = rec.get('analysis')
    if isinstance(analysis, dict):
        ak = str(analysis.get('key') or '')
        if key_has_mode(ak):
            new_key = ak

    if not new_key or not key_has_mode(new_key):
        return False

    rec['key'] = new_key
    path = str(rec.get('path') or '')
    if not path or not os.path.isfile(path):
        return True

    meta = {
        'artist': rec.get('artist', UNKNOWN),
        'primary_artist': rec.get('primary_artist'),
        'album': rec.get('album', SINGLES_ALBUM),
        'title': rec.get('title', UNKNOWN),
    }
    new_path = plan_track_path(meta, bpm=rec.get('bpm'), key=new_key)
    if os.path.normcase(path) != os.path.normcase(new_path):
        ensure_parent_dir(new_path)
        if os.path.exists(new_path):
            os.remove(new_path)
        if not _safe_replace_file(path, new_path):
            return True
        rec['path'] = new_path
        path = new_path

    write_wav_tags(path, rec)
    return True


def apply_bpm_key_to_record(
    rec: dict,
    bpm: int | float | str | None,
    key: str | None,
    *,
    bpm_source: str | None = None,
    **kwargs: Any,
) -> bool:
    """Apply external BPM/key lookup to a record; rename WAV and refresh tags."""
    return apply_track_metadata(
        rec,
        bpm=bpm,
        key=key,
        bpm_source=bpm_source,
        **kwargs,
    )


def needs_bpm_key_update(rec: dict) -> bool:
    """True when BPM or Key is still missing / Unknown."""
    bpm = str(rec.get("bpm") or "").strip()
    key = str(rec.get("key") or "").strip()
    bpm_missing = not bpm or bpm in ("0", "Unknown", UNKNOWN)
    key_missing = not key or key == UNKNOWN
    return bpm_missing or key_missing


def effective_artist_title(artist: str, title: str) -> tuple[str, str]:
    """Best-effort artist/title for external metadata search."""
    artist = str(artist or "").strip()
    title = str(title or "").strip()
    if (not artist or artist == UNKNOWN) and " - " in title:
        left, right = title.split(" - ", 1)
        left, right = left.strip(), right.strip()
        if left and right:
            return left, right
    return artist or UNKNOWN, title or UNKNOWN


def apply_spotify_metadata_to_record(
    rec: dict,
    meta: dict,
    bpm: int | str | None,
    key: str | None,
    cover_data: bytes | None = None,
    cover_mime: str | None = None,
) -> bool:
    """Apply Spotify catalog fields to a library record and refresh the WAV file."""
    changed = False
    path = str(rec.get('path') or '')

    for field in ('id', 'title', 'artist', 'primary_artist', 'album', 'genre', 'year', 'url', 'platform'):
        value = meta.get(field)
        if value and str(rec.get(field) or '') != str(value):
            rec[field] = value
            changed = True

    try:
        bpm_val = int(round(float(bpm))) if bpm not in (None, '', 0, '0') else 0
    except (TypeError, ValueError):
        bpm_val = 0
    if bpm_val > 0:
        new_bpm = str(bpm_val)
        if str(rec.get('bpm') or '') != new_bpm:
            rec['bpm'] = new_bpm
            changed = True

    if key and key != UNKNOWN:
        if str(rec.get('key') or '') != key:
            rec['key'] = key
            changed = True

    if not changed and not cover_data:
        return False
    if not path or not os.path.isfile(path):
        return changed

    meta_block = {
        'artist': rec.get('artist', UNKNOWN),
        'primary_artist': rec.get('primary_artist'),
        'album': rec.get('album', SINGLES_ALBUM),
        'title': rec.get('title', UNKNOWN),
    }
    new_path = plan_track_path(meta_block, bpm=rec.get('bpm'), key=rec.get('key'))
    if os.path.normcase(path) != os.path.normcase(new_path):
        ensure_parent_dir(new_path)
        if os.path.exists(new_path):
            os.remove(new_path)
        if not _safe_replace_file(path, new_path):
            return changed
        rec['path'] = new_path
        path = new_path
        changed = True

    write_wav_tags(path, rec, cover_data=cover_data, cover_mime=cover_mime or 'image/jpeg')
    if cover_data:
        save_album_cover_sidecar(path, cover_data, cover_mime)
    return True


def format_key_compact(key: str | None) -> str:
    """Convert ``F# Minor`` / ``C Major`` to DJ compact form ``F#m`` / ``CM``."""
    raw = str(key or '').strip()
    if not raw or raw == UNKNOWN:
        return 'Unknown Key'
    match = _KEY_COMPACT_RE.match(raw)
    if match:
        pitch = match.group(1)
        pitch = pitch[0].upper() + pitch[1:]
        if len(pitch) >= 2 and pitch[1] in '#b':
            pitch = _ENHARMONIC_COMPACT.get(pitch[:2], pitch[:2]) + pitch[2:]
        elif pitch in _ENHARMONIC_COMPACT:
            pitch = _ENHARMONIC_COMPACT[pitch]
        return f"{pitch}m" if match.group(2).lower() == 'minor' else f"{pitch}M"
    return sanitize_path_part(raw, 'Unknown Key')


def camelot_from_key(key: str | None) -> str:
    return _CAMELOT_WHEEL.get(str(key or '').strip(), '')


def format_bpm_storage(bpm: Any) -> str:
    """Store BPM for records/tags; keeps MIK-style decimals when needed."""
    try:
        value = float(bpm)
    except (TypeError, ValueError):
        return ''
    if value <= 0:
        return ''
    rounded = round(value, 3)
    if abs(rounded - round(rounded)) < 0.001:
        return str(int(round(rounded)))
    text = f"{rounded:.3f}".rstrip('0').rstrip('.')
    return text or ''


def beat_offset_from_record(record: dict[str, Any]) -> float:
    analysis = record.get('analysis')
    if isinstance(analysis, dict):
        for key in ('mik_beat_offset_sec', 'beat_offset_sec'):
            try:
                return float(analysis.get(key) or 0)
            except (TypeError, ValueError):
                continue
    return 0.0


def normalize_bpm_source(source: str | None) -> str:
    src = str(source or '').strip().lower()
    if not src:
        return ''
    if 'mik' in src:
        return 'mik'
    if 'tag' in src:
        return 'tags'
    if src in ('api', 'getsongbpm', 'verified'):
        return 'api' if src == 'getsongbpm' else src
    if src in ('analyzed', 'local', 'librosa', 'audioflux'):
        return 'analyzed'
    if 'getsongbpm' in src and 'local' in src:
        return 'analyzed'
    if 'getsongbpm' in src:
        return 'api'
    if 'local' in src or 'analy' in src:
        return 'analyzed'
    return src if src in ('api', 'analyzed', 'verified', 'mik', 'tags') else ''


def apply_track_metadata(
    rec: dict,
    *,
    bpm: int | float | str | None = None,
    key: str | None = None,
    camelot_key: str | None = None,
    energy_level: int | None = None,
    bpm_source: str | None = None,
    beat_offset_sec: float | None = None,
) -> bool:
    """Apply BPM/key/energy (and optional beat phase) from MIK, tags, or APIs."""
    from mik_metadata import key_from_camelot

    changed = False
    path = str(rec.get('path') or rec.get('local_path') or '')

    bpm_text = format_bpm_storage(bpm) if bpm not in (None, '', 0, '0') else ''
    if bpm_text and str(rec.get('bpm') or '') != bpm_text:
        rec['bpm'] = bpm_text
        changed = True

    resolved_key = str(key or '').strip()
    resolved_camelot = str(camelot_key or rec.get('camelot_key') or '').strip().upper()
    if not resolved_key or resolved_key == UNKNOWN or not key_has_mode(resolved_key):
        from_mik = key_from_camelot(resolved_camelot)
        if from_mik:
            resolved_key = from_mik
    if resolved_key and resolved_key != UNKNOWN and key_has_mode(resolved_key):
        if str(rec.get('key') or '') != resolved_key:
            rec['key'] = resolved_key
            changed = True
        camelot = camelot_from_key(resolved_key) or resolved_camelot
        if camelot and rec.get('camelot_key') != camelot:
            rec['camelot_key'] = camelot
            changed = True
    elif resolved_camelot and rec.get('camelot_key') != resolved_camelot:
        rec['camelot_key'] = resolved_camelot
        changed = True

    if energy_level is not None:
        try:
            lvl = int(energy_level)
            if 1 <= lvl <= 5 and rec.get('energy_level') != lvl:
                rec['energy_level'] = lvl
                changed = True
        except (TypeError, ValueError):
            pass

    if bpm_source:
        normalized = normalize_bpm_source(bpm_source)
        if normalized and rec.get('bpm_source') != normalized:
            rec['bpm_source'] = normalized
            changed = True

    if beat_offset_sec is not None:
        try:
            offset = float(beat_offset_sec)
        except (TypeError, ValueError):
            offset = None
        if offset is not None:
            analysis = dict(rec.get('analysis') or {}) if isinstance(rec.get('analysis'), dict) else {}
            if analysis.get('mik_beat_offset_sec') != offset:
                analysis['mik_beat_offset_sec'] = round(offset, 4)
                rec['analysis'] = analysis
                changed = True

    if not changed:
        return False

    if path and os.path.isfile(path):
        meta = {
            'artist': rec.get('artist', UNKNOWN),
            'primary_artist': rec.get('primary_artist'),
            'album': rec.get('album', SINGLES_ALBUM),
            'title': rec.get('title', UNKNOWN),
        }
        new_path = plan_track_path(meta, bpm=rec.get('bpm'), key=rec.get('key'))
        if os.path.normcase(path) != os.path.normcase(new_path):
            ensure_parent_dir(new_path)
            if os.path.exists(new_path):
                os.remove(new_path)
            if not safe_rename(path, new_path):
                sync_record_index(rec)
                return True
            rec['path'] = new_path
            rec['local_path'] = new_path
            path = new_path
        write_wav_tags(path, rec)

    sync_record_index(rec)
    return True


def new_track_id() -> str:
    return str(uuid.uuid4())


def _is_uuid(value: str | None) -> bool:
    return bool(value and _UUID_RE.match(str(value)))


def ensure_track_id(record: dict[str, Any]) -> str:
    """Assign a UUID ``track_id``; keep legacy platform id in ``external_id``."""
    existing = str(record.get('track_id') or '').strip()
    if _is_uuid(existing):
        record['track_id'] = existing
        record['id'] = existing
        return existing

    legacy = str(record.get('id') or '').strip()
    if _is_uuid(legacy):
        record['track_id'] = legacy
        record['id'] = legacy
        return legacy

    platform_id = legacy or str(record.get('external_id') or '').strip()
    track_id = new_track_id()
    record['track_id'] = track_id
    record['id'] = track_id
    if platform_id and not _is_uuid(platform_id):
        record['external_id'] = platform_id
    return track_id


def energy_level_from_record(record: dict[str, Any]) -> int:
    raw = record.get('energy_level')
    if raw is not None:
        try:
            level = int(raw)
            if 1 <= level <= 5:
                return level
        except (TypeError, ValueError):
            pass
    analysis = record.get('analysis')
    if isinstance(analysis, dict):
        for key in ('energy_level', 'energy'):
            try:
                level = int(analysis.get(key) or 0)
                if 1 <= level <= 5:
                    return level
            except (TypeError, ValueError):
                continue
    return 0


def default_mix_data() -> dict[str, Any]:
    return {
        'cues': {'mix_in': 0, 'mix_out': 0},
        'transition': dict(DEFAULT_MIX_TRANSITION),
    }


def normalize_mix_data(data: dict[str, Any] | None) -> dict[str, Any]:
    base = default_mix_data()
    if not isinstance(data, dict):
        return base

    cues = data.get('cues')
    if isinstance(cues, dict):
        for key in ('mix_in', 'mix_out'):
            try:
                base['cues'][key] = max(0, int(cues.get(key) or 0))
            except (TypeError, ValueError):
                pass

    transition = data.get('transition')
    if isinstance(transition, dict):
        try:
            base['transition']['duration_ms'] = max(
                500, int(transition.get('duration_ms') or DEFAULT_MIX_TRANSITION['duration_ms'])
            )
        except (TypeError, ValueError):
            pass
        eq = str(transition.get('eq_behavior') or DEFAULT_MIX_TRANSITION['eq_behavior'])
        if eq in ('bass_swap', 'none'):
            base['transition']['eq_behavior'] = eq
        curve = str(transition.get('volume_curve') or DEFAULT_MIX_TRANSITION['volume_curve'])
        if curve in ('linear', 'logarithmic'):
            base['transition']['volume_curve'] = curve
    return base


def parse_mix_data(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return normalize_mix_data(raw)
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return default_mix_data()
        if isinstance(parsed, dict):
            return normalize_mix_data(parsed)
    return default_mix_data()


def mix_data_to_json(data: dict[str, Any]) -> str:
    return json.dumps(normalize_mix_data(data), ensure_ascii=False, separators=(',', ':'))


def mix_data_from_record(record: dict[str, Any]) -> dict[str, Any]:
    """Resolve mix_data from explicit field, SQLite JSON, or legacy analysis cues (sec → ms)."""
    explicit = record.get('mix_data')
    if explicit:
        md = parse_mix_data(explicit)
        if md['cues']['mix_in'] or md['cues']['mix_out']:
            return md

    analysis = record.get('analysis')
    if isinstance(analysis, dict):
        data = default_mix_data()
        cue_in = analysis.get('cue_in')
        cue_out = analysis.get('cue_out')
        duration = analysis.get('duration')
        if cue_in is not None:
            try:
                data['cues']['mix_in'] = max(0, int(float(cue_in) * 1000))
            except (TypeError, ValueError):
                pass
        if cue_out is not None:
            try:
                data['cues']['mix_out'] = max(0, int(float(cue_out) * 1000))
            except (TypeError, ValueError):
                pass
        elif duration is not None:
            try:
                data['cues']['mix_out'] = max(0, int(float(duration) * 1000))
            except (TypeError, ValueError):
                pass
        return data

    return default_mix_data()


def clear_record_cues(record: dict[str, Any]) -> None:
    """Remove mix IN/OUT cues from a track record."""
    record['mix_data'] = default_mix_data()
    analysis = dict(record.get('analysis') or {})
    analysis.pop('cue_in', None)
    analysis.pop('cue_out', None)
    record['analysis'] = analysis


def clear_all_record_cues(records: list[dict[str, Any]]) -> int:
    """Clear mix cues on every track that has any. Returns count cleared."""
    cleared = 0
    for rec in records:
        md = mix_data_from_record(rec)
        analysis = rec.get('analysis') or {}
        if (
            md['cues']['mix_in']
            or md['cues']['mix_out']
            or 'cue_in' in analysis
            or 'cue_out' in analysis
        ):
            clear_record_cues(rec)
            cleared += 1
    return cleared


def remove_record_mix_cue(record: dict[str, Any], *, remove_in: bool = False, remove_out: bool = False) -> None:
    """Remove one or both mix cues while keeping the other fields intact."""
    md = mix_data_from_record(record)
    analysis = dict(record.get('analysis') or {})
    if remove_out:
        md['cues']['mix_out'] = 0
        analysis.pop('cue_out', None)
    if remove_in:
        md['cues']['mix_in'] = 0
        analysis.pop('cue_in', None)
    record['mix_data'] = md
    record['analysis'] = analysis


def update_record_mix_cues(
    record: dict[str, Any],
    *,
    mix_in_ms: int | None = None,
    mix_out_ms: int | None = None,
    transition: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Update mix_data and keep legacy analysis cue_in/out (seconds) in sync."""
    md = mix_data_from_record(record)
    if mix_in_ms is not None:
        md['cues']['mix_in'] = max(0, int(mix_in_ms))
    if mix_out_ms is not None:
        md['cues']['mix_out'] = max(0, int(mix_out_ms))
    if transition:
        md['transition'].update(normalize_mix_data({'transition': transition})['transition'])
    record['mix_data'] = md

    analysis = dict(record.get('analysis') or {})
    if mix_in_ms is not None:
        analysis['cue_in'] = round(mix_in_ms / 1000.0, 3)
    if mix_out_ms is not None:
        analysis['cue_out'] = round(mix_out_ms / 1000.0, 3)
    if analysis:
        record['analysis'] = analysis
    return md


def sanitize_record_for_db(record: dict[str, Any]) -> dict[str, Any]:
    return {
        k: v
        for k, v in record.items()
        if k not in JSON_SKIP_KEYS and not isinstance(v, (bytes, bytearray))
    }


def _parse_bpm_int(bpm: Any) -> int:
    try:
        value = int(round(float(bpm)))
        return value if value > 0 else 0
    except (TypeError, ValueError):
        return 0


def record_to_index_row(record: dict[str, Any]) -> dict[str, Any]:
    ensure_track_id(record)
    local_path = str(record.get('local_path') or record.get('path') or '')
    key = str(record.get('key') or '')
    bpm = _parse_bpm_int(record.get('bpm'))
    return {
        'track_id': record['track_id'],
        'artist': str(record.get('artist') or ''),
        'title': str(record.get('title') or ''),
        'bpm': bpm,
        'key': key,
        'camelot_key': str(record.get('camelot_key') or camelot_from_key(key)),
        'energy_level': energy_level_from_record(record),
        'bpm_source': normalize_bpm_source(str(record.get('bpm_source') or '')),
        'local_path': local_path,
        'url': str(record.get('url') or ''),
        'platform': str(record.get('platform') or ''),
        'mix_data': mix_data_to_json(mix_data_from_record(record)),
    }


def record_to_archive_core(record: dict[str, Any]) -> dict[str, Any]:
    ensure_track_id(record)
    core = sanitize_record_for_db(record)
    allowed = set(ARCHIVE_CORE_KEYS)
    stripped = {k: v for k, v in core.items() if k in allowed}
    for key in ARCHIVE_CORE_KEYS:
        if key not in stripped and key in core:
            stripped[key] = core[key]
    if 'track_id' not in stripped:
        stripped['track_id'] = record['track_id']
    return stripped


def merge_core_and_index(core: dict[str, Any], index: dict[str, Any]) -> dict[str, Any]:
    merged = dict(core)
    merged.update(index)
    track_id = str(core.get('track_id') or index.get('track_id') or '')
    merged['track_id'] = track_id
    merged['id'] = track_id
    local_path = str(index.get('local_path') or core.get('local_path') or core.get('path') or '')
    merged['local_path'] = local_path
    merged['path'] = local_path
    bpm_int = _parse_bpm_int(index.get('bpm', merged.get('bpm')))
    merged['bpm'] = str(bpm_int) if bpm_int else str(merged.get('bpm') or '')
    merged['key'] = str(index.get('key') or merged.get('key') or '')
    merged['camelot_key'] = str(
        index.get('camelot_key') or merged.get('camelot_key') or camelot_from_key(merged['key'])
    )
    merged['bpm_source'] = normalize_bpm_source(
        str(index.get('bpm_source') or merged.get('bpm_source') or '')
    )
    merged['energy_level'] = int(index.get('energy_level') or energy_level_from_record(merged))
    merged['url'] = str(index.get('url') or merged.get('url') or '')
    merged['platform'] = str(index.get('platform') or merged.get('platform') or '')
    merged['mix_data'] = mix_data_from_record({**merged, 'mix_data': index.get('mix_data')})
    return merged


class TrackIndexDB:
    """Lightweight SQLite cache for fast UI search/sort."""

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS tracks (
        track_id TEXT PRIMARY KEY NOT NULL,
        artist TEXT NOT NULL DEFAULT '',
        title TEXT NOT NULL DEFAULT '',
        bpm INTEGER NOT NULL DEFAULT 0,
        key TEXT NOT NULL DEFAULT '',
        camelot_key TEXT NOT NULL DEFAULT '',
        energy_level INTEGER NOT NULL DEFAULT 0,
        bpm_source TEXT NOT NULL DEFAULT '',
        local_path TEXT NOT NULL DEFAULT '',
        url TEXT NOT NULL DEFAULT '',
        platform TEXT NOT NULL DEFAULT '',
        mix_data TEXT NOT NULL DEFAULT '{}'
    );
    CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks(artist);
    CREATE INDEX IF NOT EXISTS idx_tracks_bpm ON tracks(bpm);
    CREATE INDEX IF NOT EXISTS idx_tracks_title ON tracks(title);
    CREATE INDEX IF NOT EXISTS idx_tracks_camelot ON tracks(camelot_key);
    """

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or TRACK_INDEX_DB_PATH

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        return conn

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(self._SCHEMA)
            self._ensure_mix_data_column(conn)

    def _ensure_mix_data_column(self, conn: sqlite3.Connection) -> None:
        cols = {row[1] for row in conn.execute('PRAGMA table_info(tracks)')}
        if 'mix_data' not in cols:
            conn.execute(
                "ALTER TABLE tracks ADD COLUMN mix_data TEXT NOT NULL DEFAULT '{}'"
            )

    def upsert(self, row: dict[str, Any]) -> None:
        self.ensure_schema()
        payload = {k: row.get(k, '') for k in _INDEX_ROW_KEYS}
        payload['bpm'] = int(payload.get('bpm') or 0)
        payload['energy_level'] = int(payload.get('energy_level') or 0)
        if not str(payload.get('mix_data') or '').strip():
            payload['mix_data'] = mix_data_to_json(default_mix_data())
        elif not isinstance(payload.get('mix_data'), str):
            payload['mix_data'] = mix_data_to_json(parse_mix_data(payload['mix_data']))
        columns = ', '.join(_INDEX_ROW_KEYS)
        placeholders = ', '.join('?' for _ in _INDEX_ROW_KEYS)
        updates = ', '.join(f'{k}=excluded.{k}' for k in _INDEX_ROW_KEYS if k != 'track_id')
        sql = (
            f'INSERT INTO tracks ({columns}) VALUES ({placeholders}) '
            f'ON CONFLICT(track_id) DO UPDATE SET {updates}'
        )
        with self._connect() as conn:
            conn.execute(sql, tuple(payload[k] for k in _INDEX_ROW_KEYS))

    def delete(self, track_id: str) -> None:
        self.ensure_schema()
        with self._connect() as conn:
            conn.execute('DELETE FROM tracks WHERE track_id = ?', (track_id,))

    def fetch_all(self) -> list[dict[str, Any]]:
        self.ensure_schema()
        with self._connect() as conn:
            rows = conn.execute(
                f'SELECT {", ".join(_INDEX_ROW_KEYS)} FROM tracks ORDER BY artist, title'
            ).fetchall()
        return [dict(row) for row in rows]

    def fetch_one(self, track_id: str) -> dict[str, Any] | None:
        self.ensure_schema()
        with self._connect() as conn:
            row = conn.execute(
                f'SELECT {", ".join(_INDEX_ROW_KEYS)} FROM tracks WHERE track_id = ?',
                (track_id,),
            ).fetchone()
        return dict(row) if row else None


def sync_record_index(record: dict[str, Any]) -> None:
    TrackIndexDB().upsert(record_to_index_row(record))


def _load_archive_json_raw() -> list[dict[str, Any]]:
    if not os.path.exists(ARCHIVE_JSON_PATH):
        return []
    try:
        with open(ARCHIVE_JSON_PATH, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]
    except Exception:
        broken = ARCHIVE_JSON_PATH + '.broken'
        try:
            os.replace(ARCHIVE_JSON_PATH, broken)
        except OSError:
            pass
        return []


def _save_archive_json(cores: list[dict[str, Any]]) -> None:
    payload = [record_to_archive_core(core) for core in cores]
    tmp = ARCHIVE_JSON_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=4, ensure_ascii=False)
    if not safe_rename(tmp, ARCHIVE_JSON_PATH):
        with open(ARCHIVE_JSON_PATH, 'w', encoding='utf-8') as handle:
            json.dump(payload, handle, indent=4, ensure_ascii=False)
        try:
            os.remove(tmp)
        except OSError:
            pass


def _looks_like_legacy_archive(records: list[dict[str, Any]]) -> bool:
    if not records:
        return False
    if os.path.exists(TRACK_INDEX_DB_PATH):
        return False
    sample = records[0]
    return bool(sample.get('path') or sample.get('bpm') or sample.get('key'))


def _remap_playlist_track_ids(id_map: dict[str, str]) -> None:
    if not id_map or not os.path.isfile(PLAYLISTS_JSON_PATH):
        return
    try:
        with open(PLAYLISTS_JSON_PATH, 'r', encoding='utf-8') as handle:
            playlists = json.load(handle)
    except Exception:
        return
    if not isinstance(playlists, dict):
        return
    changed = False
    for name, ids in playlists.items():
        if not isinstance(ids, list):
            continue
        new_ids: list[str] = []
        for tid in ids:
            mapped = id_map.get(str(tid), str(tid))
            if mapped != tid:
                changed = True
            if mapped and mapped not in new_ids:
                new_ids.append(mapped)
        playlists[name] = new_ids
    if not changed:
        return
    with open(PLAYLISTS_JSON_PATH, 'w', encoding='utf-8') as handle:
        json.dump(playlists, handle, indent=4, ensure_ascii=False)


def _migrate_legacy_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    id_map: dict[str, str] = {}
    migrated: list[dict[str, Any]] = []
    index_db = TrackIndexDB()
    index_db.ensure_schema()

    for raw in records:
        rec = sanitize_record_for_db(raw)
        old_id = str(rec.get('id') or '').strip()
        if not rec.get('track_id'):
            ensure_track_id(rec)
        if old_id and old_id != rec['track_id']:
            id_map[old_id] = rec['track_id']
        if rec.get('path') and not rec.get('local_path'):
            rec['local_path'] = rec['path']
        if rec.get('key') and not rec.get('camelot_key'):
            rec['camelot_key'] = camelot_from_key(str(rec['key']))
        if rec.get('analysis') and not rec.get('energy_level'):
            rec['energy_level'] = energy_level_from_record(rec)
        index_db.upsert(record_to_index_row(rec))
        migrated.append(merge_core_and_index(record_to_archive_core(rec), record_to_index_row(rec)))

    _remap_playlist_track_ids(id_map)
    _save_archive_json([record_to_archive_core(rec) for rec in migrated])
    print(f'[Library] legacy archive.json → hybrid storage ({len(migrated)} tracks)')
    return migrated


def load_library_records() -> list[dict[str, Any]]:
    raw = _load_archive_json_raw()
    if _looks_like_legacy_archive(raw):
        return _migrate_legacy_records(raw)

    index_db = TrackIndexDB()
    index_db.ensure_schema()
    index_by_id = {row['track_id']: row for row in index_db.fetch_all()}

    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for core in raw:
        core = sanitize_record_for_db(core)
        track_id = str(core.get('track_id') or core.get('id') or '').strip()
        if not track_id:
            track_id = ensure_track_id(core)
        core['track_id'] = track_id
        index_row = index_by_id.get(track_id)
        if index_row:
            merged.append(merge_core_and_index(core, index_row))
        else:
            fallback = record_to_index_row(core)
            index_db.upsert(fallback)
            merged.append(merge_core_and_index(core, fallback))
        seen.add(track_id)

    for track_id, index_row in index_by_id.items():
        if track_id in seen:
            continue
        merged.append(merge_core_and_index({'track_id': track_id}, index_row))

    return merged


def save_library_records(records: list[dict[str, Any]]) -> None:
    cores: list[dict[str, Any]] = []
    index_db = TrackIndexDB()
    for record in records:
        rec = sanitize_record_for_db(record)
        ensure_track_id(rec)
        if rec.get('path') and not rec.get('local_path'):
            rec['local_path'] = rec['path']
        cores.append(record_to_archive_core(rec))
        index_db.upsert(record_to_index_row(rec))
    _save_archive_json(cores)


def upsert_library_record(
    records: list[dict[str, Any]],
    record: dict[str, Any],
    *,
    prepend: bool = False,
) -> list[dict[str, Any]]:
    record = sanitize_record_for_db(record)
    ensure_track_id(record)
    if record.get('path') and not record.get('local_path'):
        record['local_path'] = record['path']
    track_id = record['track_id']
    existing = next((r for r in records if str(r.get('track_id') or r.get('id')) == track_id), None)
    if existing:
        existing.update(record)
        merged = existing
        if prepend:
            records = [r for r in records if r is not existing]
            records.insert(0, merged)
    else:
        if prepend:
            records.insert(0, record)
        else:
            records.append(record)
        merged = record
    sync_record_index(merged)
    _save_archive_json([record_to_archive_core(r) for r in records])
    return records


def move_records_to_front(records: list[dict[str, Any]], track_ids: list[str]) -> list[dict[str, Any]]:
    """Reorder library so the given track IDs appear at the top (stable order within the group)."""
    order = {str(tid): i for i, tid in enumerate(track_ids) if tid}
    if not order:
        return records
    front: list[tuple[int, dict[str, Any]]] = []
    rest: list[dict[str, Any]] = []
    for rec in records:
        rid = str(rec.get('track_id') or rec.get('id') or '')
        if rid in order:
            front.append((order[rid], rec))
        else:
            rest.append(rec)
    front.sort(key=lambda item: item[0])
    return [rec for _, rec in front] + rest


def delete_library_record(records: list[dict[str, Any]], track_id: str) -> list[dict[str, Any]]:
    records = [r for r in records if str(r.get('track_id') or r.get('id')) != str(track_id)]
    try:
        TrackIndexDB().delete(str(track_id))
    except sqlite3.Error as exc:
        print(f'[Library] index delete failed: {exc}')
    _save_archive_json([record_to_archive_core(r) for r in records])
    return records


def prepare_new_record(record: dict[str, Any], *, bpm_source: str = '') -> dict[str, Any]:
    """Normalize a freshly downloaded track for hybrid storage."""
    ensure_track_id(record)
    path = str(record.get('path') or record.get('local_path') or '')
    record['local_path'] = path
    record['path'] = path
    if bpm_source:
        record['bpm_source'] = normalize_bpm_source(bpm_source)
    key = str(record.get('key') or '')
    if key and key != UNKNOWN:
        record['camelot_key'] = camelot_from_key(key)
    record['energy_level'] = energy_level_from_record(record)
    sync_record_index(record)
    return record


def plan_track_path(meta, bpm=None, key=None):
    meta = normalize_artist_meta(meta)
    album_dir = os.path.join(WAV_ROOT, folder_artist(meta), meta['album'])
    bpm_int = _parse_bpm_int(bpm)
    bpm_part = str(bpm_int) if bpm_int else 'Unknown'
    key_part = format_key_compact(key)
    filename = sanitize_path_part(f'{bpm_part} - {key_part} - {meta["title"]}', meta['title'])
    if not filename.lower().endswith('.wav'):
        filename = f'{filename}.wav'
    return os.path.join(album_dir, filename)


def ensure_parent_dir(file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)


def build_track_paths(meta, bpm=None, key=None):
    path = plan_track_path(meta, bpm=bpm, key=key)
    ensure_parent_dir(path)
    return path


def resolve_cover_bytes(info, temp_dir, video_id):
    for name in os.listdir(temp_dir):
        if not name.startswith(f'{video_id}_temp.'):
            continue
        lower = name.lower()
        if lower.endswith(('.jpg', '.jpeg', '.png', '.webp')):
            path = os.path.join(temp_dir, name)
            with open(path, 'rb') as f:
                data = f.read()
            try:
                os.remove(path)
            except OSError:
                pass
            if lower.endswith('.png'):
                return data, 'image/png'
            if lower.endswith('.webp'):
                return data, 'image/webp'
            return data, 'image/jpeg'

    url = info.get('thumbnail_url') or info.get('thumbnail') or ''
    if not url:
        return None, None
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'WaveMash/1.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        mime = resp.headers.get_content_type() or 'image/jpeg'
        return data, mime
    except Exception as e:
        print(f'[Cover Download Error] {e}')
        return None, None


def save_album_cover_sidecar(wav_path, cover_data, mime):
    """앨범 폴더에 cover.jpg도 저장 (탐색기 미리보기용)."""
    if not cover_data:
        return None
    album_dir = os.path.dirname(wav_path)
    ext = '.jpg'
    if mime and 'png' in mime:
        ext = '.png'
    cover_path = os.path.join(album_dir, f'cover{ext}')
    with open(cover_path, 'wb') as f:
        f.write(cover_data)
    return cover_path


def find_cover_sidecar(wav_path: str) -> str | None:
    """Return an existing ``cover.jpg`` / ``cover.png`` path next to a WAV, if any."""
    folder = os.path.dirname(wav_path)
    for name in ('cover.jpg', 'cover.png', 'cover.jpeg', 'cover.webp'):
        path = os.path.join(folder, name)
        if os.path.isfile(path) and os.path.getsize(path) > 100:
            return path
    return None


def read_cover_bytes_from_wav(wav_path: str) -> tuple[bytes | None, str | None]:
    """Read embedded APIC artwork from a WAV file."""
    try:
        audio = WAVE(wav_path)
        if not audio.tags:
            return None, None
        for apic in audio.tags.getall('APIC'):
            if apic.data:
                return apic.data, apic.mime or 'image/jpeg'
    except Exception:
        pass
    return None, None


def read_cover_bytes_for_wav(wav_path: str) -> tuple[bytes | None, str | None]:
    """Sidecar first, then embedded APIC."""
    sidecar = find_cover_sidecar(wav_path)
    if sidecar:
        try:
            with open(sidecar, 'rb') as f:
                data = f.read()
            if data:
                mime = 'image/png' if sidecar.lower().endswith('.png') else 'image/jpeg'
                return data, mime
        except OSError:
            pass
    return read_cover_bytes_from_wav(wav_path)


def _move_album_cover_sidecar(old_album_dir: str, new_album_dir: str) -> None:
    if not os.path.isdir(old_album_dir):
        return
    os.makedirs(new_album_dir, exist_ok=True)
    for name in ('cover.jpg', 'cover.png', 'cover.jpeg', 'cover.webp'):
        src = os.path.join(old_album_dir, name)
        if not os.path.isfile(src):
            continue
        dst = os.path.join(new_album_dir, name)
        if os.path.isfile(dst):
            return
        try:
            shutil.copy2(src, dst)
        except OSError:
            pass
        return


def _download_cover_url(url: str) -> tuple[bytes | None, str | None]:
    if not url:
        return None, None
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'WaveMash/1.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        mime = resp.headers.get_content_type() or 'image/jpeg'
        return data, mime
    except Exception as e:
        print(f'[Cover Download Error] {e}')
        return None, None


def fetch_cover_bytes_for_record(rec: dict) -> tuple[bytes | None, str | None]:
    """Best-effort album art fetch for a library record."""
    wav_path = str(rec.get('path') or '')
    if wav_path and os.path.isfile(wav_path):
        data, mime = read_cover_bytes_for_wav(wav_path)
        if data:
            return data, mime

    tid = _spotify_track_id(str(rec.get('url') or ''))
    if tid:
        try:
            _ensure_spotify_client_for_reorg()
            from spotdl.types.song import Song

            song = Song.from_url(f'https://open.spotify.com/track/{tid}')
            if song.cover_url:
                data, mime = _download_cover_url(song.cover_url)
                if data:
                    return data, mime
        except Exception:
            pass
    elif str(rec.get('platform', '')).lower() == 'spotify':
        song = _search_song_for_record(rec)
        if song and getattr(song, 'cover_url', None):
            data, mime = _download_cover_url(song.cover_url)
            if data:
                return data, mime

    temp_dir = os.path.join(WAV_ROOT, '_temp')
    os.makedirs(temp_dir, exist_ok=True)
    return resolve_cover_bytes(rec, temp_dir, str(rec.get('id') or 'cover'))


def ensure_cover_sidecar(rec: dict) -> str | None:
    """Make sure ``cover.jpg`` exists beside the WAV; return its path."""
    wav_path = str(rec.get('path') or '')
    if not wav_path or not os.path.isfile(wav_path):
        return None
    existing = find_cover_sidecar(wav_path)
    if existing:
        return existing
    data, mime = fetch_cover_bytes_for_record(rec)
    if not data:
        return None
    return save_album_cover_sidecar(wav_path, data, mime)


def repair_missing_covers(records: list[dict]) -> int:
    """Create missing sidecar covers and re-embed APIC tags where needed."""
    repaired = 0
    for rec in records:
        wav_path = str(rec.get('path') or '')
        if not wav_path or not os.path.isfile(wav_path):
            continue
        if find_cover_sidecar(wav_path):
            continue
        sidecar = ensure_cover_sidecar(rec)
        if not sidecar:
            continue
        data, mime = read_cover_bytes_for_wav(wav_path)
        write_wav_tags(wav_path, rec, cover_data=data, cover_mime=mime or 'image/jpeg')
        repaired += 1
    return repaired


def _remove_orphan_album_sidecars(album_dir: str) -> None:
    """Remove cover art when no WAV tracks remain in the album folder."""
    if not os.path.isdir(album_dir):
        return
    has_wav = any(name.lower().endswith('.wav') for name in os.listdir(album_dir))
    if has_wav:
        return
    for name in os.listdir(album_dir):
        lower = name.lower()
        if lower.startswith('cover.') or lower.endswith(('.jpg', '.jpeg', '.png', '.webp')):
            try:
                os.remove(os.path.join(album_dir, name))
            except OSError:
                pass


def delete_track_file(file_path):
    if not file_path:
        return

    file_path = os.path.normpath(file_path)
    root = os.path.normpath(WAV_ROOT)

    if os.path.isfile(file_path):
        if not file_path.lower().endswith('.wav'):
            return
        if not file_path.startswith(root):
            os.remove(file_path)
            return
        os.remove(file_path)

    album_dir = os.path.dirname(file_path)
    _remove_orphan_album_sidecars(album_dir)

    directory = album_dir
    while directory and os.path.normcase(directory) != os.path.normcase(root):
        try:
            if not os.path.isdir(directory) or os.listdir(directory):
                break
            os.rmdir(directory)
            directory = os.path.dirname(directory)
        except OSError:
            break


def _write_riff_info_with_ffmpeg(file_path, record):
    """Windows Explorer 호환을 위해 RIFF INFO 메타데이터를 한번 더 씁니다."""
    try:
        static_ffmpeg.add_paths()
        ffmpeg = shutil.which('ffmpeg')
        if not ffmpeg:
            return

        title = str(record.get('title', '') or '')
        artist = str(record.get('artist', '') or '')
        album = str(record.get('album', '') or '')
        genre = str(record.get('genre', '') or '')
        year = str(record.get('year', '') or '')
        comment = str(record.get('url', '') or '')

        tmp = file_path + '.riff.wav'
        cmd = [
            ffmpeg,
            '-hide_banner',
            '-loglevel',
            'error',
            '-y',
            '-i',
            file_path,
            '-c',
            'copy',
            '-metadata',
            f'title={title}',
            '-metadata',
            f'artist={artist}',
            '-metadata',
            f'album={album}',
            '-metadata',
            f'genre={genre}',
        ]
        if year:
            cmd += ['-metadata', f'date={year}']
        if comment:
            cmd += ['-metadata', f'comment={comment}']
        cmd.append(tmp)

        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode != 0:
            return

        if not safe_rename(tmp, file_path):
            try:
                os.remove(tmp)
            except OSError:
                pass
    except Exception:
        # RIFF INFO 쓰기 실패는 치명적이지 않음
        try:
            tmp = file_path + '.riff.wav'
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass


def write_wav_tags(file_path, record, cover_data=None, cover_mime='image/jpeg'):
    try:
        # 1) RIFF INFO (Explorer 표시용) → 2) ID3 (커버 포함)
        _write_riff_info_with_ffmpeg(file_path, record)

        audio = WAVE(file_path)
        if audio.tags is None:
            audio.add_tags()
        tags = audio.tags

        for frame in ('TIT2', 'TPE1', 'TPE2', 'TALB', 'TCON', 'TBPM', 'TKEY', 'TDRC', 'COMM', 'APIC'):
            tags.delall(frame)

        tags.add(TIT2(encoding=3, text=record.get('title', '')))
        tags.add(TPE1(encoding=3, text=record.get('artist', '')))
        tags.add(TPE2(encoding=3, text=record.get('artist', '')))
        tags.add(TALB(encoding=3, text=record.get('album', SINGLES_ALBUM)))
        tags.add(TCON(encoding=3, text=record.get('genre', UNKNOWN)))
        tags.add(TBPM(encoding=3, text=str(record.get('bpm', ''))))
        tags.add(TKEY(encoding=3, text=str(record.get('key', ''))))
        if record.get('year'):
            tags.add(TDRC(encoding=3, text=str(record['year'])))
        if record.get('url'):
            tags.add(COMM(encoding=3, lang='eng', desc='Source', text=record['url']))

        cover = cover_data or record.get('cover_data')
        mime = record.get('cover_mime') or cover_mime
        if not cover:
            cover, mime = read_cover_bytes_for_wav(file_path)
        if cover:
            tags.add(
                APIC(
                    encoding=3,
                    mime=mime or 'image/jpeg',
                    type=3,
                    desc='Cover',
                    data=cover,
                )
            )

        audio.save()
        return True
    except Exception as e:
        print(f'[Tag Write Error] {e}')
        return False


def read_wav_tags(file_path):
    try:
        audio = WAVE(file_path)
        if not audio.tags:
            return {}
        tags = audio.tags
        comm = tags.getall('COMM')
        url = comm[0].text[0] if comm and comm[0].text else ''
        tpe1 = tags.get('TPE1')
        if tpe1 and tpe1.text:
            artist = '/'.join(str(x) for x in tpe1.text)
        else:
            artist = ''
        return {
            'title': tags.get('TIT2').text[0] if tags.get('TIT2') else '',
            'artist': artist,
            'album': tags.get('TALB').text[0] if tags.get('TALB') else '',
            'genre': tags.get('TCON').text[0] if tags.get('TCON') else '',
            'bpm': tags.get('TBPM').text[0] if tags.get('TBPM') else '',
            'key': tags.get('TKEY').text[0] if tags.get('TKEY') else '',
            'year': tags.get('TDRC').text[0] if tags.get('TDRC') else '',
            'url': url,
        }
    except Exception:
        return {}


def record_from_tags(file_path, video_id, platform, fmt='WAV'):
    tags = read_wav_tags(file_path)
    rel = os.path.relpath(file_path, WAV_ROOT)
    parts = rel.split(os.sep)
    album = tags.get('album') or (parts[1] if len(parts) > 2 else SINGLES_ALBUM)
    artist_raw = tags.get('artist') or (parts[0] if len(parts) > 1 else UNKNOWN)
    artist = display_artists(artist_raw)
    primary = primary_artist(artist_raw)
    return {
        'id': video_id,
        'title': tags.get('title') or os.path.splitext(os.path.basename(file_path))[0],
        'artist': artist,
        'primary_artist': primary,
        'album': album,
        'platform': platform,
        'format': fmt,
        'path': file_path,
        'bpm': tags.get('bpm', ''),
        'key': tags.get('key', ''),
        'genre': tags.get('genre', UNKNOWN),
        'year': tags.get('year', ''),
        'url': tags.get('url', ''),
    }


def iter_wav_files():
    if not os.path.isdir(WAV_ROOT):
        return
    for dirpath, _, filenames in os.walk(WAV_ROOT):
        for name in filenames:
            if name.lower().endswith('.wav'):
                yield os.path.join(dirpath, name)


def cleanup_empty_dirs():
    if not os.path.isdir(WAV_ROOT):
        return
    for dirpath, dirnames, filenames in os.walk(WAV_ROOT, topdown=False):
        if os.path.basename(dirpath) == '_temp':
            continue
        if dirpath == WAV_ROOT:
            continue
        _remove_orphan_album_sidecars(dirpath)
        try:
            if not os.listdir(dirpath):
                os.rmdir(dirpath)
        except OSError:
            pass


def relocate_record_file(rec: dict) -> bool:
    """Move a track to the canonical artist/album path. Returns True if moved."""
    path = str(rec.get('path') or '')
    if not path or not os.path.isfile(path):
        return False

    meta = normalize_artist_meta({
        'artist': rec.get('artist', UNKNOWN),
        'primary_artist': rec.get('primary_artist'),
        'album': rec.get('album', SINGLES_ALBUM),
        'title': rec.get('title', UNKNOWN),
    })
    new_path = plan_track_path(meta, bpm=rec.get('bpm'), key=rec.get('key'))
    if os.path.normcase(path) == os.path.normcase(new_path):
        rec['artist'] = meta['artist']
        rec['primary_artist'] = meta['primary_artist']
        return False

    ensure_parent_dir(new_path)
    if os.path.exists(new_path):
        os.remove(new_path)
    old_album = os.path.dirname(path)
    new_album = os.path.dirname(new_path)
    _move_album_cover_sidecar(old_album, new_album)
    cover_data, cover_mime = read_cover_bytes_for_wav(path)
    if not safe_rename(path, new_path):
        return False
    rec['path'] = new_path
    rec['local_path'] = new_path
    rec['artist'] = meta['artist']
    rec['primary_artist'] = meta['primary_artist']
    _remove_orphan_album_sidecars(old_album)
    cleanup_empty_dirs()
    write_wav_tags(new_path, rec, cover_data=cover_data, cover_mime=cover_mime or 'image/jpeg')
    if cover_data and not find_cover_sidecar(new_path):
        save_album_cover_sidecar(new_path, cover_data, cover_mime)
    sync_record_index(rec)
    return True


def _normalize_title_key(title: str) -> str:
    return re.sub(r'[^a-z0-9]', '', (title or '').lower())


def _match_song_for_record(songs: list, rec: dict):
    target = _normalize_title_key(str(rec.get('title', '')))
    if not target:
        return None
    exact = {_normalize_title_key(getattr(s, 'name', '')): s for s in songs}
    if target in exact:
        return exact[target]
    for song in songs:
        key = _normalize_title_key(getattr(song, 'name', ''))
        if key and (key in target or target in key):
            return song
    base, _ = split_version(str(rec.get('title', '')))
    base_key = _normalize_title_key(base)
    if base_key in exact:
        return exact[base_key]
    return None


def _looks_mangled_artist(artist: str) -> bool:
    artist = (artist or '').strip()
    if not artist or '/' in artist:
        return False
    if ',' in artist and not re.search(r'[a-z][A-Z]', artist):
        return False
    if re.search(r'[a-z][A-Z]', artist):
        return True
    return len(artist) > 36


def refresh_spotify_metadata(records: list[dict]) -> int:
    """Repair collapsed artist strings (and track URLs) using Spotify song lists."""
    updated = 0
    playlist_groups: dict[str, list[dict]] = {}
    for rec in records:
        if str(rec.get('platform', '')).lower() != 'spotify':
            continue
        url = str(rec.get('url') or '')
        if 'spotify.com/playlist' in url:
            playlist_groups.setdefault(url, []).append(rec)

    for plist_url, recs in playlist_groups.items():
        try:
            _ensure_spotify_client_for_reorg()
            from spotdl.utils.search import parse_query

            songs = parse_query([plist_url])
        except Exception as exc:
            print(f'[Library refresh] playlist metadata failed: {exc}')
            continue
        for rec in recs:
            song = _match_song_for_record(songs, rec)
            if not song:
                continue
            rec['artist'] = display_artists('/'.join(song.artists) if song.artists else song.artist)
            rec['primary_artist'] = sanitize_path_part(song.artist, UNKNOWN)
            rec['id'] = song.song_id
            rec['url'] = song.url
            updated += 1

    for rec in records:
        if str(rec.get('platform', '')).lower() != 'spotify':
            continue
        if not _looks_mangled_artist(str(rec.get('artist', ''))):
            continue
        tid = _spotify_track_id(str(rec.get('url') or ''))
        if tid:
            try:
                _ensure_spotify_client_for_reorg()
                from spotdl.types.song import Song

                song = Song.from_url(f'https://open.spotify.com/track/{tid}')
                rec['artist'] = display_artists('/'.join(song.artists) if song.artists else song.artist)
                rec['primary_artist'] = sanitize_path_part(song.artist, UNKNOWN)
                rec['id'] = song.song_id
                rec['url'] = song.url
                updated += 1
                continue
            except Exception:
                pass
        song = _search_song_for_record(rec)
        if song:
            rec['artist'] = display_artists('/'.join(song.artists) if song.artists else song.artist)
            rec['primary_artist'] = sanitize_path_part(song.artist, UNKNOWN)
            rec['id'] = song.song_id
            rec['url'] = song.url
            updated += 1

    return updated


def _search_song_for_record(rec: dict):
    try:
        _ensure_spotify_client_for_reorg()
        from spotdl.utils.search import get_search_results
    except Exception:
        return None
    title = str(rec.get('title') or '').strip()
    if not title:
        return None
    query = title
    try:
        candidates = get_search_results(query)[:8]
    except Exception:
        return None
    return _match_song_for_record(candidates, rec)


def reorganize_library(records: list[dict], *, refresh_metadata: bool = True) -> tuple[list[dict], int]:
    """Re-home every known track under ``<main artist>/<album>/`` folders."""
    if refresh_metadata:
        refresh_spotify_metadata(records)
    moved = 0
    for rec in records:
        path = str(rec.get('path') or '')
        if path and os.path.isfile(path):
            tags = read_wav_tags(path)
            if tags.get('artist') and _looks_mangled_artist(str(rec.get('artist', ''))):
                rec['artist'] = display_artists(tags['artist'])
        if relocate_record_file(rec):
            moved += 1
    cleanup_empty_dirs()
    return records, moved


def _spotify_track_id(url: str | None) -> str | None:
    if not url:
        return None
    match = _SPOTIFY_TRACK_ID_RE.search(str(url))
    return match.group(1) if match else None


def _ensure_spotify_client_for_reorg() -> None:
    from spotify_metadata import init_spotify_client

    init_spotify_client()
