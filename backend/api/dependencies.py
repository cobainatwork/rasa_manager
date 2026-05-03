"""
JWT 認證、RBAC 權限檢查、登入頻率限制。
"""
from __future__ import annotations

import os
import uuid
from typing import Optional

import redis as redis_lib
from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from api.database.models import Agent, User, UserAgentRole
from api.database.session import get_db
from api.security.jwt import decode_token

REDIS_URL: str = os.environ.get("REDIS_URL", "redis://redis:6379/0")

# I12：module-level singleton，避免每請求都新建 connection pool
_redis_client: Optional[redis_lib.Redis] = None  # type: ignore[type-arg]


def _get_redis() -> redis_lib.Redis:  # type: ignore[type-arg]
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_lib.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


def _verify_access_token(token: str) -> dict:  # type: ignore[type-arg]
    return decode_token(token)


def get_current_user(
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db),
) -> User:
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "未提供認證 Token"},
        )
    payload = _verify_access_token(access_token)
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
            detail={"code": "UNAUTHORIZED", "message": "使用者不存在或已停用"},
        )
    return user


def get_current_superadmin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "需要 Superadmin 權限"},
        )
    return current_user


def _get_agent_or_404(agent_id: uuid.UUID, db: Session) -> Agent:
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Agent 不存在"},
        )
    return agent


def require_agent_access(
    agent_id: uuid.UUID,
    current_user: User,
    db: Session,
) -> tuple[Agent, Optional[str]]:
    """回傳 (agent, role)，Superadmin 的 role 為 None。"""
    agent = _get_agent_or_404(agent_id, db)
    if current_user.is_superadmin:
        return agent, None
    uar = (
        db.query(UserAgentRole)
        .filter(
            UserAgentRole.user_id == current_user.id,
            UserAgentRole.agent_id == agent_id,
        )
        .first()
    )
    if not uar:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "您無此 Agent 的存取權限"},
        )
    return agent, str(uar.role)


def require_reviewer_or_superadmin(
    agent_id: uuid.UUID,
    current_user: User,
    db: Session,
) -> tuple[Agent, Optional[str]]:
    agent, role = require_agent_access(agent_id, current_user, db)
    if not current_user.is_superadmin and role != "reviewer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "需要 Reviewer 或 Superadmin 權限"},
        )
    return agent, role


# ── 登入頻率限制 ──────────────────────────────────────────────────────────

def _get_client_ip(request: Request) -> str:
    """取得真實客戶端 IP，優先使用 X-Forwarded-For（取第一個非私有 IP）。"""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_login_rate_limit(request: Request, username: str) -> None:
    """同 IP + 帳號 5 次失敗後封鎖 15 分鐘。"""
    ip = _get_client_ip(request)
    r = _get_redis()
    key = f"login_attempts:{ip}:{username}"
    attempts = r.get(key)
    if attempts and int(str(attempts)) >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "RATE_LIMIT", "message": "登入嘗試次數過多，請 15 分鐘後再試"},
        )


def record_login_failure(request: Request, username: str) -> None:
    ip = _get_client_ip(request)
    r = _get_redis()
    key = f"login_attempts:{ip}:{username}"
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, 900)  # 15 分鐘
    pipe.execute()


def clear_login_attempts(request: Request, username: str) -> None:
    ip = _get_client_ip(request)
    r = _get_redis()
    r.delete(f"login_attempts:{ip}:{username}")
