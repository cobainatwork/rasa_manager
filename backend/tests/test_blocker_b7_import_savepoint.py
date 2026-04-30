"""
Regression test for B7：Excel 匯入採 SAVEPOINT 隔離單筆失敗。

修正前：迴圈內任一筆失敗呼叫 db.rollback() 會把先前已成功 flush 的全部一併
回滾，破壞「第 3 筆失敗、其他 4 筆成功」這類期望語意。

修正後：每筆改以 db.begin_nested() 包裹，單筆失敗只 rollback 該 SAVEPOINT。
"""
from __future__ import annotations

import io
import uuid
from unittest.mock import MagicMock, patch

import openpyxl
from fastapi.testclient import TestClient

from tests.conftest import AGENT_ID


def _make_xlsx(rows: list[list[object]]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["question", "answer", "category_path", "tags"])  # type: ignore[union-attr]
    for row in rows:
        ws.append(row)  # type: ignore[union-attr]
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


class TestImportSavepointIsolation:
    def test_third_row_failure_does_not_rollback_others(
        self, client_superadmin: TestClient, mock_db: MagicMock
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
        # begin_nested 必須回傳一個 context manager（SAVEPOINT 模擬）
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
            # I2：簽章改為 (id, created)
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
        assert data["errors"][0]["row"] == 4  # row 含標題列偏移：第 3 筆資料即 row=4

        # 確認 begin_nested 被呼叫 5 次（每筆一個 SAVEPOINT）
        assert mock_db.begin_nested.call_count == 5
        # 確認沒有呼叫 db.rollback()（不再使用整批 rollback）
        # 注意：SQLAlchemy 內部 begin_nested context manager exit 可能呼叫 db.rollback，
        # 但我們 mock 的 nested_cm 不會。本路由層面也不應再直接呼叫 rollback。
        mock_db.rollback.assert_not_called()
