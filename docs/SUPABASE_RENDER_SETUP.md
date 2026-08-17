# WAVMASH — Supabase & Render 설정 및 배포 완벽 가이드

> **PIXMASH**와 **동일한 계정(Supabase & Render)**을 사용하면서 두 프로그램의 데이터와 서버를 완벽히 분리(Isolation)하여 운영하는 가이드입니다.

---

## 📌 아키텍처 개요 (Account Sharing & Isolation)

| 서비스 | PIXMASH 리소스 | WAVMASH 리소스 | 격리 방식 |
| :--- | :--- | :--- | :--- |
| **Supabase** | `pixmash` 프로젝트 / DB | `wavmash` 프로젝트 / DB | **독립 프로젝트 분리** (DB, 스토리지 버킷, API Key 100% 분리) |
| **Render** | `pixmash-*` Web Services | `wavmash-backend`, `wavmash-frontend` | **독립 Web Service / Blueprint 분리** (환경변수, 포트, 도메인 분리) |

---

## 1단계: Supabase 데이터베이스 설정

### 1. 새 프로젝트 생성 (동일 계정 내)
1. 기존에 PIXMASH를 사용 중인 **[Supabase 대시보드](https://supabase.com/dashboard)**에 로그인합니다.
2. 상단의 **`New Project`** 버튼을 클릭합니다.
3. 프로젝트 정보를 입력합니다:
   - **Name**: `wavmash` (또는 `wavmash-db`)
   - **Database Password**: 안전한 비밀번호 입력 후 메모
   - **Region**: 서울(`ap-northeast-2`) 또는 PIXMASH와 동일한 리전 권장
   - **Pricing Plan**: Free (무료 티어는 계정당 최대 2개 프로젝트 무료 제공)
4. **`Create new project`**를 클릭하고 프로비저닝이 완료될 때까지 약 1~2분 대기합니다.

### 2. 스키마 생성 (`schema.sql` 실행)
1. 생성된 `wavmash` 프로젝트의 좌측 메뉴에서 **`SQL Editor`**로 이동합니다.
2. **`New Query`**를 클릭합니다.
3. 프로젝트 내 [supabase/schema.sql](file:///c:/Users/junno/OneDrive/Desktop/WAVMASH/supabase/schema.sql) 파일의 전체 내용을 복사하여 붙여넣습니다.
4. **`Run`** (또는 `Ctrl+Enter`) 버튼을 클릭하여 실행합니다.
   - `tracks`, `playlists`, `playlist_tracks`, `spotify_sync_configs` 테이블 및 검색 인덱스, `wavmash-covers` 스토리지 버킷이 자동 생성됩니다.

### 3. API 키 확인
1. 좌측 메뉴 하단의 **`Project Settings`** (톱니바퀴) > **`API`**로 이동합니다.
2. 다음 두 가지 정보를 복사합니다:
   - **Project URL**: `https://<project-ref>.supabase.co`
   - **Project API Keys**:
     - `anon` `public`: 일반 접근용 키
     - `service_role` `secret`: 백엔드/마이그레이션용 마스터 키

---

## 2단계: 로컬 데이터 Supabase로 마이그레이션

기존 로컬에 있던 `archive.json`, `playlists.json`, `spotify_sync.json` 데이터를 새 Supabase DB로 업로드합니다.

1. 로컬의 `.env` 파일에 복사한 Supabase 키를 입력합니다:
   ```env
   SUPABASE_URL=https://your-project-ref.supabase.co
   SUPABASE_KEY=eyJhbGciOi... (anon key)
   SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOi... (service_role key)
   ```
2. 마이그레이션 스크립트를 실행합니다:
   ```bash
   python scripts/migrate_to_supabase.py
   ```
3. 완료 메시지가 출력되면 Supabase 대시보드의 **`Table Editor`**에서 트랙과 플레이리스트가 정상적으로 들어갔는지 확인합니다.

---

## 3단계: Render 서버 배포

### 방법 A: Render Blueprint 1-클릭 자동 배포 (강력 권장)
1. 기존에 PIXMASH를 배포한 **[Render 대시보드](https://dashboard.render.com)**에 로그인합니다.
2. 상단 우측의 **`New +`** 버튼을 누르고 **`Blueprint`**를 선택합니다.
3. **WAVMASH GitHub 레포지토리** (`N-HPE/Wavemash`)를 연결합니다.
4. Render가 루트 경로의 `render.yaml`을 감지하여 `wavmash-backend`와 `wavmash-frontend` 2개의 서비스를 자동 구성합니다.
5. 화면에 표시되는 환경변수 입력란에 Supabase 및 Spotify 키를 입력합니다:
   - `SUPABASE_URL`: `https://<your-project-ref>.supabase.co`
   - `SUPABASE_KEY`: Supabase `anon` 키
   - `SUPABASE_SERVICE_ROLE_KEY`: Supabase `service_role` 키
   - `SPOTIFY_CLIENT_ID`: Spotify Developer Client ID
   - `SPOTIFY_CLIENT_SECRET`: Spotify Developer Client Secret
6. **`Apply`**를 클릭하면 백엔드와 프론트엔드가 자동으로 빌드 및 배포됩니다.

---

### 방법 B: Render 수동 서비스 생성 (개별 생성 시)

Blueprint 대신 수동으로 생성하려면:

#### 1. 백엔드 서비스 (`wavmash-backend`)
- **New +** > **Web Service** 선택
- GitHub 레포 연결: `N-HPE/Wavemash`
- **Name**: `wavmash-backend`
- **Language / Runtime**: `Docker`
- **Dockerfile Path**: `docker/Dockerfile.backend`
- **Health Check Path**: `/health`
- **Environment Variables**:
  - `SUPABASE_URL`: Supabase Project URL
  - `SUPABASE_KEY`: Supabase Anon Key
  - `SUPABASE_SERVICE_ROLE_KEY`: Supabase Service Role Key
  - `SPOTIFY_CLIENT_ID`: Spotify Client ID
  - `SPOTIFY_CLIENT_SECRET`: Spotify Client Secret
  - `CORS_ORIGINS`: 프론트엔드 Render URL (배포 후 수정 가능)

#### 2. 프론트엔드 서비스 (`wavmash-frontend`)
- **New +** > **Web Service** 선택
- GitHub 레포 연결: `N-HPE/Wavemash`
- **Root Directory**: `web`
- **Language / Runtime**: `Docker` (또는 Node: Build `npm run build`, Start `npm run start`)
- **Dockerfile Path**: `Dockerfile`
- **Environment Variables**:
  - `NEXT_PUBLIC_API_URL`: 백엔드 Render URL (예: `https://wavmash-backend.onrender.com`)

---

## 4단계: 동작 및 격리 검증

1. **격리 확인**:
   - Supabase: PIXMASH 프로젝트 대시보드와 WAVMASH 프로젝트 대시보드가 분리되어 서로의 테이블이 노출되지 않습니다.
   - Render: PIXMASH 서비스와 WAVMASH 서비스가 별도의 Web Service로 작동하며 독립된 환경변수와 로그를 갖습니다.
2. **기능 확인**:
   - 프론트엔드 웹 URL 접속 → 라이브러리 및 플레이리스트 로딩 확인.
   - 곡 다운로드 / 메타데이터 수정 시 Supabase DB에 실시간 반영되는지 확인.
