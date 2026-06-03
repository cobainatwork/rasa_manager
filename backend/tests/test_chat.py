"""
對話測試路由測試：test_chat — 轉發至 Rasa webhook。
涵蓋：成功、無 rasa_url、timeout、HTTP 錯誤、通用連線失敗、未認證。
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.conftest import AGENT_ID

CHAT_URL = f"/api/v1/agents/{AGENT_ID}/chat/test"
CHAT_PAYLOAD = {"message": "你好"}


@pytest.fixture
def _agent_mock(agent_factory):
    """檔內 fixture，回傳建立 Agent mock 的 callable（保留 rasa_rest_url 簽章）。"""
    def _make(rasa_rest_url: str | None = "http://rasa:5005") -> MagicMock:
        return agent_factory(rasa_rest_url=rasa_rest_url)
    return _make


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
        self, client_superadmin: TestClient, mock_db: MagicMock, _agent_mock
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

    def test_custom_channel_dict_response_extracts_messages(
        self, client_superadmin: TestClient, mock_db: MagicMock, _agent_mock
    ) -> None:
        """Custom channel (/webhooks/{name}/webhook) 回傳 {messages: [...], ...} 格式應正確解析。"""
        mock_db.query.side_effect = _make_se(_agent_mock())
        fake_response = MagicMock()
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = {
            "messages": [{"recipient_id": "user1", "text": "自訂回覆"}],
            "conversation_id": "conv-123",
            "tracker_state": {},
            "metadata": {},
        }

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
        assert body["data"] == [{"recipient_id": "user1", "text": "自訂回覆"}]

    def test_empty_messages_dict_returns_empty_list(
        self, client_superadmin: TestClient, mock_db: MagicMock, _agent_mock
    ) -> None:
        """Rasa 回傳 {messages: null} 或無 messages 鍵時，data 應為 []。"""
        mock_db.query.side_effect = _make_se(_agent_mock())
        fake_response = MagicMock()
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = {"conversation_id": "conv-456"}  # 無 messages 鍵

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = fake_response
            mock_client_cls.return_value = mock_client

            resp = client_superadmin.post(CHAT_URL, json=CHAT_PAYLOAD)

        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_no_rasa_url_returns_422(
        self, client_superadmin: TestClient, mock_db: MagicMock, _agent_mock
    ) -> None:
        mock_db.query.side_effect = _make_se(_agent_mock(rasa_rest_url=None))
        resp = client_superadmin.post(CHAT_URL, json=CHAT_PAYLOAD)
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "UNPROCESSABLE"

    def test_rasa_timeout_returns_504(
        self, client_superadmin: TestClient, mock_db: MagicMock, _agent_mock
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
        self, client_superadmin: TestClient, mock_db: MagicMock, _agent_mock
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
        self, client_superadmin: TestClient, mock_db: MagicMock, _agent_mock
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

    def test_invalid_agent_id_returns_404(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        """不存在的 agent_id 應回 404。"""
        # require_agent_access 第一次 query 回傳 None → 404
        def se(*args: object) -> MagicMock:
            q = MagicMock()
            q.filter.return_value.first.return_value = None
            return q

        mock_db.query.side_effect = se
        invalid_id = "00000000-0000-0000-0000-0000000099ff"
        resp = client_superadmin.post(
            f"/api/v1/agents/{invalid_id}/chat/test", json=CHAT_PAYLOAD
        )
        assert resp.status_code == 404

    def test_empty_message_returns_422(
        self, client_superadmin: TestClient, mock_db: MagicMock, _agent_mock
    ) -> None:
        """空 message 應觸發 Pydantic min_length=1 → 422。"""
        mock_db.query.side_effect = _make_se(_agent_mock())
        resp = client_superadmin.post(CHAT_URL, json={"message": ""})
        assert resp.status_code == 422

    def test_missing_message_field_returns_422(
        self, client_superadmin: TestClient, mock_db: MagicMock, _agent_mock
    ) -> None:
        """缺少 message 欄位應回 422。"""
        mock_db.query.side_effect = _make_se(_agent_mock())
        resp = client_superadmin.post(CHAT_URL, json={})
        assert resp.status_code == 422

    def test_body_sender_is_forwarded_to_rasa(
        self, client_superadmin: TestClient, mock_db: MagicMock, _agent_mock
    ) -> None:
        """前端帶 sender 時，後端應原樣 forward 給 Rasa（per-session 隔離）。"""
        mock_db.query.side_effect = _make_se(_agent_mock())
        fake_response = MagicMock()
        fake_response.json.return_value = []
        fake_response.raise_for_status.return_value = None

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = fake_response
            mock_client_cls.return_value = mock_client

            custom_sender = "session-abc-123-uuid"
            resp = client_superadmin.post(
                CHAT_URL,
                json={"message": "你好", "sender": custom_sender},
            )

        assert resp.status_code == 200
        sent_json = mock_client.post.call_args.kwargs["json"]
        assert sent_json["sender"] == custom_sender
        assert sent_json["message"] == "你好"

    def test_missing_sender_falls_back_to_agent_user_format(
        self, client_superadmin: TestClient, mock_db: MagicMock, _agent_mock
    ) -> None:
        """未帶 sender 時 fallback 到 {agent_id}_{user_id}（向後相容舊前端）。"""
        mock_db.query.side_effect = _make_se(_agent_mock())
        fake_response = MagicMock()
        fake_response.json.return_value = []
        fake_response.raise_for_status.return_value = None

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = fake_response
            mock_client_cls.return_value = mock_client

            resp = client_superadmin.post(CHAT_URL, json={"message": "你好"})

        assert resp.status_code == 200
        sent_json = mock_client.post.call_args.kwargs["json"]
        # fallback 格式：{agent_id}_{user_id}
        assert sent_json["sender"].startswith(f"{AGENT_ID}_")
        assert sent_json["message"] == "你好"

    def test_editor_can_access_chat(
        self, client_editor: TestClient, mock_db: MagicMock, _agent_mock
    ) -> None:
        """Editor 有 agent access，可使用 chat 功能（無 rasa_url 才會 422）。"""
        agent = _agent_mock(rasa_rest_url=None)
        counter = [0]

        def query_se(*args: object) -> MagicMock:
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

        mock_db.query.side_effect = query_se
        resp = client_editor.post(CHAT_URL, json=CHAT_PAYLOAD)
        # agent access 通過（非 401/403），但 rasa_url 未設 → 422
        assert resp.status_code == 422


# ── Regression: B8 (response must not leak internal exception details) ──────

class TestChatNoInternalLeakRegression:
    """Regression: B8 (response must not leak internal exception details)."""

    @staticmethod
    def _internal_agent(agent_factory) -> MagicMock:
        return agent_factory(
            rasa_rest_url="http://internal-rasa.private.lan:5555/webhooks/myio/webhook",
        )

    @staticmethod
    def _make_se(agent: MagicMock):  # type: ignore[no-untyped-def]
        def se(*args: object) -> MagicMock:
            q = MagicMock()
            q.filter.return_value.first.return_value = agent
            return q
        return se

    def test_request_error_detail_is_generic(
        self, client_superadmin: TestClient, mock_db: MagicMock, agent_factory
    ) -> None:
        agent = self._internal_agent(agent_factory)
        mock_db.query.side_effect = self._make_se(agent)

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
        msg = body["detail"]["message"]
        assert secret_internal not in msg
        assert "internal-rasa.private.lan" not in msg
        assert msg == "Rasa 服務連線失敗"

    def test_http_status_error_detail_only_status_code(
        self, client_superadmin: TestClient, mock_db: MagicMock, agent_factory
    ) -> None:
        agent = self._internal_agent(agent_factory)
        mock_db.query.side_effect = self._make_se(agent)

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.status_code = 503
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "http://internal-rasa.private.lan/secret-path failed",
                request=MagicMock(),
                response=mock_resp,
            )
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            resp = client_superadmin.post(CHAT_URL, json={"message": "hi"})

        assert resp.status_code == 502
        msg = resp.json()["detail"]["message"]
        assert "internal-rasa.private.lan" not in msg
        assert "secret-path" not in msg
        assert "503" in msg
