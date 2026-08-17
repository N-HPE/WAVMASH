#!/usr/bin/env python3
"""WaveMash -> Supabase Data Migration Script.

Migrates local archive.json, playlists.json, and spotify_sync.json
directly into your Supabase database.

Usage:
    python scripts/migrate_to_supabase.py
    # or specify env vars directly:
    SUPABASE_URL=https://xyz.supabase.co SUPABASE_SERVICE_ROLE_KEY=ey... python scripts/migrate_to_supabase.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Add project root to sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from env_loader import ensure_env_loaded

ensure_env_loaded()

import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY", "")

ARCHIVE_PATH = _ROOT / "archive.json"
PLAYLISTS_PATH = _ROOT / "playlists.json"
SPOTIFY_SYNC_PATH = _ROOT / "spotify_sync.json"


def get_headers() -> dict[str, str]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY) must be set in .env")
        sys.exit(1)
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }


def migrate_tracks(headers: dict[str, str]) -> int:
    if not ARCHIVE_PATH.exists():
        print("⚠️ No archive.json found, skipping tracks.")
        return 0

    with open(ARCHIVE_PATH, "r", encoding="utf-8") as f:
        records: list[dict[str, Any]] = json.load(f)

    if not isinstance(records, list):
        print("⚠️ archive.json is not a list, skipping.")
        return 0

    print(f"📦 Found {len(records)} tracks in archive.json. Migrating to Supabase...")

    url = f"{SUPABASE_URL}/rest/v1/tracks"
    batch_size = 100
    migrated = 0

    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        payload = []
        for r in batch:
            track_id = str(r.get("track_id") or r.get("id") or "")
            if not track_id:
                continue

            payload.append({
                "track_id": track_id,
                "title": str(r.get("title") or ""),
                "artist": str(r.get("artist") or ""),
                "primary_artist": str(r.get("primary_artist") or r.get("artist") or ""),
                "album": str(r.get("album") or ""),
                "genre": str(r.get("genre") or "Unknown"),
                "year": str(r.get("year") or ""),
                "bpm": str(r.get("bpm") or ""),
                "key": str(r.get("key") or ""),
                "camelot_key": str(r.get("camelot_key") or r.get("camelot") or ""),
                "energy_level": int(r.get("energy_level") or 0),
                "bpm_source": str(r.get("bpm_source") or ""),
                "platform": str(r.get("platform") or "Spotify"),
                "format": str(r.get("format") or "WAV"),
                "url": str(r.get("url") or ""),
                "external_id": str(r.get("external_id") or ""),
                "thumbnail_url": str(r.get("thumbnail_url") or ""),
                "local_path": str(r.get("local_path") or r.get("path") or ""),
                "has_cover": bool(r.get("has_cover", False)),
                "has_file": bool(r.get("has_file", False)),
                "dominant_color": r.get("dominant_color"),
                "analysis": r.get("analysis") if isinstance(r.get("analysis"), dict) else {},
                "mix_data": r.get("mix_data") if isinstance(r.get("mix_data"), dict) else {},
            })

        if not payload:
            continue

        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code not in (200, 201, 204):
            print(f"❌ Failed to migrate batch {i}..{i+len(payload)}: {resp.status_code} {resp.text}")
        else:
            migrated += len(payload)
            print(f"  ✓ Migrated {migrated}/{len(records)} tracks...")

    print(f"✅ Successfully migrated {migrated} tracks to Supabase.")
    return migrated


def migrate_playlists(headers: dict[str, str]) -> int:
    if not PLAYLISTS_PATH.exists():
        print("⚠️ No playlists.json found, skipping playlists.")
        return 0

    with open(PLAYLISTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        return 0

    playlists_dict = data.get("playlists", {}) or {}
    activity_dict = data.get("activity", {}) or {}
    meta_dict = data.get("meta", {}) or {}

    print(f"📋 Found {len(playlists_dict)} playlists in playlists.json. Migrating to Supabase...")

    playlist_url = f"{SUPABASE_URL}/rest/v1/playlists"
    junction_url = f"{SUPABASE_URL}/rest/v1/playlist_tracks"

    count = 0
    for name, track_ids in playlists_dict.items():
        meta = meta_dict.get(name, {}) or {}
        act = activity_dict.get(name, time.time())

        # Upsert playlist
        pl_payload = {
            "name": name,
            "vibe": meta.get("vibe", "other"),
            "shade": int(meta.get("shade", 0)),
            "color": meta.get("color", "#6D4C41"),
            "source": meta.get("source", "local"),
            "spotify_url": meta.get("spotify_url"),
            "sync_id": meta.get("sync_id"),
            "sync_auto": meta.get("sync_auto"),
            "sync_status": meta.get("sync_status"),
            "activity": float(act) if act else time.time(),
            "meta": meta,
        }

        resp = requests.post(playlist_url, headers=headers, json=pl_payload, timeout=15)
        if resp.status_code not in (200, 201, 204):
            print(f"❌ Failed to upsert playlist '{name}': {resp.status_code} {resp.text}")
            continue

        # Upsert tracks in playlist
        if isinstance(track_ids, list) and track_ids:
            tracks_payload = [
                {
                    "playlist_name": name,
                    "track_id": str(tid),
                    "position": idx,
                }
                for idx, tid in enumerate(track_ids)
                if tid
            ]
            if tracks_payload:
                t_resp = requests.post(junction_url, headers=headers, json=tracks_payload, timeout=20)
                if t_resp.status_code not in (200, 201, 204):
                    print(f"⚠️ Warning: Some track references in '{name}' skipped or failed: {t_resp.text}")

        count += 1
        print(f"  ✓ Playlist '{name}' ({len(track_ids)} tracks) migrated.")

    print(f"✅ Successfully migrated {count} playlists to Supabase.")
    return count


def migrate_spotify_sync(headers: dict[str, str]) -> int:
    if not SPOTIFY_SYNC_PATH.exists():
        print("⚠️ No spotify_sync.json found, skipping sync configs.")
        return 0

    with open(SPOTIFY_SYNC_PATH, "r", encoding="utf-8") as f:
        configs = json.load(f)

    if not isinstance(configs, list) or not configs:
        return 0

    print(f"🔄 Found {len(configs)} Spotify Sync configs. Migrating to Supabase...")

    url = f"{SUPABASE_URL}/rest/v1/spotify_sync_configs"
    payload = []
    for c in configs:
        payload.append({
            "id": c.get("id"),
            "url": c.get("url"),
            "name": c.get("name", "Playlist"),
            "auto_sync_enabled": bool(c.get("auto_sync_enabled", True)),
            "sync_deletions": bool(c.get("sync_deletions", True)),
            "last_synced_at": c.get("last_synced_at"),
            "track_count": int(c.get("track_count") or 0),
            "synced_track_ids": c.get("synced_track_ids") or [],
            "status": c.get("status", "idle"),
            "local_count": int(c.get("local_count") or 0),
            "missing_count": int(c.get("missing_count") or 0),
            "missing_ids": c.get("missing_ids") or [],
        })

    resp = requests.post(url, headers=headers, json=payload, timeout=20)
    if resp.status_code not in (200, 201, 204):
        print(f"❌ Failed to migrate Spotify Sync configs: {resp.status_code} {resp.text}")
        return 0

    print(f"✅ Successfully migrated {len(payload)} Spotify Sync configs to Supabase.")
    return len(payload)


def main() -> None:
    print("=" * 60)
    print("🚀 WAVMASH -> Supabase Cloud Migration")
    print(f"Target URL: {SUPABASE_URL}")
    print("=" * 60)

    headers = get_headers()

    # 1. Tracks
    migrate_tracks(headers)
    print()

    # 2. Playlists
    migrate_playlists(headers)
    print()

    # 3. Spotify Sync
    migrate_spotify_sync(headers)
    print()

    print("🎉 All data migration completed!")


if __name__ == "__main__":
    main()
