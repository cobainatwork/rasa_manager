"""
使用者管理路由測試（Superadmin 專用）。
覆蓋：list_users, create_user, update_user, reset_password, _validate_password
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from api.routes.users import _validate_password

USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")


def _user_mock(
    user_id: uuid.UUID = USER_ID,
    username: str = "test_user",
    is_superadmin: bool = False,
    is_active: bool = True,
) -> MagicMock:
    u = MagicMock()
    u.id = user_id
    u.username = username
    u.is_superadmin = is_superadmin
    u.is_active = is_active
    u.created_at = None
    return u


# ─── _validate_password ───────────────────────────────────────────────────────

class TestValidatePassword:
    def test_valid_password_no_exception(self):
        _validate_password("Admin1234")  # 不應拋出例外

    def test_too_short_raises_400(self):
        with pytest.raises(HTTPException) as exc:
            _validate_password("Ab1")
        assert exc.value.status_code == 400

    def test_no_uppercase_raises_400(self):
        with pytest.raises(HTTPException) as exc:
            _validate_password("admin1234")
        assert exc.value.status_code == 400

    def test_no_lowercase_raises_400(self):
        with pytest.raises(HTTPException) as exc:
            _validate_password("ADMIN1234")
        assert exc.value.status_code == 400

    def test_no_digit_raises_400(self):
        with pytest.raises(HTTPException) as exc:
            _validate_password("AdminAdmin")
        assert exc.value.status_code == 400

    def test_exactly_8_chars_valid(self):
        _validate_password("Admin123")  # 恰好 8 字元，符合全部規則

    def test_7_chars_raises(self):
        with pytest.raises(HTTPException):
            _validate_password("Admin12")  # 7 字元，太短


# ─── list_users ───────────────────────────────────────────────────────────────

class TestListUsers:
    def test_superadmin_returns_200_and_list(self, client_superadmin, mock_db):
        user = _user_mock()
        mock_db.query.return_value.order_by.return_value.all.return_value = [user]
        resp = client_superadmin.get("/api/v1/users")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)

    def test_non_superadmin_returns_403(self, client_editor, mock_db):
        resp = client_editor.get("/api/v1/users")
        assert resp.status_code == 403

    def test_empty_db_returns_empty_list(self, client_superadmin, mock_db):
        mock_db.query.return_value.order_by.return_value.all.return_value = []
        resp = client_superadmin.get("/api/v1/users")
        assert resp.status_code == 200
        assert resp.json()["data"] == []


# ─── create_user ──────────────────────────────────────────────────────────────

class TestCreateUser:
    def test_success_returns_201(self, client_superadmin, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None
        resp = client_superadmin.post(
            "/api/v1/users",
            json={"username": "newuser", "password": "Admin1234", "is_superadmin": False},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["success"] is True
        assert "message" in data

    def test_superadmin_flag_true(self, client_superadmin, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None
        resp = client_superadmin.post(
            "/api/v1/users",
            json={"username": "superuser", "password": "Admin1234", "is_superadmin": True},
        )
        assert resp.status_code == 201

    def test_duplicate_username_returns_409(self, client_superadmin, mock_db):
        existing = _user_mock(username="taken")
        mock_db.query.return_value.filter.return_value.first.return_value = existing
        resp = client_superadmin.post(
            "/api/v1/users",
            json={"username": "taken", "password": "Admin1234"},
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "CONFLICT"

    def test_short_password_returns_422(self, client_superadmin, mock_db):
        """密碼長度 < 8 由 Pydantic schema min_length=8 在到達路由邏輯前攔截，回傳 422。"""
        resp = client_superadmin.post(
            "/api/v1/users",
            json={"username": "newuser", "password": "ab1"},
        )
        assert resp.status_code == 422

    def test_no_uppercase_password_returns_400(self, client_superadmin, mock_db):
        resp = client_superadmin.post(
            "/api/v1/users",
            json={"username": "newuser", "password": "admin1234"},
        )
        assert resp.status_code == 400

    def test_editor_returns_403(self, client_editor, mock_db):
        resp = client_editor.post(
            "/api/v1/users",
            json={"username": "newuser", "password": "Admin1234"},
        )
        assert resp.status_code == 403


# ─── update_user ──────────────────────────────────────────────────────────────

class TestUpdateUser:
    def test_deactivate_user_returns_200(self, client_superadmin, mock_db):
        user = _user_mock()
        mock_db.query.return_value.filter.return_value.first.return_value = user
        resp = client_superadmin.patch(
            f"/api/v1/users/{USER_ID}",
            json={"is_active": False},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_promote_to_superadmin_returns_200(self, client_superadmin, mock_db):
        user = _user_mock()
        mock_db.query.return_value.filter.return_value.first.return_value = user
        resp = client_superadmin.patch(
            f"/api/v1/users/{USER_ID}",
            json={"is_superadmin": True},
        )
        assert resp.status_code == 200

    def test_not_found_returns_404(self, client_superadmin, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None
        resp = client_superadmin.patch(
            f"/api/v1/users/{USER_ID}",
            json={"is_active": False},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "NOT_FOUND"

    def test_editor_returns_403(self, client_editor, mock_db):
        resp = client_editor.patch(
            f"/api/v1/users/{USER_ID}",
            json={"is_active": False},
        )
        assert resp.status_code == 403


# ─── reset_password ───────────────────────────────────────────────────────────

class TestResetPassword:
    def test_success_returns_200(self, client_superadmin, mock_db):
        user = _user_mock()
        mock_db.query.return_value.filter.return_value.first.return_value = user
        resp = client_superadmin.patch(
            f"/api/v1/users/{USER_ID}/reset-password",
            json={"new_password": "NewAdmin1234"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_weak_password_returns_400(self, client_superadmin, mock_db):
        resp = client_superadmin.patch(
            f"/api/v1/users/{USER_ID}/reset-password",
            json={"new_password": "weakpass"},
        )
        assert resp.status_code == 400

    def test_not_found_returns_404(self, client_superadmin, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None
        resp = client_superadmin.patch(
            f"/api/v1/users/{USER_ID}/reset-password",
            json={"new_password": "Admin1234"},
        )
        assert resp.status_code == 404

    def test_no_uppercase_returns_400(self, client_superadmin, mock_db):
        resp = client_superadmin.patch(
            f"/api/v1/users/{USER_ID}/reset-password",
            json={"new_password": "password123"},
        )
        assert resp.status_code == 400

    def test_editor_returns_403(self, client_editor, mock_db):
        resp = client_editor.patch(
            f"/api/v1/users/{USER_ID}/reset-password",
            json={"new_password": "Admin1234"},
        )
        assert resp.status_code == 403
