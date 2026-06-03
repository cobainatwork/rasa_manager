"""add embedding_provider and embedding_model snapshot columns to sync_logs

Revision ID: 006
Revises: 005
Create Date: 2026-06-04 00:00:00.000000

每次同步開始時，從 agent.embedding_provider / embedding_model 拷一份至 sync_logs，
凍結成不可變快照。日後 agent 切換 embedding model，歷史紀錄不會「歪掉」。

既有 row 為 NULL（不 backfill），由前端顯示「—」表示缺資料。
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sync_logs",
        sa.Column("embedding_provider", sa.String(20), nullable=True),
    )
    op.add_column(
        "sync_logs",
        sa.Column("embedding_model", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sync_logs", "embedding_model")
    op.drop_column("sync_logs", "embedding_provider")
