"""hardening: UUID server_default、TIMESTAMPTZ、外鍵 ondelete、不可變 trigger、索引補強

Revision ID: 002
Revises: 001
Create Date: 2026-05-01 00:00:00.000000

本 migration 為 schema 強化（hardening）累加修正，包含：

B2  pgcrypto 擴充 + 所有 UUID PK 加 server_default = gen_random_uuid()
B3  全部 timestamp 欄位轉為 TIMESTAMP WITH TIME ZONE（UTC）
I1  外鍵 ondelete 行為明確化（CASCADE / SET NULL / RESTRICT）
I2  knowledge_item_histories 不可變 trigger（封鎖 UPDATE / DELETE）
I3  categories 同 agent + 同 parent 下 name 唯一（partial unique index）
I5  agents.txt_output_path / agents.ingest_script_path / sync_logs.output_file
    由 VARCHAR 改為 TEXT
I6  knowledge_items.status server_default = 'draft'
    sync_logs.status server_default = 'pending'
I7  knowledge_items.locked_at partial index（WHERE locked_at IS NOT NULL）
I8  audit_logs.diff GIN 索引
N4  agents.created_at SET NOT NULL（補上現有 NULL）
"""
from __future__ import annotations
from typing import Sequence, Union

from alembic import op


revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── B2 涵蓋表清單（user_agent_roles 為 composite PK，跳過）────────────────────
_UUID_PK_TABLES = (
    "users",
    "agents",
    "categories",
    "knowledge_items",
    "knowledge_item_histories",
    "audit_logs",
    "sync_logs",
)

# ── B3 涵蓋欄位（依規格清單）──────────────────────────────────────────────────
_TIMESTAMP_COLUMNS = (
    ("users", "created_at"),
    ("agents", "created_at"),
    ("categories", "created_at"),
    ("categories", "updated_at"),
    ("knowledge_items", "locked_at"),
    ("knowledge_items", "created_at"),
    ("knowledge_items", "updated_at"),
    ("knowledge_item_histories", "created_at"),
    ("audit_logs", "created_at"),
    ("sync_logs", "started_at"),
    ("sync_logs", "finished_at"),
    ("sync_logs", "created_at"),
)

# ── I1 外鍵 ondelete 變更清單 ────────────────────────────────────────────────
# (table, fk_name, local_col, ref_table, ref_col, ondelete)
_FK_CHANGES = (
    ("categories", "categories_agent_id_fkey", "agent_id", "agents", "id", "CASCADE"),
    ("knowledge_items", "knowledge_items_agent_id_fkey", "agent_id", "agents", "id", "CASCADE"),
    # category_id 維持 RESTRICT（保守，規格未說刪 category 行為）
    ("knowledge_items", "knowledge_items_category_id_fkey", "category_id", "categories", "id", "RESTRICT"),
    ("knowledge_items", "knowledge_items_locked_by_fkey", "locked_by", "users", "id", "SET NULL"),
    # created_by 既有 NOT NULL，先放鬆為 nullable，再 SET NULL
    ("knowledge_items", "knowledge_items_created_by_fkey", "created_by", "users", "id", "SET NULL"),
    ("audit_logs", "audit_logs_agent_id_fkey", "agent_id", "agents", "id", "CASCADE"),
    ("audit_logs", "audit_logs_performed_by_fkey", "performed_by", "users", "id", "SET NULL"),
    ("sync_logs", "sync_logs_agent_id_fkey", "agent_id", "agents", "id", "CASCADE"),
    ("sync_logs", "sync_logs_triggered_by_fkey", "triggered_by", "users", "id", "SET NULL"),
    ("user_agent_roles", "user_agent_roles_user_id_fkey", "user_id", "users", "id", "CASCADE"),
    ("user_agent_roles", "user_agent_roles_agent_id_fkey", "agent_id", "agents", "id", "CASCADE"),
    ("knowledge_item_histories", "knowledge_item_histories_saved_by_fkey", "saved_by", "users", "id", "SET NULL"),
)


