# Spotify 동기화 구조

## 원칙

1. **Spotify 플레이리스트 ID 목록** = 소스 오브 트루스 (원하는 곡 집합)
2. **로컬 WAV 파일 존재** = 실제 보유 여부
3. **완료 조건** = `missing_ids == []` (목록 조회 성공 ≠ 동기화 완료)

## 흐름

```
Spotify playlist URL
        │
        ▼
list_spotify_songs()  →  desired_ids[]
        │
        ▼
로컬 아카이브에서 file 있는 곡 매칭 (url / external_id / track_id)
        │
        ├── present  → playlists.json 멤버십
        └── missing  → spotdl 개별 URL 다운로드 → archive upsert → 재매핑
        │
        ▼
spotify_sync.json 상태
  track_count   = Spotify 곡 수
  local_count   = 로컬 파일 있는 곡
  missing_count / missing_ids
  synced_track_ids = 로컬에 있는 Spotify ID만 (삭제 동기화 기준)
  status = completed | partial | syncing | error
```

## 과거에 8곡만 보이던 이유

1. 다운로드는 됐지만 **ArchiveCache를 갱신하지 않아** 플리 매핑이 옛 캐시(8곡)만 봄
2. `synced_track_ids`에 Spotify 전체 ID를 넣어 UI가 “31곡 완료”처럼 보임
3. spotdl 일괄 다운로드가 일부 곡을 빠뜨림 (현재 3곡 잔여)

## 수정 요약

- 다운로드 후 archive upsert + cache reload
- 매칭에 `external_id` 포함
- 개별 트랙 URL 다운로드 + 누락 재시도
- UI: 플리 클릭 → 트랙 리스트, Spotify URL, 누락 수, 다시 동기화
