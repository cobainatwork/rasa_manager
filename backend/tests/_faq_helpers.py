"""
FAQ 測試共用 helper。

供 test_faq.py / test_faq_lock.py / test_faq_status.py / test_faq_history.py 共用。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

from tests.conftest import AGENT_ID, EDITOR_ID

# ── 測試常數 ──────────────────────────────────────────────────────────────────
CATEGORY_ID = uuid.UUID("00000000-0000-0000-0000-000000000020")
FAQ_ID      = uuid.UUID("00000000-0000-0000-0000-000000000030")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _agent_mock() -> MagicMock:
    a = MagicMock()
    a.id = AGENT_ID
    return a


def _role_mock(role: str) -> MagicMock:
    r = MagicMock()
    r.role = role
    return r


def _make_faq(
    faq_id: uuid.UUID = FAQ_ID,
    status: str = "draft",
    locked_by: uuid.UUID | None = None,
    locked_at: datetime | None = None,
    version: int = 1,
) -> MagicMock:
    item = MagicMock()
    item.id = faq_id
    item.agent_id = AGENT_ID
    item.category_id = CATEGORY_ID
    item.question = "測試問題"
    item.answer = "測試答案"
    item.tags = ["tag1"]
    item.status = status
    item.version = version
    item.locked_by = locked_by
    item.locked_at = locked_at
    item.created_by = EDITOR_ID
    item.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    item.updated_at = datetime(2025, 1, 2, tzinfo=timezone.utc)
    return item


def _superadmin_then_faq_se(faq: MagicMock | None, extra_faq_chain: dict | None = None):
    """
    side_effect：
      第 0 次 query()：Agent 查詢（供 require_agent_access superadmin 路徑使用）
      第 1 次 query()：KnowledgeItem 查詢（支援 .first() 與 list 查詢）
      第 2+ 次 query()：其他查詢（預設回傳空 MagicMock）
    """
    counter = [0]

    def se(model: object) -> MagicMock:
        q = MagicMock()
        idx = counter[0]
        counter[0] += 1

        if idx == 0:
            q.filter.return_value.first.return_value = _agent_mock()
        elif idx == 1:
            filtered = MagicMock()
            filtered.first.return_value = faq
            filtered.filter.return_value = filtered
            filtered.count.return_value = 1 if faq else 0
            filtered.order_by.return_value.offset.return_value.limit.return_value.all.return_value = (
                [faq] if faq else []
            )
            filtered.with_for_update.return_value.first.return_value = faq
            q.filter.return_value = filtered
            if extra_faq_chain:
                for k, v in extra_faq_chain.items():
                    setattr(filtered, k, v)
        else:
            q.filter.return_value.first.return_value = None

        return q

    return se


def _editor_then_faq_se(faq: MagicMock | None, role: str = "editor"):
    """
    side_effect（editor / reviewer 路徑）：
      第 0 次：Agent
      第 1 次：UserAgentRole
      第 2 次：KnowledgeItem
    """
    counter = [0]

    def se(model: object) -> MagicMock:
        q = MagicMock()
        idx = counter[0]
        counter[0] += 1

        if idx == 0:
            q.filter.return_value.first.return_value = _agent_mock()
        elif idx == 1:
            q.filter.return_value.first.return_value = _role_mock(role)
        elif idx == 2:
            filtered = MagicMock()
            filtered.first.return_value = faq
            filtered.filter.return_value = filtered
            filtered.count.return_value = 1 if faq else 0
            filtered.order_by.return_value.offset.return_value.limit.return_value.all.return_value = (
                [faq] if faq else []
            )
            filtered.with_for_update.return_value.first.return_value = faq
            q.filter.return_value = filtered
        else:
            q.filter.return_value.first.return_value = None

        return q

    return se
