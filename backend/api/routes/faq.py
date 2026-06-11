"""
FAQ（知識問答）核心 CRUD、狀態機、編輯鎖、版本歷史、Rollback。

狀態機允許轉換（per role）：
  superadmin: draft→pending, draft→approved, pending→draft,
              pending→approved, pending→rejected, rejected→pending,
              approved→draft, synced→draft
  reviewer:   draft→pending, pending→draft, pending→approved,
              pending→rejected, rejected→pending, approved→draft, synced→draft
  editor:     draft→pending, pending→draft, rejected→pending,
              approved→draft, synced→draft
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from api.database.models import (
    Agent,
    Category,
    KnowledgeItem,
    KnowledgeItemHistory,
    User,
)
from api.database.session import get_db
from api.dependencies import get_accessible_agent, get_current_user
from api.errors import (
    raise_forbidden,
    raise_locked,
    raise_not_found,
    raise_validation_error,
)
from api.schemas import FaqCreate, FaqPatch, FaqStatusPatch, RollbackRequest
from api.services.audit import record_audit
from api.utils.category_path import collect_category_subtree

logger = structlog.get_logger()

router = APIRouter(tags=["faqs"])

LOCK_EXPIRE_SECONDS = 600  # 10 分鐘

# 各角色允許的狀態轉換
_ALLOWED_TRANSITIONS: dict[str, set[tuple[str, str]]] = {
    "superadmin": {
        ("draft", "pending"),
        ("draft", "approved"),
        ("pending", "draft"),
        ("pending", "approved"),
        ("pending", "rejected"),
        ("rejected", "pending"),
        ("approved", "draft"),
        ("synced", "draft"),
    },
    "reviewer": {
        ("draft", "pending"),
        ("pending", "draft"),
        ("pending", "approved"),
        ("pending", "rejected"),
        ("rejected", "pending"),
        ("approved", "draft"),
        ("synced", "draft"),
    },
    "editor": {
        ("draft", "pending"),
        ("pending", "draft"),
        ("rejected", "pending"),
        ("approved", "draft"),
        ("synced", "draft"),
    },
}


# ── 輔助函式 ──────────────────────────────────────────────────────────────

def _get_faq_or_404(
    db: Session, agent_id: uuid.UUID, faq_id: uuid.UUID
) -> KnowledgeItem:
    """取得屬於指定 Agent 的 FAQ，找不到時拋 404。"""
    item = (
        db.query(KnowledgeItem)
        .filter(KnowledgeItem.id == faq_id, KnowledgeItem.agent_id == agent_id)
        .first()
    )
    if not item:
        raise_not_found("FAQ 不存在")
    return item


def _get_faq_for_update_or_404(
    db: Session, agent_id: uuid.UUID, faq_id: uuid.UUID
) -> KnowledgeItem:
    """取得 FAQ 並加上 row-level lock（with_for_update），找不到時拋 404。"""
    item = (
        db.query(KnowledgeItem)
        .filter(KnowledgeItem.id == faq_id, KnowledgeItem.agent_id == agent_id)
        .with_for_update()
        .first()
    )
    if not item:
        raise_not_found("FAQ 不存在")
    return item


def _faq_to_dict(
    item: KnowledgeItem, locker_username: Optional[str] = None
) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "agent_id": str(item.agent_id),
        "category_id": str(item.category_id),
        "question": item.question,
        "answer": item.answer,
        "tags": item.tags or [],
        "status": item.status,
        "version": item.version,
        "locked_by": str(item.locked_by) if item.locked_by else None,
        "locked_by_username": locker_username,
        "locked_at": item.locked_at.isoformat() if item.locked_at else None,
        "created_by": str(item.created_by),
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


def _is_lock_expired(item: KnowledgeItem) -> bool:
    if not item.locked_by or not item.locked_at:
        return False
    locked_at = item.locked_at
    if locked_at.tzinfo is None:
        locked_at = locked_at.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - locked_at).total_seconds() >= LOCK_EXPIRE_SECONDS


def _lazy_clear_lock(item: KnowledgeItem, db: Session) -> bool:
    """
    Lazy Expire：讀取 / 編輯時惰性清除過期鎖。
    僅修改 ORM 物件並 flush，**不自行 commit**，由呼叫端決定 commit 時機。
    回傳是否實際清除了鎖（True 代表呼叫端在純讀路徑下需 commit）。
    """
    if _is_lock_expired(item):
        item.locked_by = None
        item.locked_at = None
        db.flush()
        return True
    return False


def _get_locker_username(item: KnowledgeItem, db: Session) -> Optional[str]:
    if not item.locked_by:
        return None
    locker = db.query(User).filter(User.id == item.locked_by).first()
    return str(locker.username) if locker else None


def _record_history(
    db: Session,
    item: KnowledgeItem,
    action: str,
    saved_by: Any,
    reason: Optional[str] = None,
) -> None:
    history = KnowledgeItemHistory(
        id=uuid.uuid4(),
        item_id=item.id,
        version=item.version,
        question=item.question,
        answer=item.answer,
        category_id=item.category_id,
        saved_by=saved_by,
        action=action,
        action_reason=reason,
    )
    db.add(history)


# ── FAQ CRUD ──────────────────────────────────────────────────────────────

@router.get("/api/v1/agents/{agent_id}/faqs")
def list_faqs(
    agent_id: uuid.UUID,
    category_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    access: tuple[Agent, str | None] = Depends(get_accessible_agent),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    del access  # 僅做存取驗證

    query = db.query(KnowledgeItem).filter(KnowledgeItem.agent_id == agent_id)
    if category_id:
        # 含子樹：點 root 或中間層 category 也要看到所有子孫 category 下的 FAQ
        cats = db.query(Category).filter(Category.agent_id == agent_id).all()
        cat_map = {c.id: c for c in cats}
        subtree_ids = collect_category_subtree(category_id, cat_map)
        query = query.filter(KnowledgeItem.category_id.in_(subtree_ids))
    if status_filter:
        query = query.filter(KnowledgeItem.status == status_filter)
    if q:
        query = query.filter(
            KnowledgeItem.question.ilike(f"%{q}%")
            | KnowledgeItem.answer.ilike(f"%{q}%")
        )

    total = query.count()
    items = (
        query.order_by(KnowledgeItem.updated_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    # I1：批次取得 locker username，避免逐筆 N+1 query
    locker_ids = {it.locked_by for it in items if it.locked_by}
    if locker_ids:
        lockers = (
            db.query(User.id, User.username)
            .filter(User.id.in_(locker_ids))
            .all()
        )
        locker_map: dict[Any, str] = {uid: str(uname) for uid, uname in lockers}
    else:
        locker_map = {}

    return {
        "success": True,
        "data": {
            "items": [
                _faq_to_dict(i, locker_map.get(i.locked_by) if i.locked_by else None)
                for i in items
            ],
            "total": total,
            "page": page,
            "per_page": per_page,
        },
    }


@router.get("/api/v1/agents/{agent_id}/faqs/ids")
def list_faq_ids(
    agent_id: uuid.UUID,
    category_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    q: Optional[str] = Query(None),
    access: tuple[Agent, str | None] = Depends(get_accessible_agent),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """回傳符合條件的全部 FAQ ID（不分頁），供前端「全選分類」功能使用。"""
    del access  # 僅做存取驗證

    query = db.query(KnowledgeItem.id).filter(KnowledgeItem.agent_id == agent_id)
    if category_id:
        # 含子樹：與 list_faqs 一致，避免「全選分類」漏選子孫的 FAQ
        cats = db.query(Category).filter(Category.agent_id == agent_id).all()
        cat_map = {c.id: c for c in cats}
        subtree_ids = collect_category_subtree(category_id, cat_map)
        query = query.filter(KnowledgeItem.category_id.in_(subtree_ids))
    if status_filter:
        query = query.filter(KnowledgeItem.status == status_filter)
    if q:
        query = query.filter(
            KnowledgeItem.question.ilike(f"%{q}%")
            | KnowledgeItem.answer.ilike(f"%{q}%")
        )

    ids = [str(row.id) for row in query.all()]
    return {"success": True, "data": {"ids": ids}}


@router.get("/api/v1/agents/{agent_id}/faqs/{faq_id}")
def get_faq(
    agent_id: uuid.UUID,
    faq_id: uuid.UUID,
    access: tuple[Agent, str | None] = Depends(get_accessible_agent),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    del access  # 僅做存取驗證

    item = _get_faq_or_404(db, agent_id, faq_id)

    cleared = _lazy_clear_lock(item, db)
    if cleared:
        # 純讀路徑：僅在實際清鎖時才 commit，避免無變動的讀取也觸發 commit。
        db.commit()
    return {"success": True, "data": _faq_to_dict(item, _get_locker_username(item, db))}


@router.post(
    "/api/v1/agents/{agent_id}/faqs",
    status_code=status.HTTP_201_CREATED,
)
def create_faq(
    agent_id: uuid.UUID,
    body: FaqCreate,
    access: tuple[Agent, str | None] = Depends(get_accessible_agent),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    del access  # 僅做存取驗證

    # Superadmin 建立時自動核准（跳過 pending）
    initial_status = "approved" if current_user.is_superadmin else "draft"

    item = KnowledgeItem(
        id=uuid.uuid4(),
        agent_id=agent_id,
        category_id=body.category_id,
        question=body.question,
        answer=body.answer,
        tags=body.tags,
        status=initial_status,
        version=1,
        created_by=current_user.id,
    )
    db.add(item)
    db.flush()  # 取得 item.id

    _record_history(db, item, "created", current_user.id)
    record_audit(
        db,
        agent_id=agent_id,
        item_id=item.id,
        action="create",
        user_id=current_user.id,
    )

    db.commit()
    db.refresh(item)
    logger.info(
        "faq_created",
        faq_id=str(item.id),
        agent_id=str(agent_id),
        user_id=str(current_user.id),
        initial_status=initial_status,
    )
    return {"success": True, "data": _faq_to_dict(item), "message": "FAQ 建立成功"}


@router.patch("/api/v1/agents/{agent_id}/faqs/{faq_id}")
def update_faq(
    agent_id: uuid.UUID,
    faq_id: uuid.UUID,
    body: FaqPatch,
    access: tuple[Agent, str | None] = Depends(get_accessible_agent),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    del access  # 僅做存取驗證

    # with_for_update() 確保取得鎖定後再進行鎖衝突判斷，消除 TOCTOU 競態
    item = _get_faq_for_update_or_404(db, agent_id, faq_id)

    # Lazy Expire 後檢查鎖
    _lazy_clear_lock(item, db)
    if item.locked_by and item.locked_by != current_user.id:
        raise_locked("FAQ 正在被他人編輯中")

    diff: dict[str, Any] = {}
    if body.question is not None and body.question != item.question:
        diff["question"] = {"before": item.question, "after": body.question}
        item.question = body.question
    if body.answer is not None and body.answer != item.answer:
        diff["answer"] = {"before": item.answer, "after": body.answer}
        item.answer = body.answer
    if body.category_id is not None and body.category_id != item.category_id:
        diff["category_id"] = {
            "before": str(item.category_id),
            "after": str(body.category_id),
        }
        item.category_id = body.category_id
    # tags 需比較實際值，避免送相同內容也觸發降級
    if body.tags is not None and body.tags != (item.tags or []):
        diff["tags"] = {"before": item.tags, "after": body.tags}
        item.tags = body.tags

    # 僅在有實際內容變更時才自動降級；純讀取儲存（無 diff）不改變狀態
    if diff:
        if item.status in ("approved", "synced"):
            diff["status"] = {"before": item.status, "after": "draft"}
            item.status = "draft"

        item.version += 1
        _record_history(db, item, "edited", current_user.id)
        record_audit(
            db,
            agent_id=agent_id,
            item_id=item.id,
            action="update",
            user_id=current_user.id,
            diff=diff,
        )
        db.commit()
        db.refresh(item)
        return {"success": True, "data": _faq_to_dict(item), "message": "更新成功"}

    # 無任何欄位異動 → 直接回傳現有資料，不觸發降級
    return {"success": True, "data": _faq_to_dict(item), "message": "無內容變更"}


@router.patch("/api/v1/agents/{agent_id}/faqs/{faq_id}/status")
def update_faq_status(
    agent_id: uuid.UUID,
    faq_id: uuid.UUID,
    body: FaqStatusPatch,
    access: tuple[Agent, str | None] = Depends(get_accessible_agent),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    agent, role = access
    del agent  # 僅取 role 用於狀態機判定

    # I16：寫入路徑加 with_for_update，避免兩個並發 PATCH /status 同時通過狀態機檢查
    item = _get_faq_for_update_or_404(db, agent_id, faq_id)

    new_status = body.status
    old_status = str(item.status)

    # rejected 時 reason 必填
    if new_status == "rejected" and not body.reason:
        raise_validation_error("退回時必須填寫理由")

    # 決定有效角色
    effective_role = "superadmin" if current_user.is_superadmin else (role or "editor")
    allowed = _ALLOWED_TRANSITIONS.get(effective_role, set())

    if (old_status, new_status) not in allowed:
        raise_forbidden(f"您無權將狀態從 {old_status} 轉換至 {new_status}")

    diff: dict[str, Any] = {"status": {"before": old_status, "after": new_status}}
    item.status = new_status

    _record_history(db, item, new_status, current_user.id, body.reason)
    record_audit(
        db,
        agent_id=agent_id,
        item_id=item.id,
        action=new_status,
        user_id=current_user.id,
        diff=diff,
    )

    db.commit()
    db.refresh(item)
    logger.info(
        "faq_status_changed",
        faq_id=str(faq_id),
        agent_id=str(agent_id),
        user_id=str(current_user.id),
        old_status=old_status,
        new_status=new_status,
    )
    return {"success": True, "data": _faq_to_dict(item), "message": "狀態更新成功"}


# ── 編輯鎖 ────────────────────────────────────────────────────────────────

@router.post("/api/v1/agents/{agent_id}/faqs/{faq_id}/lock")
def acquire_lock(
    agent_id: uuid.UUID,
    faq_id: uuid.UUID,
    access: tuple[Agent, str | None] = Depends(get_accessible_agent),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    del access  # 僅做存取驗證

    # I16：取鎖必須 with_for_update，避免兩個並發 acquire 都看到 locked_by=None 都成功取鎖
    item = _get_faq_for_update_or_404(db, agent_id, faq_id)

    _lazy_clear_lock(item, db)

    if item.locked_by and item.locked_by != current_user.id:
        raise_locked("FAQ 正在被他人編輯中")

    item.locked_by = current_user.id
    item.locked_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True, "message": "取鎖成功"}


@router.put("/api/v1/agents/{agent_id}/faqs/{faq_id}/lock")
def extend_lock(
    agent_id: uuid.UUID,
    faq_id: uuid.UUID,
    access: tuple[Agent, str | None] = Depends(get_accessible_agent),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    del access  # 僅做存取驗證

    # I16：寫入路徑加 with_for_update
    item = _get_faq_for_update_or_404(db, agent_id, faq_id)

    if item.locked_by != current_user.id:
        raise_forbidden("只有鎖持有者可延長鎖時效")

    item.locked_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True, "message": "鎖延長成功"}


@router.delete(
    "/api/v1/agents/{agent_id}/faqs/{faq_id}/lock",
    status_code=status.HTTP_204_NO_CONTENT,
)
def release_lock(
    agent_id: uuid.UUID,
    faq_id: uuid.UUID,
    access: tuple[Agent, str | None] = Depends(get_accessible_agent),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    del access  # 僅做存取驗證

    # I16：寫入路徑加 with_for_update
    item = _get_faq_for_update_or_404(db, agent_id, faq_id)

    if (
        item.locked_by
        and item.locked_by != current_user.id
        and not current_user.is_superadmin
    ):
        raise_forbidden("只有鎖持有者或 Superadmin 可釋放鎖")

    item.locked_by = None
    item.locked_at = None
    db.commit()


# ── 刪除 FAQ ──────────────────────────────────────────────────────────────

@router.delete(
    "/api/v1/agents/{agent_id}/faqs/{faq_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_faq(
    agent_id: uuid.UUID,
    faq_id: uuid.UUID,
    access: tuple[Agent, str | None] = Depends(get_accessible_agent),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    agent, role = access
    del agent  # 僅取 role 用於授權判定

    item = _get_faq_or_404(db, agent_id, faq_id)

    item_status = str(item.status)

    if current_user.is_superadmin:
        pass  # 全部允許
    elif role == "reviewer":
        if item_status in ("approved", "synced"):
            raise_forbidden("Reviewer 不可刪除已核准/已同步的 FAQ")
    elif role == "editor":
        if item.created_by != current_user.id or item_status != "draft":
            raise_forbidden("Editor 僅可刪除自己建立的草稿")

    record_audit(
        db,
        agent_id=agent_id,
        item_id=item.id,
        action="delete",
        user_id=current_user.id,
    )
    db.delete(item)
    db.commit()
    logger.info(
        "faq_deleted",
        faq_id=str(faq_id),
        agent_id=str(agent_id),
        user_id=str(current_user.id),
    )


# ── 版本歷史 ──────────────────────────────────────────────────────────────

@router.get("/api/v1/agents/{agent_id}/faqs/{faq_id}/histories")
def get_histories(
    agent_id: uuid.UUID,
    faq_id: uuid.UUID,
    access: tuple[Agent, str | None] = Depends(get_accessible_agent),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    del access  # 僅做存取驗證

    _get_faq_or_404(db, agent_id, faq_id)

    histories = (
        db.query(KnowledgeItemHistory)
        .filter(KnowledgeItemHistory.item_id == faq_id)
        .order_by(KnowledgeItemHistory.created_at.desc())
        .all()
    )

    return {
        "success": True,
        "data": [
            {
                "id": str(h.id),
                "item_id": str(h.item_id) if h.item_id else None,
                "version": h.version,
                "question": h.question,
                "answer": h.answer,
                "category_id": str(h.category_id) if h.category_id else None,
                "saved_by": str(h.saved_by) if h.saved_by else None,
                "action": h.action,
                "action_reason": h.action_reason,
                "created_at": h.created_at.isoformat() if h.created_at else None,
            }
            for h in histories
        ],
    }


# ── Rollback ──────────────────────────────────────────────────────────────

@router.post("/api/v1/agents/{agent_id}/faqs/{faq_id}/rollback")
def rollback_faq(
    agent_id: uuid.UUID,
    faq_id: uuid.UUID,
    body: RollbackRequest,
    access: tuple[Agent, str | None] = Depends(get_accessible_agent),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    del access  # 僅做存取驗證

    # I16：rollback 為寫入路徑，加 with_for_update
    item = _get_faq_for_update_or_404(db, agent_id, faq_id)

    target = (
        db.query(KnowledgeItemHistory)
        .filter(
            KnowledgeItemHistory.item_id == faq_id,
            KnowledgeItemHistory.version == body.version,
        )
        .first()
    )
    if not target:
        raise_not_found(f"版本 {body.version} 不存在")

    diff: dict[str, Any] = {
        "question": {"before": item.question, "after": target.question},
        "answer": {"before": item.answer, "after": target.answer},
        "status": {"before": str(item.status), "after": "draft"},
    }

    item.question = target.question
    item.answer = target.answer
    if target.category_id:
        item.category_id = target.category_id
    item.status = "draft"
    item.version += 1

    _record_history(db, item, "rollback", current_user.id)
    record_audit(
        db,
        agent_id=agent_id,
        item_id=item.id,
        action="rollback",
        user_id=current_user.id,
        diff=diff,
    )

    db.commit()
    db.refresh(item)
    return {
        "success": True,
        "data": _faq_to_dict(item),
        "message": f"已回復至版本 {body.version}",
    }
