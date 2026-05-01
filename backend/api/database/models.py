import uuid
from typing import Any

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey,
    Integer, String, Text, UniqueConstraint, func, text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from api.database.session import Base


# ── users ──────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    username = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_superadmin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    agent_roles = relationship("UserAgentRole", back_populates="user")
    locked_items = relationship(
        "KnowledgeItem", foreign_keys="KnowledgeItem.locked_by", back_populates="locker"
    )
    created_items = relationship(
        "KnowledgeItem", foreign_keys="KnowledgeItem.created_by", back_populates="creator"
    )
    histories = relationship("KnowledgeItemHistory", back_populates="saver")
    audit_logs = relationship("AuditLog", back_populates="performer")
    sync_logs = relationship("SyncLog", back_populates="triggerer")


# ── agents ─────────────────────────────────────────────────────────────────
class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint("name", name="uq_agents_name"),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name = Column(String(100), nullable=False)
    txt_output_path = Column(Text, nullable=False)
    rasa_rest_url = Column(String(255), nullable=True)
    ingest_script_path = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user_roles = relationship("UserAgentRole", back_populates="agent")
    categories = relationship("Category", back_populates="agent")
    knowledge_items = relationship("KnowledgeItem", back_populates="agent")
    audit_logs = relationship("AuditLog", back_populates="agent")
    sync_logs = relationship("SyncLog", back_populates="agent")


# ── user_agent_roles ────────────────────────────────────────────────────────
class UserAgentRole(Base):
    __tablename__ = "user_agent_roles"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Any = Column(
        Enum("reviewer", "editor", name="user_agent_role", create_type=False),
        nullable=False,
    )

    user = relationship("User", back_populates="agent_roles")
    agent = relationship("Agent", back_populates="user_roles")


# ── categories ─────────────────────────────────────────────────────────────
class Category(Base):
    __tablename__ = "categories"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_id = Column(
        UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True
    )
    name = Column(String(120), nullable=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    agent = relationship("Agent", back_populates="categories")
    parent = relationship("Category", remote_side="Category.id", back_populates="children")
    children = relationship("Category", back_populates="parent")
    knowledge_items = relationship("KnowledgeItem", back_populates="category")
    histories = relationship("KnowledgeItemHistory", back_populates="category")


# ── knowledge_items ─────────────────────────────────────────────────────────
class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    tags: Any = Column(ARRAY(String), server_default="{}")
    status: Any = Column(
        Enum("draft", "pending", "approved", "rejected", "synced",
             name="ki_status", create_type=False),
        nullable=False,
        server_default=text("'draft'"),
    )
    version = Column(Integer, default=1)
    locked_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    locked_at = Column(DateTime(timezone=True), nullable=True)
    # I1：created_by 放鬆 nullable=True，配合 ON DELETE SET NULL 行為
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    agent = relationship("Agent", back_populates="knowledge_items")
    category = relationship("Category", back_populates="knowledge_items")
    locker = relationship("User", foreign_keys=[locked_by], back_populates="locked_items")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_items")
    histories = relationship("KnowledgeItemHistory", back_populates="item")
    audit_logs = relationship("AuditLog", back_populates="item")


# ── knowledge_item_histories ────────────────────────────────────────────────
class KnowledgeItemHistory(Base):
    __tablename__ = "knowledge_item_histories"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    version = Column(Integer, nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    saved_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action = Column(String(50), nullable=False)
    action_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    item = relationship("KnowledgeItem", back_populates="histories")
    category = relationship("Category", back_populates="histories")
    saver = relationship("User", back_populates="histories")


# ── audit_logs ──────────────────────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    action = Column(String(50), nullable=False)
    performed_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    diff: Any = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    agent = relationship("Agent", back_populates="audit_logs")
    item = relationship("KnowledgeItem", back_populates="audit_logs")
    performer = relationship("User", back_populates="audit_logs")


# ── sync_logs ───────────────────────────────────────────────────────────────
class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    triggered_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    celery_task_id = Column(String(255), nullable=True)
    status: Any = Column(
        Enum("pending", "running", "completed", "failed",
             name="sync_status", create_type=False),
        nullable=False,
        server_default=text("'pending'"),
    )
    items_count = Column(Integer, default=0)
    output_file = Column(Text, nullable=True)
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_sec = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    agent = relationship("Agent", back_populates="sync_logs")
    triggerer = relationship("User", back_populates="sync_logs")
