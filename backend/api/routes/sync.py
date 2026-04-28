"""
同步路由：
  POST /api/v1/agents/{agent_id}/sync       - 觸發一鍵同步（建立 SyncLog → 推 Celery）
  GET  /api/v1/sync/tasks/{sync_log_id}     - 輪詢任務狀態與 Log
"""
from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.database.models import SyncLog, User
from api.database.session import get_db
from api.dependencies import get_current_user, require_reviewer_or_superadmin

logger = structlog.get_logger()

router = APIRouter(tags=["sync"])


@router.post(
    "/api/v1/agents/{agent_id}/sync",
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_sync(
    agent_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    require_reviewer_or_superadmin(agent_id, current_user, db)

    sync_log = SyncLog(
        id=uuid.uuid4(),
        agent_id=agent_id,
        triggered_by=current_user.id,
        status="pending",
        items_count=0,
    )
    db.add(sync_log)
    db.commit()
    db.refresh(sync_log)

    task_id: str | None = None
    try:
        from tasks import run_ingestion_sync  # noqa: PLC0415

        task = run_ingestion_sync.delay(str(agent_id), str(sync_log.id))
        sync_log.celery_task_id = task.id
        db.commit()
        task_id = task.id
    except Exception:
        # Celery 暫不可用時仍回傳 sync_log，Worker 恢復後可接續
        pass

    logger.info(
        "sync_triggered",
        agent_id=str(agent_id),
        user_id=str(current_user.id),
        sync_log_id=str(sync_log.id),
        celery_task_id=task_id,
    )
    return {
        "success": True,
        "data": {
            "task_id": task_id,
            "sync_log_id": str(sync_log.id),
            "status": "pending",
        },
    }


@router.get("/api/v1/sync/tasks/{sync_log_id}")
def get_sync_status(
    sync_log_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    sync_log = db.query(SyncLog).filter(SyncLog.id == sync_log_id).first()
    if not sync_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "同步記錄不存在"},
        )

    return {
        "success": True,
        "data": {
            "id": str(sync_log.id),
            "agent_id": str(sync_log.agent_id),
            "triggered_by": str(sync_log.triggered_by) if sync_log.triggered_by else None,
            "celery_task_id": sync_log.celery_task_id,
            "status": str(sync_log.status),
            "items_count": sync_log.items_count or 0,
            "output_file": sync_log.output_file,
            "stdout": sync_log.stdout,
            "stderr": sync_log.stderr,
            "started_at": sync_log.started_at.isoformat() if sync_log.started_at else None,
            "finished_at": sync_log.finished_at.isoformat() if sync_log.finished_at else None,
            "duration_sec": sync_log.duration_sec,
            "created_at": sync_log.created_at.isoformat() if sync_log.created_at else None,
        },
    }
