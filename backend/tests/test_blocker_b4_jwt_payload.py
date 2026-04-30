"""
Regression test for B4：JWT payload 不可寫入 is_superadmin。

依規格 §五.1，access_token / refresh_token 的 payload 都不可包含角色資訊
（is_superadmin 等），權限一律以 DB 為準。
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from jose import jwt

from api.routes.auth import _issue_tokens
from api.security.jwt import ALGORITHM, SECRET_KEY
from tests.conftest import PLAIN_PASSWORD


class TestJwtPayloadHasNoRole:
    def test_issue_tokens_payload_excludes_is_superadmin(
        self, superadmin_user: MagicMock
    ) -> None:
        access_token, refresh_token = _issue_tokens(superadmin_user)

        access_payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        refresh_payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])

        assert "is_superadmin" not in access_payload, (
            "access_token payload 不可包含 is_superadmin"
        )
        assert "is_superadmin" not in refresh_payload, (
            "refresh_token payload 不可包含 is_superadmin"
        )
        # sub / jti 仍應保留
        assert access_payload.get("sub") == str(superadmin_user.id)
        assert "jti" in access_payload
        assert refresh_payload.get("type") == "refresh"

    def test_login_response_cookie_payload_excludes_is_superadmin(
        self,
        client_no_auth: TestClient,
        mock_db: MagicMock,
        superadmin_user: MagicMock,
    ) -> None:
        mock_db.query.return_value.filter.return_value.first.return_value = superadmin_user

        with (
            patch("api.routes.auth.check_login_rate_limit"),
            patch("api.routes.auth.clear_login_attempts"),
        ):
            resp = client_no_auth.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": PLAIN_PASSWORD},
            )

        assert resp.status_code == 200
        access_token = resp.cookies.get("access_token")
        assert access_token, "登入應設定 access_token cookie"
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "is_superadmin" not in payload
        assert "role" not in payload
