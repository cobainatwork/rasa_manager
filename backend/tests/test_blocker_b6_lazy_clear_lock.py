"""
Regression test for B6：_lazy_clear_lock 不得自行 commit。

依規格 §五.2，編輯鎖採 Lazy Expire 必須在「同一 transaction」內處理，
不可獨立 commit；否則：
1. update_faq 路徑下會在 with_for_update() 取得列鎖後立刻 commit 釋放鎖，
   導致 TOCTOU 競態仍存在。
2. get_faq 純讀路徑不應在無變動時觸發 commit。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from api.routes.faq import _lazy_clear_lock


class TestLazyClearLockTransaction:
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
        # 必須只 flush，不可自行 commit
        db.flush.assert_called_once()
        db.commit.assert_not_called()

    def test_fresh_lock_makes_no_changes_and_no_commit(self) -> None:
        item = self._make_fresh_locked_item()
        original_locker = item.locked_by
        db = MagicMock()

        cleared = _lazy_clear_lock(item, db)

        assert cleared is False
        assert item.locked_by == original_locker  # 未被清除
        db.flush.assert_not_called()
        db.commit.assert_not_called()

    def test_unlocked_item_no_op(self) -> None:
        item = self._make_unlocked_item()
        db = MagicMock()

        cleared = _lazy_clear_lock(item, db)

        assert cleared is False
        db.flush.assert_not_called()
        db.commit.assert_not_called()
