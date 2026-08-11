"""Spotify → 로컬 매칭 / missing_ids 단위 테스트 (네트워크 없음)."""

from __future__ import annotations

from server.services.spotify_match import (
    find_record_for_song,
    map_spotify_songs_to_local,
    merge_missing_ids,
)


def test_find_by_external_id():
    records = [
        {
            "track_id": "t1",
            "external_id": "sp123",
            "title": "Song A",
            "artist": "Artist",
            "has_file": True,
            "path": "/wav/a.wav",
        }
    ]
    found = find_record_for_song(records, song_id="sp123")
    assert found is not None
    assert found["track_id"] == "t1"


def test_find_by_url_spotify_id():
    records = [
        {
            "track_id": "t2",
            "url": "https://open.spotify.com/track/abcXYZ99",
            "title": "Other",
            "artist": "X",
            "has_file": True,
        }
    ]
    found = find_record_for_song(records, song_id="abcXYZ99")
    assert found is not None
    assert found["track_id"] == "t2"


def test_find_by_title_artist_fallback():
    records = [
        {
            "track_id": "t3",
            "title": "Midnight City",
            "artist": "M83",
            "has_file": True,
        }
    ]
    found = find_record_for_song(
        records, song_id="unknown", name="Midnight City", artist="M83"
    )
    assert found is not None
    assert found["track_id"] == "t3"


def test_map_partial_missing():
    records = [
        {
            "track_id": "local-1",
            "external_id": "s1",
            "title": "One",
            "artist": "A",
            "has_file": True,
            "path": "/a.wav",
        },
        {
            "track_id": "local-2",
            "external_id": "s2",
            "title": "Two",
            "artist": "B",
            "has_file": False,
            "path": "",
        },
    ]
    songs = [
        {"song_id": "s1", "name": "One", "artist": "A"},
        {"song_id": "s2", "name": "Two", "artist": "B"},
        {"song_id": "s3", "name": "Three", "artist": "C"},
    ]
    mapped = map_spotify_songs_to_local(songs, records, require_file=True, check_disk=False)
    assert mapped["matching_track_ids"] == ["local-1"]
    assert mapped["local_spotify_ids"] == ["s1"]
    assert mapped["missing_ids"] == ["s2", "s3"]
    assert mapped["status"] == "partial"
    assert mapped["missing_count"] == 2
    assert mapped["local_count"] == 1


def test_map_completed_when_all_present():
    records = [
        {"track_id": "a", "external_id": "1", "has_file": True, "path": "/x"},
        {"track_id": "b", "external_id": "2", "has_file": True, "path": "/y"},
    ]
    songs = [
        {"song_id": "1", "name": "", "artist": ""},
        {"song_id": "2", "name": "", "artist": ""},
    ]
    mapped = map_spotify_songs_to_local(songs, records, require_file=True, check_disk=False)
    assert mapped["missing_ids"] == []
    assert mapped["status"] == "completed"
    assert mapped["synced" if False else "local_spotify_ids"] == ["1", "2"]


def test_merge_missing_ids_preserves_order():
    assert merge_missing_ids(["a", "b"], ["b", "c"], ["a"]) == ["a", "b", "c"]


def test_synced_track_ids_only_local_present():
    """삭제 동기화 기준: 로컬에 파일이 있는 Spotify ID만 synced."""
    records = [
        {"track_id": "t1", "external_id": "keep", "has_file": True, "path": "/k"},
        {"track_id": "t2", "external_id": "nofile", "has_file": False},
    ]
    songs = [
        {"song_id": "keep", "name": "K", "artist": "A"},
        {"song_id": "nofile", "name": "N", "artist": "B"},
        {"song_id": "gone", "name": "G", "artist": "C"},
    ]
    mapped = map_spotify_songs_to_local(songs, records, require_file=True, check_disk=False)
    assert mapped["local_spotify_ids"] == ["keep"]
    assert "nofile" in mapped["missing_ids"]
    assert "gone" in mapped["missing_ids"]
