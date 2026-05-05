"""
對話測試路由：轉發訊息至 Rasa REST webhook，回傳 RAG 結果陣列。
sender 格式：{agent_id}_{user_id}
"""
from __future__ import annotations

import uuid
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.database.models import User
from api.database.session import get_db
from api.dependencies import get_current_user, require_agent_access
from api.schemas import ChatRequest

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/agents/{agent_id}/chat", tags=["chat"])


@router.post("/test")
def test_chat(
    agent_id: uuid.UUID,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    agent, _ = require_agent_access(agent_id, current_user, db)

    if not agent.rasa_rest_url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "UNPROCESSABLE", "message": "此 Agent 未設定 Rasa REST URL"},
        )

    sender = f"{agent_id}_{current_user.id}"
    # rasa_rest_url 儲存完整 webhook URL（例如 http://host:5555/webhooks/myio/webhook）
    # 直接使用，不再拼接路徑
    webhook_url = str(agent.rasa_rest_url).rstrip("/")

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                webhook_url,
                json={"sender": sender, "message": body.message},
            )
            resp.raise_for_status()
            raw = resp.json()
            # Rasa 兩種 response 格式（依 OpenAPI pro.yaml 規格）：
            # 1. REST channel (/webhooks/rest/webhook)        → 頂層陣列 [{recipient_id, text, ...}]
            # 2. Custom channel (/webhooks/{name}/webhook)   → {"messages": [...], "conversation_id": ..., ...}
            if isinstance(raw, list):
                messages: list[Any] = raw
            elif isinstance(raw, dict):
                messages = raw.get("messages") or []
            else:
                messages = []
    except httpx.TimeoutException as exc:
        logger.warning(
            "rasa_timeout",
            agent_id=str(agent_id),
            url=webhook_url,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"code": "TIMEOUT", "message": "Rasa 服務回應逾時"},
        )
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "rasa_http_error",
            agent_id=str(agent_id),
            url=webhook_url,
            status_code=exc.response.status_code,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "BAD_GATEWAY",
                "message": f"Rasa 服務回應 HTTP {exc.response.status_code}",
            },
        )
    except httpx.RequestError as exc:
        # 連線錯誤：避免將完整 exc 訊息（可能含內網 URL）洩漏給呼叫端
        logger.warning(
            "rasa_request_error",
            agent_id=str(agent_id),
            url=webhook_url,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "BAD_GATEWAY", "message": "Rasa 服務連線失敗"},
        )

    return {"success": True, "data": messages}
