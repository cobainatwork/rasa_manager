"""
JWT 設定與編解碼集中化。

集中 SECRET_KEY、ALGORITHM、過期時間常數及 encode/decode 函式，
避免 auth.py 與 dependencies.py 兩處重複維護。
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from jose import JWTError, jwt

_jwt_secret_raw = os.environ.get("JWT_SECRET", "")
_UNSAFE_JWT_DEFAULTS = {"", "changeme-please-set-env", "change_me", "secret"}
if _jwt_secret_raw in _UNSAFE_JWT_DEFAULTS:
    raise RuntimeError(
        "JWT_SECRET 環境變數未設定或使用不安全的預設值，服務拒絕啟動。"
        "請設定至少 64 字元的隨機字串（建議使用：openssl rand -hex 32）。"
    )

SECRET_KEY: str = _jwt_secret_raw
ALGORITHM: str = "HS256"
ACCESS_MINUTES: int = int(os.environ.get("JWT_ACCESS_MINUTES", "15"))
REFRESH_DAYS: int = int(os.environ.get("JWT_REFRESH_DAYS", "7"))


def _encode(payload: dict[str, Any], expires_delta: timedelta) -> str:
    data = payload.copy()
    now = datetime.now(timezone.utc)
    data["exp"] = now + expires_delta
    data["iat"] = now
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(payload: dict[str, Any]) -> str:
    """建立 Access Token，過期時間 ACCESS_MINUTES 分鐘。"""
    return _encode(payload, timedelta(minutes=ACCESS_MINUTES))


def create_refresh_token(payload: dict[str, Any]) -> str:
    """建立 Refresh Token，過期時間 REFRESH_DAYS 天。"""
    return _encode(payload, timedelta(days=REFRESH_DAYS))


def decode_token(token: str) -> dict[str, Any]:
    """
    解碼 JWT Token。失敗（含過期）時拋 HTTPException 401。
    呼叫端若需自行處理 JWTError，請改用 jose.jwt.decode。
    """
    try:
        payload: dict[str, Any] = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Token 無效或已過期"},
        )


def decode_token_raw(token: str) -> dict[str, Any]:
    """
    解碼 JWT Token，失敗時拋 jose.JWTError。
    供需要自行處理錯誤類型的呼叫端使用（例如 logout 容錯流程）。
    """
    payload: dict[str, Any] = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return payload
