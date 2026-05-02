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


# ── ingest_kb 擴充測試 ────────────────────────────────────────────────────────

class TestParsKbWithCategoryBlocks:
    """parse_kb() 支援新格式（含 [Category] 區塊）。"""

    def _write_tmp(self, tmp_path, content: str):
        p = tmp_path / "kb.txt"
        p.write_text(content, encoding="utf-8")
        return str(p)

    def test_single_faq_with_category(self, tmp_path) -> None:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
        from ingest_kb import parse_kb  # noqa: PLC0415
        content = "[Category]\n帳號/密碼重置\n\n[Question]\n如何重設密碼？\n\n[Answer]\n點擊忘記密碼。"
        path = self._write_tmp(tmp_path, content)
        records = parse_kb(path)
        assert len(records) == 1
        assert records[0]["question"] == "如何重設密碼？"
        assert records[0]["answer"] == "點擊忘記密碼。"
        assert records[0]["category_path"] == "帳號/密碼重置"

    def test_multiple_faqs_different_categories(self, tmp_path) -> None:
        from ingest_kb import parse_kb  # noqa: PLC0415
        content = (
            "[Category]\n帳號/密碼重置\n\n[Question]\nQ1\n\n[Answer]\nA1\n\n"
            "[Category]\n帳號/帳號停用\n\n[Question]\nQ2\n\n[Answer]\nA2"
        )
        path = self._write_tmp(tmp_path, content)
        records = parse_kb(path)
        assert len(records) == 2
        assert records[0]["category_path"] == "帳號/密碼重置"
        assert records[1]["category_path"] == "帳號/帳號停用"

    def test_old_format_without_category_still_works(self, tmp_path) -> None:
        from ingest_kb import parse_kb  # noqa: PLC0415
        content = "[Question]\n舊格式問題\n\n[Answer]\n舊格式答案"
        path = self._write_tmp(tmp_path, content)
        records = parse_kb(path)
        assert len(records) == 1
        assert records[0]["question"] == "舊格式問題"
        assert records[0].get("category_path") is None


class TestDeleteByCategoryPaths:
    def test_calls_qdrant_delete_with_filter(self) -> None:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
        from ingest_kb import delete_by_category_paths  # noqa: PLC0415
        from unittest.mock import MagicMock

        qdrant = MagicMock()
        col = MagicMock()
        col.name = "agent_abc"
        qdrant.get_collections.return_value.collections = [col]

        delete_by_category_paths(qdrant, "agent_abc", ["帳號/密碼", "帳號/停用"])

        qdrant.delete.assert_called_once()
        call_kwargs = qdrant.delete.call_args.kwargs
        assert call_kwargs["collection_name"] == "agent_abc"

    def test_skips_if_collection_not_exist(self) -> None:
        from ingest_kb import delete_by_category_paths  # noqa: PLC0415
        from unittest.mock import MagicMock

        qdrant = MagicMock()
        qdrant.get_collections.return_value.collections = []

        delete_by_category_paths(qdrant, "not_exist", ["path/A"])

        qdrant.delete.assert_not_called()

    def test_skips_if_category_paths_empty(self) -> None:
        from ingest_kb import delete_by_category_paths  # noqa: PLC0415
        from unittest.mock import MagicMock

        qdrant = MagicMock()

        delete_by_category_paths(qdrant, "agent_abc", [])

        qdrant.get_collections.assert_not_called()
        qdrant.delete.assert_not_called()
