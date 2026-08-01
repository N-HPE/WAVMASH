"""플레이리스트 바이브(장르) 색 팔레트 — 프론트 vibePalette.ts 와 동기화."""

from __future__ import annotations

import re
from typing import Any

VIBE_SHADES: dict[str, list[dict[str, Any]]] = {
    "pop": [
        {"shade": 0, "hex": "#E5B820", "label": "Mainstream Pop"},
        {"shade": 1, "hex": "#F5D045", "label": "Dance Pop"},
        {"shade": 2, "hex": "#FFE566", "label": "Bright Pop"},
        {"shade": 3, "hex": "#FFF59D", "label": "Light / Soft Pop"},
    ],
    "rnb": [
        {"shade": 0, "hex": "#8B1A1A", "label": "Classic R&B"},
        {"shade": 1, "hex": "#C62828", "label": "Contemporary R&B"},
        {"shade": 2, "hex": "#E53935", "label": "Soul"},
        {"shade": 3, "hex": "#EF5350", "label": "Neo-Soul"},
    ],
    "hiphop": [
        {"shade": 0, "hex": "#111111", "label": "Hip-Hop"},
        {"shade": 1, "hex": "#2A2A2A", "label": "Boom Bap"},
        {"shade": 2, "hex": "#3D3D3D", "label": "Trap"},
        {"shade": 3, "hex": "#555555", "label": "Drill / Alt"},
    ],
    "house": [
        {"shade": 0, "hex": "#0D7377", "label": "House"},
        {"shade": 1, "hex": "#14919B", "label": "Deep House"},
        {"shade": 2, "hex": "#28A5C5", "label": "Tech House"},
        {"shade": 3, "hex": "#7DD3E8", "label": "Organic / Disco House"},
    ],
    "techno": [
        {"shade": 0, "hex": "#1A237E", "label": "Techno"},
        {"shade": 1, "hex": "#283593", "label": "Peak Techno"},
        {"shade": 2, "hex": "#5C6BC0", "label": "Melodic Techno"},
        {"shade": 3, "hex": "#9FA8DA", "label": "Minimal / Ambient Techno"},
    ],
    "bass": [
        {"shade": 0, "hex": "#1B5E20", "label": "Bass"},
        {"shade": 1, "hex": "#2E7D32", "label": "Dubstep"},
        {"shade": 2, "hex": "#43A047", "label": "Bass House"},
        {"shade": 3, "hex": "#81C784", "label": "Drum & Bass"},
    ],
    "chill": [
        {"shade": 0, "hex": "#5E35B1", "label": "Chill"},
        {"shade": 1, "hex": "#7E57C2", "label": "Lo-Fi"},
        {"shade": 2, "hex": "#9575CD", "label": "Downtempo"},
        {"shade": 3, "hex": "#B39DDB", "label": "Ambient"},
    ],
    "other": [
        {"shade": 0, "hex": "#6D4C41", "label": "Mix / Other"},
        {"shade": 1, "hex": "#8D6E63", "label": "Eclectic"},
        {"shade": 2, "hex": "#A1887F", "label": "Experimental"},
        {"shade": 3, "hex": "#BCAAA4", "label": "Misc"},
    ],
}

# 자동 분류 규칙 이름 → 바이브
AUTO_RULE_VIBE: dict[str, tuple[str, int]] = {
    "House": ("house", 0),
    "Techno": ("techno", 0),
    "Hip-Hop / R&B": ("hiphop", 0),
    "Pop / Dance": ("pop", 0),
    "Bass Music": ("bass", 0),
    "Chill / Lo-Fi": ("chill", 0),
}

VIBE_LABELS: dict[str, str] = {
    "pop": "Pop",
    "rnb": "R&B",
    "hiphop": "Hip-Hop",
    "house": "House",
    "techno": "Techno",
    "bass": "Bass",
    "chill": "Chill",
    "other": "Other",
}


def get_vibe_color(vibe: str | None, shade: int = 0) -> str:
    shades = VIBE_SHADES.get(vibe or "other") or VIBE_SHADES["other"]
    idx = max(0, min(int(shade or 0), len(shades) - 1))
    return str(shades[idx]["hex"])


def resolve_color(
    *,
    color: str | None = None,
    vibe: str | None = None,
    shade: int = 0,
) -> str:
    if color and re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
        return color
    return get_vibe_color(vibe, shade)


def infer_vibe_from_name(name: str) -> tuple[str, int]:
    n = name.lower()
    if re.search(r"(old\s*)?pop\b|dance\s*pop|electropop", n):
        if re.search(r"old|retro|vintage", n):
            return ("pop", 1)
        if re.search(r"light|soft|bright|cute", n):
            return ("pop", 2)
        return ("pop", 0)
    if re.search(r"r&?b|rnb|soul|neo.?soul", n):
        return ("rnb", 0)
    if re.search(r"hip.?hop|rap|trap|drill", n):
        return ("hiphop", 0)
    if re.search(r"house|vino|afro.?house|tech.?house", n):
        return ("house", 0)
    if re.search(r"techno|minimal", n):
        return ("techno", 0)
    if re.search(r"bass|dubstep|dnb|drum.?and.?bass", n):
        return ("bass", 0)
    if re.search(r"chill|lo.?fi|lofi|ambient|downtempo", n):
        return ("chill", 0)
    return ("other", 0)


def make_meta(
    vibe: str | None = None,
    shade: int | None = None,
    color: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """플레이리스트 meta 엔트리를 생성합니다."""
    if vibe is None and name:
        vibe, inferred_shade = infer_vibe_from_name(name)
        if shade is None:
            shade = inferred_shade
    vibe = vibe or "other"
    shade = 0 if shade is None else int(shade)
    hex_color = resolve_color(color=color, vibe=vibe, shade=shade)
    return {
        "vibe": vibe,
        "shade": shade,
        "color": hex_color,
    }


def ensure_playlist_meta(data: dict[str, Any]) -> dict[str, Any]:
    """모든 플레이리스트에 meta가 있도록 채웁니다 (in-place)."""
    playlists = data.get("playlists") or {}
    meta = data.setdefault("meta", {})
    if not isinstance(meta, dict):
        meta = {}
        data["meta"] = meta

    changed = False
    for name in playlists:
        entry = meta.get(name)
        if not isinstance(entry, dict) or not entry.get("color") or not entry.get("vibe"):
            base = entry if isinstance(entry, dict) else {}
            meta[name] = make_meta(
                name=name,
                vibe=base.get("vibe"),
                shade=base.get("shade"),
                color=base.get("color"),
            )
            changed = True
        else:
            # color 없으면 vibe/shade로 채움
            if not entry.get("color"):
                entry["color"] = resolve_color(
                    vibe=entry.get("vibe"),
                    shade=int(entry.get("shade") or 0),
                )
                changed = True

    # 삭제된 플리 meta 정리
    stale = [k for k in meta if k not in playlists]
    for k in stale:
        del meta[k]
        changed = True

    return data if changed else data
