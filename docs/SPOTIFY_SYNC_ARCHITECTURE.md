# Spotify 동기화 = WaveMash 마이그레이션 툴

> **중요:** Spotify 구독 해지 후 YouTube 검색·다운로드가 주 경로입니다.
> 이 기능은 Spotify에 모아 둔 플리/곡을 **WaveMash로 완전히 이전**하기 위한 **임시 툴**입니다.
> 이전이 끝나면 `WAVMASH_AUTO_SYNC_ON_START=false` 로 끄고, 신규 수집은 YouTube만 사용하세요.

## 원칙

1. **Spotify 플레이리스트 ID 목록** = 이전할 곡 집합 (마이그레이션 소스)
2. **로컬 WAV 파일 존재** = WaveMash 보유 여부
3. **완료 조건** = `missing_ids == []` (목록 조회 성공 ≠ 이전 완료)
4. 이전 완료 후 SoT는 **`archive.json` + `playlists.json` + WAV** (기기 동기: `docs/LIBRARY_SYNC.md`)

## 흐름

```
Spotify playlist URL
        │
        ▼
list_spotify_songs()  →  desired_ids[]
        │
        ▼
로컬 아카이브 매칭 (external_id / url / track_id / title+artist)
  → server.services.spotify_match.map_spotify_songs_to_local
        │
        ├── present  → playlists.json 멤버십
        └── missing  → spotdl 다운로드 → archive upsert → 재매핑
        │
        ▼
spotify_sync.json 상태
  track_count / local_count / missing_ids
  synced_track_ids = 로컬에 파일 있는 Spotify ID만 (삭제 동기화 기준)
  status = completed | partial | syncing | error
```

## 단위 테스트

`tests/test_spotify_match.py` — 네트워크 없이 매칭·missing·synced_track_ids 검증.

## 과거에 8곡만 보이던 이유

1. 다운로드 후 ArchiveCache 미갱신
2. `synced_track_ids`에 Spotify 전체 ID를 넣어 UI가 완료처럼 보임
3. spotdl 일괄 누락

## 수정 요약

- 다운로드 후 archive upsert + cache reload
- 매칭에 `external_id` 포함 + 순수 매칭 모듈 분리
- 개별 트랙 URL 다운로드 + 누락 재시도
- UI: 플리 클릭 → 트랙 리스트, 누락 수, 다시 동기화
