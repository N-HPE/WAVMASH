#!/usr/bin/env bash
# WaveMash — one-time (or occasional) dev setup for macOS / Linux
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> WaveMash setup ($ROOT)"

# ── Prerequisites check ──────────────────────────────────────────────
need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing: $1"
    echo "  macOS: brew install $2"
    exit 1
  fi
}

need python3 "python@3.12"
need node "node"
need npm "node"
need ffmpeg "ffmpeg"

PYTHON="$(command -v python3)"
echo "Using Python: $($PYTHON --version)"
echo "Using Node:   $(node --version)"
echo "Using ffmpeg: $(ffmpeg -version | head -n1)"

# ── Virtualenv ───────────────────────────────────────────────────────
if [[ ! -d .venv ]]; then
  echo "==> Creating .venv"
  "$PYTHON" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip

echo "==> Installing Python packages"
pip install -r requirements.txt
pip install -r server/requirements.txt
# spotdl pulls an old fastapi; install without deps then satisfy runtime needs
pip install --no-deps spotdl || true
pip install spotipy yt-music-api ytmusicapi syncedlyrics rapidfuzz rich || true

echo "==> Installing frontend packages"
npm --prefix web install

# ── Env file ─────────────────────────────────────────────────────────
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "==> Created .env from .env.example — API 키를 채워 주세요."
else
  echo "==> .env already exists (kept)"
fi

# Default WAV folder on Mac
WAV_DEFAULT="$HOME/Music/WaveMash"
mkdir -p "$WAV_DEFAULT"
if ! grep -q '^WAVMASH_WAV_ROOT=' .env 2>/dev/null; then
  echo "" >> .env
  echo "WAVMASH_WAV_ROOT=$WAV_DEFAULT" >> .env
  echo "==> Set WAVMASH_WAV_ROOT=$WAV_DEFAULT"
fi

echo ""
echo "Setup complete."
echo "  1. Edit .env  → Spotify / GetSongBPM keys"
echo "  2. Run        → ./start_wavemash.sh"
echo "  3. Open       → http://localhost:3000"
echo ""
echo "Windows PC와 같은 라이브러리를 쓰려면 WAV 폴더를 클라우드 동기화하고"
echo "양쪽 .env 의 WAVMASH_WAV_ROOT 를 그 경로로 맞추세요."
echo "archive.json / playlists.json 은 기기 로컬이므로 필요하면 수동 복사하세요."
