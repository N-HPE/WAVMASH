"""플레이리스트 서비스 — 자동 분류 및 관리 로직.

장르/BPM/키를 기반으로 자동 플레이리스트를 생성하는 규칙 엔진을 포함합니다.
"""

from __future__ import annotations

import re
import time
from typing import Any

from server.database import get_archive_cache, load_playlists, save_playlists
from server.models import AutoPlaylistRule
from server.vibe_palette import AUTO_RULE_VIBE, make_meta


# ---------------------------------------------------------------------------
# 기본 장르 규칙 (자동 분류용)
# ---------------------------------------------------------------------------

DEFAULT_AUTO_RULES: list[AutoPlaylistRule] = [
    AutoPlaylistRule(
        name="House",
        genre_patterns=["house", "deep house", "tech house", "progressive house"],
        bpm_min=120,
        bpm_max=132,
    ),
    AutoPlaylistRule(
        name="Techno",
        genre_patterns=["techno", "minimal techno", "industrial techno"],
        bpm_min=125,
        bpm_max=150,
    ),
    AutoPlaylistRule(
        name="Hip-Hop / R&B",
        genre_patterns=["hip hop", "hip-hop", "r&b", "rap", "trap"],
        bpm_min=60,
        bpm_max=110,
    ),
    AutoPlaylistRule(
        name="Pop / Dance",
        genre_patterns=["pop", "dance", "electropop", "synth-pop", "dance pop"],
    ),
    AutoPlaylistRule(
        name="Bass Music",
        genre_patterns=["bass", "dubstep", "drum and bass", "dnb", "bass house"],
        bpm_min=130,
        bpm_max=180,
    ),
    AutoPlaylistRule(
        name="Chill / Lo-Fi",
        genre_patterns=["chill", "lo-fi", "lofi", "ambient", "downtempo"],
        bpm_min=60,
        bpm_max=110,
    ),
]


def _match_genre(genre: str, patterns: list[str]) -> bool:
    """장르 문자열이 패턴 목록 중 하나라도 매치하는지 확인합니다."""
    genre_lower = genre.lower().strip()
    if not genre_lower or genre_lower == "unknown":
        return False
    for pattern in patterns:
        pattern_lower = pattern.lower().strip()
        if pattern_lower in genre_lower or genre_lower in pattern_lower:
            return True
    return False


def _match_bpm(bpm_str: str, bpm_min: int | None, bpm_max: int | None) -> bool:
    """BPM이 범위 안에 있는지 확인합니다."""
    try:
        bpm = int(float(bpm_str))
    except (TypeError, ValueError):
        return True  # BPM 정보 없으면 필터 통과
    if bpm <= 0:
        return True
    if bpm_min is not None and bpm < bpm_min:
        return False
    if bpm_max is not None and bpm > bpm_max:
        return False
    return True


def _match_key(key: str, patterns: list[str]) -> bool:
    """키가 패턴 목록 중 하나라도 매치하는지 확인합니다."""
    if not patterns:
        return True
    key_lower = key.lower().strip()
    if not key_lower or key_lower == "unknown":
        return True
    for pattern in patterns:
        if pattern.lower().strip() in key_lower:
            return True
    return False


def auto_classify_tracks(
    rules: list[AutoPlaylistRule] | None = None,
) -> dict[str, list[str]]:
    """모든 트랙을 규칙 기반으로 자동 분류합니다.

    Returns:
        ``{playlist_name: [track_id, ...], ...}``
    """
    if rules is None:
        rules = DEFAULT_AUTO_RULES

    cache = get_archive_cache()
    records = cache.get_records()

    result: dict[str, list[str]] = {}

    for rule in rules:
        matched_ids: list[str] = []
        for rec in records:
            genre = str(rec.get("genre") or "")
            bpm = str(rec.get("bpm") or "")
            key = str(rec.get("key") or "")
            track_id = str(rec.get("track_id") or rec.get("id") or "")

            if not track_id:
                continue

            genre_ok = _match_genre(genre, rule.genre_patterns) if rule.genre_patterns else True
            bpm_ok = _match_bpm(bpm, rule.bpm_min, rule.bpm_max)
            key_ok = _match_key(key, rule.key_patterns)

            if genre_ok and bpm_ok and key_ok:
                matched_ids.append(track_id)

        if matched_ids:
            result[rule.name] = matched_ids

    return result


def apply_auto_playlists(
    rules: list[AutoPlaylistRule] | None = None,
    *,
    merge: bool = True,
) -> dict[str, int]:
    """자동 분류 결과를 playlists.json에 저장합니다.

    Args:
        rules: 분류 규칙. None이면 기본 규칙 사용.
        merge: True이면 기존 플레이리스트에 병합, False이면 덮어쓰기.

    Returns:
        ``{playlist_name: track_count, ...}``
    """
    classified = auto_classify_tracks(rules)
    data = load_playlists()
    playlists = data.get("playlists", {})
    activity = data.get("activity", {})
    meta = data.setdefault("meta", {})
    now = time.time()

    result: dict[str, int] = {}

    for name, track_ids in classified.items():
        if merge and name in playlists:
            existing = set(playlists[name])
            new_ids = [tid for tid in track_ids if tid not in existing]
            playlists[name] = playlists[name] + new_ids
        else:
            playlists[name] = track_ids
        activity[name] = now
        if name not in meta or not isinstance(meta.get(name), dict):
            vibe, shade = AUTO_RULE_VIBE.get(name, (None, 0))
            meta[name] = make_meta(vibe=vibe, shade=shade, name=name)
        result[name] = len(playlists[name])

    data["playlists"] = playlists
    data["activity"] = activity
    data["meta"] = meta
    save_playlists(data)

    return result
