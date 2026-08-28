import glob
import os
import asyncio
import threading
import time
import yt_dlp
import ffmpeg
import static_ffmpeg

from library import (
    WAV_ROOT,
    UNKNOWN,
    extract_metadata,
    normalize_artist_meta,
    primary_artist,
    plan_track_path,
    ensure_parent_dir,
    write_wav_tags,
    write_mp3_tags,
    resolve_cover_bytes,
    save_album_cover_sidecar,
    is_ephemeral_mode,
    export_filename,
    sanitize_path_part,
)
from env_loader import ensure_env_loaded

ensure_env_loaded()

static_ffmpeg.add_paths()
os.makedirs(WAV_ROOT, exist_ok=True)

TEMP_DIR = os.path.join(WAV_ROOT, '_temp')

# m4a 우선(빠른 다운로드) · loudnorm 제거(2-pass라 매우 느림)
BASE_YDL_OPTS = {
    'format': '140/ba[ext=m4a]/ba/b',
    'outtmpl': os.path.join(TEMP_DIR, '%(id)s_temp.%(ext)s'),
    'noprogress': True,
    'quiet': True,
    'no_warnings': True,
    'writethumbnail': False,
    'retries': 3,
    'fragment_retries': 3,
    'concurrent_fragment_downloads': 5,
    'socket_timeout': 30,
}


def cleanup_temp_dir():
    try:
        if os.path.isdir(TEMP_DIR) and not os.listdir(TEMP_DIR):
            os.rmdir(TEMP_DIR)
    except OSError:
        pass


def make_progress_hook(callback):
    if not callback:
        return None

    last_pct = [-1.0]

    def hook(data):
        status = data.get('status')
        if status == 'downloading':
            total = data.get('total_bytes') or data.get('total_bytes_estimate') or 0
            done = data.get('downloaded_bytes') or 0
            if total:
                ratio = min(1.0, done / total)
                pct = 0.12 + ratio * 0.33
                if pct - last_pct[0] >= 0.02:
                    last_pct[0] = pct
                    _emit(callback, pct, f'오디오 다운로드 중... ({int(ratio * 100)}%)', stage='downloading')
            else:
                _emit(callback, 0.15, '오디오 다운로드 중...', stage='downloading')
        elif status == 'finished':
            _emit(callback, 0.44, '다운로드 마무리 중...', stage='downloading')

    return hook


def _emit(callback, pct, msg, *, stage='', current=None, total=None, track_title=None, track_artist=None, skipped=None):
    if not callback:
        return
    info = {}
    if stage:
        info['stage'] = stage
    if current is not None:
        info['current'] = current
    if total is not None:
        info['total'] = total
        if current is not None:
            info['remaining'] = max(0, total - current)
    if track_title is not None:
        info['track_title'] = track_title
    if track_artist is not None:
        info['track_artist'] = track_artist
    if skipped is not None:
        info['skipped'] = skipped
    try:
        callback(pct, msg, info if info else None)
    except TypeError:
        callback(pct, msg)


def find_downloaded_audio(temp_dir, video_id):
    patterns = [
        os.path.join(temp_dir, f'{video_id}_temp.*'),
        os.path.join(temp_dir, f'{video_id}.*'),
    ]
    for pattern in patterns:
        for path in sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True):
            lower = path.lower()
            if lower.endswith(('.wav', '.jpg', '.jpeg', '.png', '.webp')) or '_staging' in lower:
                continue
            if os.path.isfile(path):
                return path

    candidates = []
    for path in glob.glob(os.path.join(temp_dir, '*')):
        if not os.path.isfile(path):
            continue
        lower = path.lower()
        if lower.endswith(('.wav', '.jpg', '.jpeg', '.png', '.webp', '.part')) or '_staging' in lower:
            continue
        candidates.append(path)
    if candidates:
        return max(candidates, key=os.path.getmtime)
    return None


