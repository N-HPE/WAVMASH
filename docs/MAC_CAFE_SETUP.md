# 카페 맥북에서 WaveMash 쓰기

집에서 개발해 둔 걸 맥북으로 이어서 쓰는 최소 가이드입니다.

**방향:** Spotify는 이전용 임시 툴이고, 이후에는 YouTube 검색·다운로드 + 로컬 스트리밍이 주 경로입니다.
기기 간 목록 맞추기: [`LIBRARY_SYNC.md`](LIBRARY_SYNC.md)

---

## 터미널에 뜬 “다운로드 N곡”은 뭐야?

서버 시작 시 Spotify **마이그레이션 자동 동기화**가 돌 수 있습니다 (`WAVMASH_AUTO_SYNC_ON_START`).

```
Spotify auto-sync starting (1 playlists)...
Spotify auto-sync done — ok=1 downloaded=21 errors=0
```

이전이 끝났으면 `.env`에 `WAVMASH_AUTO_SYNC_ON_START=false` 로 끄세요.

| 표시 | 의미 |
|------|------|
| `downloaded=N` | 이 PC에 없어서 새로 받은 곡 |
| `metadata enrich: No module named 'mik_metadata'` | Mac에서 MIK 없음 → GetSongBPM/로컬 분석 폴백 (정상) |

---

## 맥북에 필요한 것

### 1) 도구
```bash
brew install python@3.12 node ffmpeg git
```

### 2) 코드
```bash
git clone https://github.com/N-HPE/WAVMASH.git
cd WAVMASH
git pull   # 이미 클론했다면
chmod +x start_wavemash.sh scripts/setup_dev.sh
./scripts/setup_dev.sh
```

### 3) `.env`
- 마이그레이션 중: Spotify Client ID/Secret
- 이후: YouTube만 쓰면 Spotify 키 불필요 (BPM 폴백용 GetSongBPM은 선택)
- `WAVMASH_WAV_ROOT` = 클라우드 동기 WAV 폴더 권장

### 4) WAV + 목록 동기

**A. WAV만 클라우드 동기 + 메타 export/import (권장)**  
1. Drive/OneDrive/Syncthing으로 WAV 폴더 공유  
2. PC에서 `GET /api/library/export` → 맥에서 `POST /api/library/import`  
자세한 내용: [`LIBRARY_SYNC.md`](LIBRARY_SYNC.md)

**B. Spotify 마이그레이션으로 누락 곡만 받기**  
- 아직 Spotify 구독이 있을 때만  
- 서버 켜면 등록 플리의 빠진 곡 자동 다운로드

### 5) 실행
```bash
./start_wavemash.sh
```
http://localhost:3000

---

## 집에서 맥 가기 전

1. [ ] `git push`
2. [ ] (마이그레이션 중) `spotify_sync.json` 등록됨
3. [ ] 또는 `library/export` JSON을 맥으로 복사
4. [ ] `.env` / WAV 경로 준비

---

## 문제 생기면

| 증상 | 조치 |
|------|------|
| Spotify 다운로드 실패 | 키/인터넷, 또는 이미 이전이면 auto-sync 끄기 |
| 목록만 안 맞음 | `/api/library/export` → `/import` |
| UI 안 됨 | `cd web && npm install && npm run dev` |
