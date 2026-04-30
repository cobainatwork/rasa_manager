"""
Regression test for B5：JWT 設定集中至 api.security.jwt，
auth.py 與 dependencies.py 不可重複定義 SECRET_KEY / ALGORITHM。
"""
from __future__ import annotations

import inspect

from api import dependencies as deps_mod
from api.routes import auth as auth_mod
from api.security import jwt as jwt_mod


class TestB5JwtCentralized:
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
        # 不可在 auth.py 內重新讀取 JWT_SECRET 或 hardcode 不安全預設值名單
        assert '_UNSAFE_JWT_DEFAULTS' not in src, (
            "_UNSAFE_JWT_DEFAULTS 應只出現於 api/security/jwt.py，避免重複維護"
        )

    def test_dependencies_module_imports_from_security_jwt(self) -> None:
        src = inspect.getsource(deps_mod)
        assert "from api.security.jwt import" in src, (
            "dependencies.py 必須從 api.security.jwt import decode_token"
        )
        assert '_UNSAFE_JWT_DEFAULTS' not in src
        # 不可重複定義 SECRET_KEY 區塊
        assert 'SECRET_KEY: str = _jwt_secret_raw' not in src

    def test_constants_identity_shared(self) -> None:
        """auth.SECRET_KEY 與 jwt_mod.SECRET_KEY 應為同一物件，確保唯一來源。"""
        assert auth_mod.SECRET_KEY is jwt_mod.SECRET_KEY
        assert auth_mod.ALGORITHM == jwt_mod.ALGORITHM
