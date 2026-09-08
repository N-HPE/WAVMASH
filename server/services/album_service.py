"""WaveMash Masterpiece Albums 서비스 (아티산별 명반 라이브러리).

Nexus 아티산(Nova, Echo, Yachi 등)과 사용자가 선정한 바이닐 명반 아카이브를 관리합니다.
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any

from server.config import get_settings

DEFAULT_MASTERPIECES: list[dict[str, Any]] = [
    # ── Nova's Vault (Club / Electronic / UKG / House) ──
    {
        "id": "2noRn2Aes5aoNVsU6iWThc",
        "title": "Discovery",
        "artist": "Daft Punk",
        "cover_url": "https://i.scdn.co/image/ab67616d0000b273b33d46f2637300a87c072049",
        "year": "2001",
        "genre": "French House / Electronic",
        "total_tracks": 14,
        "spotify_url": "https://open.spotify.com/album/2noRn2Aes5aoNVsU6iWThc",
        "artisan": "nova",
        "curator_note": "프렌치 터치와 신스 펑크의 정점. 언제 들어도 완벽한 사운드 디자인의 영원한 명반.",
        "tags": ["French Touch", "Club Classic", "Essential"],
        "created_at": "2026-09-08T00:00:00Z",
    },
    {
        "id": "5ptwM6qE7t3p70t3p1577H",
        "title": "Actual Life (April 14 - December 17 2020)",
        "artist": "Fred again..",
        "cover_url": "https://i.scdn.co/image/ab67616d0000b2737604b3a6ef866033bbd62bf3",
        "year": "2021",
        "genre": "UK Garage / Emotional Dance",
        "total_tracks": 16,
        "spotify_url": "https://open.spotify.com/album/5ptwM6qE7t3p70t3p1577H",
        "artisan": "nova",
        "curator_note": "팬데믹 일상의 음성을 샘플링해 클럽 음악의 서정성을 혁신한 2020년대 최고의 레코드.",
        "tags": ["UK Garage", "Vocal Chops", "Club Classic"],
        "created_at": "2026-09-08T00:00:01Z",
    },
    {
        "id": "6BzxX6tqD2k1dF4Q0p4u9V",
        "title": "Isles",
        "artist": "Bicep",
        "cover_url": "https://i.scdn.co/image/ab67616d0000b273c52a550eb4f6866ecfa9f379",
        "year": "2021",
        "genre": "Breakbeat / Electronic",
        "total_tracks": 10,
        "spotify_url": "https://open.spotify.com/album/6BzxX6tqD2k1dF4Q0p4u9V",
        "artisan": "nova",
        "curator_note": "브레이크비트 리듬과 신비로운 앰비언트 하우스 텍스처의 완벽한 융합.",
        "tags": ["Breakbeat", "Modern Electronic", "Atmospheric"],
        "created_at": "2026-09-08T00:00:02Z",
    },
    {
        "id": "2Z0kS1rX4W9u6K0Q7l3t1P",
        "title": "Settle",
        "artist": "Disclosure",
        "cover_url": "https://i.scdn.co/image/ab67616d0000b2739fa42c4b7ecf64beaa9aeae5",
        "year": "2013",
        "genre": "Deep House / UK Garage",
        "total_tracks": 14,
        "spotify_url": "https://open.spotify.com/album/2Z0kS1rX4W9u6K0Q7l3t1P",
        "artisan": "nova",
        "curator_note": "모던 UK Garage와 딥 하우스를 메인스트림의 정점으로 끌어올린 댄스 팝의 기념비적 데뷔작.",
        "tags": ["Deep House", "UK Garage", "Floorfiller"],
        "created_at": "2026-09-08T00:00:03Z",
    },

    # ── Echo's Crate (Indie / R&B / Hip-Hop / Culture) ──
    {
        "id": "3mH6qwIy9crq0I9YQbOuDf",
        "title": "Blonde",
        "artist": "Frank Ocean",
        "cover_url": "https://i.scdn.co/image/ab67616d0000b273c5649add07ed3720be9d5526",
        "year": "2016",
        "genre": "Alternative R&B / Art Pop",
        "total_tracks": 17,
        "spotify_url": "https://open.spotify.com/album/3mH6qwIy9crq0I9YQbOuDf",
        "artisan": "echo",
        "curator_note": "2010년대 R&B와 얼터너티브 팝의 최고봉. 드럼 없이도 꽉 차는 기타와 보컬의 감정선.",
        "tags": ["Alt-R&B", "Masterpiece", "Acoustic & Electronic"],
        "created_at": "2026-09-08T00:00:04Z",
    },
    {
        "id": "7ycBtnsMtyVbbw3fRyp0B6",
        "title": "good kid, m.A.A.d city",
        "artist": "Kendrick Lamar",
        "cover_url": "https://i.scdn.co/image/ab67616d0000b273d28d2eb5d0fcd4208a0d4c18",
        "year": "2012",
        "genre": "West Coast Hip-Hop",
        "total_tracks": 12,
        "spotify_url": "https://open.spotify.com/album/7ycBtnsMtyVbbw3fRyp0B6",
        "artisan": "echo",
        "curator_note": "영화 한 편을 듣는 듯한 컴튼 거리의 생생한 내러티브. 현대 힙합의 가장 완벽한 콘셉트 앨범.",
        "tags": ["Hip-Hop", "Cinematic", "Storytelling"],
        "created_at": "2026-09-08T00:00:05Z",
    },
    {
        "id": "5zi7WsKlIiUXv09tbGLKsE",
        "title": "IGOR",
        "artist": "Tyler, The Creator",
        "cover_url": "https://i.scdn.co/image/ab67616d0000b27370ee64a93a6125a07c132ce2",
        "year": "2019",
        "genre": "Neo-Soul / Funk Rap",
        "total_tracks": 12,
        "spotify_url": "https://open.spotify.com/album/5zi7WsKlIiUXv09tbGLKsE",
        "artisan": "echo",
        "curator_note": "디스토션 걸린 신스 베이스와 서정적인 멜로디의 충돌. 타일러의 음악적 천재성이 폭발한 명반.",
        "tags": ["Neo-Soul", "Synth Funk", "Grammy Winner"],
        "created_at": "2026-09-08T00:00:06Z",
    },

    # ── Yachi's Archive (Minimal / Jazz / Ambient / Audiophile) ──
    {
        "id": "1weenldIZQZE0yyoMe0Y0Q",
        "title": "Kind of Blue",
        "artist": "Miles Davis",
        "cover_url": "https://i.scdn.co/image/ab67616d0000b273391807d472289659e51c89f5",
        "year": "1959",
        "genre": "Modal Jazz",
        "total_tracks": 5,
        "spotify_url": "https://open.spotify.com/album/1weenldIZQZE0yyoMe0Y0Q",
        "artisan": "yachi",
        "curator_note": "모달 재즈의 영원한 이정표. 여백의 미학과 즉흥 연주의 극치가 담긴 오디오필의 성배.",
        "tags": ["Modal Jazz", "Audiophile", "All-Time Classic"],
        "created_at": "2026-09-08T00:00:07Z",
    },
    {
        "id": "2Lw2k0sL4H6k4a8u9V0p1M",
        "title": "12",
        "artist": "Ryuichi Sakamoto",
        "cover_url": "https://i.scdn.co/image/ab67616d0000b273418ba035824c2ee1fc8f8139",
        "year": "2023",
        "genre": "Ambient / Modern Classical",
        "total_tracks": 12,
        "spotify_url": "https://open.spotify.com/album/2Lw2k0sL4H6k4a8u9V0p1M",
        "artisan": "yachi",
        "curator_note": "피아노 건반의 타건음과 침묵, 숨소리마저 정교한 음악이 되는 사카모토 류이치의 마지막 스케치.",
        "tags": ["Minimalism", "Piano Ambient", "Hi-Fi Acoustic"],
        "created_at": "2026-09-08T00:00:08Z",
    },
    {
        "id": "0geTzdk2InlqIoBsWeG6Bm",
        "title": "Ambient 1: Music for Airports",
        "artist": "Brian Eno",
        "cover_url": "https://i.scdn.co/image/ab67616d0000b2737bc902c38d58546f25bebaea",
        "year": "1978",
        "genre": "Ambient / Tape Loops",
        "total_tracks": 4,
        "spotify_url": "https://open.spotify.com/album/0geTzdk2InlqIoBsWeG6Bm",
        "artisan": "yachi",
        "curator_note": "공간을 물들이는 순수한 소리의 흐름. 앰비언트 장르의 본질을 정의한 역사적 걸작.",
        "tags": ["Ambient", "Soundscape", "Historic Classic"],
        "created_at": "2026-09-08T00:00:09Z",
    },
]


class AlbumService:
    """Masterpiece Albums 관리 클래스."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._albums: list[dict[str, Any]] = []
        self._loaded = False
        self._path = os.path.join(get_settings().PROJECT_ROOT, "master_albums.json")

    def _load_local(self) -> list[dict[str, Any]]:
        if not os.path.isfile(self._path):
            # 파일이 없으면 기본 명반 시드로 초기화
            self._save_raw(DEFAULT_MASTERPIECES)
            return list(DEFAULT_MASTERPIECES)
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and data:
                    return data
                return list(DEFAULT_MASTERPIECES)
        except Exception:
            return list(DEFAULT_MASTERPIECES)

    def _save_raw(self, items: list[dict[str, Any]]) -> None:
        try:
            tmp = self._path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            if os.path.exists(self._path):
                os.replace(tmp, self._path)
            else:
                os.rename(tmp, self._path)
        except Exception as exc:
            print(f"[WaveMash] master_albums.json 저장 오류: {exc}")

    def list_albums(
        self,
        *,
        artisan: str | None = "all",
        search: str | None = None,
        genre: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._lock:
            if not self._loaded:
                self._albums = self._load_local()
                self._loaded = True

            items = list(self._albums)

            # Artisan 필터
            if artisan and artisan.lower() != "all":
                art_lower = artisan.lower().strip()
                items = [a for a in items if str(a.get("artisan", "")).lower() == art_lower]

            # Genre 필터
            if genre and genre.lower() != "all":
                g_lower = genre.lower().strip()
                items = [a for a in items if g_lower in str(a.get("genre", "")).lower()]

            # 검색어 필터
            if search:
                s_lower = search.lower().strip()
                items = [
                    a for a in items
                    if s_lower in str(a.get("title", "")).lower()
                    or s_lower in str(a.get("artist", "")).lower()
                    or s_lower in str(a.get("curator_note", "")).lower()
                ]

            return items

    def get_album(self, album_id: str) -> dict[str, Any] | None:
        with self._lock:
            if not self._loaded:
                self._albums = self._load_local()
                self._loaded = True

            for a in self._albums:
                if str(a.get("id")) == str(album_id):
                    return dict(a)
        return None

    def add_album(self, data: dict[str, Any]) -> dict[str, Any]:
        from server.services.spotify_catalog import get_album_tracks

        album_id = str(data.get("id", "")).strip()
        record = dict(data)
        record["id"] = album_id

        # 제목이나 커버가 비어있고 스포티파이 ID인 경우 스포티파이에서 자동 보강
        if (not record.get("title") or not record.get("cover_url")) and album_id:
            try:
                sp_info = get_album_tracks(album_id)
                sp_album = sp_info.get("album", {})
                if not record.get("title"):
                    record["title"] = sp_album.get("name") or "Unknown Album"
                if not record.get("artist"):
                    record["artist"] = sp_album.get("artist") or "Unknown Artist"
                if not record.get("cover_url"):
                    record["cover_url"] = sp_album.get("thumbnail_url") or ""
                if not record.get("year"):
                    release_date = sp_album.get("release_date") or ""
                    record["year"] = release_date[:4]
                if not record.get("total_tracks"):
                    record["total_tracks"] = sp_album.get("total_tracks") or len(sp_info.get("tracks", []))
                if not record.get("spotify_url"):
                    record["spotify_url"] = sp_album.get("spotify_url") or f"https://open.spotify.com/album/{album_id}"
                if not record.get("tracks"):
                    record["tracks"] = sp_info.get("tracks", [])
            except Exception as e:
                print(f"[WaveMash] Spotify album enrichment failed: {e}")

        if "created_at" not in record or not record["created_at"]:
            record["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if "artisan" not in record or not record["artisan"]:
            record["artisan"] = "nova"

        with self._lock:
            if not self._loaded:
                self._albums = self._load_local()
                self._loaded = True

            # 기존 존재 시 갱신, 미존재 시 맨 앞 추가
            idx = next((i for i, a in enumerate(self._albums) if str(a.get("id")) == album_id), None)
            if idx is not None:
                self._albums[idx].update(record)
                saved = self._albums[idx]
            else:
                self._albums.insert(0, record)
                saved = record

            self._save_raw(self._albums)
            return saved

    def delete_album(self, album_id: str) -> bool:
        with self._lock:
            if not self._loaded:
                self._albums = self._load_local()
                self._loaded = True

            orig_len = len(self._albums)
            self._albums = [a for a in self._albums if str(a.get("id")) != str(album_id)]
            if len(self._albums) < orig_len:
                self._save_raw(self._albums)
                return True
        return False

    def reset_to_defaults(self) -> list[dict[str, Any]]:
        with self._lock:
            self._albums = list(DEFAULT_MASTERPIECES)
            self._save_raw(self._albums)
            self._loaded = True
            return list(self._albums)

    def clear_legacy_archive(self) -> int:
        """기존 archive.json의 낱개 싱글 트랙들을 비워 명반 라이브러리로 새 출발."""
        from server.database import get_archive_cache
        from desktop_app.archive_store import save_archive

        cache = get_archive_cache()
        old_count = len(cache.get_records())
        save_archive([])
        cache.load(force=True)
        return old_count


_album_service = AlbumService()


def get_album_service() -> AlbumService:
    """글로벌 AlbumService 인스턴스를 반환합니다."""
    return _album_service
