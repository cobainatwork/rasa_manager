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

        assert result == existing.id
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
            patch("api.routes.import_export._resolve_category_path", return_value=uuid.uuid4()),
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
            patch("api.routes.import_export._resolve_category_path", return_value=uuid.uuid4()),
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
            patch("api.routes.import_export._resolve_category_path", return_value=uuid.uuid4()),
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
