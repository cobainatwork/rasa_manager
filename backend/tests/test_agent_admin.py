"""
agent_admin.py 路由測試。

覆蓋：
- test-connection：happy path、agent 404、未設定 url、Rasa 5xx、逾時、連線失敗、403 editor
- validate-script：happy path、agent 404、未設定路徑、檔案不存在、路徑遍歷、403 editor
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import httpx

AGENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")


def _agent_mock(rasa_url: str | None = "http://rasa:5005",
                ingest_path: str | None = "/opt/scripts/ingest.py") -> MagicMock:
    a = MagicMock()
    a.id = AGENT_ID
    a.name = "TestAgent"
    a.rasa_rest_url = rasa_url
    a.ingest_script_path = ingest_path
    return a


# ─── test-connection ──────────────────────────────────────────────────────────

class TestTestConnection:
    def test_happy_path_returns_ok_true(self, client_superadmin, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = _agent_mock()

        with patch("api.routes.agent_admin.httpx.Client") as mock_client_cls:
            client_inst = mock_client_cls.return_value.__enter__.return_value
            resp_mock = MagicMock()
            resp_mock.status_code = 200
            client_inst.get.return_value = resp_mock

            resp = client_superadmin.post(f"/api/v1/agents/{AGENT_ID}/test-connection")

        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["ok"] is True
        assert body["status_code"] == 200
        assert body["latency_ms"] is not None

    def test_agent_not_found_returns_404(self, client_superadmin, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None
        resp = client_superadmin.post(f"/api/v1/agents/{AGENT_ID}/test-connection")
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "NOT_FOUND"

    def test_url_not_configured_returns_friendly_error(self, client_superadmin, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = _agent_mock(rasa_url=None)
        resp = client_superadmin.post(f"/api/v1/agents/{AGENT_ID}/test-connection")
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["ok"] is False
        assert "未設定" in body["error"]

    def test_rasa_returns_5xx_returns_ok_false(self, client_superadmin, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = _agent_mock()

        with patch("api.routes.agent_admin.httpx.Client") as mock_client_cls:
            client_inst = mock_client_cls.return_value.__enter__.return_value
            resp_mock = MagicMock()
            resp_mock.status_code = 503
            client_inst.get.return_value = resp_mock

            resp = client_superadmin.post(f"/api/v1/agents/{AGENT_ID}/test-connection")

        body = resp.json()["data"]
        assert body["ok"] is False
        assert body["status_code"] == 503
        assert body["error"] == "HTTP 503"

    def test_rasa_timeout_returns_friendly_error(self, client_superadmin, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = _agent_mock()

        with patch("api.routes.agent_admin.httpx.Client") as mock_client_cls:
            client_inst = mock_client_cls.return_value.__enter__.return_value
            client_inst.get.side_effect = httpx.TimeoutException("timeout")

            resp = client_superadmin.post(f"/api/v1/agents/{AGENT_ID}/test-connection")

        body = resp.json()["data"]
        assert body["ok"] is False
        assert body["error"] == "連線逾時"
        # 不洩漏內部訊息
        assert "timeout" not in body["error"]

    def test_rasa_connection_error_returns_friendly_error(self, client_superadmin, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = _agent_mock()

        with patch("api.routes.agent_admin.httpx.Client") as mock_client_cls:
            client_inst = mock_client_cls.return_value.__enter__.return_value
            client_inst.get.side_effect = httpx.ConnectError("DNS resolution failed for internal.host")

            resp = client_superadmin.post(f"/api/v1/agents/{AGENT_ID}/test-connection")

        body = resp.json()["data"]
        assert body["ok"] is False
        assert body["error"] == "連線失敗"
        # 不洩漏內部訊息
        assert "DNS" not in body["error"]
        assert "internal.host" not in body["error"]

    def test_editor_returns_403(self, client_editor, mock_db):
        resp = client_editor.post(f"/api/v1/agents/{AGENT_ID}/test-connection")
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "FORBIDDEN"


# ─── validate-script ──────────────────────────────────────────────────────────

class TestValidateScript:
    def test_happy_path_returns_exists_true(self, client_superadmin, mock_db, tmp_path):
        script = tmp_path / "ingest.py"
        script.write_text("print('hi')\n", encoding="utf-8")

        mock_db.query.return_value.filter.return_value.first.return_value = _agent_mock(
            ingest_path=str(script.resolve())
        )

        resp = client_superadmin.post(f"/api/v1/agents/{AGENT_ID}/validate-script")
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["exists"] is True
        assert body["executable"] is True
        assert body["size_bytes"] > 0

    def test_agent_not_found_returns_404(self, client_superadmin, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None
        resp = client_superadmin.post(f"/api/v1/agents/{AGENT_ID}/validate-script")
        assert resp.status_code == 404

    def test_script_path_not_configured(self, client_superadmin, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = _agent_mock(ingest_path=None)
        resp = client_superadmin.post(f"/api/v1/agents/{AGENT_ID}/validate-script")
        body = resp.json()["data"]
        assert body["exists"] is False
        assert "未設定" in body["error"]

    def test_script_file_missing(self, client_superadmin, mock_db, tmp_path):
        # 使用 tmp_path 確保是當前平台的合法絕對路徑
        missing = tmp_path / "does_not_exist_xyz.py"
        mock_db.query.return_value.filter.return_value.first.return_value = _agent_mock(
            ingest_path=str(missing.resolve())
        )
        resp = client_superadmin.post(f"/api/v1/agents/{AGENT_ID}/validate-script")
        body = resp.json()["data"]
        assert body["exists"] is False
        assert body["error"] == "腳本檔案不存在"

    def test_path_traversal_rejected(self, client_superadmin, mock_db):
        """含 `..` 的路徑必須拒絕。"""
        mock_db.query.return_value.filter.return_value.first.return_value = _agent_mock(
            ingest_path="/opt/scripts/../../etc/passwd"
        )
        resp = client_superadmin.post(f"/api/v1/agents/{AGENT_ID}/validate-script")
        body = resp.json()["data"]
        assert body["exists"] is False
        assert "不合法" in body["error"]

    def test_relative_path_rejected(self, client_superadmin, mock_db):
        """相對路徑必須拒絕（須為絕對路徑）。"""
        mock_db.query.return_value.filter.return_value.first.return_value = _agent_mock(
            ingest_path="scripts/ingest.py"
        )
        resp = client_superadmin.post(f"/api/v1/agents/{AGENT_ID}/validate-script")
        body = resp.json()["data"]
        assert body["exists"] is False
        assert "不合法" in body["error"]

    def test_editor_returns_403(self, client_editor, mock_db):
        resp = client_editor.post(f"/api/v1/agents/{AGENT_ID}/validate-script")
        assert resp.status_code == 403
