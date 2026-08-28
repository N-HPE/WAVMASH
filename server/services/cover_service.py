"""앨범 커버 서비스 — 커버 아트 조회 및 색상 추출.

WAV 사이드카 파일 또는 임베디드 APIC 태그에서 커버를 읽고,
Pillow로 지배적 색상을 추출합니다 (프론트엔드 글로우 효과용).

추출된 색상은 ``cover_colors.json``에 디스크 캐시되어
동일 커버에 대해 Pillow 재분석을 건너뜁니다.
"""

from __future__ import annotations

import io
import json
import os
import threading
from typing import Any

from server.config import get_settings

# 기존 모듈 임포트
from library import (
    find_cover_sidecar,
    read_cover_bytes_for_wav,
)

_COLOR_CACHE_LOCK = threading.RLock()
_COLOR_CACHE: dict[str, dict[str, Any]] = {}
_COLOR_CACHE_LOADED = False


def _color_cache_path() -> str:
    settings = get_settings()
    return os.path.join(settings.PROJECT_ROOT, "cover_colors.json")


def _load_color_cache() -> dict[str, dict[str, Any]]:
    global _COLOR_CACHE, _COLOR_CACHE_LOADED
    with _COLOR_CACHE_LOCK:
        if _COLOR_CACHE_LOADED:
            return _COLOR_CACHE
        path = _color_cache_path()
        data: dict[str, dict[str, Any]] = {}
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    data = {
                        str(k): v
                        for k, v in raw.items()
                        if isinstance(v, dict) and v.get("color")
                    }
            except Exception:
                data = {}
        _COLOR_CACHE = data
        _COLOR_CACHE_LOADED = True
        return _COLOR_CACHE


def _save_color_cache() -> None:
    with _COLOR_CACHE_LOCK:
        path = _color_cache_path()
        tmp = path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(_COLOR_CACHE, f, indent=2, ensure_ascii=False)
            os.replace(tmp, path)
        except Exception:
            try:
                if os.path.isfile(tmp):
                    os.remove(tmp)
            except OSError:
                pass


def _cover_fingerprint(record: dict[str, Any]) -> str | None:
    """커버 파일 변경 감지용 fingerprint (경로 + mtime)."""
    sidecar = get_cover_path(record)
    if sidecar and os.path.isfile(sidecar):
        try:
            return f"sidecar:{sidecar}:{os.path.getmtime(sidecar)}"
        except OSError:
            return f"sidecar:{sidecar}"
    path = str(record.get("path") or record.get("local_path") or "")
    if path and os.path.isfile(path):
        try:
            return f"wav:{path}:{os.path.getmtime(path)}"
        except OSError:
            return f"wav:{path}"
    return None


def get_cached_color(track_id: str) -> str | None:
    """디스크/메모리 캐시에서 색상만 조회 (추출 없음)."""
    cache = _load_color_cache()
    entry = cache.get(track_id)
    if not entry:
        return None
    color = entry.get("color")
    return str(color) if color else None


def resolve_dominant_color(
    record: dict[str, Any],
    *,
    compute_if_missing: bool = True,
) -> str | None:
    """트랙의 지배적 색상을 캐시 우선으로 반환합니다."""
    track_id = str(record.get("track_id") or record.get("id") or "")
    if not track_id:
        return None

    fingerprint = _cover_fingerprint(record)
    cache = _load_color_cache()

    with _COLOR_CACHE_LOCK:
        entry = cache.get(track_id)
        if entry and entry.get("color"):
            if not fingerprint or entry.get("fp") == fingerprint:
                return str(entry["color"])

    if not compute_if_missing:
        return None

    data, _mime = get_cover_bytes(record)
    if not data:
        return None

    color = extract_dominant_color(data)
    if not color:
        return None

    with _COLOR_CACHE_LOCK:
        _COLOR_CACHE[track_id] = {"color": color, "fp": fingerprint}
        _save_color_cache()
    return color


def resolve_colors_batch(
    records_by_id: dict[str, dict[str, Any]],
    track_ids: list[str],
) -> dict[str, str | None]:
    """여러 트랙 색상을 한 번에 해석합니다 (캐시 히트는 즉시, 미스는 추출)."""
    result: dict[str, str | None] = {}
    dirty = False
    cache = _load_color_cache()

    for track_id in track_ids:
        record = records_by_id.get(track_id)
        if not record:
            result[track_id] = None
            continue

        fingerprint = _cover_fingerprint(record)
        with _COLOR_CACHE_LOCK:
            entry = cache.get(track_id)
            if entry and entry.get("color") and (
                not fingerprint or entry.get("fp") == fingerprint
            ):
                result[track_id] = str(entry["color"])
                continue

        data, _mime = get_cover_bytes(record)
        if not data:
            result[track_id] = None
            continue

        color = extract_dominant_color(data)
        result[track_id] = color
        if color:
            with _COLOR_CACHE_LOCK:
                _COLOR_CACHE[track_id] = {"color": color, "fp": fingerprint}
                dirty = True

    if dirty:
        with _COLOR_CACHE_LOCK:
            _save_color_cache()

    return result


