"""
分類節點 CRUD 路由測試。
覆蓋：_build_tree、_collect_descendants（純邏輯），
      list_categories、create_category、update_category、delete_category（HTTP）
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from api.routes.categories import _build_tree, _collect_descendants
from tests.conftest import AGENT_ID

CAT_ID   = uuid.UUID("00000000-0000-0000-0000-000000000020")
CHILD_ID = uuid.UUID("00000000-0000-0000-0000-000000000021")


def _cat_mock(
    cat_id: uuid.UUID = CAT_ID,
    parent_id: uuid.UUID | None = None,
    name: str = "測試分類",
    sort_order: int = 0,
) -> MagicMock:
    c = MagicMock()
    c.id = cat_id
    c.agent_id = AGENT_ID
    c.parent_id = parent_id
    c.name = name
    c.sort_order = sort_order
    c.created_at = None
    c.updated_at = None
    return c


@pytest.fixture
def _agent_mock(agent_factory):
    """檔內 fixture，回傳建立 Agent mock 的 callable。"""
    def _make() -> MagicMock:
        return agent_factory(name="TestAgent")
    return _make


def _make_superadmin_se(
    first_returns: list,
    all_returns: list | None = None,
) -> object:
    """
    建立 db.query.side_effect。
    first_returns[i]：第 i 次 query 的 .filter().first() 回傳值。
    all_returns：若設定，覆蓋第 1 次後的 .filter().all() 回傳值（預設空列表）。
    """
    counter = [0]

    def se(*args):
        q = MagicMock()
        idx = counter[0]
        counter[0] += 1
        fv = first_returns[idx] if idx < len(first_returns) else None
        q.filter.return_value.first.return_value = fv
        av = all_returns[idx] if (all_returns and idx < len(all_returns)) else []
        q.filter.return_value.all.return_value = av
        return q

    return se


# ─── _build_tree ──────────────────────────────────────────────────────────────

class TestBuildTree:
    def test_empty_list_returns_empty(self) -> None:
        assert _build_tree([]) == []

    def test_single_root_node(self) -> None:
        rows: list[dict] = [
            {
                "id": CAT_ID, "parent_id": None, "name": "Root",
                "sort_order": 0, "children": [], "created_at": None, "updated_at": None,
            }
        ]
        result = _build_tree(rows)
        assert len(result) == 1
        assert result[0]["name"] == "Root"
        assert result[0]["children"] == []

    def test_nested_tree_parent_child(self) -> None:
        rows: list[dict] = [
            {
                "id": CAT_ID, "parent_id": None, "name": "Parent",
                "sort_order": 0, "children": [], "created_at": None, "updated_at": None,
            },
            {
                "id": CHILD_ID, "parent_id": CAT_ID, "name": "Child",
                "sort_order": 0, "children": [], "created_at": None, "updated_at": None,
            },
        ]
        result = _build_tree(rows)
        assert len(result) == 1
        assert result[0]["name"] == "Parent"
        assert len(result[0]["children"]) == 1
        assert result[0]["children"][0]["name"] == "Child"

    def test_sort_order_ascending(self) -> None:
        id_a = uuid.uuid4()
        id_b = uuid.uuid4()
        rows: list[dict] = [
            {
                "id": id_b, "parent_id": None, "name": "B",
                "sort_order": 2, "children": [], "created_at": None, "updated_at": None,
            },
            {
                "id": id_a, "parent_id": None, "name": "A",
                "sort_order": 1, "children": [], "created_at": None, "updated_at": None,
            },
        ]
        result = _build_tree(rows)
        assert result[0]["name"] == "A"
        assert result[1]["name"] == "B"

    def test_multiple_root_nodes(self) -> None:
        rows: list[dict] = [
            {
                "id": uuid.uuid4(), "parent_id": None, "name": f"Node{i}",
                "sort_order": i, "children": [], "created_at": None, "updated_at": None,
            }
            for i in range(3)
        ]
        result = _build_tree(rows)
        assert len(result) == 3


# ─── _collect_descendants ─────────────────────────────────────────────────────

class TestCollectDescendants:
    def test_no_children_returns_empty_set(self) -> None:
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        result = _collect_descendants(db, CAT_ID, AGENT_ID)
        assert result == set()

    def test_one_direct_child(self):
        db = MagicMock()
        child = _cat_mock(CHILD_ID, parent_id=CAT_ID)
        call_count = [0]

        def se(*args):
            q = MagicMock()
            if call_count[0] == 0:
                q.filter.return_value.all.return_value = [child]
            else:
                q.filter.return_value.all.return_value = []  # 遞迴終止
            call_count[0] += 1
            return q

        db.query.side_effect = se
        result = _collect_descendants(db, CAT_ID, AGENT_ID)
        assert CHILD_ID in result

    def test_two_level_nesting(self):
        db = MagicMock()
        grandchild_id = uuid.uuid4()
        child = _cat_mock(CHILD_ID, parent_id=CAT_ID)
        grandchild = _cat_mock(grandchild_id, parent_id=CHILD_ID)
        call_count = [0]

        def se(*args):
            q = MagicMock()
            if call_count[0] == 0:
                q.filter.return_value.all.return_value = [child]
            elif call_count[0] == 1:
                q.filter.return_value.all.return_value = [grandchild]
            else:
                q.filter.return_value.all.return_value = []
            call_count[0] += 1
            return q

        db.query.side_effect = se
        result = _collect_descendants(db, CAT_ID, AGENT_ID)
        assert CHILD_ID in result
        assert grandchild_id in result


# ─── list_categories ──────────────────────────────────────────────────────────

class TestListCategories:
    def test_superadmin_returns_200_with_tree(self, client_superadmin, mock_db, _agent_mock):
        agent = _agent_mock()
        cat = _cat_mock()
        counter = [0]

        def se(*args):
            q = MagicMock()
            if counter[0] == 0:
                q.filter.return_value.first.return_value = agent
            else:
                q.filter.return_value.all.return_value = [cat]
            counter[0] += 1
            return q

        mock_db.query.side_effect = se
        resp = client_superadmin.get(f"/api/v1/agents/{AGENT_ID}/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)

    def test_empty_returns_empty_tree(self, client_superadmin, mock_db, _agent_mock):
        counter = [0]

        def se(*args):
            q = MagicMock()
            if counter[0] == 0:
                q.filter.return_value.first.return_value = _agent_mock()
            else:
                q.filter.return_value.all.return_value = []
            counter[0] += 1
            return q

        mock_db.query.side_effect = se
        resp = client_superadmin.get(f"/api/v1/agents/{AGENT_ID}/categories")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_agent_not_found_returns_404(self, client_superadmin, mock_db) -> None:
        mock_db.query.return_value.filter.return_value.first.return_value = None
        resp = client_superadmin.get(f"/api/v1/agents/{AGENT_ID}/categories")
        assert resp.status_code == 404

    def test_editor_with_role_returns_200(self, client_editor, mock_db, _agent_mock):
        agent = _agent_mock()
        counter = [0]

        def se(*args):
            q = MagicMock()
            if counter[0] == 0:
                q.filter.return_value.first.return_value = agent
            elif counter[0] == 1:
                uar = MagicMock()
                uar.role = "editor"
                q.filter.return_value.first.return_value = uar
            else:
                q.filter.return_value.all.return_value = []
            counter[0] += 1
            return q

        mock_db.query.side_effect = se
        resp = client_editor.get(f"/api/v1/agents/{AGENT_ID}/categories")
        assert resp.status_code == 200

    def test_editor_no_role_returns_403(self, client_editor, mock_db, _agent_mock):
        agent = _agent_mock()
        counter = [0]

        def se(*args):
            q = MagicMock()
            if counter[0] == 0:
                q.filter.return_value.first.return_value = agent
            else:
                q.filter.return_value.first.return_value = None  # 無 UAR
            counter[0] += 1
            return q

        mock_db.query.side_effect = se
        resp = client_editor.get(f"/api/v1/agents/{AGENT_ID}/categories")
        assert resp.status_code == 403


# ─── create_category ──────────────────────────────────────────────────────────

class TestCreateCategory:
    def test_superadmin_creates_root_category(self, client_superadmin, mock_db, _agent_mock) -> None:
        mock_db.query.return_value.filter.return_value.first.return_value = _agent_mock()
        mock_db.refresh.return_value = None
        resp = client_superadmin.post(
            f"/api/v1/agents/{AGENT_ID}/categories",
            json={"name": "新分類", "sort_order": 0},
        )
        assert resp.status_code == 201
        assert resp.json()["success"] is True

    def test_superadmin_creates_child_category(self, client_superadmin, mock_db, _agent_mock):
        counter = [0]

        def se(*args):
            q = MagicMock()
            if counter[0] == 0:
                q.filter.return_value.first.return_value = _agent_mock()
            else:
                q.filter.return_value.first.return_value = _cat_mock(CAT_ID)  # parent 存在
            counter[0] += 1
            return q

        mock_db.query.side_effect = se
        mock_db.refresh.return_value = None
        resp = client_superadmin.post(
            f"/api/v1/agents/{AGENT_ID}/categories",
            json={"name": "子分類", "sort_order": 0, "parent_id": str(CAT_ID)},
        )
        assert resp.status_code == 201

    def test_parent_not_found_returns_404(self, client_superadmin, mock_db, _agent_mock):
        counter = [0]

        def se(*args):
            q = MagicMock()
            if counter[0] == 0:
                q.filter.return_value.first.return_value = _agent_mock()
            else:
                q.filter.return_value.first.return_value = None  # parent 不存在
            counter[0] += 1
            return q

        mock_db.query.side_effect = se
        resp = client_superadmin.post(
            f"/api/v1/agents/{AGENT_ID}/categories",
            json={"name": "子分類", "sort_order": 0, "parent_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "NOT_FOUND"

    def test_editor_returns_403(self, client_editor, mock_db, _agent_mock):
        """Editor 角色無法建立分類（需要 reviewer 以上）。"""
        counter = [0]

        def se(*args):
            q = MagicMock()
            if counter[0] == 0:
                q.filter.return_value.first.return_value = _agent_mock()
            else:
                uar = MagicMock()
                uar.role = "editor"
                q.filter.return_value.first.return_value = uar
            counter[0] += 1
            return q

        mock_db.query.side_effect = se
        resp = client_editor.post(
            f"/api/v1/agents/{AGENT_ID}/categories",
            json={"name": "分類", "sort_order": 0},
        )
        assert resp.status_code == 403

    def test_missing_name_returns_422(self, client_superadmin, mock_db, _agent_mock) -> None:
        mock_db.query.return_value.filter.return_value.first.return_value = _agent_mock()
        resp = client_superadmin.post(
            f"/api/v1/agents/{AGENT_ID}/categories",
            json={"sort_order": 0},  # 缺少 name
        )
        assert resp.status_code == 422


# ─── update_category ──────────────────────────────────────────────────────────

class TestUpdateCategory:
    def test_update_name_succeeds(self, client_superadmin, mock_db, _agent_mock):
        cat = _cat_mock()
        counter = [0]

        def se(*args):
            q = MagicMock()
            if counter[0] == 0:
                q.filter.return_value.first.return_value = _agent_mock()
            else:
                q.filter.return_value.first.return_value = cat
            counter[0] += 1
            return q

        mock_db.query.side_effect = se
        mock_db.refresh.return_value = None
        resp = client_superadmin.patch(
            f"/api/v1/agents/{AGENT_ID}/categories/{CAT_ID}",
            json={"name": "更新後名稱"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_update_sort_order_succeeds(self, client_superadmin, mock_db, _agent_mock):
        cat = _cat_mock()
        counter = [0]

        def se(*args):
            q = MagicMock()
            if counter[0] == 0:
                q.filter.return_value.first.return_value = _agent_mock()
            else:
                q.filter.return_value.first.return_value = cat
            counter[0] += 1
            return q

        mock_db.query.side_effect = se
        mock_db.refresh.return_value = None
        resp = client_superadmin.patch(
            f"/api/v1/agents/{AGENT_ID}/categories/{CAT_ID}",
            json={"sort_order": 5},
        )
        assert resp.status_code == 200

    def test_category_not_found_returns_404(self, client_superadmin, mock_db, _agent_mock):
        counter = [0]

        def se(*args):
            q = MagicMock()
            if counter[0] == 0:
                q.filter.return_value.first.return_value = _agent_mock()
            else:
                q.filter.return_value.first.return_value = None
            counter[0] += 1
            return q

        mock_db.query.side_effect = se
        resp = client_superadmin.patch(
            f"/api/v1/agents/{AGENT_ID}/categories/{CAT_ID}",
            json={"name": "新名稱"},
        )
        assert resp.status_code == 404

    def test_editor_returns_403(self, client_editor, mock_db, _agent_mock):
        counter = [0]

        def se(*args):
            q = MagicMock()
            if counter[0] == 0:
                q.filter.return_value.first.return_value = _agent_mock()
            else:
                uar = MagicMock()
                uar.role = "editor"
                q.filter.return_value.first.return_value = uar
            counter[0] += 1
            return q

        mock_db.query.side_effect = se
        resp = client_editor.patch(
            f"/api/v1/agents/{AGENT_ID}/categories/{CAT_ID}",
            json={"name": "新名"},
        )
        assert resp.status_code == 403


# ─── delete_category ──────────────────────────────────────────────────────────

class TestDeleteCategory:
    def test_delete_empty_category_returns_204(self, client_superadmin, mock_db, _agent_mock):
        cat = _cat_mock()
        counter = [0]

        def se(*args):
            q = MagicMock()
            idx = counter[0]
            counter[0] += 1
            if idx == 0:
                q.filter.return_value.first.return_value = _agent_mock()  # require_agent_access
            elif idx == 1:
                q.filter.return_value.first.return_value = cat            # GET category
            elif idx == 2:
                q.filter.return_value.all.return_value = []               # _collect_descendants
            elif idx == 3:
                q.filter.return_value.first.return_value = None           # KnowledgeItem check
            else:
                q.filter.return_value.first.return_value = None
                q.filter.return_value.all.return_value = []
            return q

        mock_db.query.side_effect = se
        resp = client_superadmin.delete(
            f"/api/v1/agents/{AGENT_ID}/categories/{CAT_ID}"
        )
        assert resp.status_code == 204

    def test_category_not_found_returns_404(self, client_superadmin, mock_db, _agent_mock):
        counter = [0]

        def se(*args):
            q = MagicMock()
            if counter[0] == 0:
                q.filter.return_value.first.return_value = _agent_mock()
            else:
                q.filter.return_value.first.return_value = None
            counter[0] += 1
            return q

        mock_db.query.side_effect = se
        resp = client_superadmin.delete(
            f"/api/v1/agents/{AGENT_ID}/categories/{CAT_ID}"
        )
        assert resp.status_code == 404

    def test_has_faq_returns_422(self, client_superadmin, mock_db, _agent_mock):
        cat = _cat_mock()
        faq_mock = MagicMock()  # 代表 KnowledgeItem
        counter = [0]

        def se(*args):
            q = MagicMock()
            idx = counter[0]
            counter[0] += 1
            if idx == 0:
                q.filter.return_value.first.return_value = _agent_mock()
            elif idx == 1:
                q.filter.return_value.first.return_value = cat
            elif idx == 2:
                q.filter.return_value.all.return_value = []               # 無子孫
            elif idx == 3:
                q.filter.return_value.first.return_value = faq_mock       # 有 FAQ
            else:
                q.filter.return_value.first.return_value = None
            return q

        mock_db.query.side_effect = se
        resp = client_superadmin.delete(
            f"/api/v1/agents/{AGENT_ID}/categories/{CAT_ID}"
        )
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "UNPROCESSABLE"

    def test_editor_returns_403(self, client_editor, mock_db, _agent_mock):
        counter = [0]

        def se(*args):
            q = MagicMock()
            if counter[0] == 0:
                q.filter.return_value.first.return_value = _agent_mock()
            else:
                uar = MagicMock()
                uar.role = "editor"
                q.filter.return_value.first.return_value = uar
            counter[0] += 1
            return q

        mock_db.query.side_effect = se
        resp = client_editor.delete(
            f"/api/v1/agents/{AGENT_ID}/categories/{CAT_ID}"
        )
        assert resp.status_code == 403


# ── Regression: I5 (_collect_descendants must use recursive CTE on PG) ──────

class TestCollectDescendantsRecursiveCTERegression:
    """Regression: I5 (_collect_descendants 在 PostgreSQL 走 recursive CTE)."""

    def test_postgresql_dialect_uses_cte(self) -> None:
        from typing import Any

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
        db = MagicMock()
        db.get_bind.return_value.dialect.name = "sqlite"
        db.query.return_value.filter.return_value.all.return_value = []

        result = _collect_descendants(db, uuid.uuid4(), AGENT_ID)
        assert result == set()
        db.execute.assert_not_called()
