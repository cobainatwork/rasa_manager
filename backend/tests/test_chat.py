"""
對話測試路由測試：test_chat — 轉發至 Rasa webhook。
涵蓋：成功、無 rasa_url、timeout、HTTP 錯誤、通用連線失敗、未認證。
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
from fastapi.testclient import TestClient

from tests.conftest import AGENT_ID

CHAT_URL = f"/api/v1/agents/{AGENT_ID}/chat/test"
CHAT_PAYLOAD = {"message": "你好"}


def _agent_mock(rasa_rest_url: str | None = "http://rasa:5005") -> MagicMock:
    a = MagicMock()
    a.id = AGENT_ID
    a.rasa_rest_url = rasa_rest_url
    return a


def _make_se(agent: MagicMock) -> object:
    """
    side_effect：
      0: Agent（require_agent_access superadmin 路徑）
    """
    counter = [0]

    def se(*args: object) -> MagicMock:
        q = MagicMock()
        idx = counter[0]
        counter[0] += 1
        if idx == 0:
            q.filter.return_value.first.return_value = agent
        return q

    return se


class TestChatEndpoint:
    def test_success_returns_200_with_messages(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        mock_db.query.side_effect = _make_se(_agent_mock())
        fake_response = MagicMock()
        fake_response.json.return_value = [{"text": "回覆訊息"}]
        fake_response.raise_for_status.return_value = None

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = fake_response
            mock_client_cls.return_value = mock_client

            resp = client_superadmin.post(CHAT_URL, json=CHAT_PAYLOAD)

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"] == [{"text": "回覆訊息"}]

    def test_no_rasa_url_returns_422(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        mock_db.query.side_effect = _make_se(_agent_mock(rasa_rest_url=None))
        resp = client_superadmin.post(CHAT_URL, json=CHAT_PAYLOAD)
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "UNPROCESSABLE"

    def test_rasa_timeout_returns_504(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        mock_db.query.side_effect = _make_se(_agent_mock())

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = httpx.TimeoutException("timeout")
            mock_client_cls.return_value = mock_client

            resp = client_superadmin.post(CHAT_URL, json=CHAT_PAYLOAD)

        assert resp.status_code == 504
        assert resp.json()["detail"]["code"] == "TIMEOUT"

    def test_rasa_http_error_returns_502(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        mock_db.query.side_effect = _make_se(_agent_mock())

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            fake_resp = MagicMock()
            fake_resp.status_code = 503
            mock_client.post.side_effect = httpx.HTTPStatusError(
                "503", request=MagicMock(), response=fake_resp
            )
            mock_client_cls.return_value = mock_client

            resp = client_superadmin.post(CHAT_URL, json=CHAT_PAYLOAD)

        assert resp.status_code == 502
        assert resp.json()["detail"]["code"] == "BAD_GATEWAY"

    def test_rasa_connection_error_returns_502(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        mock_db.query.side_effect = _make_se(_agent_mock())

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            # B8：narrow except 後僅攔截 httpx.RequestError 子類
            import httpx as _httpx
            mock_client.post.side_effect = _httpx.ConnectError("Connection refused")
            mock_client_cls.return_value = mock_client

            resp = client_superadmin.post(CHAT_URL, json=CHAT_PAYLOAD)

        assert resp.status_code == 502
        assert resp.json()["detail"]["code"] == "BAD_GATEWAY"

    def test_unauthenticated_returns_401(self, client_no_auth: TestClient) -> None:
        resp = client_no_auth.post(CHAT_URL, json=CHAT_PAYLOAD)
        assert resp.status_code == 401

    def test_editor_can_access_chat(
        self, client_editor: TestClient, mock_db: MagicMock
    ) -> None:
        """Editor 有 agent access，可使用 chat 功能。"""
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
            return q

        mock_db.query.side_effect = se

        # agent 無 rasa_url → 422，但確認有進入路由（非 401/403）
        agent = _agent_mock(rasa_rest_url=None)
        counter[0] = 0

        def se2(*args: object) -> MagicMock:
            q = MagicMock()
            idx = counter[0]
            counter[0] += 1
            if idx == 0:
                q.filter.return_value.first.return_value = agent
            elif idx == 1:
                role = MagicMock()
                role.role = "editor"
                q.filter.return_value.first.return_value = role
            return q

        mock_db.query.side_effect = se2
        resp = client_editor.post(CHAT_URL, json=CHAT_PAYLOAD)
        assert resp.status_code == 422  # 有 agent access，但 rasa_url 未設定
