import glob
import asyncio
import os
import re
import subprocess
import sys
import threading
from pathlib import Path

from mutagen.id3 import ID3

from desktop_app.archive_store import load_archive
from library import SINGLES_ALBUM, UNKNOWN, display_artists, normalize_artist_meta, sanitize_path_part
from env_loader import ensure_env_loaded
from spotify_metadata import (
    init_spotify_client,
    mark_rate_limited,
    reset_spotify_client,
    spotify_track_id,
)

ensure_env_loaded()
from pipeline import (
    TEMP_DIR,
    _emit,
    convert_to_staging_wav,
    finalize_record,
    cleanup_temp_dir,
)

SPOTIFY_URL_RE = re.compile(
    r'^https?://(open\.)?spotify\.com/(track|album|playlist|artist)/',
    re.IGNORECASE,
)
SPOTIFY_TRACK_ID_RE = re.compile(r'^[a-zA-Z0-9]{22}$')
SPOTIFY_URI_RE = re.compile(
    r'^spotify:(track|album|playlist|artist):([a-zA-Z0-9]+)',
    re.IGNORECASE,
)


def normalize_spotify_url(url: str) -> str:
    """Accept https links, ``spotify:track:…`` URIs, and strip ``?si=`` params."""
    raw = (url or "").strip()
    m = SPOTIFY_URI_RE.match(raw)
    if m:
        kind, sid = m.group(1).lower(), m.group(2)
        return f"https://open.spotify.com/{kind}/{sid}"
    if SPOTIFY_URL_RE.search(raw):
        m2 = re.search(
            r'(https?://(?:open\.)?spotify\.com/(?:track|album|playlist|artist)/[a-zA-Z0-9]+)',
            raw,
            re.IGNORECASE,
        )
        if m2:
            return m2.group(1)
    return raw


def is_spotify_url(url: str) -> bool:
    raw = (url or "").strip()
    return bool(SPOTIFY_URL_RE.search(raw) or SPOTIFY_URI_RE.match(raw))


def _ensure_spotify_client() -> None:
    if init_spotify_client():
        return
    if init_spotify_client(force=True, prefer_free=True):
        return
    raise RuntimeError(
        "Spotify 클라이언트 초기화 실패. "
        "인터넷 연결을 확인하거나 .env의 SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET을 확인해 보세요."
    )


def _spotify_resource_kind(url: str) -> str | None:
    m = re.search(r'open\.spotify\.com/(track|album|playlist|artist)/', url, re.IGNORECASE)
    return m.group(1).lower() if m else None


def _is_spotify_rate_error(exc: Exception) -> bool:
    msg = str(exc).strip().lower()
    return "429" in str(exc) or "rate" in msg or "too many" in msg


def list_spotify_songs(url: str) -> list:
    """Return spotdl ``Song`` objects for a Spotify URL (track / album / playlist)."""
    from spotdl.utils.search import parse_query

    url = normalize_spotify_url(url)
    kind = _spotify_resource_kind(url)
    # Playlists/albums fan out to many API calls — prefer spotdl's free client first.
    prefer_order = (True, False) if kind in ('playlist', 'album', 'artist') else (False, True)
    last_exc: Exception | None = None
    for prefer_free in prefer_order:
        try:
            reset_spotify_client()
            if not init_spotify_client(force=True, prefer_free=prefer_free):
                continue
            return parse_query([url.strip()])
        except Exception as exc:
            last_exc = exc
            if prefer_free or not _is_spotify_rate_error(exc):
                break
            try:
                print("[Spotify] official API limited — retrying with spotdl free client")
            except UnicodeEncodeError:
                pass

    exc = last_exc or RuntimeError("Spotify 곡 목록 조회 실패")
    msg = str(exc).strip() or type(exc).__name__
    lower = msg.lower()
    if _is_spotify_rate_error(exc):
        mark_rate_limited()
        raise RuntimeError(
            "Spotify API 요청 한도에 걸렸습니다. "
            "5분 후 다시 시도하거나 .env의 Spotify 앱 설정을 확인해 주세요."
        ) from exc
    if "404" in msg or "not found" in lower:
        raise RuntimeError(
            "Spotify 플레이리스트/앨범을 찾을 수 없습니다. "
            "링크가 맞는지, 비공개 플리인지 확인해 주세요."
        ) from exc
    raise RuntimeError(f"Spotify 곡 목록 조회 실패: {msg[:240]}") from exc


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
            if str(rec.get('track_id', '')) == sid:
                return rec
            if str(rec.get('external_id', '')) == sid:
                return rec
            if spotify_track_id(str(rec.get('url') or '')) == sid:
                return rec
    name = str(getattr(song, 'name', '') or '')
    artist = str(getattr(song, 'artist', '') or '')
    if name:
        title_key = re.sub(r'[^a-z0-9]', '', name.lower())
        artist_key = re.sub(r'[^a-z0-9]', '', artist.lower())
        for rec in records:
            rec_title = re.sub(r'[^a-z0-9]', '', str(rec.get('title', '')).lower())
            if not rec_title or rec_title != title_key:
                continue
            if not artist_key:
                return rec
            rec_artist = re.sub(r'[^a-z0-9]', '', str(rec.get('artist', '')).lower())
            if artist_key in rec_artist or rec_artist in artist_key:
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


