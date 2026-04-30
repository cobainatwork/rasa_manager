"""
Superadmin 專用 Agent 工具：測試連線、驗證腳本存在。

注意：
- 兩個端點均 Superadmin 限定（與 §4.1 Agent 配置路由權限一致）。
- Agent 不存在時回傳 404，與 §4.1 行為一致。
- validate-script 對 ingest_script_path 進行路徑遍歷防護（拒絕 `..`、非絕對路徑、
  非規範化路徑），避免任何相對路徑或跳脫攻擊（CLAUDE.md §五.3）。
"""
from __future__ import annotations

import os
import time
import uuid

import httpx
import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.database.models import User
from api.database.session import get_db
from api.dependencies import _get_agent_or_404, get_current_superadmin

logger = structlog.get_logger()

router = APIRouter(tags=["agent-admin"])


def _is_safe_absolute_path(path: str) -> bool:
    """檢查路徑為絕對路徑、不含 `..`，且 normalize 後與原值等效。"""
    if not path:
        return False
    if ".." in path.replace("\\", "/").split("/"):
        return False
    if not os.path.isabs(path):
        return False
    normalized = os.path.normpath(path)
    # Windows 對 normpath 會做斜線轉換，這裡僅排除 traversal 後路徑改變的情境
    if os.path.normpath(path.replace("\\", "/")) != os.path.normpath(
        normalized.replace("\\", "/")
    ):
        return False
    return True


@router.post("/api/v1/agents/{agent_id}/test-connection")
def test_connection(
    agent_id: uuid.UUID,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    agent = _get_agent_or_404(agent_id, db)

    url = str(agent.rasa_rest_url) if agent.rasa_rest_url else None
    if not url:
        return {
            "success": True,
            "data": {
                "ok": False,
                "status_code": None,
                "latency_ms": None,
                "error": "未設定 Rasa Webhook URL",
            },
        }

    start = time.monotonic()
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url)
        latency = int((time.monotonic() - start) * 1000)
        # 4xx 視為可達但 endpoint 行為異常（仍為 ok=false 由前端決定顯示）；
        # 2xx/3xx 為連線成功；5xx 視為服務錯誤。
        ok = 200 <= resp.status_code < 400
        return {
            "success": True,
            "data": {
                "ok": ok,
                "status_code": resp.status_code,
                "latency_ms": latency,
                "error": None if ok else f"HTTP {resp.status_code}",
            },
        }
    except httpx.TimeoutException as exc:
        logger.warning(
            "agent_test_connection_timeout",
            agent_id=str(agent_id),
            url=url,
            error=str(exc),
        )
        return {
            "success": True,
            "data": {
                "ok": False,
                "status_code": None,
                "latency_ms": None,
                "error": "連線逾時",
            },
        }
    except httpx.RequestError as exc:
        logger.warning(
            "agent_test_connection_error",
            agent_id=str(agent_id),
            url=url,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return {
            "success": True,
            "data": {
                "ok": False,
                "status_code": None,
                "latency_ms": None,
                "error": "連線失敗",
            },
        }


@router.post("/api/v1/agents/{agent_id}/validate-script")
def validate_script(
    agent_id: uuid.UUID,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    agent = _get_agent_or_404(agent_id, db)

    path = str(agent.ingest_script_path) if agent.ingest_script_path else None
    if not path:
        return {
            "success": True,
            "data": {
                "exists": False,
                "executable": False,
                "size_bytes": 0,
                "error": "未設定腳本路徑",
            },
        }

    if not _is_safe_absolute_path(path):
        logger.warning(
            "agent_validate_script_unsafe_path",
            agent_id=str(agent_id),
            path=path,
        )
        return {
            "success": True,
            "data": {
                "exists": False,
                "executable": False,
                "size_bytes": 0,
                "error": "腳本路徑不合法（必須為絕對路徑且不含 `..`）",
            },
        }

    if not os.path.isfile(path):
        return {
            "success": True,
            "data": {
                "exists": False,
                "executable": False,
                "size_bytes": 0,
                "error": "腳本檔案不存在",
            },
        }

    try:
        size = os.path.getsize(path)
        readable = os.access(path, os.R_OK)
        return {
            "success": True,
            "data": {
                "exists": True,
                "executable": readable,
                "size_bytes": size,
                "error": None,
            },
        }
    except OSError as exc:
        logger.warning(
            "agent_validate_script_error",
            agent_id=str(agent_id),
            path=path,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return {
            "success": True,
            "data": {
                "exists": True,
                "executable": False,
                "size_bytes": 0,
                "error": "讀取腳本失敗",
            },
        }
