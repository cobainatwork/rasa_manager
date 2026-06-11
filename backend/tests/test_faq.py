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
from typing import Any
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from tests._faq_helpers import (
    CATEGORY_ID,
    FAQ_ID,
    _agent_mock,
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


# ── list_faqs / list_faq_ids：category_id 含子樹（regression）────────────────
#
# 既有 Bug：點 root 或中間層 category 看不到 FAQ，因為 FAQ 實際歸屬於 leaf。
# 修補：filter `category_id` 時應收集該 category 及其所有子孫 IDs。

class TestListFaqsCategorySubtree:
    """category_id filter 必須含子樹（含自身 + 所有子孫）。"""

    @staticmethod
    def _build_cat_subtree_se(
        cats: list[MagicMock], faqs: list[MagicMock]
    ) -> Any:
        """side_effect：
          idx0 Agent；idx1 Category（.filter().all() 回 cats）；
          idx2 KnowledgeItem 列出查詢；idx3 User 批次（locker 用，可選）。
        """
        from api.database.models import Category as _Cat
        from api.database.models import KnowledgeItem as _KI

        captured: dict[str, Any] = {}

        def se(model: object, *args: object) -> MagicMock:
            del args
            q = MagicMock()
            if model is _Cat:
                q.filter.return_value.all.return_value = cats
                return q
            if model is _KI:
                filtered = MagicMock()
                filtered.first.return_value = faqs[0] if faqs else None
                filtered.filter.return_value = filtered
                filtered.count.return_value = len(faqs)
                filtered.order_by.return_value.offset.return_value.limit.return_value.all.return_value = faqs
                filtered.with_for_update.return_value.first.return_value = (
                    faqs[0] if faqs else None
                )

                # 攔 .in_() 的呼叫，記錄傳入的 ids
                original_filter = filtered.filter

                def filter_with_capture(*fargs: object, **fkwargs: object) -> MagicMock:
                    for arg in fargs:
                        # SQLAlchemy clause 含 .right.value（in_ 的右值）
                        try:
                            right = getattr(arg, "right", None)
                            if right is not None:
                                val = getattr(right, "value", None)
                                if val is not None:
                                    captured.setdefault("in_values", []).append(val)
                        except Exception:  # noqa: BLE001
                            pass
                    return original_filter(*fargs, **fkwargs)

                filtered.filter = filter_with_capture
                q.filter.return_value = filtered
                return q
            # idx0 Agent + 其他
            q.filter.return_value.first.return_value = _agent_mock()
            return q

        # 包裝以暴露 captured 給測試
        se.captured = captured  # type: ignore[attr-defined]
        return se

    def test_list_with_category_subtree_root(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        """點 root → query 應該以子樹所有 ids（含自身）做 IN filter。"""
        root_id = uuid.UUID("00000000-0000-0000-0000-000000000100")
        mid_id  = uuid.UUID("00000000-0000-0000-0000-000000000101")
        leaf_id = uuid.UUID("00000000-0000-0000-0000-000000000102")

        root = MagicMock(id=root_id, parent_id=None)
        mid  = MagicMock(id=mid_id, parent_id=root_id)
        leaf = MagicMock(id=leaf_id, parent_id=mid_id)

        # 模擬 FAQ 全在 leaf
        faq = _make_faq()
        faq.category_id = leaf_id

        se = self._build_cat_subtree_se([root, mid, leaf], [faq])
        mock_db.query.side_effect = se

        resp = client_superadmin.get(
            f"/api/v1/agents/{AGENT_ID}/faqs?category_id={root_id}"
        )
        assert resp.status_code == 200, resp.text

        in_values = se.captured.get("in_values", [])  # type: ignore[attr-defined]
        assert in_values, "category_id filter 必須使用 IN(subtree_ids)"
        # 必須是 collection（IN clause），不可是單一 UUID（== clause，Bug 行為）
        first = in_values[0]
        assert not isinstance(first, uuid.UUID), (
            f"category_id filter 仍用 == 單一值，應改為 IN(subtree_ids)；got {first!r}"
        )
        ids_set = set(first)
        assert root_id in ids_set
        assert mid_id  in ids_set
        assert leaf_id in ids_set

    def test_list_with_category_subtree_middle(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        """點中間層 → 含該層 + 子孫，不含 root 兄弟。"""
        root_id   = uuid.UUID("00000000-0000-0000-0000-000000000200")
        mid_id    = uuid.UUID("00000000-0000-0000-0000-000000000201")
        leaf_id   = uuid.UUID("00000000-0000-0000-0000-000000000202")
        other_id  = uuid.UUID("00000000-0000-0000-0000-000000000203")

        root  = MagicMock(id=root_id,  parent_id=None)
        mid   = MagicMock(id=mid_id,   parent_id=root_id)
        leaf  = MagicMock(id=leaf_id,  parent_id=mid_id)
        other = MagicMock(id=other_id, parent_id=root_id)  # mid 的兄弟

        faq = _make_faq()
        faq.category_id = leaf_id
        se = self._build_cat_subtree_se([root, mid, leaf, other], [faq])
        mock_db.query.side_effect = se

        resp = client_superadmin.get(
            f"/api/v1/agents/{AGENT_ID}/faqs?category_id={mid_id}"
        )
        assert resp.status_code == 200, resp.text

        in_values = se.captured.get("in_values", [])  # type: ignore[attr-defined]
        assert in_values, "category_id filter 必須使用 IN(subtree_ids)"
        first = in_values[0]
        assert not isinstance(first, uuid.UUID), (
            f"category_id filter 仍用 == 單一值，應改為 IN(subtree_ids)；got {first!r}"
        )
        ids_set = set(first)
        assert mid_id in ids_set
        assert leaf_id in ids_set
        assert root_id not in ids_set
        assert other_id not in ids_set

    def test_list_faq_ids_with_category_subtree(
        self, client_superadmin: TestClient, mock_db: MagicMock
    ) -> None:
        """list_faq_ids endpoint：category_id filter 同樣必須含子樹。"""
        root_id = uuid.UUID("00000000-0000-0000-0000-000000000300")
        leaf_id = uuid.UUID("00000000-0000-0000-0000-000000000301")
        root = MagicMock(id=root_id, parent_id=None)
        leaf = MagicMock(id=leaf_id, parent_id=root_id)

        # list_faq_ids 用 db.query(KnowledgeItem.id)，回 row.id list
        from api.database.models import Category as _Cat

        captured: dict[str, Any] = {}
        counter = [0]

        def se(*args: object, **kwargs: object) -> MagicMock:
            del kwargs
            q = MagicMock()
            idx = counter[0]
            counter[0] += 1

            if args and args[0] is _Cat:
                q.filter.return_value.all.return_value = [root, leaf]
                return q

            if idx == 0:
                # Agent
                q.filter.return_value.first.return_value = _agent_mock()
                return q

            # KnowledgeItem.id 路徑
            filtered = MagicMock()

            def filter_capture(*fargs: object, **fkw: object) -> MagicMock:
                del fkw
                for arg in fargs:
                    try:
                        right = getattr(arg, "right", None)
                        if right is not None:
                            val = getattr(right, "value", None)
                            if val is not None:
                                captured.setdefault("in_values", []).append(val)
                    except Exception:  # noqa: BLE001
                        pass
                return filtered

            filtered.filter = filter_capture
            row = MagicMock()
            row.id = uuid.UUID("00000000-0000-0000-0000-000000000999")
            filtered.all.return_value = [row]
            q.filter.return_value = filtered
            return q

        mock_db.query.side_effect = se

        resp = client_superadmin.get(
            f"/api/v1/agents/{AGENT_ID}/faqs/ids?category_id={root_id}"
        )
        assert resp.status_code == 200, resp.text

        in_values = captured.get("in_values", [])
        assert in_values, "list_faq_ids 的 category_id filter 必須使用 IN(subtree_ids)"
        first = in_values[0]
        assert not isinstance(first, uuid.UUID), (
            f"list_faq_ids 仍用 == 單一值，應改為 IN(subtree_ids)；got {first!r}"
        )
        ids_set = set(first)
        assert root_id in ids_set
        assert leaf_id in ids_set


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
