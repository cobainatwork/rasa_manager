"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-28 00:00:00.000000

本 migration 建立完整初始 schema，包含：

ENUM 型態（3 個）：
    user_agent_role：reviewer / editor
    ki_status：draft / pending / approved / rejected / synced
    sync_status：pending / running / completed / failed

資料表（9 個）：
    users、agents、user_agent_roles（composite PK）、categories、
    knowledge_items、knowledge_item_histories、audit_logs、sync_logs

索引（13 個，依規格書 §11）：
    idx_ki_agent_id、idx_ki_status、idx_ki_category_id、
    idx_ki_locked_by（partial：locked_by IS NOT NULL）、
    idx_cat_agent_id、idx_cat_parent_id、
    idx_al_agent_id、idx_al_item_id、idx_al_created_at（DESC）、
    idx_sl_agent_id、idx_sl_started_at（DESC）、
    idx_uar_user_id、idx_uar_agent_id
"""
from __future__ import annotations
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. ENUM 型態（DO...EXCEPTION 避免重複建立時炸開）
    op.execute("""
DO $$ BEGIN
    CREATE TYPE user_agent_role AS ENUM ('reviewer', 'editor');
EXCEPTION WHEN duplicate_object THEN null;
END $$;
""")
    op.execute("""
DO $$ BEGIN
    CREATE TYPE ki_status AS ENUM ('draft', 'pending', 'approved', 'rejected', 'synced');
EXCEPTION WHEN duplicate_object THEN null;
END $$;
""")
    op.execute("""
DO $$ BEGIN
    CREATE TYPE sync_status AS ENUM ('pending', 'running', 'completed', 'failed');
EXCEPTION WHEN duplicate_object THEN null;
END $$;
""")

    # 2. users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_superadmin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )

    # 3. agents
    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("txt_output_path", sa.String(255), nullable=False),
        sa.Column("rasa_rest_url", sa.String(255), nullable=True),
        sa.Column("ingest_script_path", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("name", name="uq_agents_name"),
    )

    # 4. user_agent_roles（composite PK）
    op.create_table(
        "user_agent_roles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), primary_key=True),
        sa.Column(
            "role",
            postgresql.ENUM("reviewer", "editor", name="user_agent_role", create_type=False),
            nullable=False,
        ),
    )

    # 5. categories（自我參照）
    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )

    # 6. knowledge_items
    op.create_table(
        "knowledge_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.String()), server_default=sa.text("'{}'")),
        sa.Column(
            "status",
            postgresql.ENUM("draft", "pending", "approved", "rejected", "synced",
                            name="ki_status", create_type=False),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1")),
        sa.Column("locked_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("locked_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )

    # 7. knowledge_item_histories
    op.create_table(
        "knowledge_item_histories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("item_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("knowledge_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("saved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("action_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )

    # 8. audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("knowledge_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("performed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("diff", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )

    # 9. sync_logs
    op.create_table(
        "sync_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("triggered_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM("pending", "running", "completed", "failed",
                            name="sync_status", create_type=False),
            nullable=False,
        ),
        sa.Column("items_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("output_file", sa.String(500), nullable=True),
        sa.Column("stdout", sa.Text(), nullable=True),
        sa.Column("stderr", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("duration_sec", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )

    # 10. 索引（13 個，依規格書 §11）
    op.create_index("idx_ki_agent_id", "knowledge_items", ["agent_id"])
    op.create_index("idx_ki_status", "knowledge_items", ["status"])
    op.create_index("idx_ki_category_id", "knowledge_items", ["category_id"])
    op.create_index(
        "idx_ki_locked_by", "knowledge_items", ["locked_by"],
        postgresql_where=sa.text("locked_by IS NOT NULL"),
    )
    op.create_index("idx_cat_agent_id", "categories", ["agent_id"])
    op.create_index("idx_cat_parent_id", "categories", ["parent_id"])
    op.create_index("idx_al_agent_id", "audit_logs", ["agent_id"])
    op.create_index("idx_al_item_id", "audit_logs", ["item_id"])
    # 使用 raw SQL 因 alembic op.create_index 不支援 DESC 排序
    op.execute("CREATE INDEX idx_al_created_at ON audit_logs (created_at DESC)")
    op.create_index("idx_sl_agent_id", "sync_logs", ["agent_id"])
    # 使用 raw SQL 因 alembic op.create_index 不支援 DESC 排序
    op.execute("CREATE INDEX idx_sl_started_at ON sync_logs (started_at DESC)")
    op.create_index("idx_uar_user_id", "user_agent_roles", ["user_id"])
    op.create_index("idx_uar_agent_id", "user_agent_roles", ["agent_id"])


def downgrade() -> None:
    # 索引（逆序）
    op.drop_index("idx_uar_agent_id", table_name="user_agent_roles")
    op.drop_index("idx_uar_user_id", table_name="user_agent_roles")
    op.execute("DROP INDEX IF EXISTS idx_sl_started_at")
    op.drop_index("idx_sl_agent_id", table_name="sync_logs")
    op.execute("DROP INDEX IF EXISTS idx_al_created_at")
    op.drop_index("idx_al_item_id", table_name="audit_logs")
    op.drop_index("idx_al_agent_id", table_name="audit_logs")
    op.drop_index("idx_cat_parent_id", table_name="categories")
    op.drop_index("idx_cat_agent_id", table_name="categories")
    op.drop_index("idx_ki_locked_by", table_name="knowledge_items")
    op.drop_index("idx_ki_category_id", table_name="knowledge_items")
    op.drop_index("idx_ki_status", table_name="knowledge_items")
    op.drop_index("idx_ki_agent_id", table_name="knowledge_items")
    # 資料表（反向 FK 依賴順序）
    op.drop_table("sync_logs")
    op.drop_table("audit_logs")
    op.drop_table("knowledge_item_histories")
    op.drop_table("knowledge_items")
    op.drop_table("categories")
    op.drop_table("user_agent_roles")
    op.drop_table("agents")
    op.drop_table("users")
    # ENUM 型態（IF EXISTS 防呆，避免重複 downgrade 時炸開）
    op.execute("DROP TYPE IF EXISTS sync_status")
    op.execute("DROP TYPE IF EXISTS ki_status")
    op.execute("DROP TYPE IF EXISTS user_agent_role")
