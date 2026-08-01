# 카페 맥북에서 WaveMash 쓰기

집에서 개발해 둔 걸 맥북으로 이어서 쓰는 최소 가이드입니다.

---

## 터미널에 뜬 “다운로드 21곡”은 뭐야?

정상입니다. **에러가 아닙니다.**

서버를 켜면 Spotify **자동 동기화**가 돌아갑니다.

```
Spotify auto-sync starting (1 playlists)...
Spotify auto-sync done — ok=1 downloaded=21 errors=0
```

의미:

| 표시 | 의미 |
|------|------|
| `1 playlists` | 등록된 Spotify 동기화 플리 1개 |
| `downloaded=21` | 이 PC에 없어서 **새로 받은 곡 21개** |
| `errors=0` | 동기화 자체는 성공 |
| `metadata enrich: No module named 'mik_metadata'` | Mixed In Key 연동 모듈이 없어 BPM을 MIK DB에서 못 읽음 → **GetSongBPM/로컬 분석으로 대체** (다운로드는 됨) |

카페 맥에서도 서버를 켜면, Spotify에만 있고 맥에 없는 곡을 같은 방식으로 자동으로 받습니다.

---

## 맥북에 필요한 것 (GitHub 말고)

### 1) 필수 도구
```bash
brew install python@3.12 node ffmpeg git
```

### 2) 코드
```bash
git clone https://github.com/N-HPE/Wavemash.git
cd Wavemash
git pull   # 이미 클론했다면
chmod +x start_wavemash.sh scripts/setup_dev.sh
./scripts/setup_dev.sh
```

### 3) API 키 (`.env`)
집에서 쓰는 `.env`를 **USB / 암호 메모 / 1Password** 등으로 맥에 복사.

꼭 필요한 것:

- `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET`
- (같게) `SPOTIPY_CLIENT_ID` / `SPOTIPY_CLIENT_SECRET`
- (선택) `GETSONGBPM_API_KEY`

```bash
cp .env.example .env
# 키 붙여넣기
open -e .env
```

### 4) WAV 경로
카페에서 옵션 둘 중 하나:

**A. Spotify 동기화만 쓰기 (가장 간단)**  
- 맥에 빈 로컬 폴더만 두고  
- `WAVMASH_WAV_ROOT=~/Music/WaveMash`  
- 서버 켜면 등록된 Spotify 플리가 **빠진 곡을 자동 다운로드**

**B. Google Drive Mirror로 WAV 공유**  
- Drive for desktop **Mirror**  
- `.env`에 Drive 안 WAV 경로 지정  
- (목록까지 맞추려면 `archive.json` / `playlists.json`도 같이 맞춰야 함 — 나중에)

카페 Wi‑Fi만으로도 **A**면 충분합니다.

### 5) 실행
```bash
./start_wavemash.sh
```
브라우저: http://localhost:3000

---

## 집에서 맥 가기 전에 체크

1. [ ] GitHub `main` 최신 (`git push` 해둠)
2. [ ] Spotify 동기화 플리 등록됨 (`spotify_sync.json`이 repo에 있음)
3. [ ] `.env` 키를 맥에 옮길 방법 준비
4. [ ] (선택) Google Drive Mirror 켜 두기 — 필수는 아님

---

## 카페에서 안 해도 되는 것

- Mixed In Key (Windows 전용에 가까움) → 없어도 BPM은 다른 경로로 채움  
- 프로젝트 폴더 통째 Drive 업로드 → **하지 말 것** (venv/node 깨짐)  
- MCP → WaveMash 실행과 무관  

---

## 문제 생기면

| 증상 | 조치 |
|------|------|
| Spotify 다운로드 실패 | `.env` 키 / 인터넷 확인 |
| 서버만 되고 UI 안 됨 | `cd web && npm install && npm run dev` |
| WAV 경로 이상 | `.env`의 `WAVMASH_WAV_ROOT` |
| 자동동기화 끄기 | `.env`에 `WAVMASH_AUTO_SYNC_ON_START=false` |

더 자세한 공통 설명은 루트 `README.md` 참고.
