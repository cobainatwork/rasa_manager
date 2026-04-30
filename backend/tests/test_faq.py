"""
FAQ 路由測試：CRUD、狀態機、編輯鎖。

Mock 策略：
  - require_agent_access 透過 side_effect call_count 區分 Agent / UserAgentRole 查詢
  - FAQ 本身的查詢使用另一層 side_effect 回傳預設測試物件
  - superadmin fixture 只需 1 次 Agent 查詢；editor 需 Agent + UAR 共 2 次
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from tests.conftest import AGENT_ID, EDITOR_ID, SUPERADMIN_ID

# ── 測試常數 ──────────────────────────────────────────────────────────────────
CATEGORY_ID = uuid.UUID("00000000-0000-0000-0000-000000000020")
FAQ_ID      = uuid.UUID("00000000-0000-0000-0000-000000000030")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _agent_mock() -> MagicMock:
    a = MagicMock()
    a.id = AGENT_ID
    return a


def _role_mock(role: str) -> MagicMock:
    r = MagicMock()
    r.role = role
    return r


def _make_faq(
    faq_id: uuid.UUID = FAQ_ID,
    status: str = "draft",
    locked_by: uuid.UUID | None = None,
    locked_at: datetime | None = None,
    version: int = 1,
) -> MagicMock:
    item = MagicMock()
    item.id = faq_id
    item.agent_id = AGENT_ID
    item.category_id = CATEGORY_ID
    item.question = "測試問題"
    item.answer = "測試答案"
    item.tags = ["tag1"]
    item.status = status
    item.version = version
    item.locked_by = locked_by
    item.locked_at = locked_at
    item.created_by = EDITOR_ID
    item.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    item.updated_at = datetime(2025, 1, 2, tzinfo=timezone.utc)
    return item


def _superadmin_then_faq_se(faq: MagicMock | None, extra_faq_chain: dict | None = None):
    """
    side_effect：
      第 0 次 query()：Agent 查詢（供 require_agent_access superadmin 路徑使用）
      第 1 次 query()：KnowledgeItem 查詢（支援 .first() 與 list 查詢）
      第 2+ 次 query()：其他查詢（預設回傳空 MagicMock）
    """
    counter = [0]

    def se(model: object) -> MagicMock:
        q = MagicMock()
        idx = counter[0]
        counter[0] += 1

        if idx == 0:
            # Agent 查詢
            q.filter.return_value.first.return_value = _agent_mock()
        elif idx == 1:
            # KnowledgeItem 查詢：支援多種鏈
            filtered = MagicMock()
            filtered.first.return_value = faq
            filtered.filter.return_value = filtered          # 支援連續 filter()
            filtered.count.return_value = 1 if faq else 0
            filtered.order_by.return_value.offset.return_value.limit.return_value.all.return_value = (
                [faq] if faq else []
            )
            filtered.with_for_update.return_value.first.return_value = faq
            q.filter.return_value = filtered
            if extra_faq_chain:
                for k, v in extra_faq_chain.items():
                    setattr(filtered, k, v)
        else:
            # 後續查詢（如 User 查詢取得 locked_by_username）
            q.filter.return_value.first.return_value = None

        return q

    return se


def _editor_then_faq_se(faq: MagicMock | None, role: str = "editor"):
    """
    side_effect（editor / reviewer 路徑）：
      第 0 次：Agent
      第 1 次：UserAgentRole
      第 2 次：KnowledgeItem
    """
    counter = [0]

    def se(model: object) -> MagicMock:
        q = MagicMock()
        idx = counter[0]
        counter[0] += 1

        if idx == 0:
            q.filter.return_value.first.return_value = _agent_mock()
        elif idx == 1:
            # require_agent_access: db.query(UAR).filter(uid, aid).first()
            # filter() 接收多個位置引數但仍回傳 filter.return_value
            q.filter.return_value.first.return_value = _role_mock(role)
        elif idx == 2:
            filtered = MagicMock()
            filtered.first.return_value = faq
            filtered.filter.return_value = filtered
            filtered.count.return_value = 1 if faq else 0
            filtered.order_by.return_value.offset.return_value.limit.return_value.all.return_value = (
                [faq] if faq else []
            )
            filtered.with_for_update.return_value.first.return_value = faq
            q.filter.return_value = filtered
        else:
            q.filter.return_value.first.return_value = None

        return q

    return se


# ── list_faqs ─────────────────────────────────────────────────────────────────

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
            # 讓 refresh 不做任何事（item 已是 MagicMock）
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
        # 讓 refresh 後 item.status 反映 approved
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


# ── update_faq ────────────────────────────────────────────────────────────────

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
            locked_at=datetime.now(timezone.utc),  # 鎖未過期
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
        # status 應已被路由邏輯設為 draft
        assert faq.status == "draft"


# ── update_faq_status（狀態機）────────────────────────────────────────────────

class TestUpdateFaqStatus:
    def _post_status(
        self,
        client: TestClient,
        mock_db: MagicMock,
        faq: MagicMock,
        new_status: str,
        reason: str | None = None,
        editor_role: str = "editor",
        is_superadmin: bool = False,
    ) -> object:
        if is_superadmin:
            mock_db.query.side_effect = _superadmin_then_faq_se(faq)
        else:
            mock_db.query.side_effect = _editor_then_faq_se(faq, editor_role)

        payload: dict = {"status": new_status}
        if reason:
            payload["reason"] = reason
        return client.patch(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}/status",
            json=payload,
        )

    def test_superadmin_draft_to_approved(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq(status="draft")
        resp = self._post_status(
            client_superadmin, mock_db, faq, "approved", is_superadmin=True
        )
        assert resp.status_code == 200  # type: ignore[union-attr]

    def test_superadmin_pending_to_rejected_requires_reason(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq(status="pending")
        resp = self._post_status(
            client_superadmin, mock_db, faq, "rejected", is_superadmin=True
        )
        assert resp.status_code == 400  # type: ignore[union-attr]
        assert resp.json()["detail"]["code"] == "VALIDATION_ERROR"  # type: ignore[union-attr]

    def test_superadmin_pending_to_rejected_with_reason(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq(status="pending")
        resp = self._post_status(
            client_superadmin,
            mock_db,
            faq,
            "rejected",
            reason="內容不符標準",
            is_superadmin=True,
        )
        assert resp.status_code == 200  # type: ignore[union-attr]

    def test_editor_cannot_approve(
        self, client_editor: TestClient, mock_db: MagicMock
    ) -> None:
        """Editor 無法從 pending 直接 approve。"""
        faq = _make_faq(status="pending")
        resp = self._post_status(
            client_editor, mock_db, faq, "approved", editor_role="editor"
        )
        assert resp.status_code == 403  # type: ignore[union-attr]

    def test_reviewer_can_approve_pending(
        self, client_reviewer: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq(status="pending")
        resp = self._post_status(
            client_reviewer, mock_db, faq, "approved", editor_role="reviewer"
        )
        assert resp.status_code == 200  # type: ignore[union-attr]

    def test_invalid_transition_returns_403(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        """approved → pending 不在 superadmin 的允許轉換中。"""
        faq = _make_faq(status="approved")
        resp = self._post_status(
            client_superadmin, mock_db, faq, "pending", is_superadmin=True
        )
        assert resp.status_code == 403  # type: ignore[union-attr]

    def test_faq_not_found_returns_404(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        resp = self._post_status(
            client_superadmin, mock_db, None, "approved", is_superadmin=True  # type: ignore[arg-type]
        )
        assert resp.status_code == 404  # type: ignore[union-attr]


# ── acquire_lock（編輯鎖）────────────────────────────────────────────────────

class TestAcquireLock:
    def test_acquire_lock_success(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq(locked_by=None)
        mock_db.query.side_effect = _superadmin_then_faq_se(faq)
        resp = client_superadmin.post(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}/lock"
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_acquire_lock_conflict_returns_409(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        """其他使用者持有未過期鎖，應回傳 409。"""
        other_id = uuid.UUID("00000000-0000-0000-0000-000000000099")
        faq = _make_faq(
            locked_by=other_id,
            locked_at=datetime.now(timezone.utc),
        )
        mock_db.query.side_effect = _superadmin_then_faq_se(faq)
        resp = client_superadmin.post(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}/lock"
        )
        assert resp.status_code == 409

    def test_acquire_own_lock_succeeds(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        """重新取自己的鎖應成功。"""
        faq = _make_faq(
            locked_by=SUPERADMIN_ID,
            locked_at=datetime.now(timezone.utc),
        )
        mock_db.query.side_effect = _superadmin_then_faq_se(faq)
        resp = client_superadmin.post(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}/lock"
        )
        assert resp.status_code == 200

    def test_acquire_lock_not_found(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        mock_db.query.side_effect = _superadmin_then_faq_se(None)
        resp = client_superadmin.post(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}/lock"
        )
        assert resp.status_code == 404


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
        from api.routes.faq import _is_lock_expired
        from datetime import timedelta

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


# ── list_faqs（含過濾器）─────────────────────────────────────────────────────

class TestListFaqsFilters:
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


# ── update_faq（category_id / tags 變更）──────────────────────────────────────

class TestUpdateFaqFields:
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


# ── extend_lock ───────────────────────────────────────────────────────────────

class TestExtendLock:
    def test_extend_own_lock_returns_200(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq(locked_by=SUPERADMIN_ID, locked_at=datetime.now(timezone.utc))
        mock_db.query.side_effect = _superadmin_then_faq_se(faq)
        resp = client_superadmin.put(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}/lock"
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_extend_lock_not_found_returns_404(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        mock_db.query.side_effect = _superadmin_then_faq_se(None)
        resp = client_superadmin.put(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}/lock"
        )
        assert resp.status_code == 404

    def test_extend_other_lock_returns_403(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        other_id = uuid.UUID("00000000-0000-0000-0000-000000000099")
        faq = _make_faq(locked_by=other_id, locked_at=datetime.now(timezone.utc))
        mock_db.query.side_effect = _superadmin_then_faq_se(faq)
        resp = client_superadmin.put(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}/lock"
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "FORBIDDEN"


# ── release_lock ──────────────────────────────────────────────────────────────

class TestReleaseLock:
    def test_release_own_lock_returns_204(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq(locked_by=SUPERADMIN_ID, locked_at=datetime.now(timezone.utc))
        mock_db.query.side_effect = _superadmin_then_faq_se(faq)
        resp = client_superadmin.delete(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}/lock"
        )
        assert resp.status_code == 204

    def test_release_lock_not_found_returns_404(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        mock_db.query.side_effect = _superadmin_then_faq_se(None)
        resp = client_superadmin.delete(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}/lock"
        )
        assert resp.status_code == 404

    def test_release_other_lock_as_editor_returns_403(
        self, client_editor: TestClient, mock_db: MagicMock
    ) -> None:
        """非 Superadmin 且非鎖持有者，應回傳 403。"""
        other_id = uuid.UUID("00000000-0000-0000-0000-000000000099")
        faq = _make_faq(locked_by=other_id, locked_at=datetime.now(timezone.utc))
        mock_db.query.side_effect = _editor_then_faq_se(faq)
        resp = client_editor.delete(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}/lock"
        )
        assert resp.status_code == 403

    def test_superadmin_can_release_other_lock(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        """Superadmin 可強制釋放任何人的鎖。"""
        other_id = uuid.UUID("00000000-0000-0000-0000-000000000099")
        faq = _make_faq(locked_by=other_id, locked_at=datetime.now(timezone.utc))
        mock_db.query.side_effect = _superadmin_then_faq_se(faq)
        resp = client_superadmin.delete(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}/lock"
        )
        assert resp.status_code == 204


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
        faq.created_by = other_id  # 不是 EDITOR_ID
        mock_db.query.side_effect = _editor_then_faq_se(faq, role="editor")
        resp = client_editor.delete(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}"
        )
        assert resp.status_code == 403


# ── get_histories ─────────────────────────────────────────────────────────────

class TestGetHistories:
    def _make_history(self) -> MagicMock:
        h = MagicMock()
        h.id = uuid.UUID("00000000-0000-0000-0000-000000000040")
        h.item_id = FAQ_ID
        h.version = 1
        h.question = "歷史問題"
        h.answer = "歷史答案"
        h.category_id = CATEGORY_ID
        h.saved_by = SUPERADMIN_ID
        h.action = "create"
        h.action_reason = None
        h.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
        return h

    def _histories_se(self, faq: MagicMock | None, histories: list) -> object:
        """
        side_effect：
          0: Agent
          1: KnowledgeItem
          2: KnowledgeItemHistory（order_by / all）
        """
        counter = [0]

        def se(model: object) -> MagicMock:
            q = MagicMock()
            idx = counter[0]
            counter[0] += 1
            if idx == 0:
                q.filter.return_value.first.return_value = _agent_mock()
            elif idx == 1:
                q.filter.return_value.first.return_value = faq
            else:
                q.filter.return_value.order_by.return_value.all.return_value = histories
            return q

        return se

    def test_get_histories_success(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq()
        history = self._make_history()
        mock_db.query.side_effect = self._histories_se(faq, [history])
        resp = client_superadmin.get(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}/histories"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert len(body["data"]) == 1
        assert body["data"][0]["action"] == "create"

    def test_get_histories_faq_not_found(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        mock_db.query.side_effect = self._histories_se(None, [])
        resp = client_superadmin.get(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}/histories"
        )
        assert resp.status_code == 404

    def test_get_histories_empty(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq()
        mock_db.query.side_effect = self._histories_se(faq, [])
        resp = client_superadmin.get(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}/histories"
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == []


# ── rollback_faq ──────────────────────────────────────────────────────────────

class TestRollbackFaq:
    def _rollback_se(
        self,
        faq: MagicMock | None,
        history: MagicMock | None,
    ) -> object:
        """
        side_effect：
          0: Agent
          1: KnowledgeItem
          2: KnowledgeItemHistory（target version）
        """
        counter = [0]

        def se(model: object) -> MagicMock:
            q = MagicMock()
            idx = counter[0]
            counter[0] += 1
            if idx == 0:
                q.filter.return_value.first.return_value = _agent_mock()
            elif idx == 1:
                # rollback 改用 _get_faq_for_update_or_404，須兼顧 with_for_update 鏈式呼叫
                q.filter.return_value.first.return_value = faq
                q.filter.return_value.with_for_update.return_value.first.return_value = faq
            else:
                q.filter.return_value.first.return_value = history
            return q

        return se

    def _make_history(self, version: int = 1) -> MagicMock:
        h = MagicMock()
        h.version = version
        h.question = "回復的問題"
        h.answer = "回復的答案"
        h.category_id = CATEGORY_ID
        return h

    def test_rollback_success_returns_200(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq(status="approved", version=3)
        history = self._make_history(version=1)
        mock_db.query.side_effect = self._rollback_se(faq, history)
        mock_db.refresh.side_effect = None

        resp = client_superadmin.post(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}/rollback",
            json={"version": 1},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "已回復至版本" in body["message"]
        # status 應被設回 draft
        assert faq.status == "draft"

    def test_rollback_faq_not_found(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        mock_db.query.side_effect = self._rollback_se(None, None)
        resp = client_superadmin.post(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}/rollback",
            json={"version": 1},
        )
        assert resp.status_code == 404

    def test_rollback_version_not_found(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        faq = _make_faq(version=3)
        mock_db.query.side_effect = self._rollback_se(faq, None)
        resp = client_superadmin.post(
            f"/api/v1/agents/{AGENT_ID}/faqs/{FAQ_ID}/rollback",
            json={"version": 99},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "NOT_FOUND"
