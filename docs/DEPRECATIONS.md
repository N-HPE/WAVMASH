"""
# DJ 레거시 · Spotify 마이그레이션 deprecate 계획

## 제품 방향

WaveMash는 **로컬 WAV 컬렉션 + YouTube 검색/다운로드 + BPM/Key 정리** 앱입니다.

- Spotify 구독은 해지 예정
- Spotify sync는 **이미 모아 둔 플리/메타를 WaveMash로 옮기는 임시 툴**
- 스트리밍·신규 수집은 WaveMash 로컬 파일 + YouTube

## Spotify (마이그레이션 전용)

| 단계 | 내용 |
|------|------|
| 지금 | sync로 플리 → archive/playlists 이전, `source=spotify` 메타 유지 |
| 이전 완료 | `WAVMASH_AUTO_SYNC_ON_START=false`, sync UI 숨김/경고 |
| 이후 | `spotify_pipeline` / sync API를 optional extras로 분리 또는 제거 |

문서: `docs/SPOTIFY_SYNC_ARCHITECTURE.md` (마이그레이션 툴로 재정의)

## DJ 레거시 (`mix_data`, 데스크톱 덱)

과거 PySide DJ 믹스/큐 기능에서 웹 컬렉션으로 이전 중입니다.
`cleanup_dj.py`에 삭제 후보가 정리되어 있습니다.

| 항목 | 조치 |
|------|------|
| `archive` 레코드의 `mix_data` | 읽기 무시, 신규 기록 중단, 이후 export 시 strip |
| `desktop_app/` 분석·덱 UI | 유지하되 웹이 SoT; 미사용 모듈은 cleanup 스크립트로 제거 |
| Mixed In Key 경로 | Windows 선택적 BPM 소스 — Mac에서는 GetSongBPM/로컬 분석 |

## 스키마 노트

- `Track.bpm`: API **number** (0 = 미상). JSON archive에는 문자열로 남아 있을 수 있음 → `_record_to_track`에서 coerce
- Playlist `source`: `local` \| `spotify`(마이그레이션 유래)
- 기기 동기: `docs/LIBRARY_SYNC.md`
"""
