"""
FAQ 編輯鎖測試：acquire / extend / release / lazy clear / for-update regression。
"""
from __future__ import annotations

import inspect
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from api.routes import faq as faq_mod
from api.routes.faq import _lazy_clear_lock
from tests._faq_helpers import (
    FAQ_ID,
    _editor_then_faq_se,
    _make_faq,
    _superadmin_then_faq_se,
)
from tests.conftest import AGENT_ID, SUPERADMIN_ID


# ── acquire_lock ──────────────────────────────────────────────────────────────

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


# ── Regression: B6 (lazy clear lock must not commit, must flush only) ────────

class TestLazyClearLockRegression:
    """Regression: B6 (lazy clear lock must not commit, must flush only)."""

    def _make_expired_locked_item(self) -> MagicMock:
        item = MagicMock()
        item.locked_by = uuid.uuid4()
        item.locked_at = datetime.now(timezone.utc) - timedelta(minutes=20)
        return item

    def _make_fresh_locked_item(self) -> MagicMock:
        item = MagicMock()
        item.locked_by = uuid.uuid4()
        item.locked_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        return item

    def _make_unlocked_item(self) -> MagicMock:
        item = MagicMock()
        item.locked_by = None
        item.locked_at = None
        return item

    def test_expired_lock_clears_fields_and_flushes_without_commit(self) -> None:
        item = self._make_expired_locked_item()
        db = MagicMock()

        cleared = _lazy_clear_lock(item, db)

        assert cleared is True
        assert item.locked_by is None
        assert item.locked_at is None
        db.flush.assert_called_once()
        db.commit.assert_not_called()

    def test_fresh_lock_makes_no_changes_and_no_commit(self) -> None:
        item = self._make_fresh_locked_item()
        original_locker = item.locked_by
        db = MagicMock()

        cleared = _lazy_clear_lock(item, db)

        assert cleared is False
        assert item.locked_by == original_locker
        db.flush.assert_not_called()
        db.commit.assert_not_called()

    def test_unlocked_item_no_op(self) -> None:
        item = self._make_unlocked_item()
        db = MagicMock()

        cleared = _lazy_clear_lock(item, db)

        assert cleared is False
        db.flush.assert_not_called()
        db.commit.assert_not_called()


# ── Regression: I16 (write paths must use SELECT FOR UPDATE) ─────────────────

class TestForUpdateRegression:
    """Regression: I16 (write paths must use SELECT FOR UPDATE)."""

    def test_helper_uses_with_for_update(self) -> None:
        src = inspect.getsource(faq_mod._get_faq_for_update_or_404)
        assert ".with_for_update()" in src

    def test_update_status_uses_for_update_helper(self) -> None:
        src = inspect.getsource(faq_mod.update_faq_status)
        assert "_get_faq_for_update_or_404" in src, (
            "update_faq_status 必須使用 _get_faq_for_update_or_404，避免並發競態"
        )

    def test_acquire_lock_uses_for_update_helper(self) -> None:
        src = inspect.getsource(faq_mod.acquire_lock)
        assert "_get_faq_for_update_or_404" in src

    def test_extend_lock_uses_for_update_helper(self) -> None:
        src = inspect.getsource(faq_mod.extend_lock)
        assert "_get_faq_for_update_or_404" in src

    def test_release_lock_uses_for_update_helper(self) -> None:
        src = inspect.getsource(faq_mod.release_lock)
        assert "_get_faq_for_update_or_404" in src

    def test_rollback_uses_for_update_helper(self) -> None:
        src = inspect.getsource(faq_mod.rollback_faq)
        assert "_get_faq_for_update_or_404" in src

    def test_update_faq_uses_for_update_helper(self) -> None:
        src = inspect.getsource(faq_mod.update_faq)
        assert "_get_faq_for_update_or_404" in src
