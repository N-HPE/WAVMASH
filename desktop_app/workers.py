from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


ProgressFn = Callable[[float, str], None]


@dataclass(frozen=True)
class JobRequest:
    source: str  # 'stream' | 'spotify'
    url: str


class JobSignals(QObject):
    progress = Signal(float, str)
    finished = Signal(object)  # record | list[record]
    failed = Signal(str)


class DownloadJob(QRunnable):
    def __init__(self, request: JobRequest):
        super().__init__()
        self.request = request
        self.signals = JobSignals()

    @Slot()
    def run(self) -> None:
        def progress_cb(p: float, m: str) -> None:
            self.signals.progress.emit(float(p), str(m))

        try:
            if self.request.source == "spotify":
                from spotify_pipeline import normalize_spotify_url, process_spotify_url_sync

                result = process_spotify_url_sync(
                    normalize_spotify_url(self.request.url), progress_cb
                )
            else:
                from pipeline import process_url_sync

                result = process_url_sync(self.request.url, progress_cb)

            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.failed.emit(str(e).strip() or type(e).__name__)


class MetadataRefreshSignals(QObject):
    progress = Signal(float, str)
    one_done = Signal(str, object)  # (record_id, {bpm, key, source})
    finished = Signal(int)
    failed = Signal(str)


class MetadataRefreshJob(QRunnable):
    """BPM/Key from MIK DB & tags, then GetSongBPM / local analysis for gaps."""

    def __init__(
        self,
        tracks: list[tuple[str, str, str, str, str]],
        *,
        force: bool = False,
    ):
        # (record_id, artist, title, url, path)
        super().__init__()
        self.tracks = tracks
        self.force = force  # kept for API compatibility; no longer used
        self.signals = MetadataRefreshSignals()

    @Slot()
    def run(self) -> None:
        try:
            from library import UNKNOWN, effective_artist_title
            from track_metadata import resolve_track_metadata
        except Exception as e:
            self.signals.failed.emit(f"메타데이터 모듈 로드 실패: {e}")
            return

        valid = [
            (track_id, artist, title, path)
            for track_id, artist, title, _url, path in self.tracks
            if path and os.path.isfile(path)
        ]
        total = len(valid) or 1
        done = 0
        for i, (track_id, artist, title, path) in enumerate(valid):
            artist, title = effective_artist_title(artist, title)
            try:
                result = resolve_track_metadata(path, artist, title)
                bpm = result.get("bpm") or 0
                key = str(result.get("key") or UNKNOWN)
                has_bpm = bool(bpm) and float(bpm) > 0
                has_key = key and key != UNKNOWN
                if has_bpm or has_key or result.get("energy_level"):
                    self.signals.one_done.emit(
                        track_id,
                        {
                            "bpm": bpm,
                            "key": key,
                            "camelot_key": result.get("camelot") or "",
                            "energy_level": result.get("energy_level") or 0,
                            "beat_offset_sec": result.get("beat_offset_sec"),
                            "source": result.get("source", ""),
                        },
                    )
                    done += 1
            except Exception as e:
                print(f"[MetadataRefreshJob] {track_id}: {e}")
            name = os.path.basename(path)
            self.signals.progress.emit(
                (i + 1) / total,
                f"BPM/Key 조회 {i + 1}/{total} — {name}",
            )

        self.signals.finished.emit(done)


class AnalyzeSignals(QObject):
    progress = Signal(float, str)
    one_done = Signal(str, object)  # (record_id, analysis dict)
    finished = Signal(int)  # number analyzed
    failed = Signal(str)


class AnalyzeJob(QRunnable):
    """Deprecated: kept for compatibility; use MetadataRefreshJob instead."""

    def __init__(self, tracks: list[tuple[str, str, float]]):
        super().__init__()
        self.tracks = tracks
        self.signals = AnalyzeSignals()

    @Slot()
    def run(self) -> None:
        self.signals.failed.emit("구조 분석은 비활성화되었습니다. BPM/Key 조회를 사용하세요.")


class CoverRepairSignals(QObject):
    finished = Signal(int)


class CoverRepairJob(QRunnable):
    def __init__(self, records: list[dict[str, Any]]):
        super().__init__()
        self.records = records
        self.signals = CoverRepairSignals()

    @Slot()
    def run(self) -> None:
        try:
            from library import repair_missing_covers

            count = repair_missing_covers(self.records)
            self.signals.finished.emit(count)
        except Exception as e:
            print(f"[CoverRepairJob] {e}")
            self.signals.finished.emit(0)


