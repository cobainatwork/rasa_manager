"""
軌跡日誌查詢路由（按 Agent / 操作類型 / 時間範圍過濾）。
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.database.models import AuditLog, User
from api.database.session import get_db
from api.dependencies import get_current_user, require_agent_access

router = APIRouter(tags=["audit"])


@router.get("/api/v1/agents/{agent_id}/audit-logs")
def list_audit_logs(
    agent_id: uuid.UUID,
    action: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_agent_access(agent_id, current_user, db)

    query = db.query(AuditLog).filter(AuditLog.agent_id == agent_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)

    total = query.count()
    logs = (
        query.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    # JOIN users 取得 username
    user_ids = {log.performed_by for log in logs if log.performed_by}
    users_map: dict[Any, str] = {}
    if user_ids:
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        users_map = {u.id: str(u.username) for u in users}

    return {
        "success": True,
        "data": {
            "items": [
                {
                    "id": str(log.id),
                    "agent_id": str(log.agent_id),
                    "item_id": str(log.item_id) if log.item_id else None,
                    "action": log.action,
                    "performed_by": str(log.performed_by) if log.performed_by else None,
                    "performed_by_username": users_map.get(log.performed_by),
                    "diff": log.diff,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ],
            "total": total,
            "page": page,
            "per_page": per_page,
        },
    }
