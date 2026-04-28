"""
稽核日誌路由測試：list_audit_logs 含過濾、分頁、username JOIN。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from tests.conftest import AGENT_ID, SUPERADMIN_ID

LOG_ID = uuid.UUID("00000000-0000-0000-0000-000000000050")


def _log_mock(
    action: str = "create",
    performed_by: uuid.UUID | None = SUPERADMIN_ID,
) -> MagicMock:
    log = MagicMock()
    log.id = LOG_ID
    log.agent_id = AGENT_ID
    log.item_id = uuid.UUID("00000000-0000-0000-0000-000000000030")
    log.action = action
    log.performed_by = performed_by
    log.diff = {"question": {"before": "old", "after": "new"}}
    log.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return log


def _make_se(logs: list[MagicMock], total: int = 1, user_mock: MagicMock | None = None) -> object:
    """
    side_effect 序列：
      0: Agent 查詢（require_agent_access superadmin 路徑）
      1: AuditLog 查詢（含 filter / count / order_by / offset / limit / all）
      2: User 查詢（JOIN username）
    """
    counter = [0]

    def se(*args: object) -> MagicMock:
        q = MagicMock()
        idx = counter[0]
        counter[0] += 1

        if idx == 0:
            # Agent
            agent = MagicMock()
            agent.id = AGENT_ID
            q.filter.return_value.first.return_value = agent
        elif idx == 1:
            # AuditLog：支援鏈式呼叫
            filtered = MagicMock()
            filtered.count.return_value = total
            filtered.filter.return_value = filtered
            filtered.order_by.return_value.offset.return_value.limit.return_value.all.return_value = logs
            q.filter.return_value = filtered
        else:
            # User IN 查詢（取得 username）
            if user_mock:
                q.filter.return_value.all.return_value = [user_mock]
            else:
                q.filter.return_value.all.return_value = []

        return q

    return se


class TestListAuditLogs:
    def test_superadmin_returns_200_with_list(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        log = _log_mock()
        mock_db.query.side_effect = _make_se([log])
        resp = client_superadmin.get(f"/api/v1/agents/{AGENT_ID}/audit-logs")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["total"] == 1
        assert len(body["data"]["items"]) == 1
        item = body["data"]["items"][0]
        assert item["action"] == "create"
        assert item["id"] == str(LOG_ID)

    def test_editor_returns_200(
        self, client_editor: TestClient, mock_db: MagicMock
    ) -> None:
        """Editor 也有 agent access，可查詢 audit log。"""
        log = _log_mock()
        # editor 路徑：0=Agent, 1=UAR, 2=AuditLog, 3=User
        counter = [0]

        def se(*args: object) -> MagicMock:
            q = MagicMock()
            idx = counter[0]
            counter[0] += 1
            if idx == 0:
                agent = MagicMock()
                agent.id = AGENT_ID
                q.filter.return_value.first.return_value = agent
            elif idx == 1:
                role = MagicMock()
                role.role = "editor"
                q.filter.return_value.first.return_value = role
            elif idx == 2:
                filtered = MagicMock()
                filtered.count.return_value = 1
                filtered.filter.return_value = filtered
                filtered.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [log]
                q.filter.return_value = filtered
            else:
                q.filter.return_value.all.return_value = []
            return q

        mock_db.query.side_effect = se
        resp = client_editor.get(f"/api/v1/agents/{AGENT_ID}/audit-logs")
        assert resp.status_code == 200

    def test_unauthenticated_returns_401(self, client_no_auth: TestClient) -> None:
        resp = client_no_auth.get(f"/api/v1/agents/{AGENT_ID}/audit-logs")
        assert resp.status_code == 401

    def test_empty_list_returns_zero_total(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        mock_db.query.side_effect = _make_se([], total=0)
        resp = client_superadmin.get(f"/api/v1/agents/{AGENT_ID}/audit-logs")
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 0
        assert resp.json()["data"]["items"] == []

    def test_action_filter_applied(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        log = _log_mock(action="approve")
        mock_db.query.side_effect = _make_se([log])
        resp = client_superadmin.get(
            f"/api/v1/agents/{AGENT_ID}/audit-logs?action=approve"
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["items"][0]["action"] == "approve"

    def test_date_range_filter_accepted(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        mock_db.query.side_effect = _make_se([], total=0)
        resp = client_superadmin.get(
            f"/api/v1/agents/{AGENT_ID}/audit-logs"
            "?start_date=2025-01-01T00:00:00&end_date=2025-12-31T23:59:59"
        )
        assert resp.status_code == 200

    def test_pagination_params_reflected(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        mock_db.query.side_effect = _make_se([], total=0)
        resp = client_superadmin.get(
            f"/api/v1/agents/{AGENT_ID}/audit-logs?page=2&per_page=10"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["page"] == 2
        assert data["per_page"] == 10

    def test_username_resolved_from_user_join(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        """performed_by 有值時，應透過 JOIN 取得 performed_by_username。"""
        log = _log_mock(performed_by=SUPERADMIN_ID)
        user = MagicMock()
        user.id = SUPERADMIN_ID
        user.username = "admin"
        mock_db.query.side_effect = _make_se([log], user_mock=user)
        resp = client_superadmin.get(f"/api/v1/agents/{AGENT_ID}/audit-logs")
        assert resp.status_code == 200
        item = resp.json()["data"]["items"][0]
        assert item["performed_by_username"] == "admin"

    def test_performed_by_null_log(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        """performed_by 為 None 時，不發出 User 查詢，performed_by_username 為 None。"""
        log = _log_mock(performed_by=None)
        mock_db.query.side_effect = _make_se([log])
        resp = client_superadmin.get(f"/api/v1/agents/{AGENT_ID}/audit-logs")
        assert resp.status_code == 200
        item = resp.json()["data"]["items"][0]
        assert item["performed_by"] is None
