# WaveMash — 코드베이스 전체 요약

> 이 문서를 Gemini 새 대화에 붙여넣으면 프로젝트의 전체 구조를 이해할 수 있습니다.

---

## 1. 프로젝트 개요

**WaveMash**는 고품질 WAV 음악 파일을 수집·관리하는 웹 앱입니다.
YouTube/Spotify URL을 입력하면 WAV(무손실)로 다운로드 → 메타데이터(BPM, Key, 장르 등) 자동 태깅 → 아름다운 UI로 음반 컬렉션을 관리합니다.

**핵심 철학**: "음반을 소유하듯이 느끼는 감정" — 고화질 앨범 커버, LP 바이닐 호버 효과, 글래스모피즘 UI

---

## 2. 기술 스택

| 계층 | 기술 | 위치 |
|---|---|---|
| **백엔드** | FastAPI · Python 3.14 · Uvicorn | `server/` |
| **프론트엔드** | Next.js 16 · React 19 · TypeScript · Tailwind CSS v4 · Framer Motion · Shadcn/ui | `web/` |
| **데이터** | SQLite (`track_index.db`) + JSON (`archive.json`) 하이브리드 | 프로젝트 루트 |
| **미디어** | WAV 파일 + sidecar cover.jpg | `~/OneDrive/Desktop/WAV/` |
| **배포** | Docker Compose (backend + frontend) | `docker-compose.yml` |

---

## 3. 디렉토리 구조

```
WAVMASH/
├── server/                    # FastAPI 백엔드
│   ├── main.py                # 앱 진입점, CORS, 라우터 등록, lifespan
│   ├── config.py              # pydantic-settings 기반 환경설정
│   ├── database.py            # ArchiveCache (thread-safe), 플레이리스트 I/O
│   ├── models.py              # Pydantic v2 모델 15개
│   ├── routers/
│   │   ├── tracks.py          # GET/PUT/DELETE /api/tracks (필터/정렬/페이지네이션)
│   │   ├── download.py        # POST /api/download + SSE 진행률 스트림
│   │   ├── playlists.py       # 플레이리스트 CRUD + 자동 장르 분류
│   │   ├── covers.py          # 앨범 커버 이미지 서빙 + 색상 추출
│   │   ├── library.py         # 통계/아티스트/앨범/장르/검색
│   │   └── stream.py          # WAV 오디오 스트리밍 (Range 206 지원)
│   ├── services/
│   │   ├── download_service.py # 백그라운드 다운로드 Job 관리
│   │   ├── metadata_service.py # BPM/Key 보강 체인
│   │   ├── playlist_service.py # 자동 분류 엔진
│   │   └── cover_service.py    # Pillow 색상 추출 + 커버 탐색
│   └── requirements.txt
│
├── web/                       # Next.js 프론트엔드
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx     # 루트 레이아웃 (다크 모드, SEO, Pretendard 폰트)
│   │   │   ├── globals.css    # 디자인 시스템 (다크 테마, LP 바이닐, 글래스모피즘)
│   │   │   ├── page.tsx       # 대시보드 (통계, 빠른 다운로드, 최근 추가)
│   │   │   ├── library/page.tsx    # 라이브러리 (그리드/리스트, 검색, 필터, 정렬)
│   │   │   ├── track/[id]/page.tsx # 트랙 상세 (대형 커버, 메타데이터)
│   │   │   ├── download/page.tsx   # 다운로드 페이지
│   │   │   └── playlists/page.tsx  # 플레이리스트 관리
│   │   ├── components/
│   │   │   ├── Navbar.tsx     # 글래스모피즘 네비게이션 (골드 로고)
│   │   │   ├── TrackCard.tsx  # LP 바이닐 호버 효과 앨범 카드
│   │   │   ├── MiniPlayer.tsx # 하단 오디오 플레이어
│   │   │   ├── DownloadForm.tsx # SSE 다운로드 폼
│   │   │   ├── LibraryStats.tsx # 애니메이션 통계 카드
│   │   │   └── ui/            # Shadcn/ui 기본 컴포넌트
│   │   ├── contexts/
│   │   │   └── PlayerContext.tsx # 오디오 플레이어 상태 관리
│   │   └── lib/
│   │       ├── api.ts         # WaveMashAPI 클래스 (fetch 래퍼)
│   │       ├── types.ts       # TypeScript 인터페이스
│   │       └── utils.ts       # cn() 유틸리티
│   ├── package.json
│   └── tailwind.config.ts
│
├── library.py                 # 핵심 라이브러리 엔진 (1800+ lines)
├── pipeline.py                # YouTube 다운로드 (yt-dlp → FFmpeg → WAV)
├── spotify_pipeline.py        # Spotify 다운로드 (spotdl → WAV)
├── spotify_metadata.py        # Spotify API 클라이언트
├── track_metadata.py          # BPM/Key 해석 체인
├── archive.json               # 트랙 레코드 배열 (source of truth)
├── playlists.json             # 플레이리스트 데이터
├── track_index.db             # SQLite 검색 캐시
├── .env                       # API 키 (Spotify, GetSongBPM)
├── docker-compose.yml         # 멀티 서비스 Docker 설정
└── start_wavemash.bat         # 원클릭 서버 실행 스크립트
```

