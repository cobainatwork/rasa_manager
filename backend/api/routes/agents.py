"""
Agent 專案 CRUD 與角色分配路由（Superadmin 管理）。
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.database.models import Agent, Category, KnowledgeItem, User, UserAgentRole
from api.database.session import get_db
from api.dependencies import get_current_superadmin, get_current_user, require_agent_access
from api.schemas import AgentCreate, AgentUpdate, RoleAssignRequest

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


def _get_agent_or_404(db: Session, agent_id: uuid.UUID) -> Agent:
    """模組層級樣板：找不到 Agent 拋 404，不混入權限檢查。"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Agent 不存在"},
        )
    return agent


def _agent_to_dict(agent: Agent) -> dict:  # type: ignore[type-arg]
    return {
        "id": str(agent.id),
        "name": agent.name,
        "qdrant_collection": agent.qdrant_collection,
        "txt_output_path": agent.txt_output_path,
        "rasa_rest_url": agent.rasa_rest_url,
        "ingest_script_path": agent.ingest_script_path,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
    }


@router.get("")
def list_agents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    if current_user.is_superadmin:
        agents = db.query(Agent).order_by(Agent.created_at.desc()).all()
    else:
        agent_ids = [
            uar.agent_id
            for uar in db.query(UserAgentRole)
            .filter(UserAgentRole.user_id == current_user.id)
            .all()
        ]
        agents = db.query(Agent).filter(Agent.id.in_(agent_ids)).all()
    return {"success": True, "data": [_agent_to_dict(a) for a in agents]}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_agent(
    body: AgentCreate,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    existing = db.query(Agent).filter(Agent.name == body.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": "Agent 名稱已存在"},
        )
    agent = Agent(
        id=uuid.uuid4(),
        name=body.name,
        qdrant_collection=body.qdrant_collection,
        txt_output_path=body.txt_output_path,
        rasa_rest_url=body.rasa_rest_url,
        ingest_script_path=body.ingest_script_path,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return {"success": True, "data": _agent_to_dict(agent), "message": "Agent 建立成功"}


@router.get("/{agent_id}")
def get_agent(
    agent_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    agent, _ = require_agent_access(agent_id, current_user, db)
    return {"success": True, "data": _agent_to_dict(agent)}


@router.patch("/{agent_id}")
def update_agent(
    agent_id: uuid.UUID,
    body: AgentUpdate,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    agent = _get_agent_or_404(db, agent_id)
    # name / txt_output_path / qdrant_collection 為必填欄位，null 代表「不更新」
    if body.name is not None:
        agent.name = body.name
    if body.qdrant_collection is not None:
        agent.qdrant_collection = body.qdrant_collection
    if body.txt_output_path is not None:
        agent.txt_output_path = body.txt_output_path
    # rasa_rest_url / ingest_script_path 為可選欄位：
    # 使用 model_fields_set 區分「未帶欄位（不更新）」vs「顯式帶 null（清除）」
    if "rasa_rest_url" in body.model_fields_set:
        agent.rasa_rest_url = body.rasa_rest_url
    if "ingest_script_path" in body.model_fields_set:
        agent.ingest_script_path = body.ingest_script_path
    db.commit()
    db.refresh(agent)
    return {"success": True, "data": _agent_to_dict(agent), "message": "更新成功"}


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    agent_id: uuid.UUID,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db),
) -> None:
    agent = _get_agent_or_404(db, agent_id)
    has_items = (
        db.query(KnowledgeItem).filter(KnowledgeItem.agent_id == agent_id).first()
    )
    if has_items:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "UNPROCESSABLE", "message": "Agent 含有 FAQ 條目，無法刪除"},
        )
    has_categories = db.query(Category).filter(Category.agent_id == agent_id).first()
    if has_categories:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "UNPROCESSABLE", "message": "Agent 含有分類節點，無法刪除"},
        )
    db.delete(agent)
    db.commit()


@router.get("/{agent_id}/stats")
def get_agent_stats(
    agent_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    require_agent_access(agent_id, current_user, db)

    from sqlalchemy import case  # noqa: PLC0415

    row = db.query(
        func.count(KnowledgeItem.id).label("total"),
        func.sum(case((KnowledgeItem.status == "pending", 1), else_=0)).label("pending"),
        func.sum(case((KnowledgeItem.status == "approved", 1), else_=0)).label("approved"),
        func.sum(case((KnowledgeItem.status == "synced", 1), else_=0)).label("synced"),
        func.sum(case((KnowledgeItem.status == "draft", 1), else_=0)).label("draft"),
        func.sum(case((KnowledgeItem.status == "rejected", 1), else_=0)).label("rejected"),
    ).filter(KnowledgeItem.agent_id == agent_id).first()

    categories_count = (
        db.query(func.count(Category.id))
        .filter(Category.agent_id == agent_id)
        .scalar()
    )

    # row 在有 COUNT 的查詢中保證非 None，使用 getattr 安全讀取
    def _v(attr: str) -> int:
        return int(getattr(row, attr) or 0) if row is not None else 0

    return {
        "success": True,
        "data": {
            "total_faqs": _v("total"),
            "pending_count": _v("pending"),
            "approved_count": _v("approved"),
            "synced_count": _v("synced"),
            "draft_count": _v("draft"),
            "rejected_count": _v("rejected"),
            "categories_count": categories_count or 0,
        },
    }


@router.post("/{agent_id}/roles", status_code=status.HTTP_201_CREATED)
def assign_role(
    agent_id: uuid.UUID,
    body: RoleAssignRequest,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    _get_agent_or_404(db, agent_id)
    target_user = db.query(User).filter(User.id == body.user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "使用者不存在"},
        )
    existing = (
        db.query(UserAgentRole)
        .filter(
            UserAgentRole.user_id == body.user_id,
            UserAgentRole.agent_id == agent_id,
        )
        .first()
    )
    if existing:
        existing.role = body.role
    else:
        uar = UserAgentRole(
            user_id=body.user_id, agent_id=agent_id, role=body.role
        )
        db.add(uar)
    db.commit()
    return {"success": True, "message": "角色分配成功"}


@router.get("/{agent_id}/my-role")
def get_my_role(
    agent_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    _, role = require_agent_access(agent_id, current_user, db)
    return {
        "success": True,
        "data": {
            "role": role,
            "is_superadmin": current_user.is_superadmin,
        },
    }


@router.delete("/{agent_id}/roles/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_role(
    agent_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db),
) -> None:
    uar = (
        db.query(UserAgentRole)
        .filter(
            UserAgentRole.user_id == user_id,
            UserAgentRole.agent_id == agent_id,
        )
        .first()
    )
    if not uar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "角色分配不存在"},
        )
    db.delete(uar)
    db.commit()
