"""Load project ``.env`` into ``os.environ`` (no extra dependency)."""

from __future__ import annotations

import os

from paths import PROJECT_DIR

ENV_PATH = os.path.join(PROJECT_DIR, ".env")
_loaded = False


def load_dotenv(path: str | None = None, *, override: bool = False) -> None:
    global _loaded
    env_path = path or ENV_PATH
    if not os.path.isfile(env_path):
        return
    with open(env_path, encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.lower().startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if not key:
                continue
            if override or key not in os.environ:
                os.environ[key] = value
    _loaded = True


def ensure_env_loaded() -> None:
    if not _loaded:
        load_dotenv()
