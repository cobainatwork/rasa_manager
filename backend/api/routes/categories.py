"""
分類節點 CRUD：Adjacency List 模型，支援無限層級樹狀結構。
GET 回傳嵌套 JSON 樹；DELETE 禁止刪除含 FAQ 的節點。

註：分類「不」套用編輯鎖（CLAUDE.md §五.2 的 lazy expire 機制僅作用於
knowledge_items；分類為輕量元資料，併發改名衝突由 DB 唯一約束
uq_cat_agent_parent_name 兜底）。
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.database.models import Category, KnowledgeItem, User
from api.database.session import get_db
from api.dependencies import (
    get_current_user,
    require_agent_access,
    require_reviewer_or_superadmin,
)
from api.schemas import CategoryCreate, CategoryPatch

router = APIRouter(tags=["categories"])


def _build_tree(
    rows: list[dict[str, Any]], parent_id: Optional[uuid.UUID] = None
) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        if row["parent_id"] == parent_id:
            node = dict(row)
            node["children"] = _build_tree(rows, row["id"])
            result.append(node)
    return sorted(result, key=lambda x: x["sort_order"])


def _collect_descendants_recursive(
    db: Session, category_id: Any, agent_id: Any
) -> set[Any]:
    """遞迴 fallback（適用 SQLite 等不支援 recursive CTE 的測試場景）。"""
    result: set[Any] = set()
    children = (
        db.query(Category)
        .filter(Category.parent_id == category_id, Category.agent_id == agent_id)
        .all()
    )
    for child in children:
        result.add(child.id)
        result.update(_collect_descendants_recursive(db, child.id, agent_id))
    return result


def _collect_descendants(
    db: Session, category_id: Any, agent_id: Any
) -> set[Any]:
    """
    I5：使用 PostgreSQL recursive CTE 一次取得所有子孫節點，避免逐層 N+1 query。
    SQLite 等不支援的方言則 fallback 至遞迴查詢。
    """
    try:
        # mock 場景下 db 可能無 bind（例如 MagicMock spec=Session），fallback 至遞迴
        dialect_name = db.get_bind().dialect.name
    except (AttributeError, TypeError):
        dialect_name = ""
    if dialect_name == "postgresql":
        sql = text(
            """
            WITH RECURSIVE descendants AS (
                SELECT id, parent_id FROM categories
                WHERE parent_id = :start_id AND agent_id = :agent_id
                UNION ALL
                SELECT c.id, c.parent_id FROM categories c
                JOIN descendants d ON c.parent_id = d.id
                WHERE c.agent_id = :agent_id
            )
            SELECT id FROM descendants
            """
        )
        result = db.execute(
            sql, {"start_id": str(category_id), "agent_id": str(agent_id)}
        )
        return {row.id for row in result}

    return _collect_descendants_recursive(db, category_id, agent_id)


@router.get("/api/v1/agents/{agent_id}/categories")
def list_categories(
    agent_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    require_agent_access(agent_id, current_user, db)

    cats = (
        db.query(Category)
        .filter(Category.agent_id == agent_id)
        .all()
    )
    rows: list[dict[str, Any]] = [
        {
            "id": c.id,
            "name": c.name,
            "parent_id": c.parent_id,
            "sort_order": c.sort_order,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            "children": [],
        }
        for c in cats
    ]
    return {"success": True, "data": _build_tree(rows)}


@router.post(
    "/api/v1/agents/{agent_id}/categories",
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    agent_id: uuid.UUID,
    body: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    require_reviewer_or_superadmin(agent_id, current_user, db)

    if body.parent_id:
        parent = (
            db.query(Category)
            .filter(
                Category.id == body.parent_id,
                Category.agent_id == agent_id,
            )
            .first()
        )
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOT_FOUND", "message": "父節點不存在"},
            )

    cat = Category(
        id=uuid.uuid4(),
        agent_id=agent_id,
        parent_id=body.parent_id,
        name=body.name,
        sort_order=body.sort_order,
    )
    db.add(cat)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "DUPLICATE_NAME", "message": "同層級已有相同名稱的分類"},
        ) from None
    db.refresh(cat)
    return {
        "success": True,
        "data": {
            "id": str(cat.id),
            "agent_id": str(cat.agent_id),
            "name": cat.name,
            "parent_id": str(cat.parent_id) if cat.parent_id else None,
            "sort_order": cat.sort_order,
            "created_at": cat.created_at.isoformat() if cat.created_at else None,
            "updated_at": cat.updated_at.isoformat() if cat.updated_at else None,
            "children": [],
        },
        "message": "分類建立成功",
    }


@router.patch("/api/v1/agents/{agent_id}/categories/{category_id}")
def update_category(
    agent_id: uuid.UUID,
    category_id: uuid.UUID,
    body: CategoryPatch,
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "分類不存在"},
        )

    if body.name is not None:
        cat.name = body.name
    if body.sort_order is not None:
        cat.sort_order = body.sort_order
    # 明確設置 parent_id（允許設為 None 以移至根層）
    if "parent_id" in body.model_fields_set:
        cat.parent_id = body.parent_id

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "DUPLICATE_NAME", "message": "同層級已有相同名稱的分類"},
        ) from None
    db.refresh(cat)
    return {
        "success": True,
        "data": {
            "id": str(cat.id),
            "name": cat.name,
            "parent_id": str(cat.parent_id) if cat.parent_id else None,
            "sort_order": cat.sort_order,
        },
        "message": "更新成功",
    }


@router.delete(
    "/api/v1/agents/{agent_id}/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_category(
    agent_id: uuid.UUID,
    category_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    require_reviewer_or_superadmin(agent_id, current_user, db)

    cat = (
        db.query(Category)
        .filter(Category.id == category_id, Category.agent_id == agent_id)
        .first()
    )
    if not cat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "分類不存在"},
        )

    # 收集所有子孫節點 ID
    all_ids = _collect_descendants(db, category_id, agent_id)
    all_ids.add(category_id)

    # 檢查是否有 FAQ 關聯
    has_faq = (
        db.query(KnowledgeItem)
        .filter(KnowledgeItem.category_id.in_(all_ids))
        .first()
    )
    if has_faq:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "UNPROCESSABLE", "message": "此分類或子分類含有 FAQ，無法刪除"},
        )

    # 先刪子孫（避免 FK 衝突），再刪本節點
    for cid in all_ids - {category_id}:
        child = db.query(Category).filter(Category.id == cid).first()
        if child:
            db.delete(child)
    db.delete(cat)
    db.commit()
