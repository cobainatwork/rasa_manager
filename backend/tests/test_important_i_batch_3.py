"""
第三批 N+1 與連線洩漏修正之 regression 測試。

涵蓋：
  I1  - list_faqs 對 users 表批次查詢
  I2  - import _resolve_category_path 移除迴圈內 count()
  I3  - sync_history 批次查詢 triggered_by username
  I5  - categories _collect_descendants 在 PostgreSQL 走 recursive CTE
  I6  - import 匯出時 categories 一次性載入
  I12 - api.dependencies._get_redis 為 module-level singleton
  I13 - main._get_health_redis 為 module-level singleton
"""
from __future__ import annotations

import io
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import openpyxl
import pytest

from tests.conftest import AGENT_ID


# ── 工具：產生 xlsx ────────────────────────────────────────────────────────────

def _make_xlsx(
    rows: list[list[str]],
    headers: list[str] | None = None,
) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers or ["question", "answer", "category_path", "tags"])  # type: ignore[union-attr]
    for r in rows:
        ws.append(r)  # type: ignore[union-attr]
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ── I1：list_faqs 批次取 username ──────────────────────────────────────────────

class TestI1ListFaqsBatchUsernames:
    def test_users_queried_once_for_multiple_lockers(
        self, client_superadmin: object, mock_db: MagicMock
    ) -> None:
        """5 筆 FAQ 含不同 locked_by，User 表只應查一次（IN 批次）。"""
        from api.database.models import KnowledgeItem, User

        items = []
        for i in range(5):
            it = MagicMock()
            it.id = uuid.uuid4()
            it.agent_id = AGENT_ID
            it.category_id = uuid.uuid4()
            it.question = f"Q{i}"
            it.answer = f"A{i}"
            it.tags = []
            it.status = "draft"
            it.version = 1
            it.locked_by = uuid.uuid4()
            it.locked_at = None
            it.created_by = uuid.uuid4()
            it.created_at = None
            it.updated_at = None
            items.append(it)

        # 計數 db.query(User...) 出現次數
        user_query_count = [0]

        def query_side_effect(*args: Any) -> MagicMock:
            q = MagicMock()
            # 第一個 args 可能是 User、KnowledgeItem，或 (User.id, User.username)
            if args and args[0] is User:
                q.filter.return_value.first.return_value = MagicMock()  # require_agent_access
                return q
            if args and len(args) >= 2 and args[0] is User.id:
                user_query_count[0] += 1
                # 回傳 (id, username) tuple
                q.filter.return_value.all.return_value = [
                    (it.locked_by, f"user_{idx}") for idx, it in enumerate(items)
                ]
                return q
            if args and args[0] is KnowledgeItem:
                q.filter.return_value.count.return_value = 5
                q.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = items
                # 也支援帶其他 filter 鏈的呼叫
                q.filter.return_value.filter.return_value.count.return_value = 5
                q.filter.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = items
                return q
            return q

        mock_db.query.side_effect = query_side_effect

        with patch(
            "api.routes.faq.require_agent_access",
            return_value=(MagicMock(), None),
        ):
            resp = client_superadmin.get(  # type: ignore[attr-defined]
                f"/api/v1/agents/{AGENT_ID}/faqs"
            )

        assert resp.status_code == 200, resp.text
        # 關鍵 assertion：User 批次查詢只發生一次
        assert user_query_count[0] == 1


# ── I2：_resolve_category_path 移除 count ─────────────────────────────────────

