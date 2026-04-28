"""
Seed 腳本測試：密碼驗證、首次建立、冪等性。
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


# ── _validate_password 單元測試 ───────────────────────────────────────────────

class TestValidatePassword:
    def _validate(self, pwd: str) -> None:
        from api.seed import _validate_password
        _validate_password(pwd)

    def test_valid_password_passes(self) -> None:
        self._validate("Admin1234")

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="最少需要 8 字元"):
            self._validate("Ab1")

    def test_no_uppercase_raises(self) -> None:
        with pytest.raises(ValueError, match="大寫"):
            self._validate("admin1234")

    def test_no_lowercase_raises(self) -> None:
        with pytest.raises(ValueError, match="小寫"):
            self._validate("ADMIN1234")

    def test_no_digit_raises(self) -> None:
        with pytest.raises(ValueError, match="數字"):
            self._validate("AdminPass")

    def test_exactly_8_chars_passes(self) -> None:
        self._validate("Admin12!")   # 8 chars, has upper/lower/digit

    def test_special_chars_allowed(self) -> None:
        self._validate("Admin@1234!")


# ── run_seed 冪等性測試 ───────────────────────────────────────────────────────

class TestRunSeed:
    def _run(self, username: str, password: str, user_count: int) -> None:
        """執行 seed 並 mock 環境。"""
        db = MagicMock()
        db.execute.return_value.scalar.return_value = user_count

        env = {"SEED_ADMIN_USERNAME": username, "SEED_ADMIN_PASSWORD": password}

        with (
            patch.dict(os.environ, env),
            patch("api.seed.SessionLocal", return_value=db),
        ):
            from api.seed import run_seed
            run_seed()

        return db

    def test_first_run_inserts_user(self) -> None:
        db = self._run("admin", "Admin1234", user_count=0)
        # user_count=0 → 應執行 INSERT
        db.execute.assert_called()
        db.commit.assert_called_once()

    def test_second_run_skips(self, capsys: pytest.CaptureFixture[str]) -> None:
        db = self._run("admin", "Admin1234", user_count=1)
        # user_count=1 → 應跳過，不執行 INSERT（execute 僅被呼叫一次：SELECT COUNT）
        assert db.execute.call_count == 1
        db.commit.assert_not_called()

    def test_missing_username_exits(self) -> None:
        with (
            patch.dict(os.environ, {"SEED_ADMIN_USERNAME": "", "SEED_ADMIN_PASSWORD": "Admin1234"}),
            pytest.raises(SystemExit) as exc_info,
        ):
            from api.seed import run_seed
            run_seed()
        assert exc_info.value.code == 1

    def test_missing_password_exits(self) -> None:
        with (
            patch.dict(os.environ, {"SEED_ADMIN_USERNAME": "admin", "SEED_ADMIN_PASSWORD": ""}),
            pytest.raises(SystemExit) as exc_info,
        ):
            from api.seed import run_seed
            run_seed()
        assert exc_info.value.code == 1

    def test_weak_password_exits(self) -> None:
        with (
            patch.dict(os.environ, {"SEED_ADMIN_USERNAME": "admin", "SEED_ADMIN_PASSWORD": "weakpwd"}),
            pytest.raises(SystemExit) as exc_info,
        ):
            from api.seed import run_seed
            run_seed()
        assert exc_info.value.code == 1
