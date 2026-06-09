"""
集中 AuditLog 寫入：取代各 route 內散落的 db.add(AuditLog(...)) inline 構造。

設計原則：
1. 對齊既有 AuditLog 欄位（agent_id, item_id, action, performed_by, diff）。
2. 不自行 commit；transaction lifecycle 仍由 route handler 控制。
3. 與 faq.py 原 _record_audit / import_export.py 5 處 inline 構造等價。
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy.orm import Session

from api.database.models import AuditLog


def record_audit(
    db: Session,
    *,
    agent_id: Any,
    item_id: Optional[Any],
    action: str,
    user_id: Any,
    diff: Optional[dict[str, Any]] = None,
) -> None:
    """寫入一筆 AuditLog（不 commit）。

    Args:
        db: SQLAlchemy session。
        agent_id: 所屬 Agent UUID。
        item_id: 關聯的 KnowledgeItem UUID（匯出 / 批次刪除等情境可為 None）。
        action: 操作名稱（create, update, delete, import, export, ...）。
        user_id: 操作者 user.id（對應 DB 欄位 performed_by）。
        diff: JSONB diff 物件（可為 None）。
    """
    db.add(
        AuditLog(
            id=uuid.uuid4(),
            agent_id=agent_id,
            item_id=item_id,
            action=action,
            performed_by=user_id,
            diff=diff,
        )
    )
