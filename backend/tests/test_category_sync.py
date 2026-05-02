"""
分類同步功能測試：utils、endpoint、task。
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch
from tests.conftest import AGENT_ID, build_agent_access_query_se



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


# ── run_category_sync task ────────────────────────────────────────────────────

import os
from unittest.mock import mock_open

CATEGORY_ID = uuid.UUID("00000000-0000-0000-0000-000000000030")
CAT_SYNC_LOG_ID = uuid.UUID("00000000-0000-0000-0000-000000000051")


def _make_sync_log(sync_id=CAT_SYNC_LOG_ID):
    sl = MagicMock()
    sl.id = sync_id
    sl.agent_id = AGENT_ID
    sl.status = "pending"
    sl.started_at = None
    sl.items_count = 0
    sl.stdout = None
    sl.stderr = None
    sl.finished_at = None
    sl.duration_sec = None
    return sl


def _make_agent():
    a = MagicMock()
    a.id = AGENT_ID
    a.txt_output_path = "/opt/rasa_docs/test"
    a.ingest_script_path = None  # 預設不設 script（跳過 subprocess）
    return a


def _make_category(cat_id=CATEGORY_ID, name="帳號", parent_id=None):
    c = MagicMock()
    c.id = cat_id
    c.agent_id = AGENT_ID
    c.name = name
    c.parent_id = parent_id
    return c


class TestRunCategorySyncTask:
    SESSION_PATCH = "api.database.session.SessionLocal"

    def _make_db_with_sequence(self, sync_log, agent, category, items, all_cats):
        """
        模擬 run_category_sync 的 db.query 呼叫序列：
        idx 0: SyncLog
        idx 1: Agent
        idx 2: Category（目標分類）
        idx 3: Category.all()（全部分類）
        idx 4: KnowledgeItem.all()（FAQ）
        """
        db = MagicMock()
        counter = [0]

        def se(*args):
            q = MagicMock()
            idx = counter[0]
            counter[0] += 1
            if idx == 0:
                q.filter.return_value.first.return_value = sync_log
            elif idx == 1:
                q.filter.return_value.first.return_value = agent
            elif idx == 2:
                q.filter.return_value.first.return_value = category
            elif idx == 3:
                q.filter.return_value.all.return_value = all_cats
            elif idx == 4:
                q.filter.return_value.all.return_value = items
            return q

        db.query.side_effect = se
        return db

    def test_no_items_marks_completed_with_zero_count(self) -> None:
        from tasks import run_category_sync  # noqa: PLC0415

        sync_log = _make_sync_log()
        agent = _make_agent()
        category = _make_category()
        db = self._make_db_with_sequence(sync_log, agent, category, [], [category])

        with (
            patch(self.SESSION_PATCH, return_value=db),
            patch("builtins.open", mock_open()),
            patch("os.makedirs"),
        ):
            run_category_sync(
                str(AGENT_ID), str(CATEGORY_ID), str(CAT_SYNC_LOG_ID)
            )

        assert sync_log.status == "completed"
        assert sync_log.items_count == 0

    def test_sync_log_not_found_returns_early(self) -> None:
        from tasks import run_category_sync  # noqa: PLC0415

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with patch(self.SESSION_PATCH, return_value=db):
            run_category_sync(
                str(AGENT_ID), str(CATEGORY_ID), str(CAT_SYNC_LOG_ID)
            )

        db.commit.assert_not_called()

    def test_category_not_found_marks_failed(self) -> None:
        from tasks import run_category_sync  # noqa: PLC0415

        sync_log = _make_sync_log()
        agent = _make_agent()
        db = MagicMock()
        counter = [0]

        def se(*args):
            q = MagicMock()
            idx = counter[0]
            counter[0] += 1
            if idx == 0:
                q.filter.return_value.first.return_value = sync_log
            elif idx == 1:
                q.filter.return_value.first.return_value = agent
            else:
                q.filter.return_value.first.return_value = None  # 分類不存在
            return q

        db.query.side_effect = se

        with patch(self.SESSION_PATCH, return_value=db):
            run_category_sync(
                str(AGENT_ID), str(CATEGORY_ID), str(CAT_SYNC_LOG_ID)
            )

        assert sync_log.status == "failed"
        assert "分類不存在" in (sync_log.stderr or "")

    def test_items_written_to_txt_with_category_block(self) -> None:
        from tasks import run_category_sync  # noqa: PLC0415

        sync_log = _make_sync_log()
        agent = _make_agent()
        category = _make_category(name="帳號")

        item = MagicMock()
        item.id = uuid.uuid4()
        item.category_id = CATEGORY_ID
        item.question = "測試問題"
        item.answer = "測試答案"
        item.status = "approved"

        db = self._make_db_with_sequence(
            sync_log, agent, category, [item], [category]
        )

        written_content: list[str] = []
        m_open = mock_open()
        m_open.return_value.__enter__.return_value.write.side_effect = (
            lambda c: written_content.append(c)
        )

        with (
            patch(self.SESSION_PATCH, return_value=db),
            patch("builtins.open", m_open),
            patch("os.makedirs"),
        ):
            run_category_sync(
                str(AGENT_ID), str(CATEGORY_ID), str(CAT_SYNC_LOG_ID)
            )

        full_content = "".join(written_content)
        assert "[Category]" in full_content
        assert "帳號" in full_content
        assert "[Question]" in full_content
        assert "測試問題" in full_content

    def test_items_marked_synced_on_success(self) -> None:
        from tasks import run_category_sync  # noqa: PLC0415

        sync_log = _make_sync_log()
        agent = _make_agent()
        category = _make_category()

        item = MagicMock()
        item.id = uuid.uuid4()
        item.category_id = CATEGORY_ID
        item.question = "Q"
        item.answer = "A"
        item.status = "approved"

        db = self._make_db_with_sequence(
            sync_log, agent, category, [item], [category]
        )

        with (
            patch(self.SESSION_PATCH, return_value=db),
            patch("builtins.open", mock_open()),
            patch("os.makedirs"),
        ):
            run_category_sync(
                str(AGENT_ID), str(CATEGORY_ID), str(CAT_SYNC_LOG_ID)
            )

        assert item.status == "synced"


# ── trigger_category_sync endpoint ───────────────────────────────────────────

def _make_cat_for_api(cat_id: uuid.UUID = CATEGORY_ID, name: str = "帳號") -> MagicMock:
    """為 API 層測試建立 Category mock。"""
    c = MagicMock()
    c.id = cat_id
    c.agent_id = AGENT_ID
    c.name = name
    c.parent_id = None
    return c


class TestTriggerCategorySync:
    """POST /api/v1/agents/{agent_id}/categories/{category_id}/sync"""

    URL = f"/api/v1/agents/{AGENT_ID}/categories/{CATEGORY_ID}/sync"

    def _superadmin_db_se(self, agent: MagicMock, category: MagicMock | None):
        """Superadmin 路徑：idx 0=Agent, idx 1=Category（無 UAR query）。"""
        counter = [0]

        def se(*args):
            q = MagicMock()
            idx = counter[0]
            counter[0] += 1
            if idx == 0:
                q.filter.return_value.first.return_value = agent
            else:
                q.filter.return_value.first.return_value = category
            return q

        return se

    def test_superadmin_returns_202(
        self, client_superadmin, mock_db, agent_factory
    ) -> None:
        agent = agent_factory()
        cat = _make_cat_for_api()
        mock_db.query.side_effect = self._superadmin_db_se(agent, cat)
        mock_db.refresh.return_value = None

        with patch("tasks.run_category_sync") as mock_celery:
            mock_celery.delay.return_value.id = "cat-task-id"
            resp = client_superadmin.post(self.URL)

        assert resp.status_code == 202
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["status"] == "pending"
        assert data["data"]["task_id"] == "cat-task-id"
        assert "sync_log_id" in data["data"]

    def test_reviewer_returns_202(
        self, client_reviewer, mock_db, agent_factory
    ) -> None:
        agent = agent_factory()
        cat = _make_cat_for_api()
        mock_db.query.side_effect = build_agent_access_query_se(
            agent=agent, uar_role="reviewer", extra_results=[cat]
        )
        mock_db.refresh.return_value = None

        with patch("tasks.run_category_sync") as mock_celery:
            mock_celery.delay.return_value.id = "rev-task-id"
            resp = client_reviewer.post(self.URL)

        assert resp.status_code == 202

    def test_editor_returns_403(
        self, client_editor, mock_db, agent_factory
    ) -> None:
        agent = agent_factory()
        mock_db.query.side_effect = build_agent_access_query_se(
            agent=agent, uar_role="editor"
        )
        resp = client_editor.post(self.URL)
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "FORBIDDEN"

    def test_agent_not_found_returns_404(
        self, client_superadmin, mock_db
    ) -> None:
        mock_db.query.side_effect = self._superadmin_db_se(None, None)
        resp = client_superadmin.post(self.URL)
        assert resp.status_code == 404

    def test_category_not_found_returns_404(
        self, client_superadmin, mock_db, agent_factory
    ) -> None:
        agent = agent_factory()
        mock_db.query.side_effect = self._superadmin_db_se(agent, None)
        mock_db.refresh.return_value = None

        resp = client_superadmin.post(self.URL)
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "NOT_FOUND"

    def test_celery_unavailable_still_returns_202(
        self, client_superadmin, mock_db, agent_factory
    ) -> None:
        agent = agent_factory()
        cat = _make_cat_for_api()
        mock_db.query.side_effect = self._superadmin_db_se(agent, cat)
        mock_db.refresh.return_value = None

        with patch("tasks.run_category_sync") as mock_celery:
            mock_celery.delay.side_effect = ConnectionError("broker down")
            resp = client_superadmin.post(self.URL)

        assert resp.status_code == 202
        assert resp.json()["data"]["task_id"] is None