def convert_to_staging_wav(
    source_path,
    track_id,
    progress_callback=None,
    *,
    progress_base=0.48,
    progress_end=0.64,
    label='',
):
    os.makedirs(TEMP_DIR, exist_ok=True)
    staging_wav = os.path.join(TEMP_DIR, f'{track_id}_staging.wav')

    msg_suffix = f' · {label}' if label else ''
    _emit(
        progress_callback,
        progress_base,
        f'WAV 변환 중 (44.1kHz · 16-bit){msg_suffix}',
        stage='converting',
    )

    stop_pulse = threading.Event()
    span = max(0.01, progress_end - progress_base)

    def pulse():
        pct = progress_base
        while not stop_pulse.wait(2.0):
            if not progress_callback:
                break
            pct = min(progress_end, pct + span * 0.08)
            _emit(
                progress_callback,
                pct,
                f'WAV 변환 중...{msg_suffix}',
                stage='converting',
            )

    pulse_thread = threading.Thread(target=pulse, daemon=True) if progress_callback else None
    if pulse_thread:
        pulse_thread.start()

    try:
        stream = ffmpeg.input(source_path)
        stream = ffmpeg.output(
            stream,
            staging_wav,
            acodec='pcm_s16le',
            ar='44100',
            ac=2,
        )
        ffmpeg.run(stream, overwrite_output=True, quiet=True)
    except ffmpeg.Error as e:
        err = e.stderr.decode('utf-8', errors='replace') if e.stderr else str(e)
        raise RuntimeError(f'FFmpeg 오류: {err[:300]}') from e
    finally:
        stop_pulse.set()

    if not os.path.isfile(staging_wav) or os.path.getsize(staging_wav) < 1000:
        raise RuntimeError('WAV 변환에 실패했습니다.')
    return staging_wav


