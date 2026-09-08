"""Nexus persona identity spectrum — Echo (black) → Yachi (white).

Keep in sync with NEXUS ``config/artisan_playlists.json`` → ``persona_spectrum``.
Genre ``VIBE_SHADES`` in this module stays for chart classification.
"""

from __future__ import annotations

PERSONA_SPECTRUM: list[dict[str, object]] = [
    {
        "artisan_key": "echo",
        "name": "Echo",
        "playlist": "ECHO",
        "color": "#0A0A0A",
        "chart_buckets": ["blue", "indigo", "violet"],
    },
    {
        "artisan_key": "stock",
        "name": "Midas",
        "playlist": "MIDAS",
        "color": "#1C1C1C",
        "chart_buckets": ["red"],
    },
    {
        "artisan_key": "sports",
        "name": "Paolo",
        "playlist": "PAOLO",
        "color": "#1B4332",
        "chart_buckets": ["green", "violet"],
    },
    {
        "artisan_key": "fashion",
        "name": "Rocky",
        "playlist": "ROCKY",
        "color": "#9B2226",
        "chart_buckets": ["red", "orange"],
    },
    {
        "artisan_key": "business",
        "name": "Hermes",
        "playlist": "HERMES",
        "color": "#005F73",
        "chart_buckets": ["blue", "indigo"],
    },
    {
        "artisan_key": "music",
        "name": "Nova",
        "playlist": "NOVA",
        "color": "#6B5344",
        "chart_buckets": ["yellow", "green"],
    },
    {
        "artisan_key": "now",
        "name": "Nau",
        "playlist": "Nau",
        "color": "#CA8A04",
        "chart_buckets": ["yellow"],
    },
    {
        "artisan_key": "health",
        "name": "Galen",
        "playlist": "GALEN",
        "color": "#6D28D9",
        "chart_buckets": ["green", "indigo"],
    },
    {
        "artisan_key": "art",
        "name": "Leo",
        "playlist": "LEO",
        "color": "#A78BFA",
        "chart_buckets": ["green"],
    },
    {
        "artisan_key": "media",
        "name": "Ari",
        "playlist": "ARI",
        "color": "#FB7185",
        "chart_buckets": ["red", "orange"],
    },
    {
        "artisan_key": "macro",
        "name": "Mac",
        "playlist": "Mac",
        "color": "#E9D5FF",
        "chart_buckets": ["green", "indigo"],
    },
    {
        "artisan_key": "yachi",
        "name": "Yachi",
        "playlist": "YACHI",
        "color": "#FAFAFA",
        "chart_buckets": ["blue", "indigo"],
    },
]


def persona_color(artisan_key: str) -> str | None:
    key = (artisan_key or "").strip().lower()
    for row in PERSONA_SPECTRUM:
        if str(row.get("artisan_key") or "") == key:
            return str(row.get("color") or "") or None
    return None
