"""
Pydantic schemas for request/response validation.
"""
from __future__ import annotations

import re as _re
import uuid
from typing import Annotated, Optional

from pydantic import BaseModel, Field, field_validator

# 注意：密碼強度（大小寫 + 數字）統一由 api.security.password.validate_password_strength
# 在 router 層執行，以維持 HTTP 400 + 結構化錯誤訊息的 contract（既有測試依賴此格式）。
# Pydantic 層僅以 min_length=8 做基本長度防呆，避免 422 與 400 兩條路徑分裂。


# ── Auth Schemas ──────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


# ── User Schemas ──────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    # 長度由 Pydantic 防呆（回 422），大小寫 / 數字檢查交由 router 的 validate_password_strength（回 400）。
    password: str = Field(..., min_length=8)
    is_superadmin: bool = False


class UserUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_superadmin: Optional[bool] = None


class ResetPasswordRequest(BaseModel):
    # 長度由 Pydantic 防呆（回 422），大小寫 / 數字檢查交由 router 的 validate_password_strength（回 400）。
    new_password: str = Field(..., min_length=8)


# ── Agent Schemas ─────────────────────────────────────────────────────────
_QDRANT_COLLECTION_RE = _re.compile(r"^[a-zA-Z_][a-zA-Z0-9_-]*$")


def _validate_rasa_url(v: Optional[str]) -> Optional[str]:
    """rasa_rest_url 必須為合法 http/https URL（含協定前綴）。"""
    if v is None:
        return v
    if not (v.startswith("http://") or v.startswith("https://")):
        raise ValueError(
            "Rasa webhook URL 必須以 http:// 或 https:// 開頭，"
            "請勿包含環境變數名稱（如 RASA_URL=）。"
        )
    return v


def _validate_qdrant_collection(v: str) -> str:
    """Qdrant collection 名稱：英文字母或底線開頭，後續可含英數字、底線、連字號。"""
    if not _QDRANT_COLLECTION_RE.match(v):
        raise ValueError(
            "Qdrant collection 名稱只能包含英文字母、數字、底線與連字號，"
            "且必須以英文字母或底線開頭。"
        )
    return v


_EMBEDDING_PROVIDER_PATTERN = "^(openai|local)$"


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    qdrant_collection: str = Field(..., min_length=1, max_length=255)
    txt_output_path: str = Field(..., min_length=1, max_length=255)
    rasa_rest_url: Optional[str] = Field(None, max_length=255)
    ingest_script_path: Optional[str] = Field(None, max_length=255)
    # 既有 agent 預設 OpenAI 雲端，建立新 agent 時也以此為預設。
    embedding_provider: str = Field(
        "openai", pattern=_EMBEDDING_PROVIDER_PATTERN, max_length=20
    )
    embedding_model: str = Field(
        "text-embedding-3-small", min_length=1, max_length=100
    )

    @field_validator("rasa_rest_url", mode="before")
    @classmethod
    def validate_rasa_url(cls, v: object) -> object:
        return _validate_rasa_url(v if isinstance(v, str) or v is None else str(v))

    @field_validator("qdrant_collection", mode="before")
    @classmethod
    def validate_qdrant_collection(cls, v: object) -> object:
        return _validate_qdrant_collection(str(v) if not isinstance(v, str) else v)


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    qdrant_collection: Optional[str] = Field(None, min_length=1, max_length=255)
    txt_output_path: Optional[str] = Field(None, min_length=1, max_length=255)
    rasa_rest_url: Optional[str] = Field(None, max_length=255)
    ingest_script_path: Optional[str] = Field(None, max_length=255)
    embedding_provider: Optional[str] = Field(
        None, pattern=_EMBEDDING_PROVIDER_PATTERN, max_length=20
    )
    embedding_model: Optional[str] = Field(None, min_length=1, max_length=100)

    @field_validator("rasa_rest_url", mode="before")
    @classmethod
    def validate_rasa_url(cls, v: object) -> object:
        return _validate_rasa_url(v if isinstance(v, str) or v is None else str(v))

    @field_validator("qdrant_collection", mode="before")
    @classmethod
    def validate_qdrant_collection(cls, v: object) -> object:
        if v is None:
            return v
        return _validate_qdrant_collection(str(v) if not isinstance(v, str) else v)


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
    # sender 由前端產生（per-session UUID），透過 backend 原樣 forward 給 Rasa。
    # 對齊 Rasa OpenAPI spec custom channel webhook 的 sender 欄位。
    # Optional 為了向後相容：未帶時 backend fallback 到 {agent_id}_{user_id}（舊行為）。
    sender: Optional[str] = Field(None, min_length=1, max_length=255)
