"""WaveMash Auth Dependencies."""

from __future__ import annotations

import jwt
from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from server.config import get_settings

security = HTTPBearer(auto_error=False)

def get_optional_user(credentials: HTTPAuthorizationCredentials | None = Security(security)) -> str | None:
    """JWT 토큰에서 선택적으로 user_id를 추출합니다."""
    if not credentials:
        return None
    
    token = credentials.credentials
    settings = get_settings()
    
    # SUPABASE_JWT_SECRET 없으면 서비스 롤 키로 대체 시도
    secret = settings.SUPABASE_JWT_SECRET or settings.SUPABASE_SERVICE_ROLE_KEY
    if not secret:
        return None

    try:
        # Supabase JWT는 보통 HS256 알고리즘 사용 (aud 옵션 끄거나 알맞게 설정 필요)
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_aud": False}
        )
        user_id = payload.get("sub")
        if not user_id:
            return None
        return user_id
    except jwt.PyJWTError:
        return None

def get_current_user(credentials: HTTPAuthorizationCredentials | None = Security(security)) -> str:
    """JWT 토큰에서 user_id를 추출합니다. 없으면 401 에러."""
    user_id = get_optional_user(credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="인증되지 않은 요청입니다. 토큰이 없거나 유효하지 않습니다.")
    return user_id