---

## 4. 데이터 모델

### archive.json (Source of Truth)
```json
[
  {
    "title": "Champagne",
    "artist": "Austin Farwell",
    "primary_artist": "Austin Farwell",
    "album": "Champagne",
    "platform": "Spotify",
    "format": "WAV",
    "genre": "Classical",
    "year": "2025",
    "url": "https://open.spotify.com/track/...",
    "track_id": "uuid-string",
    "external_id": "spotify_track_id",
    "thumbnail_url": "",
    "analysis": {
      "bpm": 152,
      "key": "D Major",
      "camelot": "10B",
      "duration": 180.7,
      "key_confidence": 0.43
    }
  }
]
```

### playlists.json
```json
{
  "playlists": {
    "Dance": ["track_id_1", "track_id_2"],
    "Classical": ["track_id_3"]
  },
  "activity": { "Dance": 1780364611.0 }
}
```

### SQLite track_index.db (검색 캐시)
```sql
CREATE TABLE tracks (
    track_id TEXT PRIMARY KEY,
    artist TEXT, title TEXT,
    bpm INTEGER, key TEXT, camelot_key TEXT,
    energy_level INTEGER, bpm_source TEXT,
    local_path TEXT, url TEXT, platform TEXT
);
```

### WAV 파일 경로 규칙
```
~/OneDrive/Desktop/WAV/{Artist}/{Album}/{BPM} - {Key} - {Title}.wav
예: WAV/Dom Dolla/No Room.../129 - Gm - No Room For A Saint.wav
```

### 앨범 커버
- WAV 파일과 같은 폴더에 `cover.jpg` (sidecar)
- 또는 WAV ID3 APIC 태그에 임베딩

---

## 5. 백엔드 API (30개 엔드포인트)

### 트랙 (`/api/tracks`)
| Method | Path | 설명 |
|---|---|---|
| GET | `/api/tracks` | 전체 트랙 목록 (필터/정렬/페이지네이션) |
| GET | `/api/tracks/{id}` | 단일 트랙 상세 |
| PUT | `/api/tracks/{id}` | 메타데이터 수정 |
| DELETE | `/api/tracks/{id}` | 트랙 삭제 |

**응답 형식 (paginated)**:
```json
{
  "items": [Track, ...],
  "total": 41,
  "page": 1,
  "page_size": 50,
  "total_pages": 1
}
```

### 다운로드 (`/api/download`)
| Method | Path | 설명 |
|---|---|---|
| POST | `/api/download` | 다운로드 시작 → `{ job_id }` |
| GET | `/api/download/status/{job_id}` | SSE 진행률 스트림 |

**다운로드 파이프라인**:
1. URL 입력 → `is_spotify_url()` 판단
2. YouTube: `yt-dlp` → m4a → FFmpeg → WAV
3. Spotify: `spotdl` → MP3 → FFmpeg → WAV
4. WAV 태그 쓰기 (mutagen) → `archive.json` upsert → SQLite sync

### 라이브러리 (`/api/library`)
| Method | Path | 설명 |
|---|---|---|
| GET | `/api/library/stats` | 통계 (총 트랙/아티스트/앨범, 장르 분포, 최근 추가) |
| GET | `/api/library/artists` | 아티스트 목록 + 트랙 수 |
| GET | `/api/library/albums` | 앨범 목록 |
| GET | `/api/library/genres` | 장르 목록 |
| GET | `/api/library/search?q=...` | 전체 텍스트 검색 |

### 플레이리스트 (`/api/playlists`)
| Method | Path | 설명 |
|---|---|---|
| GET | `/api/playlists` | 전체 플레이리스트 |
| POST | `/api/playlists` | 생성 |
| PUT | `/api/playlists/{name}` | 수정 |
| DELETE | `/api/playlists/{name}` | 삭제 |
| POST | `/api/playlists/{name}/tracks` | 트랙 추가 |
| POST | `/api/playlists/auto-parse` | 장르별 자동 분류 |

