import glob
import asyncio
import os
import re
import subprocess
import sys
from pathlib import Path

from mutagen.id3 import ID3

from desktop_app.archive_store import load_archive
from library import SINGLES_ALBUM, UNKNOWN, display_artists, normalize_artist_meta, sanitize_path_part
from env_loader import ensure_env_loaded
from spotify_metadata import init_spotify_client

ensure_env_loaded()
from pipeline import (
    TEMP_DIR,
    convert_to_staging_wav,
    finalize_record,
    cleanup_temp_dir,
)

SPOTIFY_URL_RE = re.compile(
    r'^https?://(open\.)?spotify\.com/(track|album|playlist|artist)/',
    re.IGNORECASE,
)
SPOTIFY_TRACK_ID_RE = re.compile(r'^[a-zA-Z0-9]{22}$')


def is_spotify_url(url: str) -> bool:
    return bool(SPOTIFY_URL_RE.search((url or '').strip()))


def _ensure_spotify_client() -> None:
    init_spotify_client()


def list_spotify_songs(url: str) -> list:
    """Return spotdl ``Song`` objects for a Spotify URL (track / album / playlist)."""
    _ensure_spotify_client()
    from spotdl.utils.search import parse_query

    return parse_query([url.strip()])


def existing_spotify_ids(records: list[dict]) -> set[str]:
    """Spotify track IDs already present in the library."""
    ids: set[str] = set()
    for rec in records:
        tid = spotify_track_id(str(rec.get('url') or ''))
        if tid:
            ids.add(tid)
        rid = str(rec.get('id') or '')
        if rid and SPOTIFY_TRACK_ID_RE.match(rid):
            ids.add(rid)
    return ids


def existing_records_for_songs(records: list[dict], songs: list) -> list[dict]:
    """Library records that match the given Spotify songs."""
    found: list[dict] = []
    seen: set[str] = set()
    for song in songs:
        rec = find_existing_record(records, song)
        if rec is None:
            continue
        rid = str(rec.get('id', ''))
        if rid in seen:
            continue
        seen.add(rid)
        found.append(rec)
    return found


def find_existing_record(records: list[dict], song) -> dict | None:
    sid = str(getattr(song, 'song_id', '') or '')
    if sid:
        for rec in records:
            if str(rec.get('id', '')) == sid:
                return rec
            if spotify_track_id(str(rec.get('url') or '')) == sid:
                return rec
    name = str(getattr(song, 'name', '') or '')
    if name:
        key = re.sub(r'[^a-z0-9]', '', name.lower())
        for rec in records:
            rec_key = re.sub(r'[^a-z0-9]', '', str(rec.get('title', '')).lower())
            if rec_key and rec_key == key:
                return rec
    return None


def record_has_file(record: dict | None) -> bool:
    if not record:
        return False
    path = str(record.get('path') or '')
    return bool(path and os.path.isfile(path))


def is_track_in_library(records: list[dict], song) -> bool:
    """True only when the Spotify track is archived and the WAV file exists."""
    return record_has_file(find_existing_record(records, song))


def mp3_cover_from_tags(file_path):
    try:
        tags = ID3(file_path)
        for apic in tags.getall('APIC'):
            if apic.data:
                return apic.data, apic.mime or 'image/jpeg'
    except Exception:
        pass
    return None, None


def mp3_to_meta(file_path: str, spotify_url: str, song=None) -> dict:
    artist, title, album, genre, year = UNKNOWN, UNKNOWN, SINGLES_ALBUM, UNKNOWN, ''
    track_url = spotify_url
    primary = UNKNOWN

    if song is not None:
        title = song.name or title
        album = song.album_name or album
        genre = (song.genres[0] if song.genres else UNKNOWN)
        year = str(song.year or '')
        track_url = song.url or track_url
        primary = song.artist or UNKNOWN
        artist = display_artists('/'.join(song.artists) if song.artists else primary)
    else:
        try:
            from spotdl.utils.search import get_song_from_file_metadata

            file_song = get_song_from_file_metadata(Path(file_path))
            if file_song:
                song = file_song
                title = song.name or title
                album = song.album_name or album
                genre = (song.genres[0] if song.genres else UNKNOWN)
                year = str(song.year or '')
                track_url = song.url or track_url
                primary = song.artist or UNKNOWN
                artist = display_artists('/'.join(song.artists) if song.artists else primary)
        except Exception:
            pass

    if artist == UNKNOWN:
        try:
            tags = ID3(file_path)
            title = str(tags.get('TIT2').text[0]) if tags.get('TIT2') else os.path.splitext(os.path.basename(file_path))[0]
            raw_artist = str(tags.get('TPE1').text[0]) if tags.get('TPE1') else UNKNOWN
            artist = display_artists(raw_artist)
            primary = raw_artist.split('/')[0].strip() if '/' in raw_artist else artist.split(',')[0].strip()
            album = str(tags.get('TALB').text[0]) if tags.get('TALB') else SINGLES_ALBUM
            genre = str(tags.get('TCON').text[0]) if tags.get('TCON') else UNKNOWN
            year = str(tags.get('TDRC').text[0])[:4] if tags.get('TDRC') else ''
            woas = tags.get('WOAS')
            if woas and woas.url:
                track_url = woas.url
        except Exception:
            base = os.path.splitext(os.path.basename(file_path))[0]
            if ' - ' in base:
                artist, title = base.split(' - ', 1)
            else:
                title = base

    track_id = spotify_track_id(track_url) or (
        str(getattr(song, 'song_id', '') or '')
    ) or re.sub(r'[^a-zA-Z0-9]', '', f'{artist}{title}')[:32] or 'spotify_track'

    meta = normalize_artist_meta({
        'id': track_id,
        'title': sanitize_path_part(title, UNKNOWN),
        'artist': sanitize_path_part(artist, UNKNOWN),
        'primary_artist': sanitize_path_part(primary, UNKNOWN) if primary != UNKNOWN else None,
        'album': sanitize_path_part(album, SINGLES_ALBUM),
        'genre': sanitize_path_part(genre, UNKNOWN),
        'year': year,
        'platform': 'Spotify',
        'url': track_url,
    })
    return meta