def run_spotdl_download(urls: list[str], output_dir: str) -> list[str]:
    """Download via spotdl. Batches URLs to stay under Windows command-line limits."""
    os.makedirs(output_dir, exist_ok=True)
    urls = [u.strip() for u in urls if u and u.strip()]
    if not urls:
        raise RuntimeError('다운로드할 Spotify URL이 없습니다.')

    # Windows CreateProcess limit is ~8191 chars; keep batches small.
    batch_size = 25 if len(urls) > 1 else len(urls)
    errors: list[str] = []

    for start in range(0, len(urls), batch_size):
        batch = urls[start : start + batch_size]
        cmd = [
            sys.executable,
            '-m',
            'spotdl',
            'download',
            *batch,
            '--output',
            output_dir,
            '--format',
            'mp3',
            '--bitrate',
            '320k',
            '--sponsor-block',
            '--overwrite',
            'skip',
            '--print-errors',
            '--audio',
            'youtube-music',
            'youtube',
            'soundcloud',
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or '').strip()
            if detail:
                errors.append(detail[-800:])
            else:
                errors.append('spotdl 다운로드 실패')

    return errors


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


def process_spotify_url_sync(url, progress_callback=None, export_format: str = 'wav'):
    url = normalize_spotify_url(url.strip())
    if not is_spotify_url(url):
        raise ValueError('유효한 Spotify URL이 아닙니다. (트랙 / 앨범 / 플레이리스트)')

    library = load_archive()

    _emit(progress_callback, 0.03, 'Spotify 곡 목록 확인 중...', stage='listing')

    all_songs = list_spotify_songs(url)
    if not all_songs:
        raise RuntimeError('Spotify에서 곡 목록을 가져오지 못했습니다.')

    songs_by_id = {str(s.song_id): s for s in all_songs if getattr(s, 'song_id', None)}
    to_download = [s for s in all_songs if not is_track_in_library(library, s)]
    skipped = len(all_songs) - len(to_download)

    _emit(
        progress_callback,
        0.06,
        f'목록 확인 완료 · 전체 {len(all_songs)}곡 · 받을 곡 {len(to_download)} · 스킵 {skipped}',
        stage='listing',
        total=len(to_download) or len(all_songs),
        current=0,
        skipped=skipped,
    )

    if not to_download:
        existing = [
            rec
            for rec in existing_records_for_songs(library, all_songs)
            if record_has_file(rec)
        ]
        _emit(
            progress_callback,
            1.0,
            f'이미 보유 중 ({skipped}곡 스킵)',
            stage='done',
            current=0,
            total=0,
            skipped=skipped,
        )
        return {
            'records': existing,
            'skipped': skipped,
            'downloaded': 0,
            'already_have': True,
            'missing_ids': [],
            'spotify_total': len(all_songs),
        }

    spot_temp = os.path.join(TEMP_DIR, 'spotdl')
    os.makedirs(spot_temp, exist_ok=True)
    before = set(glob.glob(os.path.join(spot_temp, '**', '*.mp3'), recursive=True))

    download_urls = [s.url for s in to_download if s.url]
    if not download_urls:
        raise RuntimeError('다운로드할 Spotify 트랙 URL이 없습니다.')

    kind = _spotify_resource_kind(url)
    # 전체 플리 URL 일괄 다운로드는 spotdl이 일부 곡을 조용히 빠뜨리는 경우가 있어
    # 개별 트랙 URL로 받는 편이 동기화 신뢰도가 높다.
    spotdl_targets = download_urls
    _ = kind  # reserved for future playlist-level optimizations

    # spotdl은 일괄 실행이라 하트비트로 "살아있음"을 표시
    stop_pulse = threading.Event()
    pulse_n = [0]

    def spotdl_pulse():
        while not stop_pulse.wait(3.0):
            pulse_n[0] += 1
            dots = '.' * (1 + pulse_n[0] % 3)
            _emit(
                progress_callback,
                min(0.18, 0.08 + pulse_n[0] * 0.004),
                f'Spotify 오디오 다운로드 중 ({len(to_download)}곡){dots}',
                stage='downloading',
                current=0,
                total=len(to_download),
                skipped=skipped,
            )

    _emit(
        progress_callback,
        0.08,
        f'Spotify 오디오 다운로드 시작 ({len(to_download)}곡 · {skipped}곡 스킵)...',
        stage='downloading',
        current=0,
        total=len(to_download),
        skipped=skipped,
    )

    pulse_thread = threading.Thread(target=spotdl_pulse, daemon=True)
    pulse_thread.start()
    try:
        spotdl_errors = run_spotdl_download(spotdl_targets, spot_temp)
    finally:
        stop_pulse.set()

    mp3_files = find_new_mp3_files(spot_temp, before)
    if not mp3_files:
        mp3_files = sorted(
            glob.glob(os.path.join(spot_temp, '**', '*.mp3'), recursive=True),
            key=os.path.getmtime,
        )

    # 1차 일괄 실패/부분 실패 시 누락 곡만 개별 재시도
    if not mp3_files or len(mp3_files) < len(to_download):
        have_names = {os.path.basename(p).lower() for p in mp3_files}
        retry_urls = []
        for s in to_download:
            su = str(getattr(s, 'url', '') or '')
            if not su:
                continue
            # 이미 mp3가 대략 매칭되면 스킵 (정확 매칭은 후처리에서)
            retry_urls.append(su)
        # mp3가 전혀 없으면 전부 재시도, 일부만 있으면 트랙별 재시도
        if retry_urls and (not mp3_files or len(mp3_files) < max(1, int(len(to_download) * 0.9))):
            _emit(
                progress_callback,
                0.12,
                f'누락 곡 재시도 중 ({len(retry_urls)}개 URL)...',
                stage='downloading',
                current=0,
                total=len(to_download),
                skipped=skipped,
            )
            before_retry = set(glob.glob(os.path.join(spot_temp, '**', '*.mp3'), recursive=True))
            more_errs = run_spotdl_download(retry_urls, spot_temp)
            spotdl_errors.extend(more_errs)
            mp3_files = find_new_mp3_files(spot_temp, before)
            if not mp3_files:
                mp3_files = sorted(
                    glob.glob(os.path.join(spot_temp, '**', '*.mp3'), recursive=True),
                    key=os.path.getmtime,
                )
            _ = have_names, before_retry

    if not mp3_files:
        hint = ''
        combined = '\n'.join(spotdl_errors).lower()
        if 'too long' in combined or '206' in combined or len(download_urls) > 80:
            hint = ' (플레이리스트가 너무 길면 곡을 나눠서 받아 보세요.)'
        detail = spotdl_errors[-1] if spotdl_errors else '다운로드된 MP3 파일이 없습니다.'
        raise RuntimeError(f'{detail}{hint}')

    records = []
    total = len(mp3_files)

    prepared: list[tuple[str, object, dict]] = []
    for mp3_path in mp3_files:
        song = _match_mp3_to_song(mp3_path, songs_by_id)
        track_url = str(getattr(song, 'url', '') or '') if song else ''
        meta = mp3_to_meta(mp3_path, track_url or url, song=song)
        prepared.append((mp3_path, song, meta))

    _emit(
        progress_callback,
        0.20,
        f'오디오 확보 완료 · {total}곡 후처리 시작 (WAV · 커버 · BPM/Key)...',
        stage='converting',
        current=0,
        total=total,
        skipped=skipped,
    )

    for index, (mp3_path, song, meta) in enumerate(prepared):
        n = index + 1
        label = f'{meta["artist"]} - {meta["title"]}'
        span = 0.75 / total
        base = 0.20 + span * index

        def track_cb(pct, msg, info=None, _n=n, _meta=meta):
            merged = {
                'stage': (info or {}).get('stage') or 'converting',
                'current': _n,
                'total': total,
                'remaining': max(0, total - _n),
                'track_title': _meta.get('title'),
                'track_artist': _meta.get('artist'),
                'skipped': skipped,
            }
            if info:
                for k, v in info.items():
                    if v is not None and k not in ('current', 'total', 'remaining', 'skipped'):
                        merged[k] = v
            try:
                progress_callback(pct, f'[{_n}/{total}] {msg}', merged)
            except TypeError:
                if progress_callback:
                    progress_callback(pct, f'[{_n}/{total}] {msg}')

        _emit(
            track_cb if progress_callback else None,
            base,
            f'WAV 변환 중: {label}',
            stage='converting',
            current=n,
            total=total,
            track_title=meta.get('title'),
            track_artist=meta.get('artist'),
            skipped=skipped,
        )

        staging_wav = convert_to_staging_wav(
            mp3_path,
            meta['id'],
            track_cb if progress_callback else None,
            progress_base=base + span * 0.05,
            progress_end=base + span * 0.45,
            label=label,
        )
        cover_data, cover_mime = mp3_cover_from_tags(mp3_path)
        record = finalize_record(
            staging_wav,
            meta,
            '',
            UNKNOWN,
            cover_data,
            cover_mime,
            track_cb if progress_callback else None,
            progress_cover=base + span * 0.55,
            progress_meta=base + span * 0.75,
            export_format=export_format,
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

    # 아카이브에 즉시 반영 (동기화/재매핑이 캐시를 볼 수 있도록)
    try:
        from desktop_app.archive_store import load_archive, upsert_record

        lib = load_archive()
        for rec in records:
            lib = upsert_record(lib, rec, prepend=True)
    except Exception as exc:
        print(f'[spotify_pipeline] archive upsert: {exc}')

    # 아직 라이브러리에 없는 Spotify 곡 ID
    refreshed = load_archive() if 'load_archive' in dir() else library
    try:
        from desktop_app.archive_store import load_archive as _load

        refreshed = _load()
    except Exception:
        refreshed = library
    missing_ids: list[str] = []
    for s in all_songs:
        sid = str(getattr(s, 'song_id', '') or '')
        if not sid:
            continue
        if not is_track_in_library(refreshed, s):
            missing_ids.append(sid)

    msg = f'완료! ({len(records)}곡'
    if skipped:
        msg += f' · {skipped}곡 스킵'
    if missing_ids:
        msg += f' · {len(missing_ids)}곡 미확보'
    elif spotdl_errors and len(records) < len(to_download):
        msg += f' · {len(to_download) - len(records)}곡 spotdl 실패'
    msg += ')'
    _emit(
        progress_callback,
        1.0,
        msg,
        stage='done',
        current=len(records),
        total=max(total, len(to_download)),
        skipped=skipped,
    )

    if len(records) == 1 and skipped == 0 and not missing_ids:
        return records[0]
    return {
        'records': records,
        'skipped': skipped,
        'downloaded': len(records),
        'already_have': False,
        'missing_ids': missing_ids,
        'spotify_total': len(all_songs),
    }


async def process_spotify_url(url, progress_callback=None):
    return await asyncio.to_thread(process_spotify_url_sync, url, progress_callback)
