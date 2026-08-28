# AGENTS.md

WaveMash — 로컬 음악 보관소. YouTube/SoundCloud/Spotify 링크로 WAV를 받아 BPM·Key·커버를 정리합니다.

- Backend: FastAPI (`server/`), Python. 코어 다운로드/분석 엔진은 저장소 루트의 `pipeline.py`, `spotify_pipeline.py`, `library.py` 등이 공유합니다.
- Frontend: Next.js 16 / React 19 (`web/`).
- Data: SQLite 인덱스(`track_index.db`) + JSON 아카이브(`archive.json`, `playlists.json`, `spotify_sync.json`) + 디스크의 WAV 파일. 별도 DB 서버는 없습니다.

표준 셋업/실행 명령은 `README.md`, `scripts/setup_dev.sh`, `start_wavemash.sh`, `web/package.json`에 이미 문서화되어 있으니 그쪽을 참고하세요.

## 배포 파이프라인 (자동)

기능/수정 작업이 끝나면 **커밋·푸시 여부를 묻지 말고** `main`에 커밋 후 `git push origin main` 한다.
`main` 푸시 → **Vercel**(프론트 https://wavmash.vercel.app) + **Render**(백엔드 https://wavmash-backend.onrender.com, `render.yaml` autoDeploy)가 자동 배포한다.
시크릿·`.cache`·임시 파일은 커밋하지 않는다. 자세한 에이전트 규칙은 `.cursor/rules/auto-deploy.mdc`.

## Cursor Cloud specific instructions

이 환경은 업데이트 스크립트가 의존성(Python `.venv` + `web/node_modules`)을 이미 설치한 상태로 시작합니다. 아래는 서비스를 안전하게 띄우기 위한 비자명한 주의사항입니다.

### 서비스 실행 (두 개 모두 필요)

- Backend (`:8000`): `.venv` 활성화 후 `python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload`
- Frontend (`:3000`): `npm --prefix web run dev`
- 두 개를 한 번에: `./start_wavemash.sh` (`.venv`와 `.env`가 있어야 실행됨. macOS 전용 `open` 호출은 Linux에선 조용히 무시됨). Health: `GET http://127.0.0.1:8000/health`, API 문서: `/docs`.

### 필수 주의사항 (gotchas)

- `.env`가 없으면 `start_wavemash.sh`가 즉시 종료됩니다. gitignore 대상이라 스냅샷에만 존재하므로, 없으면 `cp .env.example .env` 후 `WAVMASH_WAV_ROOT`를 유효한 디렉터리(예: `$HOME/Music/WaveMash`)로 설정하세요. 이 값이 없으면 `paths.default_wav_root()`의 OS 기본 경로가 쓰입니다.
- **Spotify 자동 동기화**: `WAVMASH_AUTO_SYNC_ON_START`가 기본 `true`라, Spotify 크리덴셜이 없으면 서버 시작 시 등록된 플리 동기화가 실패하고 `spotify_sync.json`(git 추적 파일)을 런타임에 수정합니다. 커밋 전 `git checkout -- spotify_sync.json`으로 되돌리세요. 시작 시 동기화를 끄려면 `.env`에 `WAVMASH_AUTO_SYNC_ON_START=false`.
- **다운로드 소스**: YouTube 미디어 다운로드는 데이터센터 IP에 대한 봇 차단으로 실제 파일 단계에서 HTTP 403이 납니다(메타데이터 조회는 됨). 크리덴셜 없이 엔드투엔드로 다운로드/분석을 검증하려면 **SoundCloud** 링크를 쓰세요(yt-dlp 경유, 잘 동작). Spotify 경로는 `SPOTIFY_CLIENT_ID`/`SPOTIFY_CLIENT_SECRET`가 필요합니다.
- `spotdl`은 `--no-deps`로 설치됩니다(구버전 fastapi를 끌어와 서버가 깨지는 것 방지). `pip check`에 spotdl 관련 버전 충돌 경고가 뜨는 건 정상이며 웹 앱 동작에는 영향 없습니다.
- `desktop_app` (PySide6 Qt)는 선택 사항이며 디스플레이가 필요합니다. `desktop_app/__main__`이 존재하지 않는 `desktop_app/app` 모듈을 임포트해 현재 `python -m desktop_app`는 ImportError가 납니다. 웹 제품 테스트에는 불필요합니다.
- `docker-compose.yml`은 존재하지 않는 `docker/Dockerfile.backend`, `web/Dockerfile`을 참조해 그대로는 빌드되지 않습니다. 로컬 개발은 위의 uvicorn + next dev를 쓰세요.

### Lint / Build (frontend)

- Lint: `npm --prefix web run lint` — ESLint는 정상 동작하지만 현재 코드에 사전 존재하는 error/warning이 있습니다(환경 문제 아님).
- Build: `npm --prefix web run build` — 성공, TypeScript 통과. (Turbopack 빌드는 lint error로 실패하지 않음.)
- Backend는 빌드 단계가 없고 자동화 테스트 스위트도 정의돼 있지 않습니다.
