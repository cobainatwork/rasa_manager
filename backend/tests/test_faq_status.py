"""
FAQ 狀態機測試：update_faq_status（draft / pending / approved / rejected 等轉換）。
"""
from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from tests._faq_helpers import (
    FAQ_ID,
    _editor_then_faq_se,
    _make_faq,
    _superadmin_then_faq_se,
)
from tests.conftest import AGENT_ID


class TestUpdateFaqStatus:
    def _post_status(
        self,
        client: TestClient,
        mock_db: MagicMock,
        faq: MagicMock,
        new_status: str,
        reason: str | None = None,
        editor_role: str = "editor",
        is_superadmin: bool = False,
    ) -> object:
        if is_superadmin:
            mock_db.query.side_effect = _superadmin_then_faq_se(faq)
        else:
            mock_db.query.side_effect = _editor_then_faq_se(faq, editor_role)

        payload: dict = {"status": new_status}
        if reason:
            payload["reason"] = reason
        return client.patch(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}/status",
            json=payload,
        )

    def test_superadmin_draft_to_approved(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq(status="draft")
        resp = self._post_status(
            client_superadmin, mock_db, faq, "approved", is_superadmin=True
        )
        assert resp.status_code == 200  # type: ignore[union-attr]

    def test_superadmin_pending_to_rejected_requires_reason(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq(status="pending")
        resp = self._post_status(
            client_superadmin, mock_db, faq, "rejected", is_superadmin=True
        )
        assert resp.status_code == 400  # type: ignore[union-attr]
        assert resp.json()["detail"]["code"] == "VALIDATION_ERROR"  # type: ignore[union-attr]

    def test_superadmin_pending_to_rejected_with_reason(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq(status="pending")
        resp = self._post_status(
            client_superadmin,
            mock_db,
            faq,
            "rejected",
            reason="內容不符標準",
            is_superadmin=True,
        )
        assert resp.status_code == 200  # type: ignore[union-attr]

    def test_editor_cannot_approve(
        self, client_editor: TestClient, mock_db: MagicMock
    ) -> None:
        """Editor 無法從 pending 直接 approve。"""
        faq = _make_faq(status="pending")
        resp = self._post_status(
            client_editor, mock_db, faq, "approved", editor_role="editor"
        )
        assert resp.status_code == 403  # type: ignore[union-attr]

    def test_reviewer_can_approve_pending(
        self, client_reviewer: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq(status="pending")
        resp = self._post_status(
            client_reviewer, mock_db, faq, "approved", editor_role="reviewer"
        )
        assert resp.status_code == 200  # type: ignore[union-attr]

    def test_invalid_transition_returns_403(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        """approved → pending 不在 superadmin 的允許轉換中。"""
        faq = _make_faq(status="approved")
        resp = self._post_status(
            client_superadmin, mock_db, faq, "pending", is_superadmin=True
        )
        assert resp.status_code == 403  # type: ignore[union-attr]

    def test_faq_not_found_returns_404(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        resp = self._post_status(
            client_superadmin, mock_db, None, "approved", is_superadmin=True  # type: ignore[arg-type]
        )
        assert resp.status_code == 404  # type: ignore[union-attr]
