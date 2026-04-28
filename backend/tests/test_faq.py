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
