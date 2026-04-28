"""
對話測試路由：轉發訊息至 Rasa REST webhook，回傳 RAG 結果陣列。
sender 格式：{agent_id}_{user_id}
"""
from __future__ import annotations

import uuid
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.database.models import User
from api.database.session import get_db
from api.dependencies import get_current_user, require_agent_access
from api.schemas import ChatRequest

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
    webhook_url = f"{str(agent.rasa_rest_url).rstrip('/')}/webhooks/rest/webhook"

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                webhook_url,
                json={"sender": sender, "message": body.message},
            )
            resp.raise_for_status()
            messages: list[Any] = resp.json()
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"code": "TIMEOUT", "message": "Rasa 服務回應逾時"},
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "BAD_GATEWAY",
                "message": f"Rasa 服務回傳錯誤：{exc.response.status_code}",
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "BAD_GATEWAY", "message": f"無法連線至 Rasa 服務：{exc}"},
        )

    return {"success": True, "data": messages}
