"""
Regression test for I9：密碼強度驗證集中至 api.security.password.validate_password_strength。

四種違規 + 一個 happy path：
- 過短
- 缺大寫
- 缺小寫
- 缺數字
- 全部符合
"""
from __future__ import annotations

import pytest

from api.security.password import validate_password_strength


class TestI9PasswordStrength:
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
        # 不應拋例外
        validate_password_strength("Admin1234")
        validate_password_strength("StrongPa55word")


class TestI9SeedDelegation:
    def test_seed_validate_delegates(self) -> None:
        """seed.py 的 _validate_password 應委派至共用函式（同樣 raise ValueError）。"""
        from api.seed import _validate_password

        with pytest.raises(ValueError):
            _validate_password("short")
        # happy path
        _validate_password("Admin1234")


class TestI9UsersRouterDelegation:
    def test_users_router_validator_uses_shared_function(self) -> None:
        """users.py 的 _validate_password 應 raise HTTPException(400) 而非 ValueError。"""
        from fastapi import HTTPException

        from api.routes.users import _validate_password

        with pytest.raises(HTTPException) as exc:
            _validate_password("abcdefgh")  # 缺大寫
        assert exc.value.status_code == 400
        assert exc.value.detail["code"] == "VALIDATION_ERROR"
        assert "大寫" in exc.value.detail["message"]
