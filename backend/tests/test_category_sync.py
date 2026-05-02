"""
分類同步功能測試：utils、endpoint、task。
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock



CAT_A_ID = uuid.UUID("00000000-0000-0000-0000-000000000020")
CAT_B_ID = uuid.UUID("00000000-0000-0000-0000-000000000021")
CAT_C_ID = uuid.UUID("00000000-0000-0000-0000-000000000022")


def _make_cat(cat_id: uuid.UUID, name: str, parent_id=None):
    c = MagicMock()
    c.id = cat_id
    c.name = name
    c.parent_id = parent_id
    return c


# ── api.utils.category_path ───────────────────────────────────────────────────

class TestBuildCategoryPath:
    def test_single_level(self) -> None:
        from api.utils.category_path import build_category_path
        cat = _make_cat(CAT_A_ID, "帳號")
        cat_map = {CAT_A_ID: cat}
        assert build_category_path(CAT_A_ID, cat_map) == "帳號"

    def test_two_levels(self) -> None:
        from api.utils.category_path import build_category_path
        parent = _make_cat(CAT_A_ID, "帳號", parent_id=None)
        child = _make_cat(CAT_B_ID, "密碼重置", parent_id=CAT_A_ID)
        cat_map = {CAT_A_ID: parent, CAT_B_ID: child}
        assert build_category_path(CAT_B_ID, cat_map) == "帳號/密碼重置"

    def test_three_levels(self) -> None:
        from api.utils.category_path import build_category_path
        root = _make_cat(CAT_A_ID, "客服", parent_id=None)
        mid = _make_cat(CAT_B_ID, "帳號", parent_id=CAT_A_ID)
        leaf = _make_cat(CAT_C_ID, "密碼", parent_id=CAT_B_ID)
        cat_map = {CAT_A_ID: root, CAT_B_ID: mid, CAT_C_ID: leaf}
        assert build_category_path(CAT_C_ID, cat_map) == "客服/帳號/密碼"

    def test_missing_category_returns_empty(self) -> None:
        from api.utils.category_path import build_category_path
        assert build_category_path(CAT_A_ID, {}) == ""


class TestCollectCategorySubtree:
    def test_leaf_returns_self_only(self) -> None:
        from api.utils.category_path import collect_category_subtree
        leaf = _make_cat(CAT_A_ID, "葉節點", parent_id=None)
        cat_map = {CAT_A_ID: leaf}
        result = collect_category_subtree(CAT_A_ID, cat_map)
        assert result == {CAT_A_ID}

    def test_parent_includes_children(self) -> None:
        from api.utils.category_path import collect_category_subtree
        parent = _make_cat(CAT_A_ID, "父", parent_id=None)
        child = _make_cat(CAT_B_ID, "子", parent_id=CAT_A_ID)
        grandchild = _make_cat(CAT_C_ID, "孫", parent_id=CAT_B_ID)
        cat_map = {CAT_A_ID: parent, CAT_B_ID: child, CAT_C_ID: grandchild}
        result = collect_category_subtree(CAT_A_ID, cat_map)
        assert result == {CAT_A_ID, CAT_B_ID, CAT_C_ID}

    def test_subtree_only_one_branch(self) -> None:
        from api.utils.category_path import collect_category_subtree
        root = _make_cat(CAT_A_ID, "根", parent_id=None)
        branch1 = _make_cat(CAT_B_ID, "分支1", parent_id=CAT_A_ID)
        branch2 = _make_cat(CAT_C_ID, "分支2", parent_id=CAT_A_ID)
        cat_map = {CAT_A_ID: root, CAT_B_ID: branch1, CAT_C_ID: branch2}
        # 只收集 branch1 的子樹
        result = collect_category_subtree(CAT_B_ID, cat_map)
        assert result == {CAT_B_ID}
