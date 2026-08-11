"""
# 기기 간 라이브러리 동기 (archive / playlists)

WAV 파일은 OneDrive · Google Drive Mirror · Syncthing 등으로 맞추고,
**목록 메타데이터**(`archive.json`, `playlists.json`)는 아래 API로 맞춥니다.

Spotify 자동 동기화는 **구독 해지 전 마이그레이션용**입니다.
이전이 끝나면 YouTube 검색·다운로드만으로 수집합니다.

## API

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/library/sync/status` | 해시·트랙/플리 수·mtime |
| GET | `/api/library/export` | 번들 JSON 내보내기 |
| POST | `/api/library/import` | 번들 반영 (`merge` \| `replace`) |

### Export 예시

```bash
curl -o wavemash-library.json "http://127.0.0.1:8000/api/library/export"
# 마이그레이션 설정도 포함
curl -o wavemash-library.json \
  "http://127.0.0.1:8000/api/library/export?include_spotify_sync=true"
```

### Import 예시

```bash
curl -X POST "http://127.0.0.1:8000/api/library/import" \
  -H "Content-Type: application/json" \
  -d @wavemash-library.json
```

요청 본문에 `mode`를 넣을 수 있습니다.

- **merge** (기본): `track_id` / 플리 이름 기준 병합. 들어오는 메타가 우선하되, incoming 경로가 비어 있으면 기존 로컬 WAV 경로를 유지합니다.
- **replace**: archive 또는 playlists 영역을 통째로 교체합니다.

```json
{
  "mode": "merge",
  "import_archive": true,
  "import_playlists": true,
  "archive": [ ... ],
  "playlists": {
    "playlists": { "My Mix": ["track-id-1"] },
    "activity": {},
    "meta": {}
  }
}
```

## 권장 워크플로 (Windows ↔ Mac)

1. 양쪽 `.env`의 `WAVMASH_WAV_ROOT`를 **같은 클라우드 폴더**로 지정
2. PC A에서 export → USB/클라우드로 JSON 복사
3. PC B에서 import (`merge`)
4. 해시가 다르면 `GET /api/library/sync/status`로 확인

## Spotify 이후

이전 완료 후:

- `WAVMASH_AUTO_SYNC_ON_START=false`
- Spotify sync UI는 마이그레이션 전용으로만 사용
- 신규 수집은 YouTube URL / (예정) 검색 다운로드
"""
