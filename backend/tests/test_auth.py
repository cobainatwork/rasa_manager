"""
認證測試：登入/登出、Token 機制、Rate Limiting。
"""
from __future__ import annotations

import inspect
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt as _jwt

from api import dependencies as deps_mod
from api.routes import auth as auth_mod
from api.routes.auth import _issue_tokens
from api.security import jwt as jwt_mod
from api.security.jwt import ALGORITHM, SECRET_KEY
from api.security.password import validate_password_strength
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


# ── logout（jti 黑名單）──────────────────────────────────────────────────────────

class TestLogoutJti:
    """logout 時若帶有效 refresh_token，應將 jti 加入 Redis 黑名單。"""

    def test_logout_with_valid_refresh_token_blacklists_jti(
        self,
        client_superadmin: TestClient,
        mock_redis: MagicMock,
    ) -> None:
        from api.routes.auth import _create_token
        from datetime import timedelta
        import uuid

        jti = str(uuid.uuid4())
        refresh_token = _create_token(
            {"sub": "00000000-0000-0000-0000-000000000001", "jti": jti, "type": "refresh"},
            timedelta(days=7),
        )

        resp = client_superadmin.post(
            "/api/v1/auth/logout",
            cookies={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        # Redis setex 應被呼叫（黑名單 jti）
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args[0]
        assert f"revoked_refresh:{jti}" in call_args[0]

    def test_logout_with_invalid_refresh_token_still_succeeds(
        self,
        client_superadmin: TestClient,
        mock_redis: MagicMock,
    ) -> None:
        """無效 refresh token 應被忽略（JWTError catch），logout 仍回 200。"""
        resp = client_superadmin.post(
            "/api/v1/auth/logout",
            cookies={"refresh_token": "invalid.token.here"},
        )
        assert resp.status_code == 200
        mock_redis.setex.assert_not_called()

    def test_logout_without_refresh_token_succeeds(
        self,
        client_superadmin: TestClient,
        mock_redis: MagicMock,
    ) -> None:
        resp = client_superadmin.post("/api/v1/auth/logout")
        assert resp.status_code == 200
        mock_redis.setex.assert_not_called()


# ── refresh token endpoint ────────────────────────────────────────────────────

class TestRefreshToken:
    def _make_refresh_token(self, sub: str = "00000000-0000-0000-0000-000000000001") -> str:
        from api.routes.auth import _create_token
        from datetime import timedelta
        import uuid

        return _create_token(
            {"sub": sub, "jti": str(uuid.uuid4()), "type": "refresh"},
            timedelta(days=7),
        )

    def test_no_refresh_token_returns_401(self, client_no_auth: TestClient) -> None:
        resp = client_no_auth.post("/api/v1/auth/refresh")
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "UNAUTHORIZED"

    def test_invalid_token_returns_401(self, client_no_auth: TestClient) -> None:
        resp = client_no_auth.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": "bad.token.value"},
        )
        assert resp.status_code == 401

    def test_wrong_token_type_returns_401(self, client_no_auth: TestClient) -> None:
        """type != 'refresh' 的 token 應被拒絕。"""
        from api.routes.auth import _create_token
        from datetime import timedelta
        import uuid

        token = _create_token(
            {"sub": "00000000-0000-0000-0000-000000000001", "jti": str(uuid.uuid4()), "type": "access"},
            timedelta(minutes=15),
        )
        resp = client_no_auth.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": token},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "UNAUTHORIZED"

    def test_revoked_token_returns_401(
        self, client_no_auth: TestClient, mock_redis: MagicMock
    ) -> None:
        """jti 已在黑名單，應回傳 401。"""
        token = self._make_refresh_token()
        mock_redis.get.return_value = "1"  # 模擬 jti 在黑名單中

        resp = client_no_auth.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": token},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "UNAUTHORIZED"

    def test_user_not_found_returns_401(
        self, client_no_auth: TestClient, mock_db: MagicMock, mock_redis: MagicMock
    ) -> None:
        """DB 中找不到使用者，應回傳 401。"""
        mock_redis.get.return_value = None  # jti 未吊銷
        mock_db.query.return_value.filter.return_value.first.return_value = None

        token = self._make_refresh_token()
        resp = client_no_auth.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": token},
        )
        assert resp.status_code == 401

    def test_valid_refresh_token_returns_200_and_new_cookies(
        self, client_no_auth: TestClient, mock_db: MagicMock, mock_redis: MagicMock,
        superadmin_user: MagicMock,
    ) -> None:
        """有效 refresh token 應回傳 200，並設定新的 access_token cookie。"""
        mock_redis.get.return_value = None  # jti 未吊銷
        mock_db.query.return_value.filter.return_value.first.return_value = superadmin_user

        token = self._make_refresh_token(sub=str(superadmin_user.id))
        resp = client_no_auth.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": token},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        # 新 access_token cookie 應已設定
        assert "access_token" in resp.cookies


