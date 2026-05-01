"""
Excel 匯入/匯出測試：欄位映射、無效資料容錯、重複檢測、category_path 自動建立。
"""
from __future__ import annotations

import io
import uuid
from unittest.mock import MagicMock, patch

import openpyxl
import pytest

from tests.conftest import AGENT_ID


# ── 輔助：在記憶體建立測試用 xlsx ─────────────────────────────────────────────

def _make_xlsx(rows: list[list[object]], headers: list[str] | None = None) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    if headers is None:
        headers = ["question", "answer", "category_path", "tags"]
    ws.append(headers)  # type: ignore[union-attr]
    for row in rows:
        ws.append(row)  # type: ignore[union-attr]
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


# ── category_path 解析（單元測試）────────────────────────────────────────────

class TestResolveCategoryPath:
    def test_new_single_level_category_created(self) -> None:
        from api.routes.import_export import _resolve_category_path

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        db.flush = MagicMock()
        db.add = MagicMock()

        with patch("api.routes.import_export.Category") as MockCat:
            instance = MagicMock()
            instance.id = uuid.uuid4()
            MockCat.return_value = instance
            _resolve_category_path(db, AGENT_ID, "常見問題")

        db.add.assert_called_once()
        db.flush.assert_called_once()

    def test_existing_category_reused(self) -> None:
        from api.routes.import_export import _resolve_category_path

        existing = MagicMock()
        existing.id = uuid.UUID("00000000-0000-0000-0000-000000000020")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = existing
        db.add = MagicMock()

        result = _resolve_category_path(db, AGENT_ID, "既有分類")

        # I2：簽章改為 (id, created)
        assert result == (existing.id, False)
        db.add.assert_not_called()

    def test_empty_path_raises_value_error(self) -> None:
        from api.routes.import_export import _resolve_category_path

        db = MagicMock()
        with pytest.raises(ValueError, match="不可為空"):
            _resolve_category_path(db, AGENT_ID, "")

    def test_slash_only_path_raises_value_error(self) -> None:
        from api.routes.import_export import _resolve_category_path

        db = MagicMock()
        with pytest.raises(ValueError, match="不可為空"):
            _resolve_category_path(db, AGENT_ID, "///")


# ── 匯入端點（整合測試）──────────────────────────────────────────────────────

