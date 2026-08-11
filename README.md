# WaveMash

YouTube에서 곡을 검색·다운로드하고, BPM·Key·커버까지 정리하는 **로컬 음악 보관소**.
로컬 WAV를 스트리밍하고, (일시적으로) Spotify에 모아 둔 플리를 WaveMash로 이전할 수 있습니다.

| Layer    | Stack                            | Directory  |
|----------|----------------------------------|------------|
| Backend  | FastAPI · Python 3.11+           | `server/`  |
| Frontend | Next.js 16 · React 19 · Tailwind | `web/`     |
| Data     | SQLite index · JSON archive      | project root + WAV 폴더 |

**제품 방향:** Spotify 구독 해지 → YouTube 수집이 주 경로. Spotify sync는 **마이그레이션 임시 툴**.

---

## 필요한 API 키

| 키 | 필수? | 발급 | 용도 |
|----|-------|------|------|
| (없음 — YouTube) | YouTube URL 다운로드만이면 키 불필요 | yt-dlp | 검색/다운로드 (검색 UI는 추가 예정) |
| `SPOTIFY_CLIENT_ID` / `SECRET` | 마이그레이션 중에만 | [Dashboard](https://developer.spotify.com/dashboard) | 기존 플리 → WaveMash 이전 |
| `GETSONGBPM_API_KEY` | 선택 | [GetSongBPM](https://getsongbpm.com/api) | BPM/Key 폴백 |

**MCP는 앱 실행에 필요 없습니다.**

---

## macOS 셋업 (MacBook)

카페/외출용: [`docs/MAC_CAFE_SETUP.md`](docs/MAC_CAFE_SETUP.md)  
기기 간 목록 동기: [`docs/LIBRARY_SYNC.md`](docs/LIBRARY_SYNC.md)

```bash
brew install python@3.12 node ffmpeg git
git clone https://github.com/N-HPE/Wavemash.git
cd Wavemash
chmod +x start_wavemash.sh scripts/setup_dev.sh
./scripts/setup_dev.sh
open -e .env
./start_wavemash.sh
```

브라우저: [http://localhost:3000](http://localhost:3000)  
API 문서: [http://localhost:8000/docs](http://localhost:8000/docs)

### Windows PC와 라이브러리 공유

- WAV 폴더를 OneDrive / iCloud / Syncthing 등으로 동기화
- 양쪽 `.env`의 `WAVMASH_WAV_ROOT`를 그 폴더로 지정
- **목록 동기:** `GET /api/library/export` → 다른 기기에서 `POST /api/library/import` ([문서](docs/LIBRARY_SYNC.md))
- Spotify 이전 중이면 `spotify_sync.json`이 git에 포함되어 맥/윈도우에 같이 따라갑니다. 이전 후 `WAVMASH_AUTO_SYNC_ON_START=false`

---

## Windows 셋업

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r server\requirements.txt
pip install --no-deps spotdl
cd web && npm install && cd ..
copy .env.example .env
start_wavemash.bat
```

---

## Quick Start (공통)

```bash
cp .env.example .env
pip install -r server/requirements.txt
pip install -r requirements.txt
cd web && npm install && npm run dev
uvicorn server.main:app --reload
```

백엔드 단위 테스트:

```bash
pip install pytest
pytest tests/ -q
```

---

## 프로젝트 구조

```
WAVMASH/
├── server/              # FastAPI backend
├── web/                 # Next.js frontend
├── tests/               # 단위 테스트
├── docs/                # 동기·마이그레이션·Job 설계
├── library.py           # 트랙 라이브러리
├── pipeline.py          # YouTube 다운로드
├── spotify_pipeline.py  # Spotify 이전(마이그레이션)
├── start_wavemash.sh
└── scripts/setup_dev.sh
```

---

## API (로컬)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/tracks` | 트랙 목록 |
| POST | `/api/tracks/enrich-batch` | BPM/Key 일괄 보강 |
| POST | `/api/download` | URL 다운로드 시작 |
| GET | `/api/download/status/{job_id}` | SSE 진행 |
| GET | `/api/playlists` | 플레이리스트 |
| POST | `/api/playlists/auto-parse` | 장르 자동 분류 |
| GET | `/api/library/stats` | 통계 |
| GET | `/api/library/export` | 메타 번들 export |
| POST | `/api/library/import` | 메타 번들 import |
| GET | `/api/library/sync/status` | 기기 메타 해시 |
| GET | `/api/stream/{id}` | WAV 스트리밍 |
| * | `/api/spotify-sync/*` | Spotify→WaveMash 이전 (임시) |
| GET | `/health` | 헬스체크 |

추가 문서: [`docs/DEPRECATIONS.md`](docs/DEPRECATIONS.md) · [`docs/DOWNLOAD_JOB_MODEL.md`](docs/DOWNLOAD_JOB_MODEL.md)
