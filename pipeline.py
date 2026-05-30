import glob
import os
import asyncio
import threading
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
    resolve_cover_bytes,
    save_album_cover_sidecar,
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
                    callback(pct, '다운로드 중...')
            else:
                callback(0.15, '다운로드 중...')
        elif status == 'finished':
            callback(0.44, '다운로드 마무리 중...')

    return hook


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


def convert_to_staging_wav(source_path, track_id, progress_callback=None):
    os.makedirs(TEMP_DIR, exist_ok=True)
    staging_wav = os.path.join(TEMP_DIR, f'{track_id}_staging.wav')

    if progress_callback:
        progress_callback(0.48, 'WAV 변환 중 (44.1kHz · 16-bit)...')

    stop_pulse = threading.Event()

    def pulse():
        pct = 0.48
        while not stop_pulse.wait(2.0):
            if not progress_callback:
                break
            pct = min(0.64, pct + 0.015)
            progress_callback(pct, 'WAV 변환 중...')

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


def finalize_record(staging_wav, meta, bpm, key, cover_data, cover_mime, progress_callback=None, analysis=None):
    meta = normalize_artist_meta(meta)
    final_wav = plan_track_path(meta, bpm=bpm, key=key)
    ensure_parent_dir(final_wav)

    if os.path.exists(final_wav):
        os.remove(final_wav)
    os.replace(staging_wav, final_wav)

    if progress_callback:
        progress_callback(0.88, '태그 · 앨범 커버 저장 중...')

    record = {
        'id': meta['id'],
        'title': meta['title'],
        'artist': meta['artist'],
        'primary_artist': meta.get('primary_artist') or primary_artist(meta['artist']),
        'album': meta['album'],
        'platform': meta['platform'],
        'format': 'WAV',
        'path': final_wav,
        'bpm': str(bpm) if bpm else '',
        'key': key,
        'genre': meta['genre'],
        'year': meta['year'],
        'url': meta['url'],
    }
    if analysis:
        record['analysis'] = analysis
    write_wav_tags(final_wav, record, cover_data=cover_data, cover_mime=cover_mime or 'image/jpeg')
    save_album_cover_sidecar(final_wav, cover_data, cover_mime)
    cleanup_temp_dir()
    return record


def process_url_sync(url, progress_callback=None):
    os.makedirs(TEMP_DIR, exist_ok=True)

    if progress_callback:
        progress_callback(0.05, 'URL 분석 중...')

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

    if progress_callback:
        progress_callback(0.47, 'WAV 변환 중...')

    temp_file = find_downloaded_audio(TEMP_DIR, video_id)
    if not temp_file or not os.path.isfile(temp_file):
        raise FileNotFoundError(f'다운로드 파일을 찾을 수 없습니다. (id={video_id})')

    try:
        staging_wav = convert_to_staging_wav(temp_file, video_id, progress_callback)
    finally:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass

    if progress_callback:
        progress_callback(0.66, '앨범 커버 가져오는 중...')

    cover_data, cover_mime = resolve_cover_bytes(meta, TEMP_DIR, video_id)

    record = finalize_record(
        staging_wav, meta, '', UNKNOWN, cover_data, cover_mime, progress_callback
    )
    if progress_callback:
        progress_callback(1.0, '완료!')
    return record


async def process_url(url, progress_callback=None):
    return await asyncio.to_thread(process_url_sync, url, progress_callback)
