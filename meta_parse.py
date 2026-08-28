"""YouTube / messy title → clean artist + track title parsing."""

from __future__ import annotations

import re
from typing import Tuple

UNKNOWN = "Unknown"

# Junk phrases inside () [] 【】 etc.
_JUNK_PAREN = re.compile(
    r"[\(\[【｛{]\s*(?:"
    r"official(?:\s+(?:music|lyric|audio|video|mv|visualizer))?|"
    r"official\s*(?:video|audio|mv|hd|4k|visualizer|lyric\s*video)?|"
    r"music\s*video|lyric\s*video|lyrics?|audio|visualizer|mv|m/?v|"
    r"hd|hq|4k|1080p|720p|explicit|clean\s*version|"
    r"remaster(?:ed)?(?:\s*\d{2,4})?|live(?:\s+(?:at|from|version))?|"
    r"topic|full\s*album|color\s*coded|eng(?:lish)?(?:\s*/\s*kor)?|"
    r"sub(?:title)?s?|karaoke|instrumental\s*only|speed\s*up|slowed|"
    r"reverb|nightcore|tiktok|shorts?|preview|snippet|"
    r"clip\s*officiel|videoclip|performance\s*video|"
    r"prod\.?\s*by|produced\s*by|dir(?:ected)?\.?\s*by|"
    r"with\s*lyrics|fan\s*made|cover\s*by|"
    r"audio\s*only|video\s*only|vertical\s*video|"
    r"spotify|apple\s*music|amazon\s*music"
    r")[^)\]】｝}]*[\)\]】｝}]",
    re.I,
)

_JUNK_TRAILING = re.compile(
    r"\s*[-–—|]\s*(?:"
    r"official(?:\s+(?:music\s*)?(?:video|audio))?|"
    r"lyrics?|audio|mv|visualizer|remaster(?:ed)?|live|hd|4k|"
    r"prod\.?\s*.+|with\s*lyrics"
    r")\s*$",
    re.I,
)

_FEAT = re.compile(
    r"\s*[\(\[]?\s*(?:feat\.?|ft\.?|featuring)\s+([^)\]]+)[\)\]]?",
    re.I,
)

_TOPIC_CHANNEL = re.compile(r"\s*-\s*topic\s*$", re.I)
_VEVO = re.compile(r"vevo$", re.I)
_OFFICIAL_CHANNEL = re.compile(r"\s*(?:official|music|vevo)\s*$", re.I)

_SEPARATORS = (" - ", " – ", " — ", " | ", " · ", " • ", " / ")


def strip_junk(title: str) -> str:
    t = (title or "").strip()
    t = t.replace("【", "[").replace("】", "]").replace("「", "").replace("」", "")
    t = t.replace("『", "").replace("』", "")
    prev = None
    while prev != t:
        prev = t
        t = _JUNK_PAREN.sub("", t)
    t = _JUNK_TRAILING.sub("", t)
    t = re.sub(r"\s{2,}", " ", t).strip(" -–—|·•/\"'")
    return t


def clean_channel_artist(channel: str | None) -> str:
    if not channel:
        return UNKNOWN
    name = _TOPIC_CHANNEL.sub("", channel.strip())
    name = _VEVO.sub("", name).strip()
    name2 = _OFFICIAL_CHANNEL.sub("", name).strip()
    if name2 and len(name2) >= 2:
        name = name2
    return name or UNKNOWN


def parse_artist_title(raw_title: str, fallback_artist: str | None = None) -> Tuple[str, str]:
    """Parse messy YouTube-style titles into (artist, title)."""
    fallback = clean_channel_artist(fallback_artist)
    cleaned = strip_junk(raw_title or "")
    if not cleaned:
        return fallback, UNKNOWN

    # Artist「Title」 / Artist『Title』
    m = re.search(r"^(.+?)\s*[「『](.+?)[」』]\s*$", (raw_title or "").strip())
    if m:
        return strip_junk(m.group(1)) or fallback, strip_junk(m.group(2)) or cleaned

    # "Artist - Title"
    for sep in _SEPARATORS:
        if sep in cleaned:
            left, right = cleaned.split(sep, 1)
            left, right = left.strip(), strip_junk(right)
            if left and right and len(left) < 80 and len(left.split()) <= 8:
                artist, title = left, right
                feat_m = _FEAT.search(title)
                if feat_m:
                    feat = feat_m.group(1).strip()
                    title = _FEAT.sub("", title).strip()
                    if feat and feat.lower() not in artist.lower():
                        artist = f"{artist}, {feat}"
                return artist, title or cleaned

    # "Title by Artist"
    m = re.search(r"^(.+?)\s+by\s+(.+)$", cleaned, re.I)
    if m:
        return m.group(2).strip(), strip_junk(m.group(1))

    if fallback and fallback != UNKNOWN:
        return fallback, cleaned

    return fallback, cleaned