class TestImportEndpoint:
    """
    使用 patch 將 require_agent_access bypass，
    專注測試 Excel 解析與匯入業務邏輯。
    """

    def _setup_db(self, mock_db: MagicMock) -> None:
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.count.return_value = 0
        mock_db.flush = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.rollback = MagicMock()

    def test_valid_xlsx_imports_successfully(
        self, client_superadmin: object, mock_db: MagicMock
    ) -> None:
        self._setup_db(mock_db)
        xlsx = _make_xlsx([["問題一", "答案一", "分類A", "tag1,tag2"]])

        with (
            patch("api.routes.import_export.require_agent_access", return_value=(MagicMock(), None)),
            patch("api.routes.import_export._resolve_category_path", return_value=(uuid.uuid4(), False)),
        ):
            resp = client_superadmin.post(  # type: ignore[attr-defined]
                f"/api/v1/agents/{AGENT_ID}/faqs/import",
                files={"file": ("test.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["imported"] == 1
        assert data["skipped"] == 0
        assert data["errors"] == []

    def test_wrong_file_type_rejected(
        self, client_superadmin: object, mock_db: MagicMock
    ) -> None:
        with patch("api.routes.import_export.require_agent_access", return_value=(MagicMock(), None)):
            resp = client_superadmin.post(  # type: ignore[attr-defined]
                f"/api/v1/agents/{AGENT_ID}/faqs/import",
                files={"file": ("test.csv", b"q,a,c\n1,2,3", "text/csv")},
            )
        assert resp.status_code == 400
        assert "xlsx" in resp.json()["detail"].lower()

    def test_missing_required_column_rejected(
        self, client_superadmin: object, mock_db: MagicMock
    ) -> None:
        xlsx = _make_xlsx([["Q", "A"]], headers=["question", "answer"])

        with patch("api.routes.import_export.require_agent_access", return_value=(MagicMock(), None)):
            resp = client_superadmin.post(  # type: ignore[attr-defined]
                f"/api/v1/agents/{AGENT_ID}/faqs/import",
                files={"file": ("test.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            )
        assert resp.status_code == 400
        assert "category_path" in resp.json()["detail"]

    def test_duplicate_question_skipped(
        self, client_superadmin: object, mock_db: MagicMock
    ) -> None:
        # "問題一" 已存在
        mock_db.query.return_value.filter.return_value.all.return_value = [("問題一",)]
        mock_db.query.return_value.filter.return_value.count.return_value = 0
        mock_db.flush = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.rollback = MagicMock()

        xlsx = _make_xlsx([["問題一", "答案一", "分類A", ""]])

        with (
            patch("api.routes.import_export.require_agent_access", return_value=(MagicMock(), None)),
            patch("api.routes.import_export._resolve_category_path", return_value=(uuid.uuid4(), False)),
        ):
            resp = client_superadmin.post(  # type: ignore[attr-defined]
                f"/api/v1/agents/{AGENT_ID}/faqs/import",
                files={"file": ("test.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["skipped"] == 1
        assert data["imported"] == 0

    def test_empty_rows_skipped_gracefully(
        self, client_superadmin: object, mock_db: MagicMock
    ) -> None:
        self._setup_db(mock_db)
        xlsx = _make_xlsx([
            ["問題一", "答案一", "分類A", ""],
            ["", "", "", ""],       # 完全空白列
            ["問題二", "答案二", "分類B", ""],
        ])

        with (
            patch("api.routes.import_export.require_agent_access", return_value=(MagicMock(), None)),
            patch("api.routes.import_export._resolve_category_path", return_value=(uuid.uuid4(), False)),
        ):
            resp = client_superadmin.post(  # type: ignore[attr-defined]
                f"/api/v1/agents/{AGENT_ID}/faqs/import",
                files={"file": ("test.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            )

        assert resp.status_code == 200
        assert resp.json()["data"]["imported"] == 2


# ── 匯出端點（整合測試）──────────────────────────────────────────────────────

class TestExportEndpoint:
    def test_export_returns_xlsx(
        self, client_superadmin: object, mock_db: MagicMock
    ) -> None:
        faq = MagicMock()
        faq.id = uuid.uuid4()
        faq.status = "approved"
        faq.category_id = uuid.uuid4()
        faq.tags = ["t1"]
        faq.question = "Q"
        faq.answer = "A"
        faq.version = 1
        faq.created_at = None
        faq.updated_at = None

        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [faq]
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        with (
            patch("api.routes.import_export.require_agent_access", return_value=(MagicMock(), None)),
            patch("api.routes.import_export._build_category_path", return_value="分類A"),
        ):
            resp = client_superadmin.get(  # type: ignore[attr-defined]
                f"/api/v1/agents/{AGENT_ID}/faqs/export"
            )

        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers.get("content-type", "")
        assert "faq_export.xlsx" in resp.headers.get("content-disposition", "")

    def test_export_empty_agent_returns_header_only(
        self, client_superadmin: object, mock_db: MagicMock
    ) -> None:
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        with patch("api.routes.import_export.require_agent_access", return_value=(MagicMock(), None)):
            resp = client_superadmin.get(  # type: ignore[attr-defined]
                f"/api/v1/agents/{AGENT_ID}/faqs/export"
            )

        assert resp.status_code == 200
        wb = openpyxl.load_workbook(io.BytesIO(resp.content))
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))  # type: ignore[union-attr]
        assert len(rows) == 1  # 僅標題行


# ── Regression: B7 (import per-row failure must use SAVEPOINT) ───────────────

class TestImportSavepointRegression:
    """Regression: B7 (import per-row failure must use SAVEPOINT, not full rollback)."""

    def test_third_row_failure_does_not_rollback_others(
        self, client_superadmin, mock_db: MagicMock
    ) -> None:
        """
        匯入 5 筆，第 3 筆 _resolve_category_path 拋例外。
        預期：success=4、failed=1、其餘 4 筆不受牽連。
        """
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.count.return_value = 0
        mock_db.flush = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        nested_cm = MagicMock()
        nested_cm.__enter__ = MagicMock(return_value=nested_cm)
        nested_cm.__exit__ = MagicMock(return_value=False)
        mock_db.begin_nested = MagicMock(return_value=nested_cm)

        xlsx = _make_xlsx([
            ["Q1", "A1", "分類A", ""],
            ["Q2", "A2", "分類A", ""],
            ["Q3", "A3", "分類BAD", ""],
            ["Q4", "A4", "分類A", ""],
            ["Q5", "A5", "分類A", ""],
        ])

        call_count = [0]

        def fake_resolve(db: object, agent_id: object, path: str) -> object:
            call_count[0] += 1
            if call_count[0] == 3:
                raise RuntimeError("simulated category resolve failure")
            return uuid.uuid4(), False

        with (
            patch(
                "api.routes.import_export.require_agent_access",
                return_value=(MagicMock(), None),
            ),
            patch(
                "api.routes.import_export._resolve_category_path",
                side_effect=fake_resolve,
            ),
        ):
            resp = client_superadmin.post(
                f"/api/v1/agents/{AGENT_ID}/faqs/import",
                files={
                    "file": (
                        "test.xlsx",
                        xlsx,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["imported"] == 4, f"成功筆數應為 4，實際 {data['imported']}"
        assert len(data["errors"]) == 1
        assert data["errors"][0]["row"] == 4

        assert mock_db.begin_nested.call_count == 5
        mock_db.rollback.assert_not_called()


# ── Regression: I2 (_resolve_category_path must not call count() in loop) ────

class TestResolveCategoryPathNoCountRegression:
    """Regression: I2 (import _resolve_category_path 移除迴圈內 count())."""

    def test_signature_returns_tuple_with_created_flag(self) -> None:
        from api.routes.import_export import _resolve_category_path

        existing = MagicMock()
        existing.id = uuid.uuid4()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = existing

        result = _resolve_category_path(db, AGENT_ID, "已存在")
        assert result == (existing.id, False)

    def test_created_flag_true_when_new(self) -> None:
        from api.routes.import_export import _resolve_category_path

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with patch("api.routes.import_export.Category") as MockCat:
            inst = MagicMock()
            inst.id = uuid.uuid4()
            MockCat.return_value = inst
            result = _resolve_category_path(db, AGENT_ID, "新分類")
        assert result == (inst.id, True)

    def test_no_count_calls_during_import(
        self, client_superadmin, mock_db: MagicMock
    ) -> None:
        """匯入 3 筆相同 category_path 的 FAQ，不應出現 count() 呼叫。"""
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.flush = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.rollback = MagicMock()

        count_calls = [0]

        def count_spy() -> int:
            count_calls[0] += 1
            return 0

        mock_db.query.return_value.filter.return_value.count.side_effect = count_spy

        xlsx = _make_xlsx([
            ["問題一", "答案一", "分類A", ""],
            ["問題二", "答案二", "分類A", ""],
            ["問題三", "答案三", "分類A", ""],
        ])

        with (
            patch(
                "api.routes.import_export.require_agent_access",
                return_value=(MagicMock(), None),
            ),
            patch(
                "api.routes.import_export._resolve_category_path",
                return_value=(uuid.uuid4(), False),
            ),
        ):
            resp = client_superadmin.post(
                f"/api/v1/agents/{AGENT_ID}/faqs/import",
                files={
                    "file": (
                        "t.xlsx",
                        xlsx,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )

        assert resp.status_code == 200
        assert count_calls[0] <= 1


# ── Regression: I6 (export must load categories table once) ─────────────────

class TestExportCategoriesLoadedOnceRegression:
    """Regression: I6 (匯出時 categories 表一次性載入)."""

    def test_categories_table_queried_once(
        self, client_superadmin, mock_db: MagicMock
    ) -> None:
        from api.database.models import Category, KnowledgeItem

        items = []
        for _ in range(5):
            it = MagicMock()
            it.id = uuid.uuid4()
            it.status = "approved"
            it.category_id = uuid.uuid4()
            it.tags = []
            it.question = "Q"
            it.answer = "A"
            it.version = 1
            it.created_at = None
            it.updated_at = None
            items.append(it)

        category_query_count = [0]

        def query_side_effect(*args):
            q = MagicMock()
            if args and args[0] is KnowledgeItem:
                q.filter.return_value.order_by.return_value.all.return_value = items
                return q
            if args and args[0] is Category:
                category_query_count[0] += 1
                q.filter.return_value.all.return_value = []
                return q
            return q

        mock_db.query.side_effect = query_side_effect
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        with patch("api.routes.import_export.require_agent_access", return_value=(MagicMock(), None)):
            resp = client_superadmin.get(
                f"/api/v1/agents/{AGENT_ID}/faqs/export"
            )

        assert resp.status_code == 200
        assert category_query_count[0] == 1
