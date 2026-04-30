"""
Regression test for B8：chat.py 與 agent_admin.py 不應將 str(exc) 內部訊息
（內網 URL、堆疊片段、原始 connection 錯誤字串）回給 API 呼叫端。
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
from fastapi.testclient import TestClient

from tests.conftest import AGENT_ID

CHAT_URL = f"/api/v1/agents/{AGENT_ID}/chat/test"


def _agent_mock() -> MagicMock:
    a = MagicMock()
    a.id = AGENT_ID
    a.rasa_rest_url = "http://internal-rasa.private.lan:5555/webhooks/myio/webhook"
    return a


def _make_se(agent: MagicMock):  # type: ignore[no-untyped-def]
    def se(*args: object) -> MagicMock:
        q = MagicMock()
        q.filter.return_value.first.return_value = agent
        return q
    return se


class TestB8ChatNoInternalLeak:
    def test_request_error_detail_is_generic(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        mock_db.query.side_effect = _make_se(_agent_mock())

        secret_internal = "internal-rasa.private.lan:5555 connection refused"

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = httpx.ConnectError(secret_internal)
            mock_client_cls.return_value = mock_client

            resp = client_superadmin.post(CHAT_URL, json={"message": "hi"})

        assert resp.status_code == 502
        body = resp.json()
        # detail.message 不可含原始 exc 字串（避免洩漏內網 hostname）
        msg = body["detail"]["message"]
        assert secret_internal not in msg
        assert "internal-rasa.private.lan" not in msg
        # 應為固定訊息
        assert msg == "Rasa 服務連線失敗"

    def test_http_status_error_detail_only_status_code(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        mock_db.query.side_effect = _make_se(_agent_mock())

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.status_code = 503
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "http://internal-rasa.private.lan/secret-path failed", request=MagicMock(), response=mock_resp
            )
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            resp = client_superadmin.post(CHAT_URL, json={"message": "hi"})

        assert resp.status_code == 502
        msg = resp.json()["detail"]["message"]
        assert "internal-rasa.private.lan" not in msg
        assert "secret-path" not in msg
        assert "503" in msg


class TestB8AgentAdminNoInternalLeak:
    def test_test_connection_error_message_is_generic(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        mock_db.query.side_effect = _make_se(_agent_mock())

        secret_internal = "internal-rasa.private.lan resolved to 10.0.0.5"

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.side_effect = httpx.ConnectError(secret_internal)
            mock_client_cls.return_value = mock_client

            resp = client_superadmin.post(
                f"/api/v1/agents/{AGENT_ID}/test-connection"
            )

        assert resp.status_code == 200
        data = resp.json()["data"]
        err = data.get("error") or ""
        assert secret_internal not in err
        assert "10.0.0.5" not in err
        # 不應為原本的 "{type(exc).__name__}: {exc}" 形式
        assert "ConnectError:" not in err
