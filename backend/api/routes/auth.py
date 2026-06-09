"""
認證路由：登入、登出、Token 刷新、當前使用者資訊。
Cookie 設定：HttpOnly, SameSite=Strict
Access Token 15 分鐘 / Refresh Token 7 天（含 jti）
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import structlog
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from jose import JWTError
from sqlalchemy.orm import Session

from api.database.models import User
from api.database.session import get_db
from api.dependencies import (
    _get_redis,
    check_login_rate_limit,
    clear_login_attempts,
    get_current_user,
    record_login_failure,
)
from api.schemas import LoginRequest
from api.security.jwt import (
    ACCESS_MINUTES,
    ALGORITHM,
    REFRESH_DAYS,
    SECRET_KEY,
    create_access_token,
    create_refresh_token,
    decode_token_raw,
)
from api.security.password import pwd_context as _pwd_context
from jose import jwt as _jose_jwt

# 對外 re-export，保持向下相容（既有測試 / 工具仍可從本模組 import）。
__all__ = [
    "router",
    "ACCESS_MINUTES",
    "REFRESH_DAYS",
    "SECRET_KEY",
    "ALGORITHM",
    "_create_token",
    "_issue_tokens",
]


def _create_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    """
    向下相容包裝：等同 api.security.jwt._encode。
    新程式請直接呼叫 create_access_token / create_refresh_token。
    """
    payload = data.copy()
    now = datetime.now(timezone.utc)
    payload["exp"] = now + expires_delta
    payload["iat"] = now
    return _jose_jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

IS_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="strict",
        secure=IS_SECURE,
        max_age=ACCESS_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="strict",
        secure=IS_SECURE,
        max_age=REFRESH_DAYS * 86400,
        path="/api/v1/auth/refresh",
    )


def _issue_tokens(user: User) -> tuple[str, str]:
    jti_access = str(uuid.uuid4())
    jti_refresh = str(uuid.uuid4())
    # 注意：依規格 §五.1，is_superadmin 等角色資訊不寫入 JWT payload，
    # 一律以 DB 為唯一權威來源（角色變動時舊 token 不會殘留過期權限）。
    access_token = create_access_token(
        {
            "sub": str(user.id),
            "jti": jti_access,
        },
    )
    refresh_token = create_refresh_token(
        {"sub": str(user.id), "jti": jti_refresh, "type": "refresh"},
    )
    return access_token, refresh_token


@router.post("/login")
def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    check_login_rate_limit(request, body.username)

    user = (
        db.query(User)
        .filter(User.username == body.username, User.is_active.is_(True))
        .first()
    )

    if not user or not _pwd_context.verify(body.password, user.password_hash):
        record_login_failure(request, body.username)
        logger.warning("login_failed", username=body.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "帳號或密碼錯誤"},
        )

    clear_login_attempts(request, body.username)
    logger.info("login_success", user_id=str(user.id), username=user.username)
    access_token, refresh_token = _issue_tokens(user)
    _set_auth_cookies(response, access_token, refresh_token)

    return {
        "success": True,
        "data": {
            "id": str(user.id),
            "username": user.username,
            "is_superadmin": user.is_superadmin,
        },
        "message": "登入成功",
    }


@router.post("/logout")
def logout(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    current_user: User = Depends(get_current_user),
) -> dict:  # type: ignore[type-arg]
    if refresh_token:
        try:
            payload: dict = decode_token_raw(refresh_token)  # type: ignore[type-arg]
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                r = _get_redis()
                remaining = int(exp - datetime.now(timezone.utc).timestamp())
                if remaining > 0:
                    r.setex(f"revoked_refresh:{jti}", remaining, "1")
        except JWTError:
            pass

    logger.info("logout", user_id=str(current_user.id))
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/v1/auth/refresh")
    return {"success": True, "message": "登出成功"}


@router.post("/refresh")
def refresh_token_endpoint(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "無 Refresh Token"},
        )

    try:
        payload: dict = decode_token_raw(refresh_token)  # type: ignore[type-arg]
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Refresh Token 無效"},
        )

    jti = payload.get("jti")
    token_type = payload.get("type")
    if token_type != "refresh" or not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Token 類型錯誤"},
        )

    r = _get_redis()
    if r.get(f"revoked_refresh:{jti}"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Refresh Token 已失效"},
        )

    # 將舊 refresh token 加入黑名單（Rotation）
    exp = payload.get("exp", 0)
    remaining = int(exp - datetime.now(timezone.utc).timestamp())
    if remaining > 0:
        r.setex(f"revoked_refresh:{jti}", remaining, "1")

    user_id_str: Optional[str] = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Token 格式錯誤"},
        )

    user = (
        db.query(User)
        .filter(User.id == uuid.UUID(user_id_str), User.is_active.is_(True))
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "使用者不存在"},
        )

    access_token, new_refresh_token = _issue_tokens(user)
    _set_auth_cookies(response, access_token, new_refresh_token)
    return {"success": True, "message": "Token 已更新"}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)) -> dict:  # type: ignore[type-arg]
    return {
        "success": True,
        "data": {
            "id": str(current_user.id),
            "username": current_user.username,
            "is_superadmin": current_user.is_superadmin,
            "is_active": current_user.is_active,
            "created_at": current_user.created_at.isoformat()
            if current_user.created_at
            else None,
        },
    }
