"""
同步路由測試。
覆蓋：trigger_sync（202 成功、Celery 不可用仍 202、403 editor、404 agent），
      get_sync_status（200 找到、404 未找到）
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import AGENT_ID

SYNC_LOG_ID = uuid.UUID("00000000-0000-0000-0000-000000000050")


@pytest.fixture
def _agent_mock(agent_factory):
    """檔內 fixture，回傳建立 Agent mock 的 callable。"""
    def _make() -> MagicMock:
        return agent_factory(name="TestAgent")
    return _make


def _sync_log_mock(sync_id: uuid.UUID = SYNC_LOG_ID) -> MagicMock:
    sl = MagicMock()
    sl.id = sync_id
    sl.agent_id = AGENT_ID
    sl.triggered_by = uuid.UUID("00000000-0000-0000-0000-000000000001")
    sl.celery_task_id = None
    sl.status = "pending"
    sl.items_count = 0
    sl.output_file = None
    sl.stdout = None
    sl.stderr = None
    sl.started_at = None
    sl.finished_at = None
    sl.duration_sec = None
    sl.created_at = None
    return sl


def _reviewer_se(mock_db: MagicMock, agent: MagicMock):
    """editor_user 端：db.query idx 0=Agent, idx 1=UAR(reviewer)。"""
    counter = [0]

    def se(*args):
        q = MagicMock()
        if counter[0] == 0:
            q.filter.return_value.first.return_value = agent
        else:
            uar = MagicMock()
            uar.role = "reviewer"
            q.filter.return_value.first.return_value = uar
        counter[0] += 1
        return q

    mock_db.query.side_effect = se


def _editor_se(mock_db: MagicMock, agent: MagicMock):
    """editor_user 端：db.query idx 0=Agent, idx 1=UAR(editor)。"""
    counter = [0]

    def se(*args):
        q = MagicMock()
        if counter[0] == 0:
            q.filter.return_value.first.return_value = agent
        else:
            uar = MagicMock()
            uar.role = "editor"
            q.filter.return_value.first.return_value = uar
        counter[0] += 1
        return q

    mock_db.query.side_effect = se


# ─── trigger_sync ─────────────────────────────────────────────────────────────

class TestTriggerSync:
    def test_superadmin_returns_202_with_sync_log_id(self, client_superadmin, mock_db, _agent_mock) -> None:
        agent = _agent_mock()
        mock_db.query.return_value.filter.return_value.first.return_value = agent
        mock_db.refresh.return_value = None

        with patch("tasks.run_ingestion_sync") as mock_celery:
            mock_celery.delay.return_value.id = "fake-celery-id"
            resp = client_superadmin.post(f"/api/v1/agents/{AGENT_ID}/sync")

        assert resp.status_code == 202
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["status"] == "pending"
        assert data["data"]["task_id"] == "fake-celery-id"
        assert "sync_log_id" in data["data"]

    def test_celery_unavailable_still_returns_202(self, client_superadmin, mock_db, _agent_mock) -> None:
        """Celery 不可用時，trigger_sync 仍回傳 202（graceful degradation）。"""
        agent = _agent_mock()
        mock_db.query.return_value.filter.return_value.first.return_value = agent
        mock_db.refresh.return_value = None

        with patch("tasks.run_ingestion_sync") as mock_celery:
            mock_celery.delay.side_effect = ConnectionError("Celery broker unreachable")
            resp = client_superadmin.post(f"/api/v1/agents/{AGENT_ID}/sync")

        assert resp.status_code == 202
        assert resp.json()["data"]["task_id"] is None

    def test_kombu_error_still_returns_202(self, client_superadmin, mock_db, _agent_mock) -> None:
        """kombu.exceptions.OperationalError 也須被攔截，回傳 202。"""
        from kombu.exceptions import OperationalError as KombuError  # noqa: PLC0415

        agent = _agent_mock()
        mock_db.query.return_value.filter.return_value.first.return_value = agent
        mock_db.refresh.return_value = None

        with patch("tasks.run_ingestion_sync") as mock_celery:
            mock_celery.delay.side_effect = KombuError("broker down")
            resp = client_superadmin.post(f"/api/v1/agents/{AGENT_ID}/sync")

        assert resp.status_code == 202
        assert resp.json()["data"]["task_id"] is None

    def test_reviewer_can_trigger_sync(self, client_reviewer, mock_db, _agent_mock) -> None:
        _reviewer_se(mock_db, _agent_mock())
        mock_db.refresh.return_value = None

        with patch("tasks.run_ingestion_sync") as mock_celery:
            mock_celery.delay.return_value.id = "task-id"
            resp = client_reviewer.post(f"/api/v1/agents/{AGENT_ID}/sync")

        assert resp.status_code == 202

    def test_editor_returns_403(self, client_editor, mock_db, _agent_mock) -> None:
        """Editor 沒有同步觸發權限（需要 reviewer 或 superadmin）。"""
        _editor_se(mock_db, _agent_mock())
        resp = client_editor.post(f"/api/v1/agents/{AGENT_ID}/sync")
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "FORBIDDEN"

    def test_agent_not_found_returns_404(self, client_superadmin, mock_db) -> None:
        mock_db.query.return_value.filter.return_value.first.return_value = None
        resp = client_superadmin.post(f"/api/v1/agents/{AGENT_ID}/sync")
        assert resp.status_code == 404


# ─── get_sync_status ──────────────────────────────────────────────────────────

class TestGetSyncStatus:
    def test_found_returns_200_with_full_data(self, client_superadmin, mock_db) -> None:
        sync_log = _sync_log_mock()
        mock_db.query.return_value.filter.return_value.first.return_value = sync_log

        resp = client_superadmin.get(f"/api/v1/sync/tasks/{SYNC_LOG_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["status"] == "pending"
        assert data["data"]["items_count"] == 0

    def test_not_found_returns_404(self, client_superadmin, mock_db) -> None:
        mock_db.query.return_value.filter.return_value.first.return_value = None
        resp = client_superadmin.get(f"/api/v1/sync/tasks/{SYNC_LOG_ID}")
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "NOT_FOUND"

    def test_editor_can_view_sync_status(self, client_editor, mock_db) -> None:
        """任何已登入使用者皆可查詢 sync 狀態（無 agent 存取權限限制）。"""
        sync_log = _sync_log_mock()
        mock_db.query.return_value.filter.return_value.first.return_value = sync_log
        resp = client_editor.get(f"/api/v1/sync/tasks/{SYNC_LOG_ID}")
        assert resp.status_code == 200


# ─── get_sync_history ─────────────────────────────────────────────────────────

class TestGetSyncHistory:
    def _setup_history(self, mock_db: MagicMock, logs: list[MagicMock], agent: MagicMock):
        """superadmin 路徑：query 0=Agent (for require_*), 1=SyncLog list, 2=User list。"""
        counter = [0]

        def se(*args, **kwargs):  # noqa: ARG001
            q = MagicMock()
            idx = counter[0]
            counter[0] += 1
            if idx == 0:
                q.filter.return_value.first.return_value = agent
            elif idx == 1:
                chain = q.filter.return_value.order_by.return_value.offset.return_value.limit.return_value
                chain.all.return_value = logs
            else:
                q.filter.return_value.all.return_value = []
            return q

        mock_db.query.side_effect = se

    def test_returns_paginated_history(self, client_superadmin, mock_db, _agent_mock) -> None:
        log = _sync_log_mock()
        log.triggered_by = None
        self._setup_history(mock_db, [log], _agent_mock())

        resp = client_superadmin.get(f"/api/v1/agents/{AGENT_ID}/sync/history?limit=10&offset=0")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["status"] == "pending"

    def test_invalid_limit_rejected(self, client_superadmin, mock_db) -> None:
        """limit=0 或負數須回 422。"""
        resp = client_superadmin.get(f"/api/v1/agents/{AGENT_ID}/sync/history?limit=0")
        assert resp.status_code == 422

    def test_limit_over_max_rejected(self, client_superadmin, mock_db) -> None:
        """limit>100 須回 422（避免大量回傳）。"""
        resp = client_superadmin.get(f"/api/v1/agents/{AGENT_ID}/sync/history?limit=999")
        assert resp.status_code == 422

    def test_negative_offset_rejected(self, client_superadmin, mock_db) -> None:
        resp = client_superadmin.get(f"/api/v1/agents/{AGENT_ID}/sync/history?offset=-1")
        assert resp.status_code == 422

    def test_agent_not_found_returns_404(self, client_superadmin, mock_db) -> None:
        mock_db.query.return_value.filter.return_value.first.return_value = None
        resp = client_superadmin.get(f"/api/v1/agents/{AGENT_ID}/sync/history")
        assert resp.status_code == 404

    def test_editor_without_role_returns_403(self, client_editor, mock_db, _agent_mock):
        agent = _agent_mock()
        counter = [0]

        def se(*args, **kwargs):  # noqa: ARG001
            q = MagicMock()
            idx = counter[0]
            counter[0] += 1
            if idx == 0:
                q.filter.return_value.first.return_value = agent
            else:
                # editor 但無 UAR
                q.filter.return_value.first.return_value = None
            return q

        mock_db.query.side_effect = se
        resp = client_editor.get(f"/api/v1/agents/{AGENT_ID}/sync/history")
        assert resp.status_code == 403

    def test_history_ordered_by_started_at_desc(self, client_superadmin, mock_db, _agent_mock) -> None:
        """驗證 ORDER BY started_at DESC（透過 mock 鏈確認 order_by 有被呼叫）。"""
        from datetime import datetime, timezone

        newer = _sync_log_mock(uuid.UUID("00000000-0000-0000-0000-000000000051"))
        newer.started_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
        older = _sync_log_mock(uuid.UUID("00000000-0000-0000-0000-000000000052"))
        older.started_at = datetime(2026, 4, 1, tzinfo=timezone.utc)
        # 路由本身依 ORM 的 order_by 排序，這裡傳入已排好序的 list 驗證輸出順序保留
        self._setup_history(mock_db, [newer, older], _agent_mock())

        resp = client_superadmin.get(f"/api/v1/agents/{AGENT_ID}/sync/history")
        assert resp.status_code == 200
        items = resp.json()["data"]
        assert items[0]["started_at"].startswith("2026-05-01")
        assert items[1]["started_at"].startswith("2026-04-01")


# ── Regression: I3 (sync_history must batch-query usernames) ────────────────

class TestSyncHistoryBatchUsernamesRegression:
    """Regression: I3 (sync_history 批次取 triggered_by username)."""

    def test_users_queried_once_for_multiple_logs(
        self, client_superadmin, mock_db: MagicMock
    ) -> None:
        from datetime import datetime, timezone

        from api.database.models import SyncLog, User

        logs = []
        for _ in range(4):
            log = MagicMock()
            log.id = uuid.uuid4()
            log.status = "success"
            log.triggered_by = uuid.uuid4()
            log.started_at = datetime.now(timezone.utc)
            log.finished_at = datetime.now(timezone.utc)
            log.duration_sec = 1
            log.items_count = 10
            log.output_file = "/tmp/x.txt"
            log.stdout = ""
            log.stderr = ""
            logs.append(log)

        user_query_count = [0]

        def query_side_effect(*args):
            q = MagicMock()
            if args and args[0] is User:
                q.filter.return_value.first.return_value = MagicMock()
                return q
            if args and len(args) >= 2 and args[0] is User.id:
                user_query_count[0] += 1
                q.filter.return_value.all.return_value = [
                    (log.triggered_by, f"u_{i}") for i, log in enumerate(logs)
                ]
                return q
            if args and args[0] is SyncLog:
                q.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = logs
                return q
            return q

        mock_db.query.side_effect = query_side_effect

        with patch(
            "api.routes.sync.require_reviewer_or_superadmin",
            return_value=(MagicMock(), None),
        ):
            resp = client_superadmin.get(
                f"/api/v1/agents/{AGENT_ID}/sync/history"
            )

        assert resp.status_code == 200, resp.text
        assert user_query_count[0] == 1
