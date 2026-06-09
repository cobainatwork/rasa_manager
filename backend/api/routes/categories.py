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

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.database.models import Agent, Category, KnowledgeItem, User
from api.database.session import get_db
from api.dependencies import (
    get_accessible_agent,
    get_current_user,
    require_reviewer_or_superadmin,
)
from api.errors import raise_http, raise_not_found, raise_unprocessable
from api.schemas import CategoryCreate, CategoryPatch

router = APIRouter(tags=["categories"])


def _build_tree(
    rows: list[dict[str, Any]], parent_id: Optional[uuid.UUID] = None
) -> list[dict[str, Any]]:
    """以 children_by_parent 索引一次性建樹（O(N)），取代原本逐層 filter（O(N²)）。"""
    children_by_parent: dict[Optional[uuid.UUID], list[dict[str, Any]]] = {}
    for row in rows:
        children_by_parent.setdefault(row["parent_id"], []).append(row)

    def _attach(pid: Optional[uuid.UUID]) -> list[dict[str, Any]]:
        nodes = children_by_parent.get(pid, [])
        result = []
        for row in nodes:
            node = dict(row)
            node["children"] = _attach(row["id"])
            result.append(node)
        return sorted(result, key=lambda x: x["sort_order"])

    return _attach(parent_id)


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
    access: tuple[Agent, str | None] = Depends(get_accessible_agent),
    db: Session = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    del access  # 僅做存取驗證

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
            raise_not_found("父節點不存在")
        # 最大兩層（根 → 子），禁止在子分類下再建子分類
        if parent.parent_id is not None:
            raise_http(
                "DEPTH_EXCEEDED",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "分類最多支援兩層，不允許再新增子分類",
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
        raise_http(
            "DUPLICATE_NAME",
            status.HTTP_409_CONFLICT,
            "同層級已有相同名稱的分類",
        )
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
        raise_not_found("分類不存在")

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
        raise_http(
            "DUPLICATE_NAME",
            status.HTTP_409_CONFLICT,
            "同層級已有相同名稱的分類",
        )
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
        raise_not_found("分類不存在")

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
        raise_unprocessable("此分類或子分類含有 FAQ，無法刪除")

    # bulk DELETE 以單一 SQL 語句刪除全部節點（含自身）；
    # PostgreSQL NO ACTION FK 在語句結束時才檢查，不受集合迭代順序影響，
    # 避免逐筆刪除時父節點先於子節點造成的自我參照 FK 衝突。
    db.query(Category).filter(Category.id.in_(all_ids)).delete(synchronize_session=False)
    db.commit()
