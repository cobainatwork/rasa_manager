"""fix: drop FK constraints from immutable knowledge_item_histories table

Revision ID: 003
Revises: 002
Create Date: 2026-05-02 00:00:00.000000

knowledge_item_histories 是不可變（append-only）審計表，migration 002 加入
trg_history_immutable 觸發器（BEFORE UPDATE/DELETE 全封鎖），但 item_id /
category_id / saved_by 三欄位仍帶有 ON DELETE SET NULL FK 約束。

當父表記錄被刪除時，PostgreSQL 會試圖 UPDATE knowledge_item_histories
SET <col> = NULL，觸發器攔截並拋出異常，導致刪除操作回傳 500。

修復：移除這三個 FK 約束。歷史記錄保留原始 UUID 作為歷史參照（
即使父記錄已刪除），符合不可變審計日誌的正確設計模式。
"""
from __future__ import annotations
from typing import Sequence, Union

from alembic import op


revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_HISTORY_FK_NAMES = (
    "knowledge_item_histories_item_id_fkey",
    "knowledge_item_histories_category_id_fkey",
    "knowledge_item_histories_saved_by_fkey",
)


def upgrade() -> None:
    for fk_name in _HISTORY_FK_NAMES:
        op.execute(
            f'ALTER TABLE knowledge_item_histories DROP CONSTRAINT IF EXISTS "{fk_name}"'
        )


def downgrade() -> None:
    # 注意：downgrade 後若 trg_history_immutable 仍存在，ON DELETE SET NULL 仍會衝突
    op.execute(
        'ALTER TABLE knowledge_item_histories '
        'ADD CONSTRAINT "knowledge_item_histories_item_id_fkey" '
        "FOREIGN KEY (item_id) REFERENCES knowledge_items(id) ON DELETE SET NULL"
    )
    op.execute(
        'ALTER TABLE knowledge_item_histories '
        'ADD CONSTRAINT "knowledge_item_histories_category_id_fkey" '
        "FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL"
    )
    op.execute(
        'ALTER TABLE knowledge_item_histories '
        'ADD CONSTRAINT "knowledge_item_histories_saved_by_fkey" '
        "FOREIGN KEY (saved_by) REFERENCES users(id) ON DELETE SET NULL"
    )
