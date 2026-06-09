"""
FAQ 路由 CRUD 測試：list / get / create / update / delete + helper 單元測試。

Mock 策略：
  - require_agent_access 透過 side_effect call_count 區分 Agent / UserAgentRole 查詢
  - FAQ 本身的查詢使用另一層 side_effect 回傳預設測試物件
  - superadmin fixture 只需 1 次 Agent 查詢；editor 需 Agent + UAR 共 2 次

狀態機、編輯鎖、歷史 / 回復測試已拆至：
  - tests/test_faq_status.py
  - tests/test_faq_lock.py
  - tests/test_faq_history.py
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from tests._faq_helpers import (
    CATEGORY_ID,
    FAQ_ID,
    _editor_then_faq_se,
    _make_faq,
    _superadmin_then_faq_se,
)
from tests.conftest import AGENT_ID, EDITOR_ID, SUPERADMIN_ID


# ── list_faqs（含過濾器）─────────────────────────────────────────────────────

class TestListFaqs:
    def test_list_faqs_success(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq()
        mock_db.query.side_effect = _superadmin_then_faq_se(faq)
        resp = client_superadmin.get(f"/api/v1/agents/{AGENT_ID}/faqs")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "items" in body["data"]
        assert body["data"]["total"] == 1

    def test_list_faqs_empty(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        mock_db.query.side_effect = _superadmin_then_faq_se(None)
        resp = client_superadmin.get(f"/api/v1/agents/{AGENT_ID}/faqs")
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 0

    def test_list_faqs_requires_auth(self, client_no_auth: TestClient) -> None:
        resp = client_no_auth.get(f"/api/v1/agents/{AGENT_ID}/faqs")
        assert resp.status_code == 401

    def test_list_with_category_filter(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq()
        mock_db.query.side_effect = _superadmin_then_faq_se(faq)
        resp = client_superadmin.get(
            f"/api/v1/agents/{AGENT_ID}/faqs?category_id={CATEGORY_ID}"
        )
        assert resp.status_code == 200

    def test_list_with_status_filter(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq(status="approved")
        mock_db.query.side_effect = _superadmin_then_faq_se(faq)
        resp = client_superadmin.get(
            f"/api/v1/agents/{AGENT_ID}/faqs?status=approved"
        )
        assert resp.status_code == 200

    def test_list_with_search_query(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq()
        mock_db.query.side_effect = _superadmin_then_faq_se(faq)
        resp = client_superadmin.get(
            f"/api/v1/agents/{AGENT_ID}/faqs?q=測試"
        )
        assert resp.status_code == 200


# ── get_faq ───────────────────────────────────────────────────────────────────

class TestGetFaq:
    def test_get_faq_success(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq()
        mock_db.query.side_effect = _superadmin_then_faq_se(faq)
        resp = client_superadmin.get(f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["id"] == str(FAQ_ID)
        assert body["data"]["question"] == "測試問題"

    def test_get_faq_not_found(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        mock_db.query.side_effect = _superadmin_then_faq_se(None)
        resp = client_superadmin.get(f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}")
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "NOT_FOUND"


# ── create_faq ────────────────────────────────────────────────────────────────

class TestCreateFaq:
    _PAYLOAD = {
        "category_id": str(CATEGORY_ID),
        "question": "新問題",
        "answer": "新答案",
        "tags": ["alpha"],
    }

    def _setup_create_mock(self, mock_db: MagicMock) -> None:
        """create_faq 呼叫 db.add / flush / commit / refresh，設定 refresh 後的 item。"""
        faq = _make_faq(status="draft")
        mock_db.query.side_effect = _superadmin_then_faq_se(faq)

        def refresh_side_effect(obj: object) -> None:
            pass

        mock_db.refresh.side_effect = refresh_side_effect

    def test_editor_creates_draft(
        self, client_editor: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq(status="draft")
        mock_db.query.side_effect = _editor_then_faq_se(faq)

        resp = client_editor.post(
            f"/api/v1/agents/{AGENT_ID}/faqs", json=self._PAYLOAD
        )
        assert resp.status_code == 201
        assert resp.json()["success"] is True

    def test_superadmin_creates_approved(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        """Superadmin 建立時 initial_status 為 approved（直接跳過 pending）。"""
        faq = _make_faq(status="approved")
        mock_db.query.side_effect = _superadmin_then_faq_se(faq)
        mock_db.refresh.side_effect = lambda obj: setattr(obj, "status", "approved")  # type: ignore[misc]

        resp = client_superadmin.post(
            f"/api/v1/agents/{AGENT_ID}/faqs", json=self._PAYLOAD
        )
        assert resp.status_code == 201

    def test_create_faq_missing_question_returns_422(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        mock_db.query.side_effect = _superadmin_then_faq_se(None)
        resp = client_superadmin.post(
            f"/api/v1/agents/{AGENT_ID}/faqs",
            json={"category_id": str(CATEGORY_ID), "answer": "答"},
        )
        assert resp.status_code == 422

    def test_create_faq_empty_question_returns_422(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        mock_db.query.side_effect = _superadmin_then_faq_se(None)
        resp = client_superadmin.post(
            f"/api/v1/agents/{AGENT_ID}/faqs",
            json={"category_id": str(CATEGORY_ID), "question": "", "answer": "答"},
        )
        assert resp.status_code == 422


# ── update_faq（一般欄位 + category_id / tags 變更）──────────────────────────

class TestUpdateFaq:
    def test_update_success(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq(status="draft")
        mock_db.query.side_effect = _superadmin_then_faq_se(faq)
        resp = client_superadmin.patch(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}",
            json={"question": "更新後問題"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_update_not_found(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        mock_db.query.side_effect = _superadmin_then_faq_se(None)
        resp = client_superadmin.patch(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}",
            json={"question": "更新"},
        )
        assert resp.status_code == 404

    def test_update_locked_by_other_returns_409(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        """其他使用者持有鎖，應回傳 409。"""
        other_id = uuid.UUID("00000000-0000-0000-0000-000000000099")
        faq = _make_faq(
            status="draft",
            locked_by=other_id,
            locked_at=datetime.now(timezone.utc),
        )
        mock_db.query.side_effect = _superadmin_then_faq_se(faq)
        resp = client_superadmin.patch(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}",
            json={"question": "更新"},
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "LOCKED"

    def test_approved_faq_auto_demoted_to_draft(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        """編輯 approved FAQ 應自動降級為 draft。"""
        faq = _make_faq(status="approved")
        mock_db.query.side_effect = _superadmin_then_faq_se(faq)
        resp = client_superadmin.patch(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}",
            json={"answer": "更新後答案"},
        )
        assert resp.status_code == 200
        assert faq.status == "draft"

    def test_update_category_id(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq(status="draft")
        mock_db.query.side_effect = _superadmin_then_faq_se(faq)
        new_cat = uuid.UUID("00000000-0000-0000-0000-000000000021")
        resp = client_superadmin.patch(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}",
            json={"category_id": str(new_cat)},
        )
        assert resp.status_code == 200
        assert faq.category_id == new_cat

    def test_update_tags(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq(status="draft")
        mock_db.query.side_effect = _superadmin_then_faq_se(faq)
        resp = client_superadmin.patch(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}",
            json={"tags": ["new_tag", "another"]},
        )
        assert resp.status_code == 200
        assert faq.tags == ["new_tag", "another"]

    def test_update_synced_faq_auto_demoted(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq(status="synced")
        mock_db.query.side_effect = _superadmin_then_faq_se(faq)
        resp = client_superadmin.patch(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}",
            json={"answer": "新答案"},
        )
        assert resp.status_code == 200
        assert faq.status == "draft"

    def test_no_content_change_does_not_downgrade_approved(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        """PATCH 傳入與現有值完全相同的內容 → 不應降級、不應變更版本。"""
        faq = _make_faq(status="approved", version=2)
        mock_db.query.side_effect = _superadmin_then_faq_se(faq)
        original_version = faq.version
        resp = client_superadmin.patch(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}",
            # 傳入與 _make_faq 預設值相同的內容（question / answer / tags 均未變動）
            json={"question": "測試問題", "answer": "測試答案", "tags": ["tag1"]},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        # 狀態不得降級
        assert faq.status == "approved", (
            f"無實際變更時不應降級，期望 approved，實際 {faq.status}"
        )
        # 版本不得遞增
        assert faq.version == original_version, (
            f"無實際變更時版本不應遞增，期望 {original_version}，實際 {faq.version}"
        )

    def test_same_tags_patch_does_not_downgrade(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        """PATCH 只傳 tags 且值與現有完全相同 → 不應觸發降級（原 Bug：無條件降級）。"""
        faq = _make_faq(status="approved")
        mock_db.query.side_effect = _superadmin_then_faq_se(faq)
        resp = client_superadmin.patch(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}",
            json={"tags": ["tag1"]},   # 與 _make_faq 預設 tags 相同
        )
        assert resp.status_code == 200
        assert faq.status == "approved", (
            f"相同 tags 不應觸發降級，期望 approved，實際 {faq.status}"
        )


# ── delete_faq ────────────────────────────────────────────────────────────────

class TestDeleteFaq:
    def test_superadmin_deletes_any_faq(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq(status="approved")
        mock_db.query.side_effect = _superadmin_then_faq_se(faq)
        resp = client_superadmin.delete(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}"
        )
        assert resp.status_code == 204

    def test_delete_not_found_returns_404(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        mock_db.query.side_effect = _superadmin_then_faq_se(None)
        resp = client_superadmin.delete(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}"
        )
        assert resp.status_code == 404

    def test_reviewer_cannot_delete_approved_faq(
        self, client_reviewer: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq(status="approved")
        mock_db.query.side_effect = _editor_then_faq_se(faq, role="reviewer")
        resp = client_reviewer.delete(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}"
        )
        assert resp.status_code == 403

    def test_reviewer_can_delete_draft_faq(
        self, client_reviewer: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq(status="draft")
        mock_db.query.side_effect = _editor_then_faq_se(faq, role="reviewer")
        resp = client_reviewer.delete(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}"
        )
        assert resp.status_code == 204

    def test_editor_can_delete_own_draft(
        self, client_editor: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq(status="draft")
        faq.created_by = EDITOR_ID
        mock_db.query.side_effect = _editor_then_faq_se(faq, role="editor")
        resp = client_editor.delete(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}"
        )
        assert resp.status_code == 204

    def test_editor_cannot_delete_others_draft(
        self, client_editor: TestClient, mock_db: MagicMock
    ) -> None:
        other_id = uuid.UUID("00000000-0000-0000-0000-000000000099")
        faq = _make_faq(status="draft")
        faq.created_by = other_id
        mock_db.query.side_effect = _editor_then_faq_se(faq, role="editor")
        resp = client_editor.delete(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}"
        )
        assert resp.status_code == 403


# ── helper 函式單元測試 ────────────────────────────────────────────────────────

class TestFaqHelpers:
    def test_is_lock_expired_no_lock(self) -> None:
        from api.routes.faq import _is_lock_expired

        faq = _make_faq(locked_by=None, locked_at=None)
        assert _is_lock_expired(faq) is False

    def test_is_lock_expired_fresh_lock(self) -> None:
        from api.routes.faq import _is_lock_expired

        faq = _make_faq(
            locked_by=SUPERADMIN_ID,
            locked_at=datetime.now(timezone.utc),
        )
        assert _is_lock_expired(faq) is False

    def test_is_lock_expired_old_lock(self) -> None:
        from datetime import timedelta

        from api.routes.faq import _is_lock_expired

        faq = _make_faq(
            locked_by=SUPERADMIN_ID,
            locked_at=datetime.now(timezone.utc) - timedelta(seconds=700),
        )
        assert _is_lock_expired(faq) is True

    def test_faq_to_dict_structure(self) -> None:
        from api.routes.faq import _faq_to_dict

        faq = _make_faq()
        d = _faq_to_dict(faq)
        assert "id" in d
        assert "question" in d
        assert "answer" in d
        assert "status" in d
        assert "version" in d
        assert "locked_by" in d

    def test_get_locker_username_returns_username(self) -> None:
        from api.routes.faq import _get_locker_username

        faq = _make_faq(locked_by=SUPERADMIN_ID)
        db = MagicMock()
        locker = MagicMock()
        locker.username = "admin"
        db.query.return_value.filter.return_value.first.return_value = locker
        result = _get_locker_username(faq, db)
        assert result == "admin"

    def test_get_locker_username_no_lock_returns_none(self) -> None:
        from api.routes.faq import _get_locker_username

        faq = _make_faq(locked_by=None)
        db = MagicMock()
        result = _get_locker_username(faq, db)
        assert result is None

    def test_get_locker_username_user_not_found_returns_none(self) -> None:
        from api.routes.faq import _get_locker_username

        faq = _make_faq(locked_by=SUPERADMIN_ID)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        result = _get_locker_username(faq, db)
        assert result is None


# ── Regression: I1 (list_faqs must batch-query usernames) ───────────────────

class TestListFaqsBatchUsernamesRegression:
    """Regression: I1 (list_faqs 對 users 表必須批次查詢，避免 N+1)."""

    def test_users_queried_once_for_multiple_lockers(
        self, client_superadmin, mock_db: MagicMock
    ) -> None:
        """5 筆 FAQ 含不同 locked_by，User 表只應查一次（IN 批次）。"""
        from contextlib import contextmanager

        from main import app
        from api.database.models import KnowledgeItem, User
        from api.dependencies import get_accessible_agent

        @contextmanager
        def _bypass():
            app.dependency_overrides[get_accessible_agent] = lambda: (MagicMock(), None)
            try:
                yield
            finally:
                app.dependency_overrides.pop(get_accessible_agent, None)

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

        user_query_count = [0]

        def query_side_effect(*args):
            q = MagicMock()
            if args and args[0] is User:
                q.filter.return_value.first.return_value = MagicMock()
                return q
            if args and len(args) >= 2 and args[0] is User.id:
                user_query_count[0] += 1
                q.filter.return_value.all.return_value = [
                    (it.locked_by, f"user_{idx}") for idx, it in enumerate(items)
                ]
                return q
            if args and args[0] is KnowledgeItem:
                q.filter.return_value.count.return_value = 5
                q.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = items
                q.filter.return_value.filter.return_value.count.return_value = 5
                q.filter.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = items
                return q
            return q

        mock_db.query.side_effect = query_side_effect

        with _bypass():
            resp = client_superadmin.get(
                f"/api/v1/agents/{AGENT_ID}/faqs"
            )

        assert resp.status_code == 200, resp.text
        assert user_query_count[0] == 1
