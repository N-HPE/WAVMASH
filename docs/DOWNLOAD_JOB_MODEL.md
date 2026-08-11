"""
# 다운로드 Job 모델 설계

현재 구현(`server/services/download_service.py`)은 **인메모리 Job 맵**입니다.

- 서버 재시작 → 진행 중 SSE/상태 소멸
- 동시 다운로드 상한 2
- TTL 약 1시간

YouTube 검색·대량 수집으로 전환하면 영속 Job이 필요합니다.
스키마 초안은 `server/services/download_job_model.py` 에 있습니다.

## 목표 상태 머신

```
pending → queued → downloading → converting → metadata → completed
                         ↘ failed
                         ↘ cancelled (cancel_requested)
```

Stages: `listing` | `searching` | `downloading` | `converting` | `cover` | `metadata` | `done`

## 소스 타입

| source | 용도 |
|--------|------|
| `youtube_url` | 기본 (앞으로의 주 경로) |
| `youtube_search` | 검색어 → 후보 선택 → 다운로드 (예정) |
| `spotify_url` | Spotify→WaveMash 마이그레이션 기간만 |

## 영속 권장

- SQLite `download_jobs.db` (`WAVMASH_JOBS_DB`)
- TTL 72시간, 동시 실행 2
- SSE는 `job_id`로 재구독
- `cancel_requested` 플래그로 워커 안전 중단

## 다음 구현 단계

1. Job 테이블/JSONL 저장
2. `POST /api/download` 가 DB에 persist
3. `GET /api/download/jobs` 가 재시작 후에도 목록 유지
4. YouTube search 엔드포인트가 `source=youtube_search` Job 생성
"""