def finalize_record(
    staging_wav,
    meta,
    bpm,
    key,
    cover_data,
    cover_mime,
    progress_callback=None,
    analysis=None,
    *,
    progress_cover=0.88,
    progress_meta=0.92,
    export_format: str = 'wav',
):
    meta = normalize_artist_meta(meta)
    export_format = (export_format or 'wav').lower().strip()
    if export_format not in ('wav', 'mp3'):
        export_format = 'wav'
    ephemeral = is_ephemeral_mode()

    from library import prepare_new_record, safe_rename

    if ephemeral:
        export_dir = os.path.join(TEMP_DIR, 'export')
        os.makedirs(export_dir, exist_ok=True)
        nice = export_filename(
            {
                'artist': meta.get('artist'),
                'title': meta.get('title'),
            },
            'wav',
        )
        final_wav = os.path.join(export_dir, f"{meta.get('id', 'track')}_{nice}")
    else:
        final_wav = plan_track_path(meta, bpm=bpm, key=key)
        ensure_parent_dir(final_wav)

    if os.path.exists(final_wav):
        os.remove(final_wav)

    if not safe_rename(staging_wav, final_wav):
        raise RuntimeError('WAV 파일 이동 실패 (OneDrive 잠금). 잠시 후 다시 시도하세요.')

    label = f'{meta.get("artist", "")} - {meta.get("title", "")}'.strip(' -')
    _emit(
        progress_callback,
        progress_cover,
        f'태그 · 앨범 커버 저장 중... · {label}' if label else '태그 · 앨범 커버 저장 중...',
        stage='cover',
        track_title=meta.get('title'),
        track_artist=meta.get('artist'),
    )

    record = {
        'id': meta['id'],
        'title': meta['title'],
        'artist': meta['artist'],
        'primary_artist': meta.get('primary_artist') or primary_artist(meta['artist']),
        'album': meta['album'],
        'platform': meta['platform'],
        'format': 'WAV',
        'path': final_wav,
        'local_path': final_wav,
        'bpm': str(bpm) if bpm else '',
        'key': key,
        'genre': meta['genre'],
        'year': meta['year'],
        'url': meta['url'],
        'thumbnail_url': meta.get('thumbnail_url') or '',
    }
    if analysis:
        record['analysis'] = analysis
    record = prepare_new_record(record)
    try:
        from track_metadata import enrich_record_metadata

        def enrich_cb(msg: str) -> None:
            _emit(
                progress_callback,
                progress_meta,
                f'{msg} · {label}' if label else msg,
                stage='metadata',
                track_title=meta.get('title'),
                track_artist=meta.get('artist'),
            )

        enrich_record_metadata(record, progress_callback=enrich_cb)
        final_wav = str(record.get('path') or final_wav)
    except Exception as exc:
        print(f'[pipeline] metadata enrich: {exc}')

    write_wav_tags(final_wav, record, cover_data=cover_data, cover_mime=cover_mime or 'image/jpeg')
    if not ephemeral:
        save_album_cover_sidecar(final_wav, cover_data, cover_mime)

    export_path = final_wav
    if export_format == 'mp3':
        _emit(
            progress_callback,
            0.96,
            f'MP3 320k 변환 중... · {label}' if label else 'MP3 320k 변환 중...',
            stage='converting',
            track_title=meta.get('title'),
            track_artist=meta.get('artist'),
        )
        mp3_path = os.path.splitext(final_wav)[0] + '.mp3'
        if os.path.exists(mp3_path):
            os.remove(mp3_path)
        try:
            (
                ffmpeg.input(final_wav)
                .output(mp3_path, audio_bitrate='320k', format='mp3', **{'id3v2_version': '3'})
                .overwrite_output()
                .run(quiet=True, capture_stdout=True, capture_stderr=True)
            )
        except ffmpeg.Error as e:
            err = (e.stderr or b'').decode('utf-8', errors='replace')
            raise RuntimeError(f'MP3 변환 실패: {err[:300]}') from e
        write_mp3_tags(mp3_path, record, cover_data=cover_data, cover_mime=cover_mime or 'image/jpeg')
        # Keep WAV only if not ephemeral (local archive); else delete WAV keep MP3
        if ephemeral:
            try:
                os.remove(final_wav)
            except OSError:
                pass
            export_path = mp3_path
            record['format'] = 'MP3'
            record['path'] = mp3_path
            record['local_path'] = mp3_path
        else:
            # Local: keep WAV as archive, also offer mp3 beside it
            export_path = mp3_path
            record['format'] = 'WAV'
            record['export_path'] = mp3_path
    else:
        record['format'] = 'WAV'

    record['export_path'] = export_path
    record['export_name'] = export_filename(record, 'mp3' if export_format == 'mp3' else 'wav')

    if ephemeral:
        # Metadata archive only — binary served once then GC'd
        record['ephemeral'] = True
        record['downloaded_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    cleanup_temp_dir()
    return record


def process_url_sync(url, progress_callback=None, export_format: str = 'wav'):
    os.makedirs(TEMP_DIR, exist_ok=True)

    _emit(progress_callback, 0.05, 'URL 분석 중...', stage='listing')

    ydl_opts = dict(BASE_YDL_OPTS)
    hook = make_progress_hook(progress_callback)
    if hook:
        ydl_opts['progress_hooks'] = [hook]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            meta = extract_metadata(info)
            video_id = meta['id']
    except yt_dlp.utils.DownloadError as e:
        raise RuntimeError(f'다운로드 실패: {e}') from e

    label = f'{meta.get("artist", "")} - {meta.get("title", "")}'.strip(' -')
    _emit(
        progress_callback,
        0.47,
        f'WAV 변환 중... · {label}' if label else 'WAV 변환 중...',
        stage='converting',
        current=1,
        total=1,
        track_title=meta.get('title'),
        track_artist=meta.get('artist'),
    )

    temp_file = find_downloaded_audio(TEMP_DIR, video_id)
    if not temp_file or not os.path.isfile(temp_file):
        raise FileNotFoundError(f'다운로드 파일을 찾을 수 없습니다. (id={video_id})')

    try:
        staging_wav = convert_to_staging_wav(
            temp_file, video_id, progress_callback, label=label
        )
    finally:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass

    _emit(
        progress_callback,
        0.66,
        f'앨범 커버 가져오는 중... · {label}' if label else '앨범 커버 가져오는 중...',
        stage='cover',
        current=1,
        total=1,
        track_title=meta.get('title'),
        track_artist=meta.get('artist'),
    )

    cover_data, cover_mime = resolve_cover_bytes(meta, TEMP_DIR, video_id)

    record = finalize_record(
        staging_wav,
        meta,
        '',
        UNKNOWN,
        cover_data,
        cover_mime,
        progress_callback,
        export_format=export_format,
    )
    _emit(
        progress_callback,
        1.0,
        '완료!',
        stage='done',
        current=1,
        total=1,
        track_title=meta.get('title'),
        track_artist=meta.get('artist'),
    )
    return record


async def process_url(url, progress_callback=None, export_format: str = 'wav'):
    return await asyncio.to_thread(process_url_sync, url, progress_callback, export_format)
