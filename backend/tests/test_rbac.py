"""
RBAC 權限矩陣測試：superadmin / reviewer / editor 三角色。

關鍵設計：
- require_agent_access 使用 db.query(Agent).filter(id).first() → db.query(UAR).filter(uid, aid).first()
  兩次查詢共用同一個 MagicMock 鏈，用 side_effect 的 call_count 區分回傳值
- require_reviewer_or_superadmin 委派給 require_agent_access，再加角色驗證
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from tests.conftest import AGENT_ID, build_agent_access_query_se


@pytest.fixture
def _agent_mock(agent_factory):
    """檔內 fixture，回傳建立極簡 Agent mock 的 callable。"""
    def _make() -> MagicMock:
        return agent_factory()
    return _make


# ── require_agent_access ──────────────────────────────────────────────────────

class TestRequireAgentAccess:
    def test_superadmin_always_allowed(
        self, mock_db: MagicMock, superadmin_user: MagicMock, _agent_mock
    ) -> None:
        from api.dependencies import require_agent_access

        mock_db.query.side_effect = build_agent_access_query_se(
            agent=_agent_mock()
        )
        agent, role = require_agent_access(AGENT_ID, superadmin_user, mock_db)
        assert agent is not None
        assert role is None  # superadmin 無角色

    def test_editor_with_role_allowed(
        self, mock_db: MagicMock, editor_user: MagicMock, _agent_mock
    ) -> None:
        from api.dependencies import require_agent_access

        mock_db.query.side_effect = build_agent_access_query_se(
            agent=_agent_mock(), uar_role="editor"
        )
        agent, role = require_agent_access(AGENT_ID, editor_user, mock_db)
        assert role == "editor"

    def test_user_without_role_forbidden(
        self, mock_db: MagicMock, editor_user: MagicMock, _agent_mock
    ) -> None:
        from api.dependencies import require_agent_access
        from fastapi import HTTPException

        mock_db.query.side_effect = build_agent_access_query_se(
            agent=_agent_mock(), uar_role=None  # UAR 不存在 → 403
        )

        with pytest.raises(HTTPException) as exc_info:
            require_agent_access(AGENT_ID, editor_user, mock_db)

        assert exc_info.value.status_code == 403

    def test_agent_not_found_raises_404(
        self, mock_db: MagicMock, editor_user: MagicMock
    ) -> None:
        from api.dependencies import require_agent_access
        from fastapi import HTTPException

        mock_db.query.side_effect = build_agent_access_query_se(
            agent=None  # Agent 不存在 → 404
        )

        with pytest.raises(HTTPException) as exc_info:
            require_agent_access(AGENT_ID, editor_user, mock_db)

        assert exc_info.value.status_code == 404


# ── require_reviewer_or_superadmin ────────────────────────────────────────────

class TestRequireReviewerOrSuperadmin:
    def test_superadmin_passes(
        self, mock_db: MagicMock, superadmin_user: MagicMock, _agent_mock
    ) -> None:
        from api.dependencies import require_reviewer_or_superadmin

        mock_db.query.side_effect = build_agent_access_query_se(
            agent=_agent_mock()
        )
        require_reviewer_or_superadmin(AGENT_ID, superadmin_user, mock_db)

    def test_reviewer_passes(
        self, mock_db: MagicMock, reviewer_user: MagicMock, _agent_mock
    ) -> None:
        from api.dependencies import require_reviewer_or_superadmin

        mock_db.query.side_effect = build_agent_access_query_se(
            agent=_agent_mock(), uar_role="reviewer"
        )
        agent, role = require_reviewer_or_superadmin(AGENT_ID, reviewer_user, mock_db)
        assert role == "reviewer"

    def test_editor_forbidden(
        self, mock_db: MagicMock, editor_user: MagicMock, _agent_mock
    ) -> None:
        from api.dependencies import require_reviewer_or_superadmin
        from fastapi import HTTPException

        mock_db.query.side_effect = build_agent_access_query_se(
            agent=_agent_mock(), uar_role="editor"
        )

        with pytest.raises(HTTPException) as exc_info:
            require_reviewer_or_superadmin(AGENT_ID, editor_user, mock_db)

        assert exc_info.value.status_code == 403


# ── 使用者管理 API（僅 superadmin）────────────────────────────────────────────

class TestUserManagementRBAC:
    def test_superadmin_can_list_users(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        mock_db.query.return_value.all.return_value = []
        resp = client_superadmin.get("/api/v1/users")
        assert resp.status_code == 200

    def test_editor_cannot_list_users(
        self, client_editor: TestClient, mock_db: MagicMock
    ) -> None:
        resp = client_editor.get("/api/v1/users")
        assert resp.status_code == 403

    def test_reviewer_cannot_list_users(
        self, client_reviewer: TestClient, mock_db: MagicMock
    ) -> None:
        resp = client_reviewer.get("/api/v1/users")
        assert resp.status_code == 403
