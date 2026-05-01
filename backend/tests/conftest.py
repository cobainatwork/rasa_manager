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
from typing import Callable, Generator
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

@pytest.fixture
def mock_redis() -> Generator[MagicMock, None, None]:
    """opt-in：需要 assert redis 行為或避免真實連線的測試明確注入。"""
    r = MagicMock()
    r.get.return_value = None
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

def _user_factory(uid: uuid.UUID, username: str, is_superadmin: bool) -> MagicMock:
    u = MagicMock()
    u.id = uid
    u.username = username
    u.password_hash = HASHED_PASSWORD
    u.is_superadmin = is_superadmin
    u.is_active = True
    return u


@pytest.fixture
def superadmin_user() -> MagicMock:
    return _user_factory(SUPERADMIN_ID, "admin", is_superadmin=True)


@pytest.fixture
def editor_user() -> MagicMock:
    return _user_factory(EDITOR_ID, "editor", is_superadmin=False)


@pytest.fixture
def reviewer_user() -> MagicMock:
    return _user_factory(REVIEWER_ID, "reviewer", is_superadmin=False)


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


# ── Agent mock factory ────────────────────────────────────────────────────────

@pytest.fixture
def agent_factory():
    """建立 Agent MagicMock 的 factory，可覆寫任意欄位。

    預設值適用於大多數測試；對 Rasa 測試可覆寫 rasa_rest_url、
    對 ingestion 測試可覆寫 txt_output_path / ingest_script_path。
    """
    def _factory(
        agent_id: uuid.UUID = AGENT_ID,
        name: str = "TestAgent",
        txt_output_path: str = "/opt/rasa_docs/test",
        rasa_rest_url: str | None = "http://rasa:5005/webhooks/rest/webhook",
        ingest_script_path: str | None = "ingest.py",
        **kwargs,
    ) -> MagicMock:
        a = MagicMock()
        a.id = agent_id
        a.name = name
        a.txt_output_path = txt_output_path
        a.rasa_rest_url = rasa_rest_url
        a.ingest_script_path = ingest_script_path
        for k, v in kwargs.items():
            setattr(a, k, v)
        return a
    return _factory


# ── 共用 query.side_effect helper（require_agent_access 序列）─────────────────

def build_agent_access_query_se(
    *,
    agent: MagicMock,
    uar_role: str | None = None,
    extra_results: list | None = None,
) -> Callable:
    """模擬 require_agent_access 的 query 序：第 0 次回 Agent，第 1 次回 UAR。

    Args:
        agent: Agent MagicMock（通常由 agent_factory 建立）
        uar_role: UAR 角色字串
            - None: 沒有 UAR（superadmin 路徑或無權限）
            - 'reviewer' / 'editor': 一般使用者
        extra_results: 第 2 次起的查詢結果（依序對應）
            每個元素若為 list 則該次回傳 .all() 結果；
            若為單一物件則回傳 .first() 結果；
            若為 None 則回傳 None（first）或 [] (all)

    範例：
        # 純 require_agent_access（無後續查詢）
        mock_db.query.side_effect = build_agent_access_query_se(
            agent=agent, uar_role='reviewer')

        # require_agent_access + 後續取 SyncLog list 與 user list
        mock_db.query.side_effect = build_agent_access_query_se(
            agent=agent, uar_role=None,
            extra_results=[logs, users])
    """
    counter = [0]
    extras = extra_results or []

    def se(*args, **kwargs):  # noqa: ARG001
        q = MagicMock()
        idx = counter[0]
        counter[0] += 1

        if idx == 0:
            q.filter.return_value.first.return_value = agent
        elif idx == 1:
            if uar_role is None:
                q.filter.return_value.first.return_value = None
            else:
                uar = MagicMock()
                uar.role = uar_role
                q.filter.return_value.first.return_value = uar
        else:
            extra_idx = idx - 2
            if extra_idx < len(extras):
                result = extras[extra_idx]
                if isinstance(result, list):
                    q.filter.return_value.all.return_value = result
                elif result is None:
                    q.filter.return_value.first.return_value = None
                    q.filter.return_value.all.return_value = []
                else:
                    q.filter.return_value.first.return_value = result
        return q

    return se
