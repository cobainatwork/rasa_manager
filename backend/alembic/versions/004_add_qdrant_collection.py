"""add qdrant_collection to agents

Revision ID: 004
Revises: 003
Create Date: 2026-05-12 00:00:00.000000

agents 表新增 qdrant_collection 欄位（VARCHAR 255, NOT NULL, UNIQUE）。
現有 agent 以 'agent_' || id::text 作為回填預設值，維持向後相容。
"""
from __future__ import annotations
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 先加可空欄位（避免空表以外的現有資料違反 NOT NULL）
    op.add_column(
        "agents",
        sa.Column("qdrant_collection", sa.String(255), nullable=True),
    )
    # 2. 回填現有 agent：以 'agent_' || id::text 作為預設 collection 名稱
    op.execute(
        "UPDATE agents SET qdrant_collection = 'agent_' || id::text "
        "WHERE qdrant_collection IS NULL"
    )
    # 3. 加 NOT NULL 約束
    op.alter_column("agents", "qdrant_collection", nullable=False)
    # 4. 加 UNIQUE 約束（每個 Agent 使用獨立的 Qdrant collection）
    op.create_unique_constraint(
        "uq_agents_qdrant_collection", "agents", ["qdrant_collection"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_agents_qdrant_collection", "agents", type_="unique")
    op.drop_column("agents", "qdrant_collection")
