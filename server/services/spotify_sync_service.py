"""스포티파이 플레이리스트 자동 동기화 서비스 — 지정 플레이리스트 감지, 다운로드, 곡/폴더 완전 삭제 동기화, 로컬 플레이리스트 자동 생성."""

from __future__ import annotations

import html
import json
import os
import re
import threading
import time
import urllib.request
from typing import Any

from paths import PROJECT_DIR
from library import (
    WAV_ROOT,
    cleanup_empty_dirs,
    delete_track_file,
    find_cover_sidecar,
)
from server.database import (
    get_archive_cache,
    load_playlists,
    save_playlists,
)
from spotify_metadata import spotify_track_id
import spotify_pipeline

SYNC_CONFIGS_JSON_PATH = os.path.join(PROJECT_DIR, "spotify_sync.json")
_sync_lock = threading.RLock()


def get_spotify_playlist_title(url: str) -> str:
    """스포티파이 플레이리스트 페이지 HTML에서 제목을 추출하거나 API로 가져옵니다."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
            m = re.search(r"<title>(.*?)</title>", content, re.I)
            if m:
                raw_title = html.unescape(m.group(1))
                clean = re.sub(r"\s*-\s*playlist by.*$", "", raw_title, flags=re.I)
                clean = re.sub(r"\s*\|\s*Spotify.*$", "", clean, flags=re.I).strip()
                if clean and clean != "Spotify":
                    return clean
    except Exception:
        pass
    return "Spotify Playlist"


def _load_configs_file() -> list[dict[str, Any]]:
    if not os.path.isfile(SYNC_CONFIGS_JSON_PATH):
        return []
    try:
        with open(SYNC_CONFIGS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_configs_file(configs: list[dict[str, Any]]) -> None:
    with open(SYNC_CONFIGS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(configs, f, indent=4, ensure_ascii=False)


def get_sync_configs() -> list[dict[str, Any]]:
    with _sync_lock:
        return _load_configs_file()


def get_sync_config(config_id: str) -> dict[str, Any] | None:
    with _sync_lock:
        configs = _load_configs_file()
        for cfg in configs:
            if cfg.get("id") == config_id:
                return dict(cfg)
        return None


def add_sync_config(
    url: str,
    auto_sync_enabled: bool = True,
    sync_deletions: bool = True,
) -> dict[str, Any]:
    url = spotify_pipeline.normalize_spotify_url(url.strip())
    if not spotify_pipeline.is_spotify_url(url):
        raise ValueError("유효한 Spotify 플레이리스트 URL이 아닙니다.")

    with _sync_lock:
        configs = _load_configs_file()
        for cfg in configs:
            if cfg.get("url") == url:
                raise ValueError("이미 등록된 스포티파이 플레이리스트 URL입니다.")

        # 플레이리스트 제목 및 기본 정보 추출
        name = get_spotify_playlist_title(url)
        config_id = f"sync_{int(time.time() * 1000)}"

        new_cfg = {
            "id": config_id,
            "url": url,
            "name": name,
            "auto_sync_enabled": auto_sync_enabled,
            "sync_deletions": sync_deletions,
            "last_synced_at": None,
            "status": "pending",  # pending, syncing, completed, error
            "track_count": 0,
            "synced_track_ids": [],
        }
        configs.append(new_cfg)
        _save_configs_file(configs)

    # 등록 후 첫 동기화 백그라운드 자동 실행
    threading.Thread(
        target=sync_single_playlist,
        args=(config_id,),
        daemon=True,
    ).start()

    return new_cfg


def update_sync_config(
    config_id: str,
    auto_sync_enabled: bool | None = None,
    sync_deletions: bool | None = None,
) -> dict[str, Any]:
    with _sync_lock:
        configs = _load_configs_file()
        target = None
        for cfg in configs:
            if cfg.get("id") == config_id:
                target = cfg
                break
        if not target:
            raise KeyError("동기화 설정을 찾을 수 없습니다.")

        if auto_sync_enabled is not None:
            target["auto_sync_enabled"] = auto_sync_enabled
        if sync_deletions is not None:
            target["sync_deletions"] = sync_deletions

        _save_configs_file(configs)
        return dict(target)


def delete_sync_config(config_id: str) -> None:
    with _sync_lock:
        configs = _load_configs_file()
        new_configs = [cfg for cfg in configs if cfg.get("id") != config_id]
        _save_configs_file(new_configs)


def sync_single_playlist(config_id: str) -> dict[str, Any]:
    """단일 스포티파이 플레이리스트를 동기화합니다 (다운로드 + 삭제동기화 + 로컬 플레이리스트 생성 + 빈폴더정리)."""
    with _sync_lock:
        configs = _load_configs_file()
        cfg_index = -1
        cfg = None
        for i, c in enumerate(configs):
            if c.get("id") == config_id:
                cfg_index = i
                cfg = dict(c)
                configs[i]["status"] = "syncing"
                _save_configs_file(configs)
                break
        if not cfg:
            raise KeyError("동기화 설정을 찾을 수 없습니다.")

    url = cfg["url"]
    sync_deletions = cfg.get("sync_deletions", True)
    old_synced_ids = set(cfg.get("synced_track_ids") or [])

    try:
        # 1. 플레이리스트 실제 이름 및 곡 목록 파싱
        name = get_spotify_playlist_title(url)
        songs = spotify_pipeline.list_spotify_songs(url)
        current_spotify_ids = {str(s.song_id): s for s in songs if getattr(s, "song_id", None)}
        current_id_set = set(current_spotify_ids.keys())

        # 2. 신규 곡 다운로드 (아카이브 upsert는 pipeline 내부에서도 수행)
        download_res = spotify_pipeline.process_spotify_url_sync(url)
        downloaded_count = 0
        missing_from_download: list[str] = []
        archive_cache = get_archive_cache()
        from library import ensure_track_id

        if isinstance(download_res, dict) and "records" in download_res:
            downloaded_count = int(download_res.get("downloaded") or 0)
            missing_from_download = list(download_res.get("missing_ids") or [])
            for rec in download_res.get("records") or []:
                ensure_track_id(rec)
                archive_cache.upsert(rec, prepend=True)
        elif isinstance(download_res, dict):
            # 단일 트랙이 dict로 온 경우 (records 키 없음)
            ensure_track_id(download_res)
            archive_cache.upsert(download_res, prepend=True)
            downloaded_count = 1
        elif download_res:
            ensure_track_id(download_res)
            archive_cache.upsert(download_res, prepend=True)
            downloaded_count = 1

        # 디스크 기준 최신본으로 강제 리로드 (캐시 불일치 방지)
        library_records = archive_cache.reload()

        # 3. 삭제 동기화 처리
        deleted_count = 0
        deleted_titles: list[str] = []

        if sync_deletions and old_synced_ids:
            # old_synced_ids 중 "실제로 로컬에 있던" 것만 삭제 대상으로
            # (과거 버그로 Spotify ID 전체가 synced에 들어가 있을 수 있음)
            removed_spotify_ids = old_synced_ids - current_id_set

            for rec in list(library_records):
                rec_url = str(rec.get("url") or "")
                rec_spotify_id = (
                    spotify_track_id(rec_url)
                    or str(rec.get("external_id") or "")
                    or str(rec.get("id") or "")
                )

                if rec_spotify_id in removed_spotify_ids:
                    track_id = str(rec.get("track_id") or rec.get("id") or "")
                    file_path = str(rec.get("path") or rec.get("local_path") or "")
                    title = str(rec.get("title") or "알 수 없는 트랙")

                    if file_path and os.path.isfile(file_path):
                        sidecar = find_cover_sidecar(file_path)
                        if sidecar and os.path.isfile(sidecar):
                            try:
                                os.remove(sidecar)
                            except OSError:
                                pass
                        delete_track_file(file_path)

                    archive_cache.delete(track_id)
                    deleted_count += 1
                    deleted_titles.append(title)

            if deleted_count > 0:
                cleanup_empty_dirs()
                library_records = archive_cache.reload()

        # 4. 로컬 플레이리스트 매핑 — Spotify 순서 유지, 파일 있는 곡만
        from server.services.spotify_match import map_spotify_songs_to_local, merge_missing_ids

        song_dicts = [
            {
                "song_id": str(getattr(song, "song_id", "") or ""),
                "name": str(getattr(song, "name", "") or ""),
                "artist": str(getattr(song, "artist", "") or ""),
            }
            for song in songs
        ]
        mapped = map_spotify_songs_to_local(
            song_dicts,
            library_records,
            require_file=True,
            check_disk=True,
        )
        matching_track_ids = list(mapped["matching_track_ids"])
        local_spotify_ids = list(mapped["local_spotify_ids"])
        missing_ids = merge_missing_ids(
            list(mapped["missing_ids"]),
            list(missing_from_download),
        )

        from server.vibe_palette import make_meta

        pdata = load_playlists()
        if "playlists" not in pdata:
            pdata["playlists"] = {}
        if "activity" not in pdata:
            pdata["activity"] = {}
        if "meta" not in pdata:
            pdata["meta"] = {}
        pdata["playlists"][name] = matching_track_ids
        pdata["activity"][name] = time.time()
        existing_meta = pdata["meta"].get(name) if isinstance(pdata["meta"].get(name), dict) else {}
        base_meta = make_meta(
            vibe=existing_meta.get("vibe"),
            shade=existing_meta.get("shade"),
            color=existing_meta.get("color"),
            name=name,
        )
        base_meta.update({
            "source": "spotify",
            "spotify_url": url,
            "sync_id": config_id,
            "spotify_count": len(songs),
            "local_count": len(matching_track_ids),
            "missing_count": len(missing_ids),
        })
        pdata["meta"][name] = base_meta
        save_playlists(pdata)

        # 5. 설정 정보 갱신
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        status = "completed" if not missing_ids else "partial"
        with _sync_lock:
            configs = _load_configs_file()
            if 0 <= cfg_index < len(configs) and configs[cfg_index]["id"] == config_id:
                configs[cfg_index]["name"] = name
                configs[cfg_index]["last_synced_at"] = now_str
                configs[cfg_index]["status"] = status
                configs[cfg_index]["track_count"] = len(songs)
                configs[cfg_index]["local_count"] = len(matching_track_ids)
                configs[cfg_index]["missing_count"] = len(missing_ids)
                configs[cfg_index]["missing_ids"] = missing_ids
                # 실제로 로컬에 있는 Spotify ID만 (삭제 동기화 기준)
                configs[cfg_index]["synced_track_ids"] = local_spotify_ids
                _save_configs_file(configs)

        return {
            "config_id": config_id,
            "name": name,
            "total_spotify_tracks": len(songs),
            "local_count": len(matching_track_ids),
            "missing_count": len(missing_ids),
            "missing_ids": missing_ids,
            "downloaded": downloaded_count,
            "deleted": deleted_count,
            "deleted_titles": deleted_titles,
            "status": status,
            "synced_at": now_str,
        }

    except Exception as exc:
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        with _sync_lock:
            configs = _load_configs_file()
            if 0 <= cfg_index < len(configs) and configs[cfg_index]["id"] == config_id:
                configs[cfg_index]["status"] = "error"
                configs[cfg_index]["last_synced_at"] = now_str
                _save_configs_file(configs)
        raise exc


def sync_all_active_playlists() -> list[dict[str, Any]]:
    configs = get_sync_configs()
    results = []
    for cfg in configs:
        if cfg.get("auto_sync_enabled", True):
            try:
                res = sync_single_playlist(cfg["id"])
                results.append(res)
            except Exception as exc:
                results.append({
                    "config_id": cfg["id"],
                    "name": cfg.get("name"),
                    "error": str(exc),
                })
    return results


def sync_lookup_by_name() -> dict[str, dict[str, Any]]:
    """플레이리스트 이름 → 동기화 설정 맵."""
    out: dict[str, dict[str, Any]] = {}
    for cfg in get_sync_configs():
        name = str(cfg.get("name") or "").strip()
        if name:
            out[name] = cfg
        # sync_id / url로도 meta에서 매칭할 수 있게 id 키도 보관
        sid = str(cfg.get("id") or "")
        if sid:
            out[f"__id__:{sid}"] = cfg
    return out


def schedule_startup_auto_sync(*, delay_sec: float = 3.0) -> None:
    """서버 기동 후 백그라운드에서 자동 동기화 (기기 간 누락 곡 보완)."""

    def _run() -> None:
        time.sleep(max(0.0, delay_sec))
        configs = [c for c in get_sync_configs() if c.get("auto_sync_enabled", True)]
        if not configs:
            print("[WaveMash] Spotify auto-sync: no active configs")
            return
        print(f"[WaveMash] Spotify auto-sync starting ({len(configs)} playlists)...")
        results = sync_all_active_playlists()
        ok = sum(1 for r in results if not r.get("error"))
        dl = sum(int(r.get("downloaded") or 0) for r in results if not r.get("error"))
        err = sum(1 for r in results if r.get("error"))
        print(f"[WaveMash] Spotify auto-sync done — ok={ok} downloaded={dl} errors={err}")

    threading.Thread(
        target=_run,
        daemon=True,
        name="spotify-startup-sync",
    ).start()
