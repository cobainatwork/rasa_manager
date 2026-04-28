"""
pytest 共用 fixtures。

策略：
- 使用 FastAPI TestClient + dependency override
- DB Session 以 MagicMock 替代，避免需要真實 PostgreSQL
- Redis 以 MagicMock 替代，autouse=True 全域套用
- 提供 superadmin / editor / reviewer 三種使用者 fixture
"""
from __future__ import annotations

# ── 測試環境變數（必須在 app 模組匯入前設定）────────────────────────────────
import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault(
    "JWT_SECRET",
    "test-secret-key-for-unit-tests-64-chars-long-padding-xxxxxxxxxxxx",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import uuid
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from main import app
from api.database.session import get_db
from api.dependencies import get_current_user

# 測試用低 cost bcrypt（加速測試執行）
_test_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=4)

# 固定 UUID（方便 assert）
SUPERADMIN_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
EDITOR_ID     = uuid.UUID("00000000-0000-0000-0000-000000000002")
REVIEWER_ID   = uuid.UUID("00000000-0000-0000-0000-000000000003")
AGENT_ID      = uuid.UUID("00000000-0000-0000-0000-000000000010")

PLAIN_PASSWORD = "Admin1234"
HASHED_PASSWORD = _test_pwd.hash(PLAIN_PASSWORD)


# ── Redis mock（全域套用，阻止所有測試真正連線 Redis）────────────────────────

@pytest.fixture(autouse=True)
def mock_redis() -> Generator[MagicMock, None, None]:
    r = MagicMock()
    r.get.return_value = None       # 無限速限制
    r.incr.return_value = 1
    r.expire.return_value = True
    r.setex.return_value = True
    r.delete.return_value = 1
    r.ping.return_value = True
    with (
        patch("api.dependencies._get_redis", return_value=r),
        patch("api.routes.auth._get_redis", return_value=r),
    ):
        yield r


# ── DB mock ───────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db() -> MagicMock:
    return MagicMock(spec=Session)


# ── 使用者 fixtures ────────────────────────────────────────────────────────────

def _make_user(uid: uuid.UUID, username: str, is_superadmin: bool) -> MagicMock:
    u = MagicMock()
    u.id = uid
    u.username = username
    u.password_hash = HASHED_PASSWORD
    u.is_superadmin = is_superadmin
    u.is_active = True
    return u


@pytest.fixture
def superadmin_user() -> MagicMock:
    return _make_user(SUPERADMIN_ID, "admin", is_superadmin=True)


@pytest.fixture
def editor_user() -> MagicMock:
    return _make_user(EDITOR_ID, "editor", is_superadmin=False)


@pytest.fixture
def reviewer_user() -> MagicMock:
    return _make_user(REVIEWER_ID, "reviewer", is_superadmin=False)


# ── TestClient factories ───────────────────────────────────────────────────────

def _make_client(mock_db: MagicMock, current_user: MagicMock) -> TestClient:
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def client_superadmin(mock_db: MagicMock, superadmin_user: MagicMock) -> Generator[TestClient, None, None]:
    c = _make_client(mock_db, superadmin_user)
    yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_editor(mock_db: MagicMock, editor_user: MagicMock) -> Generator[TestClient, None, None]:
    c = _make_client(mock_db, editor_user)
    yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_reviewer(mock_db: MagicMock, reviewer_user: MagicMock) -> Generator[TestClient, None, None]:
    c = _make_client(mock_db, reviewer_user)
    yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_no_auth(mock_db: MagicMock) -> Generator[TestClient, None, None]:
    """未登入的 client（僅 override DB，不 override user）。"""
    app.dependency_overrides[get_db] = lambda: mock_db
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()