def run_spotdl_download(urls: list[str], output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        sys.executable,
        '-m',
        'spotdl',
        'download',
        *urls,
        '--output',
        output_dir,
        '--format',
        'mp3',
        '--bitrate',
        '320k',
        '--sponsor-block',
        '--audio',
        'youtube-music',
        'youtube',
        'soundcloud',
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or '').strip()
        raise RuntimeError(detail or 'spotdl 다운로드 실패')


def find_new_mp3_files(output_dir: str, before: set) -> list:
    found = []
    for path in glob.glob(os.path.join(output_dir, '**', '*.mp3'), recursive=True):
        if path not in before and os.path.isfile(path):
            found.append(path)
    return sorted(found, key=os.path.getmtime)


def _match_mp3_to_song(mp3_path: str, songs_by_id: dict[str, object]) -> object | None:
    try:
        tags = ID3(mp3_path)
        woas = tags.get('WOAS')
        if woas and woas.url:
            tid = spotify_track_id(woas.url)
            if tid and tid in songs_by_id:
                return songs_by_id[tid]
    except Exception:
        pass
    return None


def process_spotify_url_sync(url, progress_callback=None):
    url = url.strip()
    if not is_spotify_url(url):
        raise ValueError('유효한 Spotify URL이 아닙니다. (트랙 / 앨범 / 플레이리스트)')

    library = load_archive()

    if progress_callback:
        progress_callback(0.05, 'Spotify 플레이리스트 확인 중...')

    all_songs = list_spotify_songs(url)
    if not all_songs:
        raise RuntimeError('Spotify에서 곡 목록을 가져오지 못했습니다.')

    songs_by_id = {str(s.song_id): s for s in all_songs if getattr(s, 'song_id', None)}
    to_download = [s for s in all_songs if not is_track_in_library(library, s)]
    skipped = len(all_songs) - len(to_download)

    if not to_download:
        existing = [
            rec
            for rec in existing_records_for_songs(library, all_songs)
            if record_has_file(rec)
        ]
        if progress_callback:
            progress_callback(1.0, f'이미 보유 중 ({skipped}곡 스킵)')
        return {
            'records': existing,
            'skipped': skipped,
            'downloaded': 0,
            'already_have': True,
        }

    spot_temp = os.path.join(TEMP_DIR, 'spotdl')
    os.makedirs(spot_temp, exist_ok=True)
    before = set(glob.glob(os.path.join(spot_temp, '**', '*.mp3'), recursive=True))

    if progress_callback:
        progress_callback(
            0.12,
            f'Spotify 다운로드 중 ({len(to_download)}곡 · {skipped}곡 스킵)...',
        )

    download_urls = [s.url for s in to_download if s.url]
    run_spotdl_download(download_urls, spot_temp)
    mp3_files = find_new_mp3_files(spot_temp, before)
    if not mp3_files:
        mp3_files = sorted(
            glob.glob(os.path.join(spot_temp, '**', '*.mp3'), recursive=True),
            key=os.path.getmtime,
        )

    if not mp3_files:
        raise RuntimeError('다운로드된 MP3 파일이 없습니다.')

    records = []
    total = len(mp3_files)

    prepared: list[tuple[str, object, dict]] = []
    for mp3_path in mp3_files:
        song = _match_mp3_to_song(mp3_path, songs_by_id)
        meta = mp3_to_meta(mp3_path, url, song=song)
        prepared.append((mp3_path, song, meta))

    for index, (mp3_path, song, meta) in enumerate(prepared):
        base = 0.2 + (0.7 * index / total)
        if progress_callback:
            progress_callback(
                base,
                f'WAV 변환 중 ({index + 1}/{total}): {meta["artist"]} - {meta["title"]}',
            )
        staging_wav = convert_to_staging_wav(mp3_path, meta['id'], progress_callback)
        cover_data, cover_mime = mp3_cover_from_tags(mp3_path)
        record = finalize_record(
            staging_wav, meta, '', UNKNOWN, cover_data, cover_mime, progress_callback
        )
        records.append(record)

        try:
            os.remove(mp3_path)
        except OSError:
            pass

    try:
        if os.path.isdir(spot_temp) and not os.listdir(spot_temp):
            os.rmdir(spot_temp)
    except OSError:
        pass
    cleanup_temp_dir()

    if progress_callback:
        msg = f'완료! ({len(records)}곡'
        if skipped:
            msg += f' · {skipped}곡 스킵'
        msg += ')'
        progress_callback(1.0, msg)

    if len(records) == 1 and skipped == 0:
        return records[0]
    return {
        'records': records,
        'skipped': skipped,
        'downloaded': len(records),
        'already_have': False,
    }


async def process_spotify_url(url, progress_callback=None):
    return await asyncio.to_thread(process_spotify_url_sync, url, progress_callback)
