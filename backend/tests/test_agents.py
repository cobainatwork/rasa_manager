"""
Agent CRUD 與角色管理路由測試。
覆蓋：list_agents, create_agent, get_agent, update_agent, delete_agent,
      get_agent_stats, assign_role, get_my_role, remove_role
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

AGENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")
USER_ID  = uuid.UUID("00000000-0000-0000-0000-000000000099")


def _agent_mock(
    agent_id: uuid.UUID = AGENT_ID,
    name: str = "TestAgent",
) -> MagicMock:
    a = MagicMock()
    a.id = agent_id
    a.name = name
    a.txt_output_path = "/output/path"
    a.rasa_rest_url = None
    a.ingest_script_path = None
    a.created_at = None
    return a


def _user_mock(user_id: uuid.UUID = USER_ID) -> MagicMock:
    u = MagicMock()
    u.id = user_id
    u.username = "target_user"
    u.is_superadmin = False
    u.is_active = True
    u.created_at = None
    return u


def _uar_mock(role: str = "editor") -> MagicMock:
    uar = MagicMock()
    uar.user_id = USER_ID
    uar.agent_id = AGENT_ID
    uar.role = role
    return uar


def _make_counter_se(returns_map: dict[int, MagicMock | list]) -> object:
    """
    依呼叫順序回傳不同值的 side_effect。
    returns_map[i] 可為 MagicMock（.first() 用）或 list（.all() 用）。
    未設定的 index 回傳 None / []。
    """
    counter = [0]

    def se(*args):
        q = MagicMock()
        idx = counter[0]
        counter[0] += 1
        val = returns_map.get(idx, None)
        if isinstance(val, list):
            q.filter.return_value.all.return_value = val
            q.filter.return_value.first.return_value = val[0] if val else None
        else:
            q.filter.return_value.first.return_value = val
            q.filter.return_value.all.return_value = [val] if val is not None else []
        return q

    return se


# ─── list_agents ──────────────────────────────────────────────────────────────

class TestListAgents:
    def test_superadmin_sees_all(self, client_superadmin, mock_db):
        agent = _agent_mock()
        mock_db.query.return_value.order_by.return_value.all.return_value = [agent]
        resp = client_superadmin.get("/api/v1/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["data"]) == 1

    def test_editor_sees_only_assigned(self, client_editor, mock_db):
        uar = _uar_mock("editor")
        uar.agent_id = AGENT_ID
        agent = _agent_mock()
        counter = [0]

        def se(*args):
            q = MagicMock()
            if counter[0] == 0:
                # UserAgentRole query
                q.filter.return_value.all.return_value = [uar]
            else:
                # Agent query
                q.filter.return_value.all.return_value = [agent]
            counter[0] += 1
            return q

        mock_db.query.side_effect = se
        resp = client_editor.get("/api/v1/agents")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1

    def test_editor_with_no_roles_returns_empty_list(self, client_editor, mock_db):
        counter = [0]

        def se(*args):
            q = MagicMock()
            if counter[0] == 0:
                q.filter.return_value.all.return_value = []  # 無任何 UAR
            else:
                q.filter.return_value.all.return_value = []
            counter[0] += 1
            return q

        mock_db.query.side_effect = se
        resp = client_editor.get("/api/v1/agents")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_superadmin_empty_db_returns_empty(self, client_superadmin, mock_db):
        mock_db.query.return_value.order_by.return_value.all.return_value = []
        resp = client_superadmin.get("/api/v1/agents")
        assert resp.status_code == 200
        assert resp.json()["data"] == []


# ─── create_agent ─────────────────────────────────────────────────────────────

class TestCreateAgent:
    def test_success_returns_201(self, client_superadmin, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.refresh.return_value = None
        resp = client_superadmin.post(
            "/api/v1/agents",
            json={"name": "NewAgent", "txt_output_path": "/output/new"},
        )
        assert resp.status_code == 201
        assert resp.json()["success"] is True

    def test_duplicate_name_returns_409(self, client_superadmin, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = _agent_mock()
        resp = client_superadmin.post(
            "/api/v1/agents",
            json={"name": "TestAgent", "txt_output_path": "/output"},
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "CONFLICT"

    def test_editor_returns_403(self, client_editor, mock_db):
        resp = client_editor.post(
            "/api/v1/agents",
            json={"name": "NewAgent", "txt_output_path": "/output"},
        )
        assert resp.status_code == 403

    def test_missing_txt_output_path_returns_422(self, client_superadmin, mock_db):
        resp = client_superadmin.post(
            "/api/v1/agents",
            json={"name": "NewAgent"},
        )
        assert resp.status_code == 422


# ─── get_agent ────────────────────────────────────────────────────────────────

class TestGetAgent:
    def test_superadmin_returns_200(self, client_superadmin, mock_db):
        agent = _agent_mock()
        mock_db.query.return_value.filter.return_value.first.return_value = agent
        resp = client_superadmin.get(f"/api/v1/agents/{AGENT_ID}")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_agent_not_found_returns_404(self, client_superadmin, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None
        resp = client_superadmin.get(f"/api/v1/agents/{AGENT_ID}")
        assert resp.status_code == 404

    def test_editor_with_role_returns_200(self, client_editor, mock_db):
        mock_db.query.side_effect = _make_counter_se({
            0: _agent_mock(),
            1: _uar_mock("editor"),
        })
        resp = client_editor.get(f"/api/v1/agents/{AGENT_ID}")
        assert resp.status_code == 200


# ─── update_agent ─────────────────────────────────────────────────────────────

class TestUpdateAgent:
    def test_success_returns_200(self, client_superadmin, mock_db):
        agent = _agent_mock()
        mock_db.query.return_value.filter.return_value.first.return_value = agent
        mock_db.refresh.return_value = None
        resp = client_superadmin.put(
            f"/api/v1/agents/{AGENT_ID}",
            json={"name": "UpdatedAgent", "txt_output_path": "/new/path"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_agent_not_found_returns_404(self, client_superadmin, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None
        resp = client_superadmin.put(
            f"/api/v1/agents/{AGENT_ID}",
            json={"name": "X"},
        )
        assert resp.status_code == 404

    def test_editor_returns_403(self, client_editor, mock_db):
        resp = client_editor.put(
            f"/api/v1/agents/{AGENT_ID}",
            json={"name": "X"},
        )
        assert resp.status_code == 403


# ─── delete_agent ─────────────────────────────────────────────────────────────

class TestDeleteAgent:
    def test_success_no_items_returns_204(self, client_superadmin, mock_db):
        mock_db.query.side_effect = _make_counter_se({
            0: _agent_mock(),   # Agent found
            1: None,            # KnowledgeItem → none
            2: None,            # Category → none
        })
        resp = client_superadmin.delete(f"/api/v1/agents/{AGENT_ID}")
        assert resp.status_code == 204

    def test_agent_not_found_returns_404(self, client_superadmin, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None
        resp = client_superadmin.delete(f"/api/v1/agents/{AGENT_ID}")
        assert resp.status_code == 404

    def test_has_knowledge_items_returns_422(self, client_superadmin, mock_db):
        faq_mock = MagicMock()
        mock_db.query.side_effect = _make_counter_se({
            0: _agent_mock(),
            1: faq_mock,        # KnowledgeItem 存在 → 422
        })
        resp = client_superadmin.delete(f"/api/v1/agents/{AGENT_ID}")
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "UNPROCESSABLE"

    def test_has_categories_returns_422(self, client_superadmin, mock_db):
        cat_mock = MagicMock()
        mock_db.query.side_effect = _make_counter_se({
            0: _agent_mock(),
            1: None,            # 無 KnowledgeItem
            2: cat_mock,        # Category 存在 → 422
        })
        resp = client_superadmin.delete(f"/api/v1/agents/{AGENT_ID}")
        assert resp.status_code == 422

    def test_editor_returns_403(self, client_editor, mock_db):
        resp = client_editor.delete(f"/api/v1/agents/{AGENT_ID}")
        assert resp.status_code == 403


# ─── get_agent_stats ──────────────────────────────────────────────────────────

class TestGetAgentStats:
    def test_returns_200_with_counts(self, client_superadmin, mock_db):
        agent = _agent_mock()
        row = MagicMock()
        row.total = 10
        row.pending = 2
        row.approved = 3
        row.synced = 4
        row.draft = 1
        row.rejected = 0

        counter = [0]

        def se(*args):
            q = MagicMock()
            idx = counter[0]
            counter[0] += 1
            if idx == 0:
                # require_agent_access → Agent
                q.filter.return_value.first.return_value = agent
            elif idx == 1:
                # 統計彙總查詢 → row
                q.filter.return_value.first.return_value = row
            elif idx == 2:
                # Category count → scalar
                q.filter.return_value.scalar.return_value = 3
            else:
                q.filter.return_value.first.return_value = None
            return q

        mock_db.query.side_effect = se
        resp = client_superadmin.get(f"/api/v1/agents/{AGENT_ID}/stats")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_faqs"] == 10
        assert data["pending_count"] == 2
        assert data["approved_count"] == 3
        assert data["synced_count"] == 4
        assert data["draft_count"] == 1
        assert data["rejected_count"] == 0
        assert data["categories_count"] == 3

    def test_agent_not_found_returns_404(self, client_superadmin, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None
        resp = client_superadmin.get(f"/api/v1/agents/{AGENT_ID}/stats")
        assert resp.status_code == 404


# ─── assign_role ──────────────────────────────────────────────────────────────

class TestAssignRole:
    def test_assign_new_role_returns_201(self, client_superadmin, mock_db):
        mock_db.query.side_effect = _make_counter_se({
            0: _agent_mock(),   # Agent
            1: _user_mock(),    # target User
            2: None,            # UAR → not existing
        })
        resp = client_superadmin.post(
            f"/api/v1/agents/{AGENT_ID}/roles",
            json={"user_id": str(USER_ID), "role": "editor"},
        )
        assert resp.status_code == 201
        assert resp.json()["success"] is True

    def test_update_existing_role_returns_201(self, client_superadmin, mock_db):
        existing_uar = _uar_mock("editor")
        mock_db.query.side_effect = _make_counter_se({
            0: _agent_mock(),
            1: _user_mock(),
            2: existing_uar,    # UAR 已存在 → 更新
        })
        resp = client_superadmin.post(
            f"/api/v1/agents/{AGENT_ID}/roles",
            json={"user_id": str(USER_ID), "role": "reviewer"},
        )
        assert resp.status_code == 201

    def test_agent_not_found_returns_404(self, client_superadmin, mock_db):
        mock_db.query.side_effect = _make_counter_se({0: None})
        resp = client_superadmin.post(
            f"/api/v1/agents/{AGENT_ID}/roles",
            json={"user_id": str(USER_ID), "role": "editor"},
        )
        assert resp.status_code == 404

    def test_user_not_found_returns_404(self, client_superadmin, mock_db):
        mock_db.query.side_effect = _make_counter_se({
            0: _agent_mock(),
            1: None,            # target user 不存在
        })
        resp = client_superadmin.post(
            f"/api/v1/agents/{AGENT_ID}/roles",
            json={"user_id": str(USER_ID), "role": "editor"},
        )
        assert resp.status_code == 404

    def test_invalid_role_returns_422(self, client_superadmin, mock_db):
        """role 欄位只允許 reviewer | editor。"""
        resp = client_superadmin.post(
            f"/api/v1/agents/{AGENT_ID}/roles",
            json={"user_id": str(USER_ID), "role": "superadmin"},
        )
        assert resp.status_code == 422

    def test_editor_returns_403(self, client_editor, mock_db):
        resp = client_editor.post(
            f"/api/v1/agents/{AGENT_ID}/roles",
            json={"user_id": str(USER_ID), "role": "editor"},
        )
        assert resp.status_code == 403


# ─── get_my_role ──────────────────────────────────────────────────────────────

class TestGetMyRole:
    def test_superadmin_returns_200_with_no_role(self, client_superadmin, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = _agent_mock()
        resp = client_superadmin.get(f"/api/v1/agents/{AGENT_ID}/my-role")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["is_superadmin"] is True
        assert data["role"] is None

    def test_reviewer_returns_role(self, client_reviewer, mock_db):
        mock_db.query.side_effect = _make_counter_se({
            0: _agent_mock(),
            1: _uar_mock("reviewer"),
        })
        resp = client_reviewer.get(f"/api/v1/agents/{AGENT_ID}/my-role")
        assert resp.status_code == 200
        assert resp.json()["data"]["role"] == "reviewer"

    def test_agent_not_found_returns_404(self, client_superadmin, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None
        resp = client_superadmin.get(f"/api/v1/agents/{AGENT_ID}/my-role")
        assert resp.status_code == 404


# ─── remove_role ──────────────────────────────────────────────────────────────

class TestRemoveRole:
    def test_success_returns_204(self, client_superadmin, mock_db):
        uar = _uar_mock("editor")
        mock_db.query.return_value.filter.return_value.first.return_value = uar
        resp = client_superadmin.delete(
            f"/api/v1/agents/{AGENT_ID}/roles/{USER_ID}"
        )
        assert resp.status_code == 204

    def test_not_found_returns_404(self, client_superadmin, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None
        resp = client_superadmin.delete(
            f"/api/v1/agents/{AGENT_ID}/roles/{USER_ID}"
        )
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "NOT_FOUND"

    def test_editor_returns_403(self, client_editor, mock_db):
        resp = client_editor.delete(
            f"/api/v1/agents/{AGENT_ID}/roles/{USER_ID}"
        )
        assert resp.status_code == 403