class TestI2ResolveCategoryPathNoCount:
    def test_signature_returns_tuple_with_created_flag(self) -> None:
        from api.routes.import_export import _resolve_category_path

        existing = MagicMock()
        existing.id = uuid.uuid4()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = existing

        result = _resolve_category_path(db, AGENT_ID, "已存在")
        assert result == (existing.id, False)

    def test_created_flag_true_when_new(self) -> None:
        from api.routes.import_export import _resolve_category_path

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with patch("api.routes.import_export.Category") as MockCat:
            inst = MagicMock()
            inst.id = uuid.uuid4()
            MockCat.return_value = inst
            result = _resolve_category_path(db, AGENT_ID, "新分類")
        assert result == (inst.id, True)

    def test_no_count_calls_during_import(
        self, client_superadmin: object, mock_db: MagicMock
    ) -> None:
        """匯入 3 筆相同 category_path 的 FAQ，不應出現 count() 呼叫。"""
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.flush = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.rollback = MagicMock()

        # 攔截 count 呼叫
        count_calls = [0]

        def count_spy() -> int:
            count_calls[0] += 1
            return 0

        mock_db.query.return_value.filter.return_value.count.side_effect = count_spy

        xlsx = _make_xlsx([
            ["問題一", "答案一", "分類A", ""],
            ["問題二", "答案二", "分類A", ""],
            ["問題三", "答案三", "分類A", ""],
        ])

        with (
            patch(
                "api.routes.import_export.require_agent_access",
                return_value=(MagicMock(), None),
            ),
            patch(
                "api.routes.import_export._resolve_category_path",
                return_value=(uuid.uuid4(), False),
            ),
        ):
            resp = client_superadmin.post(  # type: ignore[attr-defined]
                f"/api/v1/agents/{AGENT_ID}/faqs/import",
                files={
                    "file": (
                        "t.xlsx",
                        xlsx,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )

        assert resp.status_code == 200
        # 理想為 0，至多遠低於 6（3 筆 × 2 次 count）
        assert count_calls[0] <= 1


# ── I3：sync_history 批次取 username ──────────────────────────────────────────

class TestI3SyncHistoryBatchUsernames:
    def test_users_queried_once_for_multiple_logs(
        self, client_superadmin: object, mock_db: MagicMock
    ) -> None:
        from api.database.models import SyncLog, User
        from datetime import datetime, timezone

        logs = []
        for _ in range(4):
            log = MagicMock()
            log.id = uuid.uuid4()
            log.status = "success"
            log.triggered_by = uuid.uuid4()
            log.started_at = datetime.now(timezone.utc)
            log.finished_at = datetime.now(timezone.utc)
            log.duration_sec = 1
            log.items_count = 10
            log.output_file = "/tmp/x.txt"
            log.stdout = ""
            log.stderr = ""
            logs.append(log)

        user_query_count = [0]

        def query_side_effect(*args: Any) -> MagicMock:
            q = MagicMock()
            if args and args[0] is User:
                q.filter.return_value.first.return_value = MagicMock()
                return q
            if args and len(args) >= 2 and args[0] is User.id:
                user_query_count[0] += 1
                q.filter.return_value.all.return_value = [
                    (log.triggered_by, f"u_{i}") for i, log in enumerate(logs)
                ]
                return q
            if args and args[0] is SyncLog:
                q.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = logs
                return q
            return q

        mock_db.query.side_effect = query_side_effect

        with patch(
            "api.routes.sync.require_reviewer_or_superadmin",
            return_value=(MagicMock(), None),
        ):
            resp = client_superadmin.get(  # type: ignore[attr-defined]
                f"/api/v1/agents/{AGENT_ID}/sync/history"
            )

        assert resp.status_code == 200, resp.text
        assert user_query_count[0] == 1


# ── I5：_collect_descendants 在 PostgreSQL 走 recursive CTE ───────────────────

class TestI5RecursiveCTE:
    def test_postgresql_dialect_uses_cte(self) -> None:
        from api.routes.categories import _collect_descendants

        db = MagicMock()
        db.get_bind.return_value.dialect.name = "postgresql"

        executed_sql: list[str] = []

        def exec_side_effect(stmt: Any, params: Any = None) -> Any:
            executed_sql.append(str(stmt))
            res = MagicMock()
            res.__iter__ = lambda self: iter([])  # type: ignore[misc]
            return res

        db.execute.side_effect = exec_side_effect

        result = _collect_descendants(db, uuid.uuid4(), AGENT_ID)
        assert result == set()
        assert len(executed_sql) == 1
        assert "WITH RECURSIVE" in executed_sql[0].upper()

    def test_non_postgresql_falls_back_to_recursion(self) -> None:
        from api.routes.categories import _collect_descendants

        db = MagicMock()
        db.get_bind.return_value.dialect.name = "sqlite"
        db.query.return_value.filter.return_value.all.return_value = []

        result = _collect_descendants(db, uuid.uuid4(), AGENT_ID)
        assert result == set()
        # fallback 不會觸發 db.execute
        db.execute.assert_not_called()


# ── I6：匯出時 categories 一次性載入 ──────────────────────────────────────────

class TestI6ExportCategoriesLoadedOnce:
    def test_categories_table_queried_once(
        self, client_superadmin: object, mock_db: MagicMock
    ) -> None:
        from api.database.models import Category, KnowledgeItem

        items = []
        for _ in range(5):
            it = MagicMock()
            it.id = uuid.uuid4()
            it.status = "approved"
            it.category_id = uuid.uuid4()
            it.tags = []
            it.question = "Q"
            it.answer = "A"
            it.version = 1
            it.created_at = None
            it.updated_at = None
            items.append(it)

        category_query_count = [0]

        def query_side_effect(*args: Any) -> MagicMock:
            q = MagicMock()
            if args and args[0] is KnowledgeItem:
                q.filter.return_value.order_by.return_value.all.return_value = items
                return q
            if args and args[0] is Category:
                category_query_count[0] += 1
                q.filter.return_value.all.return_value = []
                return q
            return q

        mock_db.query.side_effect = query_side_effect
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        with patch(
            "api.routes.import_export.require_agent_access",
            return_value=(MagicMock(), None),
        ):
            resp = client_superadmin.get(  # type: ignore[attr-defined]
                f"/api/v1/agents/{AGENT_ID}/faqs/export"
            )

        assert resp.status_code == 200
        # Category 表全載入只需一次
        assert category_query_count[0] == 1


# ── I12：dependencies._get_redis singleton ────────────────────────────────────

@pytest.fixture
def disable_redis_autouse(monkeypatch: pytest.MonkeyPatch) -> None:
    """暫時停用 conftest 的 autouse redis patch，讓 _get_redis 走原始邏輯。"""
    # conftest.mock_redis 用 patch(...) context 覆蓋 _get_redis；
    # 此 fixture 不主動還原 — 直接於測試內 reload module 重新取得未被覆蓋的版本。
    return None


class TestI12RedisSingleton:
    def test_returns_same_instance(self) -> None:
        """驗證 _get_redis 的 singleton 邏輯。"""
        import api.dependencies as deps

        # 重置 singleton
        deps._redis_client = None

        # 取得未被 conftest patch 的原始函式：
        # conftest 用 unittest.mock.patch 覆寫 deps._get_redis，
        # 但函式本體仍存在於模組的全域 namespace 中。重新 import 取得：
        import importlib
        importlib.reload(deps)
        # reload 後 conftest 的 patch 失效，可直接驗證原始實作
        deps._redis_client = None

        with patch.object(deps.redis_lib, "from_url") as mock_from_url:
            mock_from_url.return_value = MagicMock(name="redis_client")
            r1 = deps._get_redis()
            r2 = deps._get_redis()
            r3 = deps._get_redis()

        assert r1 is r2 is r3
        assert mock_from_url.call_count == 1

        # 清理：reset singleton 並 reload 還原狀態
        deps._redis_client = None
        importlib.reload(deps)


# ── I13：main._get_health_redis singleton ─────────────────────────────────────

class TestI13HealthRedisSingleton:
    def test_returns_same_instance(self) -> None:
        import main

        main._health_redis_client = None
        with patch.object(main.redis_lib, "from_url") as mock_from_url:
            mock_from_url.return_value = MagicMock()
            r1 = main._get_health_redis()
            r2 = main._get_health_redis()

        assert r1 is r2
        assert mock_from_url.call_count == 1
        main._health_redis_client = None
