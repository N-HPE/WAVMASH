#!/usr/bin/env bash
# WaveMash — macOS / Linux starter (backend + frontend)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  echo "[WaveMash] .venv 없음 — scripts/setup_dev.sh 를 먼저 실행하세요."
  exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate

if [[ ! -f .env ]]; then
  echo "[WaveMash] .env 없음 — .env.example 을 복사해 API 키를 넣어 주세요."
  exit 1
fi

if [[ ! -d web/node_modules ]]; then
  echo "[WaveMash] web 의존성 설치 중..."
  npm --prefix web install
fi

echo ""
echo "  ============================================"
echo "          W A V E M A S H   S E R V E R"
echo "  ============================================"
echo "  Backend  http://127.0.0.1:8000"
echo "  Frontend http://localhost:3000"
echo "  (Ctrl+C 로 종료)"
echo ""

# Open browser after a short delay (macOS)
if [[ "$(uname -s)" == "Darwin" ]]; then
  (sleep 4 && open "http://localhost:3000") &
fi

npx --prefix web concurrently -n "FastAPI,Next.js" -c "cyan,green" \
  "python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload" \
  "npm --prefix web run dev"
