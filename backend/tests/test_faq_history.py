"""
FAQ 歷史與回復測試：get_histories、rollback_faq。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from tests._faq_helpers import (
    CATEGORY_ID,
    FAQ_ID,
    _agent_mock,
    _make_faq,
)
from tests.conftest import AGENT_ID, SUPERADMIN_ID


# ── get_histories ─────────────────────────────────────────────────────────────

class TestGetHistories:
    def _make_history(self) -> MagicMock:
        h = MagicMock()
        h.id = uuid.UUID("00000000-0000-0000-0000-000000000040")
        h.item_id = FAQ_ID
        h.version = 1
        h.question = "歷史問題"
        h.answer = "歷史答案"
        h.category_id = CATEGORY_ID
        h.saved_by = SUPERADMIN_ID
        h.action = "create"
        h.action_reason = None
        h.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
        return h

    def _histories_se(self, faq: MagicMock | None, histories: list) -> object:
        """
        side_effect：
          0: Agent
          1: KnowledgeItem
          2: KnowledgeItemHistory（order_by / all）
        """
        counter = [0]

        def se(model: object) -> MagicMock:
            q = MagicMock()
            idx = counter[0]
            counter[0] += 1
            if idx == 0:
                q.filter.return_value.first.return_value = _agent_mock()
            elif idx == 1:
                q.filter.return_value.first.return_value = faq
            else:
                q.filter.return_value.order_by.return_value.all.return_value = histories
            return q

        return se

    def test_get_histories_success(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq()
        history = self._make_history()
        mock_db.query.side_effect = self._histories_se(faq, [history])
        resp = client_superadmin.get(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}/histories"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert len(body["data"]) == 1
        assert body["data"][0]["action"] == "create"

    def test_get_histories_faq_not_found(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        mock_db.query.side_effect = self._histories_se(None, [])
        resp = client_superadmin.get(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}/histories"
        )
        assert resp.status_code == 404

    def test_get_histories_empty(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq()
        mock_db.query.side_effect = self._histories_se(faq, [])
        resp = client_superadmin.get(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}/histories"
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == []


# ── rollback_faq ──────────────────────────────────────────────────────────────

class TestRollbackFaq:
    def _rollback_se(
        self,
        faq: MagicMock | None,
        history: MagicMock | None,
    ) -> object:
        """
        side_effect：
          0: Agent
          1: KnowledgeItem
          2: KnowledgeItemHistory（target version）
        """
        counter = [0]

        def se(model: object) -> MagicMock:
            q = MagicMock()
            idx = counter[0]
            counter[0] += 1
            if idx == 0:
                q.filter.return_value.first.return_value = _agent_mock()
            elif idx == 1:
                q.filter.return_value.first.return_value = faq
                q.filter.return_value.with_for_update.return_value.first.return_value = faq
            else:
                q.filter.return_value.first.return_value = history
            return q

        return se

    def _make_history(self, version: int = 1) -> MagicMock:
        h = MagicMock()
        h.version = version
        h.question = "回復的問題"
        h.answer = "回復的答案"
        h.category_id = CATEGORY_ID
        return h

    def test_rollback_success_returns_200(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq(status="approved", version=3)
        history = self._make_history(version=1)
        mock_db.query.side_effect = self._rollback_se(faq, history)
        mock_db.refresh.side_effect = None

        resp = client_superadmin.post(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}/rollback",
            json={"version": 1},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "已回復至版本" in body["message"]
        assert faq.status == "draft"

    def test_rollback_faq_not_found(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        mock_db.query.side_effect = self._rollback_se(None, None)
        resp = client_superadmin.post(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}/rollback",
            json={"version": 1},
        )
        assert resp.status_code == 404

    def test_rollback_version_not_found(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq(version=3)
        mock_db.query.side_effect = self._rollback_se(faq, None)
        resp = client_superadmin.post(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}/rollback",
            json={"version": 99},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "NOT_FOUND"