def get_cover_bytes(record: dict[str, Any]) -> tuple[bytes | None, str | None]:
    """트랙의 앨범 커버 바이트를 반환합니다.

    1. 사이드카 파일 (cover.jpg / cover.png)
    2. WAV 임베디드 APIC 태그
    3. thumbnail_url (CDN) — ephemeral / 클라우드 메타 전용 아카이브

    Returns:
        ``(image_data, mime_type)`` 또는 ``(None, None)``
    """
    path = str(record.get("path") or record.get("local_path") or "")
    if path and os.path.isfile(path):
        data, mime = read_cover_bytes_for_wav(path)
        if data:
            return data, mime

    thumb = str(record.get("thumbnail_url") or "").strip()
    if thumb.startswith("http"):
        try:
            import urllib.request

            req = urllib.request.Request(thumb, headers={"User-Agent": "WaveMash/1.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = resp.read()
                mime = resp.headers.get_content_type() or "image/jpeg"
                return data, mime
        except Exception:
            return None, None
    return None, None


def get_cover_path(record: dict[str, Any]) -> str | None:
    """트랙의 커버 사이드카 파일 경로를 반환합니다."""
    path = str(record.get("path") or record.get("local_path") or "")
    if not path or not os.path.isfile(path):
        return None
    return find_cover_sidecar(path)


def extract_dominant_color(
    image_data: bytes,
    *,
    resize_to: int = 64,
) -> str | None:
    """이미지에서 지배적 색상을 추출합니다 (HEX).

    Pillow를 사용하여 이미지를 축소한 뒤 가장 많이 등장하는 색상을
    반환합니다. 프론트엔드 글로우 효과에 사용됩니다.

    Args:
        image_data: 이미지 바이트 데이터.
        resize_to: 분석 전 이미지 축소 크기.

    Returns:
        ``"#RRGGBB"`` 형태의 HEX 색상 문자열, 또는 None.
    """
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(image_data))
        img = img.convert("RGB")
        img = img.resize((resize_to, resize_to), Image.Resampling.LANCZOS)

        pixels = list(img.getdata())
        if not pixels:
            return None

        # 어두운/밝은 극단값 제외
        filtered = [
            (r, g, b)
            for r, g, b in pixels
            if (r + g + b) > 60 and (r + g + b) < 700
        ]
        if not filtered:
            filtered = pixels

        # 가장 빈도 높은 색상 영역 (양자화)
        color_buckets: dict[tuple[int, int, int], int] = {}
        for r, g, b in filtered:
            # 16단계로 양자화
            qr = (r // 16) * 16
            qg = (g // 16) * 16
            qb = (b // 16) * 16
            key = (qr, qg, qb)
            color_buckets[key] = color_buckets.get(key, 0) + 1

        if not color_buckets:
            return None

        dominant = max(color_buckets, key=color_buckets.get)  # type: ignore
        return "#{:02x}{:02x}{:02x}".format(*dominant)

    except ImportError:
        # Pillow 미설치 시
        return None
    except Exception:
        return None


def get_cover_with_color(
    record: dict[str, Any],
) -> dict[str, Any]:
    """트랙의 커버 바이트와 지배적 색상을 함께 반환합니다.

    Returns:
        ``{"has_cover": bool, "mime": str|None, "dominant_color": str|None, "data": bytes|None}``
    """
    dominant_color = resolve_dominant_color(record, compute_if_missing=True)
    data, mime = get_cover_bytes(record)

    return {
        "has_cover": data is not None,
        "mime": mime,
        "dominant_color": dominant_color,
        "data": data,
    }


def make_thumbnail(
    image_data: bytes,
    size: int = 200,
    mime: str = "image/jpeg",
    *,
    cache_key: str | None = None,
) -> tuple[bytes, str]:
    """이미지를 지정 크기로 축소합니다.

    ``cache_key``가 있으면 디스크에 썸네일을 캐시합니다.

    Args:
        image_data: 원본 이미지 바이트.
        size: 최대 가로/세로 크기.
        mime: 원본 MIME 타입.
        cache_key: 캐시 키 (보통 track_id).

    Returns:
        ``(thumbnail_bytes, mime_type)``
    """
    settings = get_settings()
    cache_dir = os.path.join(settings.PROJECT_ROOT, ".thumb_cache")
    cached_path: str | None = None
    if cache_key:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in cache_key)
        cached_path = os.path.join(cache_dir, f"{safe}_{size}.jpg")
        if os.path.isfile(cached_path):
            try:
                with open(cached_path, "rb") as f:
                    return f.read(), "image/jpeg"
            except OSError:
                pass

    try:
        from PIL import Image

        img = Image.open(io.BytesIO(image_data))
        img = img.convert("RGB")
        img.thumbnail((size, size), Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=82, optimize=True)
        out = buf.getvalue()

        if cached_path:
            try:
                os.makedirs(cache_dir, exist_ok=True)
                tmp = cached_path + ".tmp"
                with open(tmp, "wb") as f:
                    f.write(out)
                os.replace(tmp, cached_path)
            except OSError:
                pass

        return out, "image/jpeg"
    except ImportError:
        return image_data, mime
    except Exception:
        return image_data, mime
