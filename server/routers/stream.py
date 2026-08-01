"""오디오 스트리밍 API 라우터 — WAV 파일 스트리밍 (Range 요청 지원)."""

from __future__ import annotations

import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from server.database import get_archive_cache

router = APIRouter(prefix="/stream", tags=["스트리밍"])


@router.get("/{track_id}")
async def stream_audio(track_id: str) -> FileResponse:
    """WAV 오디오 파일을 스트리밍합니다.

    Starlette FileResponse를 사용하여 HTTP Range 헤더 (206 Partial Content),
    시킹(seeking), 클라이언트 소켓 연결 해제 및 스트리밍 버퍼링을 네이티브로 처리합니다.
    """
    cache = get_archive_cache()
    record = cache.get_record(track_id)
    if not record:
        raise HTTPException(status_code=404, detail="트랙을 찾을 수 없습니다.")

    file_path = str(record.get("path") or record.get("local_path") or "")
    if not file_path or not os.path.isfile(file_path):
        raise HTTPException(
            status_code=404,
            detail="WAV 파일을 찾을 수 없습니다. 파일이 삭제되었거나 경로가 변경되었을 수 있습니다.",
        )

    return FileResponse(
        path=file_path,
        media_type="audio/wav",
        filename=os.path.basename(file_path),
    )

