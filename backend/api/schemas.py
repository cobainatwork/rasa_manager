"""
Pydantic schemas for request/response validation.
"""
from __future__ import annotations

import uuid
from typing import Annotated, Optional

from pydantic import BaseModel, Field


# ── Auth Schemas ──────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


# ── User Schemas ──────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8)
    is_superadmin: bool = False


class UserUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_superadmin: Optional[bool] = None


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8)


# ── Agent Schemas ─────────────────────────────────────────────────────────
class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    txt_output_path: str = Field(..., min_length=1, max_length=255)
    rasa_rest_url: Optional[str] = Field(None, max_length=255)
    ingest_script_path: Optional[str] = Field(None, max_length=255)


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    txt_output_path: Optional[str] = Field(None, min_length=1, max_length=255)
    rasa_rest_url: Optional[str] = Field(None, max_length=255)
    ingest_script_path: Optional[str] = Field(None, max_length=255)


class RoleAssignRequest(BaseModel):
    user_id: uuid.UUID
    role: str = Field(..., pattern="^(reviewer|editor)$")


# ── Category Schemas ──────────────────────────────────────────────────────
class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    parent_id: Optional[uuid.UUID] = None
    sort_order: int = 0


class CategoryPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    parent_id: Optional[uuid.UUID] = None
    sort_order: Optional[int] = None


# ── FAQ Schemas ───────────────────────────────────────────────────────────
_Tag = Annotated[str, Field(min_length=1, max_length=100)]


class FaqCreate(BaseModel):
    category_id: uuid.UUID
    question: str = Field(..., min_length=1, max_length=5000)
    answer: str = Field(..., min_length=1, max_length=50000)
    tags: list[_Tag] = Field(default=[], max_length=20)


class FaqPatch(BaseModel):
    category_id: Optional[uuid.UUID] = None
    question: Optional[str] = Field(None, min_length=1, max_length=5000)
    answer: Optional[str] = Field(None, min_length=1, max_length=50000)
    tags: Optional[list[_Tag]] = Field(None, max_length=20)


class FaqStatusPatch(BaseModel):
    status: str
    reason: Optional[str] = None


class RollbackRequest(BaseModel):
    version: int = Field(..., ge=1)


# ── Sync Schemas ──────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
