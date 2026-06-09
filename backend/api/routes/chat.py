"""
對話測試路由：轉發訊息至 Rasa REST webhook，回傳 RAG 結果陣列。
sender 格式：{agent_id}_{user_id}
"""
from __future__ import annotations

import uuid
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, Depends, status

from api.database.models import Agent, User
from api.dependencies import get_accessible_agent, get_current_user
from api.errors import raise_http, raise_unprocessable
from api.schemas import ChatRequest

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/agents/{agent_id}/chat", tags=["chat"])


def _extract_messages(raw: Any) -> list[Any]:
    """正規化 Rasa 兩種 response 格式為訊息陣列。

    REST channel (/webhooks/rest/webhook)         → 頂層陣列 [{recipient_id, text, ...}]
    Custom channel (/webhooks/{name}/webhook)     → {"messages": [...], "conversation_id": ..., ...}
    其他（含 None / 非預期型別）一律回傳 []。
    """
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return raw.get("messages") or []
    return []


@router.post("/test")
def test_chat(
    agent_id: uuid.UUID,
    body: ChatRequest,
    access: tuple[Agent, str | None] = Depends(get_accessible_agent),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    agent, _ = access

    if not agent.rasa_rest_url:
        raise_unprocessable("此 Agent 未設定 Rasa REST URL")

    # sender：前端產生的 per-session UUID 優先（對齊 Rasa OpenAPI spec），
    # 未帶則 fallback 到 {agent_id}_{user_id}（向後相容，無 nonce 等同 v1 行為）。
    # 換 sender 是 conversation 隔離的正解 — Rasa 用 sender_id 當 tracker key。
    sender = body.sender or f"{agent_id}_{current_user.id}"
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
            messages = _extract_messages(resp.json())
    except httpx.TimeoutException as exc:
        logger.warning(
            "rasa_timeout",
            agent_id=str(agent_id),
            url=webhook_url,
            error=str(exc),
        )
        raise_http("TIMEOUT", status.HTTP_504_GATEWAY_TIMEOUT, "Rasa 服務回應逾時")
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "rasa_http_error",
            agent_id=str(agent_id),
            url=webhook_url,
            status_code=exc.response.status_code,
            error=str(exc),
        )
        raise_http(
            "BAD_GATEWAY",
            status.HTTP_502_BAD_GATEWAY,
            f"Rasa 服務回應 HTTP {exc.response.status_code}",
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
        raise_http("BAD_GATEWAY", status.HTTP_502_BAD_GATEWAY, "Rasa 服務連線失敗")

    return {"success": True, "data": messages}
