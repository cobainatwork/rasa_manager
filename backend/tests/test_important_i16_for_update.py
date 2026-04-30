"""
Regression test for I16：FAQ 寫入路徑必須使用 with_for_update 取得 row-level lock。

無法在 unit test 模擬真實的 Postgres row lock 競態，這裡退而檢查：
1. 寫入路徑的 query 內含 with_for_update 呼叫鏈（透過 mock 觀察）。
2. 目前已有的 _get_faq_for_update_or_404 helper 確實使用 with_for_update。
"""
from __future__ import annotations

import inspect

from api.routes import faq as faq_mod


class TestI16ForUpdateHelper:
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
