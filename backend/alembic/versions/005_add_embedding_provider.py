"""add embedding_provider and embedding_model to agents

Revision ID: 005
Revises: 004
Create Date: 2026-06-02 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """每個 agent 可獨立選擇 embedding provider（openai 雲端 / local 地端）。

    既有 agent 維持 OpenAI 雲端 + text-embedding-3-small 行為（向後相容）。
    NOT NULL DEFAULT 讓 ALTER 原子完成，不需 backfill 階段。
    """
    op.add_column(
        "agents",
        sa.Column(
            "embedding_provider",
            sa.String(20),
            nullable=False,
            server_default="openai",
        ),
    )
    op.add_column(
        "agents",
        sa.Column(
            "embedding_model",
            sa.String(100),
            nullable=False,
            server_default="text-embedding-3-small",
        ),
    )


def downgrade() -> None:
    op.drop_column("agents", "embedding_model")
    op.drop_column("agents", "embedding_provider")
