"""
main.py 與 api.dependencies 的 module-level singleton regression 測試。
"""
from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def disable_redis_autouse(monkeypatch: pytest.MonkeyPatch) -> None:
    """暫時停用 conftest 的 autouse redis patch，讓 _get_redis 走原始邏輯。"""
    return None


# ── Regression: I12 (api.dependencies._get_redis must be module-level singleton) ──

class TestRedisSingletonRegression:
    """Regression: I12 (api.dependencies._get_redis 為 module-level singleton)."""

    def test_returns_same_instance(self) -> None:
        """驗證 _get_redis 的 singleton 邏輯。"""
        import api.dependencies as deps

        # 重置 singleton
        deps._redis_client = None

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


# ── Regression: I13 (main._get_health_redis must be module-level singleton) ─

class TestHealthRedisSingletonRegression:
    """Regression: I13 (main._get_health_redis 為 module-level singleton)."""

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