def upgrade() -> None:
    # ── B2：pgcrypto + UUID server_default ────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    for table in _UUID_PK_TABLES:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN id SET DEFAULT gen_random_uuid()"
        )

    # ── N4：agents.created_at 補 NOT NULL（先填補既有 NULL）────────────────
    op.execute("UPDATE agents SET created_at = NOW() WHERE created_at IS NULL")
    op.execute("ALTER TABLE agents ALTER COLUMN created_at SET NOT NULL")

    # ── B3：DateTime → TIMESTAMP WITH TIME ZONE（以 UTC 解讀既有 naive 值）
    for table, column in _TIMESTAMP_COLUMNS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} "
            f"TYPE TIMESTAMP WITH TIME ZONE "
            f"USING {column} AT TIME ZONE 'UTC'"
        )

    # ── I5：路徑類欄位 VARCHAR → TEXT ───────────────────────────────────────
    op.execute("ALTER TABLE agents ALTER COLUMN txt_output_path TYPE TEXT")
    op.execute("ALTER TABLE agents ALTER COLUMN ingest_script_path TYPE TEXT")
    op.execute("ALTER TABLE sync_logs ALTER COLUMN output_file TYPE TEXT")

    # ── I6：status server_default ──────────────────────────────────────────
    op.execute(
        "ALTER TABLE knowledge_items ALTER COLUMN status SET DEFAULT 'draft'"
    )
    op.execute(
        "ALTER TABLE sync_logs ALTER COLUMN status SET DEFAULT 'pending'"
    )

    # ── I1：外鍵 ondelete 變更 ────────────────────────────────────────────
    # 先放鬆 knowledge_items.created_by 為 nullable，配合 SET NULL 行為
    op.execute(
        "ALTER TABLE knowledge_items ALTER COLUMN created_by DROP NOT NULL"
    )
    for table, fk_name, local_col, ref_table, ref_col, ondelete in _FK_CHANGES:
        op.execute(f'ALTER TABLE {table} DROP CONSTRAINT IF EXISTS "{fk_name}"')
        op.execute(
            f'ALTER TABLE {table} '
            f'ADD CONSTRAINT "{fk_name}" '
            f"FOREIGN KEY ({local_col}) REFERENCES {ref_table}({ref_col}) "
            f"ON DELETE {ondelete}"
        )

    # ── I2：knowledge_item_histories 不可變 trigger ──────────────────────────
    op.execute(
        """
        CREATE OR REPLACE FUNCTION block_history_modification() RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'knowledge_item_histories is immutable; UPDATE/DELETE forbidden';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_history_immutable
        BEFORE UPDATE OR DELETE ON knowledge_item_histories
        FOR EACH ROW EXECUTE FUNCTION block_history_modification();
        """
    )

    # ── I3：categories 同層唯一（partial unique index）────────────────────
    # COALESCE 處理 parent_id IS NULL 的情況（NULL 不參與一般 UNIQUE 比對）
    op.execute(
        """
        CREATE UNIQUE INDEX uq_cat_agent_parent_name
        ON categories (
            agent_id,
            COALESCE(parent_id, '00000000-0000-0000-0000-000000000000'),
            name
        )
        """
    )

    # ── I7：knowledge_items.locked_at partial index ────────────────────────
    op.execute(
        "CREATE INDEX idx_ki_locked_at ON knowledge_items(locked_at) "
        "WHERE locked_at IS NOT NULL"
    )

    # ── I8：audit_logs.diff GIN 索引 ────────────────────────────────────────
    op.execute("CREATE INDEX idx_al_diff_gin ON audit_logs USING GIN (diff)")


def downgrade() -> None:
    # I8
    op.execute("DROP INDEX IF EXISTS idx_al_diff_gin")
    # I7
    op.execute("DROP INDEX IF EXISTS idx_ki_locked_at")
    # I3
    op.execute("DROP INDEX IF EXISTS uq_cat_agent_parent_name")
    # I2
    op.execute("DROP TRIGGER IF EXISTS trg_history_immutable ON knowledge_item_histories")
    op.execute("DROP FUNCTION IF EXISTS block_history_modification()")

    # I1：外鍵還原為無 ondelete（保持原 fk 名稱，無 ON DELETE 子句即預設 NO ACTION）
    for table, fk_name, local_col, ref_table, ref_col, _ondelete in _FK_CHANGES:
        op.execute(f'ALTER TABLE {table} DROP CONSTRAINT IF EXISTS "{fk_name}"')
        op.execute(
            f'ALTER TABLE {table} '
            f'ADD CONSTRAINT "{fk_name}" '
            f"FOREIGN KEY ({local_col}) REFERENCES {ref_table}({ref_col})"
        )
    # 還原 knowledge_items.created_by NOT NULL
    op.execute(
        "ALTER TABLE knowledge_items ALTER COLUMN created_by SET NOT NULL"
    )

    # I6
    op.execute("ALTER TABLE sync_logs ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE knowledge_items ALTER COLUMN status DROP DEFAULT")

    # I5
    op.execute("ALTER TABLE sync_logs ALTER COLUMN output_file TYPE VARCHAR(500)")
    op.execute("ALTER TABLE agents ALTER COLUMN ingest_script_path TYPE VARCHAR(255)")
    op.execute("ALTER TABLE agents ALTER COLUMN txt_output_path TYPE VARCHAR(255)")

    # B3：TIMESTAMPTZ → TIMESTAMP（剝除 timezone，存 UTC 後的 naive 值）
    for table, column in _TIMESTAMP_COLUMNS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} "
            f"TYPE TIMESTAMP "
            f"USING {column} AT TIME ZONE 'UTC'"
        )

    # N4：放鬆 agents.created_at NOT NULL（還原至 001 的 nullable=True 狀態）
    op.execute("ALTER TABLE agents ALTER COLUMN created_at DROP NOT NULL")

    # B2：移除 UUID server_default（pgcrypto 不卸載，避免影響其他物件）
    for table in _UUID_PK_TABLES:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN id DROP DEFAULT")
