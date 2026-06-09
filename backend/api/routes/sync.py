"""
同步路由：
  POST /api/v1/agents/{agent_id}/sync       - 觸發一鍵同步（建立 SyncLog → 推 Celery）
  GET  /api/v1/sync/tasks/{sync_log_id}     - 輪詢任務狀態與 Log
  GET  /api/v1/agents/{agent_id}/sync/history - 查詢同步歷史
"""
from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from api.database.models import Category, SyncLog, User
from api.database.session import get_db
from api.dependencies import (
    get_current_user,
    require_reviewer_or_superadmin,
)
from api.errors import raise_not_found

logger = structlog.get_logger()

router = APIRouter(tags=["sync"])

# kombu.exceptions.OperationalError（繼承自 Exception，非 OSError）
# 當 Redis broker 不可用時 Celery 可能拋出此例外；安全 fallback 至 OSError
try:
    from kombu.exceptions import OperationalError as _KombuError  # noqa: PLC0415
except ImportError:  # pragma: no cover
    _KombuError = OSError  # type: ignore[misc,assignment]


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
    except (ConnectionError, OSError, TimeoutError, _KombuError) as exc:
        # Celery broker 暫不可用時仍回傳 sync_log，Worker 恢復後可接續
        logger.warning(
            "celery_dispatch_failed",
            agent_id=str(agent_id),
            sync_log_id=str(sync_log.id),
            error=str(exc),
        )

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


@router.post(
    "/api/v1/agents/{agent_id}/categories/{category_id}/sync",
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_category_sync(
    agent_id: uuid.UUID,
    category_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    require_reviewer_or_superadmin(agent_id, current_user, db)

    cat = (
        db.query(Category)
        .filter(Category.id == category_id, Category.agent_id == agent_id)
        .first()
    )
    if not cat:
        raise_not_found("分類不存在")

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
        from tasks import run_category_sync  # noqa: PLC0415

        task = run_category_sync.delay(str(agent_id), str(category_id), str(sync_log.id))
        sync_log.celery_task_id = task.id
        db.commit()
        task_id = task.id
    except (ConnectionError, OSError, TimeoutError, _KombuError) as exc:
        logger.warning(
            "celery_category_sync_dispatch_failed",
            agent_id=str(agent_id),
            category_id=str(category_id),
            sync_log_id=str(sync_log.id),
            error=str(exc),
        )

    logger.info(
        "category_sync_triggered",
        agent_id=str(agent_id),
        category_id=str(category_id),
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


@router.get("/api/v1/agents/{agent_id}/sync/history")
def get_sync_history(
    agent_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    require_reviewer_or_superadmin(agent_id, current_user, db)

    logs = (
        db.query(SyncLog)
        .filter(SyncLog.agent_id == agent_id)
        .order_by(desc(SyncLog.started_at))
        .offset(offset)
        .limit(limit)
        .all()
    )

    # I3：批次取得 triggered_by 的 username，避免逐筆 N+1 query
    triggerer_ids = {log.triggered_by for log in logs if log.triggered_by}
    user_map: dict = {}
    if triggerer_ids:
        users = (
            db.query(User.id, User.username)
            .filter(User.id.in_(triggerer_ids))
            .all()
        )
        user_map = {uid: str(uname) for uid, uname in users}

    items = []
    for log in logs:
        triggerer = user_map.get(log.triggered_by) if log.triggered_by else None

        items.append({
            "id": str(log.id),
            "status": str(log.status),
            "triggered_by_username": triggerer,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "finished_at": log.finished_at.isoformat() if log.finished_at else None,
            "duration_sec": log.duration_sec,
            "items_count": log.items_count or 0,
            "output_file": log.output_file,
            "stdout": log.stdout,
            "stderr": log.stderr,
            # 同步當下凍結的 embedding 快照（migration 006 之前為 None）
            "embedding_provider": log.embedding_provider,
            "embedding_model": log.embedding_model,
        })

    return {"success": True, "data": items}


@router.get("/api/v1/sync/tasks/{sync_log_id}")
def get_sync_status(
    sync_log_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    sync_log = db.query(SyncLog).filter(SyncLog.id == sync_log_id).first()
    if not sync_log:
        raise_not_found("同步記錄不存在")

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
            # 同步當下凍結的 embedding 快照（migration 006 之前為 None）
            "embedding_provider": sync_log.embedding_provider,
            "embedding_model": sync_log.embedding_model,
        },
    }