class VersionSearchSignals(QObject):
    results = Signal(list)  # list[dict]: id/title/duration/uploader/url
    failed = Signal(str)


class VersionSearchJob(QRunnable):
    """Search YouTube for alternate versions (extended / radio / original ...)."""

    def __init__(self, query: str, limit: int = 10):
        super().__init__()
        self.query = query
        self.limit = limit
        self.signals = VersionSearchSignals()

    @Slot()
    def run(self) -> None:
        try:
            import yt_dlp

            opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
                "skip_download": True,
            }
            out: list[dict[str, Any]] = []
            seen: set[str] = set()
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(
                    f"ytsearch{self.limit}:{self.query}", download=False
                )
                for e in (info.get("entries") or []):
                    vid = e.get("id")
                    if not vid or vid in seen:
                        continue
                    seen.add(vid)
                    out.append(
                        {
                            "id": vid,
                            "title": e.get("title") or "",
                            "duration": int(e.get("duration") or 0),
                            "uploader": e.get("uploader") or e.get("channel") or "",
                            "url": f"https://www.youtube.com/watch?v={vid}",
                        }
                    )
            self.signals.results.emit(out)
        except Exception as e:
            self.signals.failed.emit(str(e).strip() or type(e).__name__)


class UrlPreviewSignals(QObject):
    finished = Signal(object)  # dict: artist, title, url, platform, id, track_count?
    failed = Signal(str)


class UrlPreviewJob(QRunnable):
    """Fetch title/artist from a URL without downloading (yt-dlp or Spotify metadata)."""

    def __init__(self, url: str, source: str):
        super().__init__()
        self.url = url.strip()
        self.source = source
        self.signals = UrlPreviewSignals()

    @Slot()
    def run(self) -> None:
        try:
            if self.source == "spotify":
                from library import display_artists
                from spotify_pipeline import list_spotify_songs, normalize_spotify_url

                norm = normalize_spotify_url(self.url)
                songs = list_spotify_songs(norm)
                if not songs:
                    raise RuntimeError("Spotify 곡 정보를 찾을 수 없습니다.")
                song = songs[0]
                primary = str(getattr(song, "artist", "") or "Unknown")
                artists = getattr(song, "artists", None) or []
                artist = display_artists(
                    "/".join(artists) if artists else primary
                )
                payload = {
                    "title": str(getattr(song, "name", "") or "Unknown"),
                    "artist": artist,
                    "url": str(getattr(song, "url", "") or self.url),
                    "platform": "spotify",
                    "id": str(getattr(song, "song_id", "") or ""),
                    "track_count": len(songs),
                }
                self.signals.finished.emit(payload)
                return

            import yt_dlp

            from library import extract_metadata

            opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
            meta = extract_metadata(info)
            self.signals.finished.emit(
                {
                    "title": meta.get("title") or "Unknown",
                    "artist": meta.get("artist") or "Unknown",
                    "url": meta.get("url") or self.url,
                    "platform": meta.get("platform") or "stream",
                    "id": meta.get("id") or "",
                    "track_count": 1,
                }
            )
        except Exception as e:
            self.signals.failed.emit(str(e).strip() or type(e).__name__)


class WorkerPool:
    def __init__(self) -> None:
        self.pool = QThreadPool.globalInstance()

    def start_download(self, request: JobRequest) -> DownloadJob:
        job = DownloadJob(request)
        self.pool.start(job)
        return job

    def start_version_search(self, query: str, limit: int = 10) -> VersionSearchJob:
        job = VersionSearchJob(query, limit)
        self.pool.start(job)
        return job

    def start_url_preview(self, url: str, source: str) -> UrlPreviewJob:
        job = UrlPreviewJob(url, source)
        self.pool.start(job)
        return job

    def start_analyze(self, tracks: list[tuple[str, str, float]]) -> AnalyzeJob:
        job = AnalyzeJob(tracks)
        self.pool.start(job)
        return job

    def start_metadata_refresh(
        self,
        tracks: list[tuple[str, str, str, str, str]],
        *,
        force: bool = True,
    ) -> MetadataRefreshJob:
        job = MetadataRefreshJob(tracks, force=force)
        self.pool.start(job)
        return job

    def start_cover_repair(self, records: list[dict[str, Any]]) -> CoverRepairJob:
        job = CoverRepairJob(records)
        self.pool.start(job)
        return job