# ── Regression: I9 (password rules must be centralized) ──────────────────────

class TestPasswordValidationRegression:
    """Regression: I9 (password rules must be centralized)."""

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError) as exc:
            validate_password_strength("Ab1")
        assert "8" in str(exc.value)

    def test_missing_uppercase_raises(self) -> None:
        with pytest.raises(ValueError) as exc:
            validate_password_strength("abcdef12")
        assert "大寫" in str(exc.value)

    def test_missing_lowercase_raises(self) -> None:
        with pytest.raises(ValueError) as exc:
            validate_password_strength("ABCDEF12")
        assert "小寫" in str(exc.value)

    def test_missing_digit_raises(self) -> None:
        with pytest.raises(ValueError) as exc:
            validate_password_strength("Abcdefgh")
        assert "數字" in str(exc.value)

    def test_happy_path_passes(self) -> None:
        validate_password_strength("Admin1234")
        validate_password_strength("StrongPa55word")

    def test_seed_validate_delegates(self) -> None:
        """seed.py 的 _validate_password 應委派至共用函式（同樣 raise ValueError）。"""
        from api.seed import _validate_password

        with pytest.raises(ValueError):
            _validate_password("short")
        _validate_password("Admin1234")

    def test_users_router_validator_uses_shared_function(self) -> None:
        """users.py 的 _validate_password 應 raise HTTPException(400) 而非 ValueError。"""
        from fastapi import HTTPException

        from api.routes.users import _validate_password

        with pytest.raises(HTTPException) as exc:
            _validate_password("abcdefgh")
        assert exc.value.status_code == 400
        assert exc.value.detail["code"] == "VALIDATION_ERROR"
        assert "大寫" in exc.value.detail["message"]


# ── Regression: B4 (JWT payload must not include is_superadmin) ─────────────

class TestJwtPayloadNoRoleRegression:
    """Regression: B4 (JWT payload must not include is_superadmin)."""

    def test_issue_tokens_payload_excludes_is_superadmin(
        self, superadmin_user: MagicMock
    ) -> None:
        access_token, refresh_token = _issue_tokens(superadmin_user)

        access_payload = _jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        refresh_payload = _jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])

        assert "is_superadmin" not in access_payload, (
            "access_token payload 不可包含 is_superadmin"
        )
        assert "is_superadmin" not in refresh_payload, (
            "refresh_token payload 不可包含 is_superadmin"
        )
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
        payload = _jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "is_superadmin" not in payload
        assert "role" not in payload


# ── Regression: B5 (JWT logic must be centralized in api.security.jwt) ──────

class TestJwtCentralModuleRegression:
    """Regression: B5 (JWT logic must be centralized in api.security.jwt)."""

    def test_security_jwt_module_exposes_constants(self) -> None:
        assert hasattr(jwt_mod, "SECRET_KEY")
        assert hasattr(jwt_mod, "ALGORITHM")
        assert hasattr(jwt_mod, "ACCESS_MINUTES")
        assert hasattr(jwt_mod, "REFRESH_DAYS")
        assert hasattr(jwt_mod, "create_access_token")
        assert hasattr(jwt_mod, "create_refresh_token")
        assert hasattr(jwt_mod, "decode_token")

    def test_auth_module_imports_from_security_jwt(self) -> None:
        src = inspect.getsource(auth_mod)
        assert "from api.security.jwt import" in src, (
            "auth.py 必須從 api.security.jwt import JWT 設定 / 函式"
        )
        assert '_UNSAFE_JWT_DEFAULTS' not in src, (
            "_UNSAFE_JWT_DEFAULTS 應只出現於 api/security/jwt.py，避免重複維護"
        )

    def test_dependencies_module_imports_from_security_jwt(self) -> None:
        src = inspect.getsource(deps_mod)
        assert "from api.security.jwt import" in src, (
            "dependencies.py 必須從 api.security.jwt import decode_token"
        )
        assert '_UNSAFE_JWT_DEFAULTS' not in src
        assert 'SECRET_KEY: str = _jwt_secret_raw' not in src

    def test_constants_identity_shared(self) -> None:
        """auth.SECRET_KEY 與 jwt_mod.SECRET_KEY 應為同一物件，確保唯一來源。"""
        assert auth_mod.SECRET_KEY is jwt_mod.SECRET_KEY
        assert auth_mod.ALGORITHM == jwt_mod.ALGORITHM
