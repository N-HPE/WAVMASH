"""라이브러리 export/import 병합 단위 테스트."""

from __future__ import annotations

from server.services.library_sync_service import _merge_archive, _merge_playlists


def test_merge_archive_adds_and_updates():
    current = [
        {
            "track_id": "t1",
            "title": "Old",
            "path": "/local/a.wav",
            "bpm": "120",
        }
    ]
    incoming = [
        {
            "track_id": "t1",
            "title": "New Title",
            "path": "",
            "bpm": "128",
        },
        {
            "track_id": "t2",
            "title": "Brand",
            "path": "/other/b.wav",
        },
    ]
    merged, added, updated = _merge_archive(current, incoming)
    assert added == 1
    assert updated == 1
    by_id = {r["track_id"]: r for r in merged}
    assert by_id["t1"]["title"] == "New Title"
    assert by_id["t1"]["path"] == "/local/a.wav"  # 빈 경로면 기존 유지
    assert by_id["t1"]["bpm"] == "128"
    assert by_id["t2"]["title"] == "Brand"


def test_merge_playlists_unions_track_ids():
    current = {
        "playlists": {"House": ["a", "b"]},
        "activity": {"House": 1.0},
        "meta": {"House": {"vibe": "house", "source": "local"}},
    }
    incoming = {
        "playlists": {"House": ["b", "c"], "Chill": ["d"]},
        "activity": {"House": 2.0, "Chill": 3.0},
        "meta": {"Chill": {"vibe": "chill"}},
    }
    out = _merge_playlists(current, incoming)
    assert out["playlists"]["House"] == ["a", "b", "c"]
    assert out["playlists"]["Chill"] == ["d"]
    assert out["activity"]["House"] == 2.0
    assert out["meta"]["Chill"]["vibe"] == "chill"
    assert out["meta"]["House"]["source"] == "local"
