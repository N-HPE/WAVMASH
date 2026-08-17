# WaveMash

YouTube / Spotify 링크로 WAV를 받고, BPM·Key·커버까지 정리하는 로컬 음악 보관소.

| Layer    | Stack                            | Directory  |
|----------|----------------------------------|------------|
| Backend  | FastAPI · Python 3.11+           | `server/`  |
| Frontend | Next.js 16 · React 19 · Tailwind | `web/`     |
| Data     | SQLite index · JSON archive      | project root + WAV 폴더 |

---

## 필요한 API 키

| 키 | 필수? | 발급 | 용도 |
|----|-------|------|------|
| `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` | **예** (Spotify 다운로드 시) | [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) | 플리/트랙 메타데이터 |
| `SPOTIPY_CLIENT_ID` / `SPOTIPY_CLIENT_SECRET` | 권장 (위와 동일 값) | 동일 | spotipy 호환 |
| `GETSONGBPM_API_KEY` | 선택 | [GetSongBPM API](https://getsongbpm.com/api) | BPM/Key 폴백 |

**MCP는 앱 실행에 필요 없습니다.** Cursor MCP는 IDE 보조 도구일 뿐 WaveMash 런타임과 무관합니다.

---

## macOS 셋업 (MacBook)

카페/외출용 짧은 가이드: [`docs/MAC_CAFE_SETUP.md`](docs/MAC_CAFE_SETUP.md)

```bash
# 1) 도구 설치
brew install python@3.12 node ffmpeg git

# 2) 클론
git clone https://github.com/N-HPE/WAVMASH.git
cd WAVMASH

# 3) 의존성 + .env + WAV 폴더
chmod +x start_wavemash.sh scripts/setup_dev.sh
./scripts/setup_dev.sh

# 4) .env 에 Spotify / GetSongBPM 키 입력
open -e .env

# 5) 실행
./start_wavemash.sh
```

브라우저: [http://localhost:3000](http://localhost:3000)  
API 문서: [http://localhost:8000/docs](http://localhost:8000/docs)

### Windows PC와 라이브러리 공유

- WAV 파일 폴더를 OneDrive / iCloud / Syncthing 등으로 동기화
- 양쪽 `.env`의 `WAVMASH_WAV_ROOT`를 그 폴더로 지정
- `archive.json`, `playlists.json`은 git에 안 올라가므로, 같은 목록이 필요하면 파일을 수동 복사하거나 클라우드 동기 폴더에 두고 심볼릭 링크
- **`spotify_sync.json`은 git에 포함**됩니다. Spotify 동기화로 등록한 플리 URL이 맥/윈도우에 같이 따라가고, 서버 시작 시(`WAVMASH_AUTO_SYNC_ON_START=true`) 이 기기에 없는 곡을 자동으로 받습니다.

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
:: .env 편집 후
start_wavemash.bat
```

또는 수동:

```bat
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
cd web && npm run dev
```

---

## Quick Start (공통)

```bash
cp .env.example .env   # 키 입력 + WAVMASH_WAV_ROOT 설정
pip install -r server/requirements.txt
pip install -r requirements.txt
cd web && npm install && npm run dev   # :3000
# 다른 터미널
uvicorn server.main:app --reload       # :8000
```

---

## 프로젝트 구조

```
WAVMASH/
├── server/              # FastAPI backend
├── web/                 # Next.js frontend
├── library.py           # 트랙 라이브러리
├── pipeline.py          # YouTube 다운로드
├── spotify_pipeline.py  # Spotify 다운로드
├── start_wavemash.sh    # macOS/Linux 실행
├── start_wavemash.bat   # Windows 실행
└── scripts/setup_dev.sh # macOS/Linux 최초 셋업
```

---

## Cursor / Mac 개발 팁

1. Mac에서 이 repo를 클론한 뒤 Cursor로 폴더 열기
2. `.env`는 **기기마다 따로** 두고 Git에 올리지 말 것
3. Windows에만 있는 경로(`OneDrive\Desktop\WAV`)는 Mac에서 통하지 않으므로 반드시 `WAVMASH_WAV_ROOT` 설정
4. `ffmpeg`는 Homebrew로 설치 (`brew install ffmpeg`) — 다운로드/변환에 필요

---

## API (로컬)

| Method | Path               | Description        |
|--------|--------------------|--------------------|
| GET    | `/api/tracks`      | 트랙 목록          |
| POST   | `/api/download`    | URL 다운로드 시작  |
| GET    | `/api/download/status/{job_id}` | SSE 진행 상황 |
| GET    | `/api/playlists`   | 플레이리스트       |
| GET    | `/api/stream/{id}` | WAV 스트리밍       |
| GET    | `/health`          | 헬스체크           |
