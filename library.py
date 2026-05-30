import os
import re
import shutil
import subprocess
import urllib.request

import static_ffmpeg
from mutagen.wave import WAVE
from mutagen.id3 import TIT2, TPE1, TPE2, TALB, TCON, TBPM, TKEY, TDRC, COMM, APIC

WAV_ROOT = os.path.join(os.path.expanduser('~'), 'OneDrive', 'Desktop', 'WAV')
SINGLES_ALBUM = 'Singles'
UNKNOWN = 'Unknown'

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
        os.replace(path, new_path)
        rec['path'] = new_path
        path = new_path

    write_wav_tags(path, rec)
    return True


def apply_bpm_key_to_record(rec: dict, bpm: int | str | None, key: str | None) -> bool:
    """Apply external BPM/key lookup to a record; rename WAV and refresh tags."""
    changed = False
    path = str(rec.get('path') or '')

    try:
        bpm_val = int(round(float(bpm))) if bpm not in (None, '', 0, '0') else 0
    except (TypeError, ValueError):
        bpm_val = 0
    if bpm_val > 0:
        new_bpm = str(bpm_val)
        if str(rec.get('bpm') or '') != new_bpm:
            rec['bpm'] = new_bpm
            changed = True

    if key and key != UNKNOWN and key_has_mode(key):
        if str(rec.get('key') or '') != key:
            rec['key'] = key
            changed = True

    if not changed or not path or not os.path.isfile(path):
        return changed

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
        os.replace(path, new_path)
        rec['path'] = new_path
        path = new_path

    write_wav_tags(path, rec)
    return True


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
        os.replace(path, new_path)
        rec['path'] = new_path
        path = new_path
        changed = True

    write_wav_tags(path, rec, cover_data=cover_data, cover_mime=cover_mime or 'image/jpeg')
    if cover_data:
        save_album_cover_sidecar(path, cover_data, cover_mime)
    return True


def plan_track_path(meta, bpm=None, key=None):
    meta = normalize_artist_meta(meta)
    album_dir = os.path.join(WAV_ROOT, folder_artist(meta), meta['album'])
    bpm_part = f'{bpm} BPM' if bpm else 'Unknown BPM'
    key_part = key or 'Unknown Key'
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

        os.replace(tmp, file_path)
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
    os.replace(path, new_path)
    rec['path'] = new_path
    rec['artist'] = meta['artist']
    rec['primary_artist'] = meta['primary_artist']
    _remove_orphan_album_sidecars(old_album)
    cleanup_empty_dirs()
    write_wav_tags(new_path, rec, cover_data=cover_data, cover_mime=cover_mime or 'image/jpeg')
    if cover_data and not find_cover_sidecar(new_path):
        save_album_cover_sidecar(new_path, cover_data, cover_mime)
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
