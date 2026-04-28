"""
認證測試：登入/登出、Token 機制、Rate Limiting。
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from tests.conftest import (
    PLAIN_PASSWORD,
    _test_pwd,
)


# ── 登入成功 ───────────────────────────────────────────────────────────────────

class TestLogin:
    def test_login_success(self, client_no_auth: TestClient, mock_db: MagicMock, superadmin_user: MagicMock) -> None:
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
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["username"] == "admin"
        assert body["data"]["is_superadmin"] is True
        # HttpOnly cookie 應已設定
        assert "access_token" in resp.cookies

    def test_login_wrong_password(self, client_no_auth: TestClient, mock_db: MagicMock, superadmin_user: MagicMock) -> None:
        mock_db.query.return_value.filter.return_value.first.return_value = superadmin_user

        with (
            patch("api.routes.auth.check_login_rate_limit"),
            patch("api.routes.auth.record_login_failure"),
        ):
            resp = client_no_auth.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "WrongPass1"},
            )

        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "UNAUTHORIZED"

    def test_login_user_not_found(self, client_no_auth: TestClient, mock_db: MagicMock) -> None:
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with (
            patch("api.routes.auth.check_login_rate_limit"),
            patch("api.routes.auth.record_login_failure"),
        ):
            resp = client_no_auth.post(
                "/api/v1/auth/login",
                json={"username": "nobody", "password": PLAIN_PASSWORD},
            )

        assert resp.status_code == 401

    def test_login_rate_limit_triggered(self, client_no_auth: TestClient, mock_db: MagicMock) -> None:
        from fastapi import HTTPException

        def raise_rate_limit(*args: object, **kwargs: object) -> None:
            raise HTTPException(status_code=429, detail={"code": "RATE_LIMITED", "message": "帳號暫時鎖定"})

        with patch("api.routes.auth.check_login_rate_limit", side_effect=raise_rate_limit):
            resp = client_no_auth.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": PLAIN_PASSWORD},
            )

        assert resp.status_code == 429


# ── /me 端點 ───────────────────────────────────────────────────────────────────

class TestMe:
    def test_me_returns_current_user(self, client_superadmin: TestClient) -> None:
        resp = client_superadmin.get("/api/v1/auth/me")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["username"] == "admin"

    def test_me_unauthenticated(self, client_no_auth: TestClient) -> None:
        resp = client_no_auth.get("/api/v1/auth/me")
        assert resp.status_code == 401


# ── 登出 ────────────────────────────────────────────────────────────────────────

class TestLogout:
    def test_logout_clears_cookies(self, client_superadmin: TestClient) -> None:
        resp = client_superadmin.post("/api/v1/auth/logout")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        # 登出後 cookie 應被刪除（Set-Cookie: max-age=0 或 expires=past）
        set_cookie_headers = resp.headers.get("set-cookie", "")
        assert "access_token" in set_cookie_headers


# ── 密碼驗證工具（內部函式）────────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_and_verify(self) -> None:
        hashed = _test_pwd.hash("Secure1pw")
        assert _test_pwd.verify("Secure1pw", hashed) is True
        assert _test_pwd.verify("wrong", hashed) is False

    def test_different_passwords_different_hashes(self) -> None:
        h1 = _test_pwd.hash("Admin1234")
        h2 = _test_pwd.hash("Admin1234")
        # bcrypt salt 不同，hash 應不同
        assert h1 != h2
        # 但都能驗證通過
        assert _test_pwd.verify("Admin1234", h1) is True
        assert _test_pwd.verify("Admin1234", h2) is True
