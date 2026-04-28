"""
使用者管理路由（Superadmin 專用）。
"""
from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from api.database.models import User
from api.database.session import get_db
from api.dependencies import get_current_superadmin
from api.schemas import ResetPasswordRequest, UserCreate, UserUpdate

router = APIRouter(prefix="/api/v1/users", tags=["users"])
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def _validate_password(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_ERROR", "message": "密碼最少 8 個字元"},
        )
    if not re.search(r"[A-Z]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_ERROR", "message": "密碼需含大寫英文字母"},
        )
    if not re.search(r"[a-z]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_ERROR", "message": "密碼需含小寫英文字母"},
        )
    if not re.search(r"\d", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_ERROR", "message": "密碼需含數字"},
        )


@router.get("")
def list_users(
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    users = db.query(User).order_by(User.created_at.desc()).all()
    return {
        "success": True,
        "data": [
            {
                "id": str(u.id),
                "username": u.username,
                "is_superadmin": u.is_superadmin,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    _validate_password(body.password)
    existing = db.query(User).filter(User.username == body.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": "使用者名稱已存在"},
        )
    user = User(
        id=uuid.uuid4(),
        username=body.username,
        password_hash=_pwd_context.hash(body.password),
        is_superadmin=body.is_superadmin,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "success": True,
        "data": {
            "id": str(user.id),
            "username": user.username,
            "is_superadmin": user.is_superadmin,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "message": "使用者建立成功",
    }


@router.patch("/{user_id}")
def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "使用者不存在"},
        )
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.is_superadmin is not None:
        user.is_superadmin = body.is_superadmin
    db.commit()
    return {"success": True, "message": "更新成功"}


@router.patch("/{user_id}/reset-password")
def reset_password(
    user_id: uuid.UUID,
    body: ResetPasswordRequest,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    _validate_password(body.new_password)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "使用者不存在"},
        )
    user.password_hash = _pwd_context.hash(body.new_password)
    db.commit()
    return {"success": True, "message": "密碼重設成功"}