### 미디어
| Method | Path | 설명 |
|---|---|---|
| GET | `/api/covers/{id}` | 앨범 커버 이미지 |
| GET | `/api/covers/{id}/color` | 커버 dominant color (글로우 효과용) |
| GET | `/api/stream/{id}` | WAV 오디오 스트리밍 (Range 206) |

---

## 6. 프론트엔드 컴포넌트 구조

### 디자인 시스템
- **다크 모드 퍼스트**: 배경 `#0a0a14` (딥 네이비), 텍스트 `#f9fafb`
- **골드 악센트**: `#d4a853` (버튼, 로고, 활성 링크)
- **글래스모피즘**: `backdrop-blur(20px)` + 반투명 카드
- **LP 바이닐 효과**: 호버 시 레코드판 슬라이드 아웃 애니메이션
- **커버 글로우**: 앨범 커버 dominant color로 배경 발광 효과
- **폰트**: Pretendard (한국어), Inter (영문)

### API 클라이언트 (`lib/api.ts`)
```typescript
class WaveMashAPI {
  baseUrl = "http://localhost:8000"
  getTracks(params) → Track[]     // items 배열 추출
  getTrack(id) → Track
  startDownload(url) → { job_id }
  subscribeDownload(jobId, cb)    // SSE EventSource
  getStats() → LibraryStats
  getCoverUrl(id) → string
  getStreamUrl(id) → string
  getPlaylists() → Playlist[]
  // ... 20+ 메서드
}
```

### 상태 관리 (`PlayerContext`)
- HTML5 `Audio` 객체 래핑
- 재생/일시정지/탐색/볼륨/큐 관리
- `usePlayer()` 훅으로 전역 접근

---

## 7. 핵심 Python 모듈 (루트)

### library.py (1800+ lines)
- `load_archive_json()` / `save_archive_json()` — archive.json 읽기/쓰기
- `TrackIndexDB` — SQLite 검색 캐시 (upsert, query, schema migration)
- `plan_track_path()` — `WAV/{Artist}/{Album}/{BPM} - {Key} - {Title}.wav` 경로 생성
- `write_wav_tags()` — mutagen으로 WAV ID3 태그 쓰기
- `resolve_cover_bytes()` — 커버 아트 바이너리 추출
- `normalize_artist_meta()` — 아티스트명 정규화 (feat. 분리 등)
- `camelot_from_key()` — 음악 키 → 카멜롯 키 변환

### pipeline.py
- `process_url_sync(url, progress_callback)` — YouTube URL → WAV 변환
- 내부: `yt-dlp` → m4a → `ffmpeg` → WAV

### spotify_pipeline.py
- `process_spotify_url_sync(url, progress_callback)` — Spotify → WAV
- `is_spotify_url(url)` — URL 판별
- `list_spotify_songs(url)` — 앨범/플레이리스트 곡 목록

### track_metadata.py
- `enrich_record_metadata(record)` — BPM/Key 보강 체인
- 우선순위: MIK DB → WAV 태그 → GetSongBPM API → 로컬 분석

---

## 8. 환경 변수 (.env)

```bash
SPOTIFY_CLIENT_ID=c2960a7cd7d046bbb375984508bbb850
SPOTIFY_CLIENT_SECRET=900d777e5b5f490281c1fc93f3b624a7
GETSONGBPM_API_KEY=1c6feb1a363ffd989ba48a0f8edaaf1c
```

---

## 9. 실행 방법

```bash
# 원클릭 실행 (바탕화면 바로가기 또는)
start_wavemash.bat

# 수동 실행
# 터미널 1: 백엔드
python -m uvicorn server.main:app --reload --host 0.0.0.0 --port 8000

# 터미널 2: 프론트엔드
cd web && npm run dev

# 브라우저: http://localhost:3000
```

---

## 10. 현재 상태 및 알려진 이슈

### 작동 확인됨 ✅
- 대시보드 통계/최근 추가 (41곡, 32 아티스트, 35 앨범)
- 라이브러리 그리드 (앨범 커버 고화질 표시)
- 트랙 상세 페이지 (BPM/Key/장르/커버)
- 모든 API 엔드포인트 200 OK
- Next.js 프로덕션 빌드 통과

### 향후 개선점
- `library.py`에서 `mix_data` 관련 코드 수동 제거 필요 (17곳)
- `track_index.db`의 `mix_data` 컬럼 DROP (SQLite 테이블 재생성)
- Docker용 `Dockerfile.backend`, `web/Dockerfile` 작성
- 프론트엔드 다운로드 SSE 실제 테스트
- 검색/필터 성능 최적화 (대규모 라이브러리)
- 오디오 재생 (MiniPlayer) 실제 WAV 스트리밍 테스트
