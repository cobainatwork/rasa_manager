# 分類獨立匯入/匯出 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓每個分類節點可在下拉選單中觸發獨立的 Excel 匯出（含該分類及所有子分類的 FAQ）與 Excel 匯入（只需 question/answer 兩欄，分類自動設為所選節點；匯入提供「新增匯入」與「覆蓋匯入」兩種模式）。

**Architecture:** 後端在現有 `import_export.py` 新增兩個 REST endpoint；Import endpoint 以 `mode` query param 控制覆蓋或新增模式；前端在 `CategoryTreeNode` DropdownMenu 以 `DropdownMenuSub` 提供兩個匯入子選項，透過 `pendingImportMode` ref 傳遞選擇的模式，結果以 sonner toast 顯示。

**Tech Stack:** FastAPI, openpyxl, SQLAlchemy, React, TypeScript, Lucide icons, Sonner toast

---

## 檔案異動清單

| 操作 | 路徑 | 說明 |
|------|------|------|
| Modify | `backend/api/routes/import_export.py` | 新增 `_collect_category_ids` helper + 2 endpoints；import 加 `Literal`、`Query` |
| Modify | `backend/tests/test_import_export.py` | 新增 `TestCollectCategoryIds` + `TestExportCategoryEndpoint` + `TestImportCategoryEndpoint` |
| Modify | `frontend/src/api/endpoints/categories.ts` | 新增 `CategoryImportResult` 型別 + 2 API 函數（importCategoryFaqs 含 mode 參數） |
| Modify | `frontend/src/features/knowledge/useCategoryTree.ts` | 新增 `exportCategory` / `importCategory` handler + 更新介面（importCategory 含 mode） |
| Modify | `frontend/src/features/knowledge/CategoryTreeNode.tsx` | 新增 2 props + 隱藏 file input + DropdownMenuSub 兩種匯入模式 |
| Modify | `frontend/src/features/knowledge/CategoryTree.tsx` | 解構並傳遞 `exportCategory` / `importCategory` |

---

## Task 1：後端 — `_collect_category_ids` 輔助函式

**Files:**
- Modify: `backend/tests/test_import_export.py`（在檔案尾端新增）
- Modify: `backend/api/routes/import_export.py`（在 `_build_category_path` 函式後新增）

---

- [ ] **Step 1：撰寫 failing test**

在 `backend/tests/test_import_export.py` 尾端加入：

```python
# ── _collect_category_ids 單元測試 ────────────────────────────────────────────

class TestCollectCategoryIds:
    def test_collects_self_when_no_children(self) -> None:
        from api.routes.import_export import _collect_category_ids

        cat_id = uuid.uuid4()
        cat = MagicMock()
        cat.id = cat_id
        cat.parent_id = None

        result = _collect_category_ids(cat_id, {cat_id: cat})
        assert result == {cat_id}

    def test_collects_children_recursively(self) -> None:
        from api.routes.import_export import _collect_category_ids

        root_id = uuid.uuid4()
        child_id = uuid.uuid4()
        grandchild_id = uuid.uuid4()

        root = MagicMock(); root.id = root_id; root.parent_id = None
        child = MagicMock(); child.id = child_id; child.parent_id = root_id
        grandchild = MagicMock(); grandchild.id = grandchild_id; grandchild.parent_id = child_id

        cat_map = {root_id: root, child_id: child, grandchild_id: grandchild}

        result = _collect_category_ids(root_id, cat_map)
        assert result == {root_id, child_id, grandchild_id}

    def test_does_not_collect_sibling_categories(self) -> None:
        from api.routes.import_export import _collect_category_ids

        root_id = uuid.uuid4()
        sibling_id = uuid.uuid4()

        root = MagicMock(); root.id = root_id; root.parent_id = None
        sibling = MagicMock(); sibling.id = sibling_id; sibling.parent_id = None

        result = _collect_category_ids(root_id, {root_id: root, sibling_id: sibling})
        assert result == {root_id}
```

- [ ] **Step 2：確認測試失敗**

```bash
cd D:\mini_test\backend
python -m pytest tests/test_import_export.py::TestCollectCategoryIds -v
```

預期：`ImportError: cannot import name '_collect_category_ids'`

- [ ] **Step 3：實作 `_collect_category_ids`**

在 `backend/api/routes/import_export.py` 第 98 行之後（`_build_category_path` 函式結束後），插入：

```python
def _collect_category_ids(root_id: Any, cat_map: dict[Any, Category]) -> set[Any]:
    """
    從 root_id 出發，以迭代 DFS 收集所有子孫分類 ID（含自身）。
    使用預先載入的 cat_map 避免 N+1 查詢。
    """
    result: set[Any] = set()
    stack = [root_id]
    while stack:
        cid = stack.pop()
        if cid in result:
            continue
        result.add(cid)
        for cat in cat_map.values():
            if cat.parent_id == cid:
                stack.append(cat.id)
    return result
```

- [ ] **Step 4：確認測試通過**

```bash
python -m pytest tests/test_import_export.py::TestCollectCategoryIds -v
```

預期：3 passed

- [ ] **Step 5：commit**

```bash
git add backend/api/routes/import_export.py backend/tests/test_import_export.py
git commit -m "feat: add _collect_category_ids helper for recursive category descent"
```

---

## Task 2：後端 — Export category endpoint

**Files:**
- Modify: `backend/tests/test_import_export.py`（在 `TestCollectCategoryIds` 後新增）
- Modify: `backend/api/routes/import_export.py`（在現有 `export_faqs` 函式後新增）

---

- [ ] **Step 1：撰寫 failing tests**

在 `backend/tests/test_import_export.py` 尾端加入：

```python
# ── 分類匯出端點 ──────────────────────────────────────────────────────────────

class TestExportCategoryEndpoint:
    def _make_db(
        self,
        mock_db: MagicMock,
        cat_id: uuid.UUID,
        faqs: list | None = None,
    ) -> MagicMock:
        """設定 mock_db query 序列（require_agent_access 已被 patch，不含前 2 次查詢）。"""
        faqs = faqs or []
        mock_cat = MagicMock()
        mock_cat.id = cat_id
        mock_cat.parent_id = None
        mock_cat.name = "測試分類"

        counter = [0]

        def se(*_args, **_kwargs):
            q = MagicMock()
            idx = counter[0]
            counter[0] += 1
            if idx == 0:  # Category.filter().first() — 驗證分類存在
                q.filter.return_value.first.return_value = mock_cat
            elif idx == 1:  # Category.filter().all() — cat_map
                q.filter.return_value.all.return_value = [mock_cat]
            elif idx == 2:  # KnowledgeItem.filter().filter().order_by().all()
                (q.filter.return_value
                  .filter.return_value
                  .order_by.return_value
                  .all.return_value) = faqs
            return q

        mock_db.query.side_effect = se
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        return mock_cat

    def test_returns_xlsx_stream(
        self, client_superadmin: object, mock_db: MagicMock
    ) -> None:
        cat_id = uuid.uuid4()
        self._make_db(mock_db, cat_id)

        with patch("api.routes.import_export.require_agent_access"):
            resp = client_superadmin.get(  # type: ignore[attr-defined]
                f"/api/v1/agents/{AGENT_ID}/categories/{cat_id}/export"
            )

        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers["content-type"]

    def test_xlsx_contains_faq_rows(
        self, client_superadmin: object, mock_db: MagicMock
    ) -> None:
        cat_id = uuid.uuid4()
        mock_faq = MagicMock()
        mock_faq.question = "問題一"
        mock_faq.answer = "答案一"
        mock_faq.tags = ["t1"]
        mock_faq.status = "approved"
        mock_faq.version = 1
        mock_faq.created_at = None
        self._make_db(mock_db, cat_id, faqs=[mock_faq])

        with patch("api.routes.import_export.require_agent_access"):
            resp = client_superadmin.get(  # type: ignore[attr-defined]
                f"/api/v1/agents/{AGENT_ID}/categories/{cat_id}/export"
            )

        assert resp.status_code == 200
        wb = openpyxl.load_workbook(io.BytesIO(resp.content))
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))  # type: ignore[union-attr]
        assert rows[0][0] == "question"  # 標題列
        assert rows[1][0] == "問題一"    # 資料列

    def test_invalid_category_returns_404(
        self, client_superadmin: object, mock_db: MagicMock
    ) -> None:
        cat_id = uuid.uuid4()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        with patch("api.routes.import_export.require_agent_access"):
            resp = client_superadmin.get(  # type: ignore[attr-defined]
                f"/api/v1/agents/{AGENT_ID}/categories/{cat_id}/export"
            )

        assert resp.status_code == 404
```

- [ ] **Step 2：確認測試失敗**

```bash
python -m pytest tests/test_import_export.py::TestExportCategoryEndpoint -v
```

預期：404 因 endpoint 尚未存在

- [ ] **Step 3：實作 `export_category_faqs` endpoint**

在 `backend/api/routes/import_export.py` 現有 `export_faqs` 函式（第 313 行）之後新增：

```python
# ── 分類匯出端點 ──────────────────────────────────────────────────────────────

@router.get("/api/v1/agents/{agent_id}/categories/{category_id}/export")
def export_category_faqs(
    agent_id: uuid.UUID,
    category_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    require_agent_access(agent_id, current_user, db)

    category = (
        db.query(Category)
        .filter(Category.id == category_id, Category.agent_id == agent_id)
        .first()
    )
    if category is None:
        raise HTTPException(status_code=404, detail="找不到分類")

    all_cats = db.query(Category).filter(Category.agent_id == agent_id).all()
    cat_map: dict[Any, Category] = {c.id: c for c in all_cats}

    cat_ids = _collect_category_ids(category_id, cat_map)

    items = (
        db.query(KnowledgeItem)
        .filter(KnowledgeItem.agent_id == agent_id)
        .filter(KnowledgeItem.category_id.in_(cat_ids))
        .order_by(KnowledgeItem.created_at)
        .all()
    )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "FAQs"  # type: ignore[union-attr]
    ws.append(["question", "answer", "tags", "status", "version"])  # type: ignore[union-attr]

    for item in items:
        tags_str = ",".join(item.tags) if item.tags else ""
        ws.append([  # type: ignore[union-attr]
            str(item.question),
            str(item.answer),
            tags_str,
            str(item.status),
            item.version if item.version is not None else 1,
        ])

    db.add(AuditLog(
        id=uuid.uuid4(),
        agent_id=agent_id,
        item_id=None,
        action="export_category",
        performed_by=current_user.id,
        diff={"category_id": str(category_id), "count": len(items)},
    ))
    db.commit()

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=category_{category_id}_export.xlsx"
        },
    )
```

- [ ] **Step 4：確認測試通過**

```bash
python -m pytest tests/test_import_export.py::TestExportCategoryEndpoint -v
```

預期：3 passed

- [ ] **Step 5：commit**

```bash
git add backend/api/routes/import_export.py backend/tests/test_import_export.py
git commit -m "feat: add GET /categories/{id}/export endpoint"
```

---

## Task 3：後端 — Import category endpoint（append / replace 兩模式）

**Files:**
- Modify: `backend/tests/test_import_export.py`（在 `TestExportCategoryEndpoint` 後新增）
- Modify: `backend/api/routes/import_export.py`（在 `export_category_faqs` 後新增；同時更新頂部 import）

---

- [ ] **Step 1：更新 `import_export.py` 頂部 import**

將第 18 行的 typing import 從：
```python
from typing import Any, Optional
```
改為：
```python
from typing import Any, Literal, Optional
```

將第 24 行的 fastapi import 從：
```python
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
```
改為：
```python
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
```

- [ ] **Step 2：撰寫 failing tests**

在 `backend/tests/test_import_export.py` 尾端加入：

```python
# ── 分類匯入端點 ──────────────────────────────────────────────────────────────

class TestImportCategoryEndpoint:
    def _make_db(self, mock_db: MagicMock, cat_id: uuid.UUID) -> None:
        """append 模式下的 mock_db：query 0 = 分類驗證，query 1 = existing_questions。"""
        mock_cat = MagicMock()
        mock_cat.id = cat_id
        mock_cat.agent_id = AGENT_ID

        counter = [0]

        def se(*_args, **_kwargs):
            q = MagicMock()
            idx = counter[0]
            counter[0] += 1
            if idx == 0:  # Category.filter().first()
                q.filter.return_value.first.return_value = mock_cat
            elif idx == 1:  # KnowledgeItem.question.filter().all()
                q.filter.return_value.all.return_value = []
            return q

        mock_db.query.side_effect = se
        mock_db.flush = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.begin_nested.return_value.__enter__ = MagicMock(return_value=None)
        mock_db.begin_nested.return_value.__exit__ = MagicMock(return_value=False)

    def test_only_question_answer_required(
        self, client_superadmin: object, mock_db: MagicMock
    ) -> None:
        """category_path 欄位不應是必填欄位。"""
        cat_id = uuid.uuid4()
        self._make_db(mock_db, cat_id)
        xlsx = _make_xlsx(
            [["問題一", "答案一"]],
            headers=["question", "answer"],
        )

        with patch("api.routes.import_export.require_agent_access"):
            resp = client_superadmin.post(  # type: ignore[attr-defined]
                f"/api/v1/agents/{AGENT_ID}/categories/{cat_id}/import",
                files={"file": ("t.xlsx", xlsx,
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["imported"] == 1
        assert data["skipped"] == 0
        assert data["errors"] == []

    def test_missing_answer_column_rejected(
        self, client_superadmin: object, mock_db: MagicMock
    ) -> None:
        cat_id = uuid.uuid4()
        self._make_db(mock_db, cat_id)
        xlsx = _make_xlsx([["Q"]], headers=["question"])

        with patch("api.routes.import_export.require_agent_access"):
            resp = client_superadmin.post(  # type: ignore[attr-defined]
                f"/api/v1/agents/{AGENT_ID}/categories/{cat_id}/import",
                files={"file": ("t.xlsx", xlsx,
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            )

        assert resp.status_code == 400
        assert "answer" in resp.json()["detail"].lower()

    def test_duplicate_question_skipped(
        self, client_superadmin: object, mock_db: MagicMock
    ) -> None:
        cat_id = uuid.uuid4()
        mock_cat = MagicMock(); mock_cat.id = cat_id

        counter = [0]
        def se(*_args, **_kwargs):
            q = MagicMock()
            idx = counter[0]; counter[0] += 1
            if idx == 0:
                q.filter.return_value.first.return_value = mock_cat
            elif idx == 1:
                q.filter.return_value.all.return_value = [("問題一",)]
            return q
        mock_db.query.side_effect = se
        mock_db.flush = MagicMock(); mock_db.add = MagicMock(); mock_db.commit = MagicMock()
        mock_db.begin_nested.return_value.__enter__ = MagicMock(return_value=None)
        mock_db.begin_nested.return_value.__exit__ = MagicMock(return_value=False)

        xlsx = _make_xlsx([["問題一", "答案一"]], headers=["question", "answer"])
        with patch("api.routes.import_export.require_agent_access"):
            resp = client_superadmin.post(  # type: ignore[attr-defined]
                f"/api/v1/agents/{AGENT_ID}/categories/{cat_id}/import",
                files={"file": ("t.xlsx", xlsx,
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["imported"] == 0
        assert data["skipped"] == 1

    def test_replace_mode_calls_delete_on_existing_items(
        self, client_superadmin: object, mock_db: MagicMock
    ) -> None:
        """mode=replace → 應對現有 FAQ 呼叫 db.delete()。"""
        cat_id = uuid.uuid4()
        mock_cat = MagicMock(); mock_cat.id = cat_id; mock_cat.parent_id = None

        existing_item = MagicMock()

        counter = [0]
        def se(*_args, **_kwargs):
            q = MagicMock()
            idx = counter[0]; counter[0] += 1
            if idx == 0:   # Category.filter().first() — validate category
                q.filter.return_value.first.return_value = mock_cat
            elif idx == 1:  # Category.filter().all() — cat_map for _collect_category_ids
                q.filter.return_value.all.return_value = [mock_cat]
            elif idx == 2:  # KnowledgeItem.filter().filter().all() — items_to_del
                q.filter.return_value.filter.return_value.all.return_value = [existing_item]
            elif idx == 3:  # KnowledgeItem.question.filter().all() — existing_questions
                q.filter.return_value.all.return_value = []
            return q
        mock_db.query.side_effect = se
        mock_db.flush = MagicMock(); mock_db.add = MagicMock()
        mock_db.commit = MagicMock(); mock_db.delete = MagicMock()
        mock_db.begin_nested.return_value.__enter__ = MagicMock(return_value=None)
        mock_db.begin_nested.return_value.__exit__ = MagicMock(return_value=False)

        xlsx = _make_xlsx([["新問題", "新答案"]], headers=["question", "answer"])
        with patch("api.routes.import_export.require_agent_access"):
            resp = client_superadmin.post(  # type: ignore[attr-defined]
                f"/api/v1/agents/{AGENT_ID}/categories/{cat_id}/import?mode=replace",
                files={"file": ("t.xlsx", xlsx,
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            )

        assert resp.status_code == 200
        mock_db.delete.assert_called_once_with(existing_item)

    def test_append_mode_does_not_delete(
        self, client_superadmin: object, mock_db: MagicMock
    ) -> None:
        """mode=append（預設）→ 不應呼叫 db.delete()。"""
        cat_id = uuid.uuid4()
        self._make_db(mock_db, cat_id)
        mock_db.delete = MagicMock()

        xlsx = _make_xlsx([["問題A", "答案A"]], headers=["question", "answer"])
        with patch("api.routes.import_export.require_agent_access"):
            resp = client_superadmin.post(  # type: ignore[attr-defined]
                f"/api/v1/agents/{AGENT_ID}/categories/{cat_id}/import",
                files={"file": ("t.xlsx", xlsx,
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            )

        assert resp.status_code == 200
        mock_db.delete.assert_not_called()

    def test_invalid_category_returns_404(
        self, client_superadmin: object, mock_db: MagicMock
    ) -> None:
        cat_id = uuid.uuid4()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.add = MagicMock(); mock_db.commit = MagicMock()

        xlsx = _make_xlsx([["Q", "A"]], headers=["question", "answer"])
        with patch("api.routes.import_export.require_agent_access"):
            resp = client_superadmin.post(  # type: ignore[attr-defined]
                f"/api/v1/agents/{AGENT_ID}/categories/{cat_id}/import",
                files={"file": ("t.xlsx", xlsx,
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            )

        assert resp.status_code == 404
```

- [ ] **Step 3：確認測試失敗**

```bash
python -m pytest tests/test_import_export.py::TestImportCategoryEndpoint -v
```

預期：404 因 endpoint 尚未存在

- [ ] **Step 4：實作 `import_category_faqs` endpoint**

在 `backend/api/routes/import_export.py` `export_category_faqs` 函式之後新增：

```python
# ── 分類匯入端點 ──────────────────────────────────────────────────────────────

@router.post("/api/v1/agents/{agent_id}/categories/{category_id}/import")
def import_category_faqs(
    agent_id: uuid.UUID,
    category_id: uuid.UUID,
    mode: Literal["append", "replace"] = Query("append"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_agent_access(agent_id, current_user, db)

    # 驗證分類存在且屬於此 agent
    category = (
        db.query(Category)
        .filter(Category.id == category_id, Category.agent_id == agent_id)
        .first()
    )
    if category is None:
        raise HTTPException(status_code=404, detail="找不到分類")

    # replace 模式：先刪除該分類（含所有子分類）的全部 FAQ
    if mode == "replace":
        all_cats = db.query(Category).filter(Category.agent_id == agent_id).all()
        cat_map_del: dict[Any, Category] = {c.id: c for c in all_cats}
        del_cat_ids = _collect_category_ids(category_id, cat_map_del)
        items_to_del = (
            db.query(KnowledgeItem)
            .filter(
                KnowledgeItem.agent_id == agent_id,
                KnowledgeItem.category_id.in_(del_cat_ids),
            )
            .all()
        )
        deleted_count = len(items_to_del)
        for item in items_to_del:
            db.delete(item)
        db.flush()
        if deleted_count > 0:
            db.add(AuditLog(
                id=uuid.uuid4(),
                agent_id=agent_id,
                item_id=None,
                action="bulk_delete_category",
                performed_by=current_user.id,
                diff={"category_id": str(category_id), "deleted_count": deleted_count},
            ))

    # 檔案格式與大小驗證
    filename = file.filename or ""
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="僅接受 .xlsx 格式檔案")

    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="檔案大小超過 10 MB 上限")

    # 解析 Excel
    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
        if ws is None:
            raise ValueError("找不到工作表")
        all_rows = list(ws.iter_rows(values_only=True))
        wb.close()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"無法解析 Excel 檔案：{exc}") from exc

    if len(all_rows) < 2:
        raise HTTPException(status_code=400, detail="Excel 無資料列（需含標題行）")

    header = [str(c).strip().lower() if c is not None else "" for c in all_rows[0]]
    data_rows = all_rows[1:]

    if len(data_rows) > MAX_ROWS:
        raise HTTPException(status_code=400, detail=f"資料列數超過 {MAX_ROWS} 行上限")

    # 只需 question + answer（無 category_path）
    def require_col(name: str) -> int:
        if name not in header:
            raise HTTPException(status_code=400, detail=f"缺少必填欄位：{name}")
        return header.index(name)

    q_idx = require_col("question")
    a_idx = require_col("answer")
    tags_idx: Optional[int] = header.index("tags") if "tags" in header else None

    # replace 後 existing_questions 應已清空，flush 確保可見
    existing_questions: set[str] = {
        str(q)
        for (q,) in db.query(KnowledgeItem.question)
        .filter(KnowledgeItem.agent_id == agent_id)
        .all()
    }

    success = 0
    skipped = 0
    errors: list[dict[str, Any]] = []

    for row_num, row in enumerate(data_rows, start=2):
        def cell(idx: int) -> str:
            val = row[idx] if idx < len(row) else None  # type: ignore[index]
            return str(val).strip() if val is not None else ""

        question = cell(q_idx)
        answer = cell(a_idx)
        tags_raw = cell(tags_idx) if tags_idx is not None else ""

        # 空列跳過
        if not question and not answer:
            continue

        if not question or not answer:
            errors.append({"row": row_num, "reason": "question / answer 不可為空"})
            continue

        if question in existing_questions:
            skipped += 1
            continue

        tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []

        try:
            with db.begin_nested():
                item = KnowledgeItem(
                    id=uuid.uuid4(),
                    agent_id=agent_id,
                    category_id=category_id,
                    question=question,
                    answer=answer,
                    tags=tags_list,
                    status="draft",
                    version=1,
                    created_by=current_user.id,
                )
                db.add(item)
                db.flush()

                db.add(AuditLog(
                    id=uuid.uuid4(),
                    agent_id=agent_id,
                    item_id=item.id,
                    action="import_category",
                    performed_by=current_user.id,
                    diff={"question": question, "category_id": str(category_id)},
                ))

            existing_questions.add(question)
            success += 1

        except Exception as exc:
            errors.append({"row": row_num, "reason": str(exc)})

    db.commit()

    return {
        "success": True,
        "data": {
            "imported": success,
            "skipped": skipped,
            "errors": errors,
        },
    }
```

- [ ] **Step 5：執行所有 import/export 測試**

```bash
python -m pytest tests/test_import_export.py -v
```

預期：全部 passed（含舊有測試，基線維持 295+ passed）

- [ ] **Step 6：commit**

```bash
git add backend/api/routes/import_export.py backend/tests/test_import_export.py
git commit -m "feat: add POST /categories/{id}/import with append/replace mode"
```

---

## Task 4：前端 — API 函數與型別

**Files:**
- Modify: `frontend/src/api/endpoints/categories.ts`

---

- [ ] **Step 1：撰寫 failing test**

建立 `frontend/src/api/endpoints/__tests__/categories.import-export.test.ts`：

```typescript
import { describe, it, expect, vi } from 'vitest'
import { exportCategoryFaqs, importCategoryFaqs } from '../categories'
import { apiClient } from '../../client'

vi.mock('../../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

const AGENT_ID = 'agent-uuid'
const CAT_ID = 'cat-uuid'

describe('exportCategoryFaqs', () => {
  it('calls GET /categories/{id}/export with blob responseType', async () => {
    const mockBlob = new Blob(['test'])
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockBlob })

    const result = await exportCategoryFaqs(AGENT_ID, CAT_ID)

    expect(apiClient.get).toHaveBeenCalledWith(
      `/api/v1/agents/${AGENT_ID}/categories/${CAT_ID}/export`,
      { responseType: 'blob' }
    )
    expect(result).toBe(mockBlob)
  })
})

describe('importCategoryFaqs', () => {
  it('calls POST /categories/{id}/import with mode=append by default', async () => {
    const mockResult = { success: true, data: { imported: 1, skipped: 0, errors: [] } }
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockResult })

    const file = new File(['col'], 'test.xlsx')
    await importCategoryFaqs(AGENT_ID, CAT_ID, file)

    expect(apiClient.post).toHaveBeenCalledWith(
      `/api/v1/agents/${AGENT_ID}/categories/${CAT_ID}/import?mode=append`,
      expect.any(FormData)
    )
  })

  it('calls POST /categories/{id}/import with mode=replace when specified', async () => {
    const mockResult = { success: true, data: { imported: 2, skipped: 0, errors: [] } }
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockResult })

    const file = new File(['col'], 'test.xlsx')
    await importCategoryFaqs(AGENT_ID, CAT_ID, file, 'replace')

    expect(apiClient.post).toHaveBeenCalledWith(
      `/api/v1/agents/${AGENT_ID}/categories/${CAT_ID}/import?mode=replace`,
      expect.any(FormData)
    )
  })
})
```

- [ ] **Step 2：確認測試失敗**

```bash
cd D:\mini_test\frontend
npm test -- src/api/endpoints/__tests__/categories.import-export.test.ts
```

預期：`exportCategoryFaqs is not a function`

- [ ] **Step 3：實作 API 函數**

在 `frontend/src/api/endpoints/categories.ts` 尾端加入：

```typescript
// ── 分類匯入/匯出 ─────────────────────────────────────────────────────────────

export interface CategoryImportResult {
  imported: number
  skipped: number
  errors: Array<{ row: number; reason: string }>
}

export async function exportCategoryFaqs(
  agentId: string,
  categoryId: string
): Promise<Blob> {
  const res = await apiClient.get(
    `/api/v1/agents/${agentId}/categories/${categoryId}/export`,
    { responseType: 'blob' }
  )
  return res.data as Blob
}

export async function importCategoryFaqs(
  agentId: string,
  categoryId: string,
  file: File,
  mode: 'append' | 'replace' = 'append'
): Promise<CategoryImportResult> {
  const form = new FormData()
  form.append('file', file)
  return unwrap(
    apiClient.post(
      `/api/v1/agents/${agentId}/categories/${categoryId}/import?mode=${mode}`,
      form
    )
  )
}
```

- [ ] **Step 4：確認測試通過**

```bash
npm test -- src/api/endpoints/__tests__/categories.import-export.test.ts
```

預期：3 passed

- [ ] **Step 5：確認 TypeScript 型別無誤**

```bash
npx tsc --noEmit
```

預期：0 errors

- [ ] **Step 6：commit**

```bash
git add frontend/src/api/endpoints/categories.ts \
         frontend/src/api/endpoints/__tests__/categories.import-export.test.ts
git commit -m "feat: add exportCategoryFaqs/importCategoryFaqs API functions with mode param"
```

---

## Task 5：前端 — `useCategoryTree` Hook

**Files:**
- Modify: `frontend/src/features/knowledge/useCategoryTree.ts`

---

- [ ] **Step 1：更新 Hook**

將 `frontend/src/features/knowledge/useCategoryTree.ts` 全部內容替換為：

```typescript
import { useState, useEffect, useCallback } from 'react'
import * as api from '@/api/endpoints/categories'
import { extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'
import type { CategoryNode } from '@/api/types'

export interface UseCategoryTreeResult {
  tree: CategoryNode[]
  loading: boolean
  selectedId: string | null
  pendingRenameId: string | null
  select: (id: string | null) => void
  reload: () => void
  rename: (id: string, name: string) => Promise<void>
  addChild: (parentId: string | null) => Promise<void>
  remove: (id: string) => Promise<void>
  clearPendingRename: () => void
  exportCategory: (id: string) => Promise<void>
  importCategory: (id: string, file: File, mode: 'append' | 'replace') => Promise<void>
}

export function useCategoryTree(agentId: string | undefined): UseCategoryTreeResult {
  const [tree, setTree] = useState<CategoryNode[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [pendingRenameId, setPendingRenameId] = useState<string | null>(null)

  const reload = useCallback(() => {
    if (!agentId) return
    setLoading(true)
    api.listCategories(agentId)
      .then((nested) => setTree(nested))
      .catch((err) => toast.error(extractErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [agentId])

  useEffect(() => { reload() }, [reload])

  async function rename(id: string, name: string) {
    if (!agentId) return
    try {
      await api.updateCategory(agentId, id, { name })
      reload()
    } catch (err) { toast.error(extractErrorMessage(err)) }
  }

  async function addChild(parentId: string | null) {
    if (!agentId) return
    const suffix = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`
    const name = `新分類_${suffix}`
    try {
      const created = await api.createCategory(agentId, { name, parent_id: parentId })
      setPendingRenameId(created.id)
      reload()
    } catch (err) { toast.error(extractErrorMessage(err)) }
  }

  async function remove(id: string) {
    if (!agentId) return
    try {
      await api.deleteCategory(agentId, id)
      if (selectedId === id) setSelectedId(null)
      reload()
    } catch (err) { toast.error(extractErrorMessage(err)) }
  }

  function clearPendingRename() { setPendingRenameId(null) }

  async function exportCategory(id: string) {
    if (!agentId) return
    try {
      const blob = await api.exportCategoryFaqs(agentId, id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'category_export.xlsx'
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) { toast.error(extractErrorMessage(err)) }
  }

  async function importCategory(id: string, file: File, mode: 'append' | 'replace') {
    if (!agentId) return
    try {
      const result = await api.importCategoryFaqs(agentId, id, file, mode)
      const modeLabel = mode === 'replace' ? '覆蓋' : '新增'
      toast.success(`${modeLabel}匯入完成：新增 ${result.imported} 筆，跳過 ${result.skipped} 筆`)
      if (result.errors.length > 0) {
        const rows = result.errors.map((e) => e.row).join('、')
        toast.warning(`${result.errors.length} 列匯入失敗（第 ${rows} 列）`)
      }
      reload()
    } catch (err) { toast.error(extractErrorMessage(err)) }
  }

  return {
    tree, loading, selectedId, pendingRenameId,
    select: setSelectedId, reload, rename, addChild, remove,
    clearPendingRename, exportCategory, importCategory,
  }
}
```

- [ ] **Step 2：確認 TypeScript 型別無誤**

```bash
cd D:\mini_test\frontend
npx tsc --noEmit
```

預期：0 errors

- [ ] **Step 3：commit**

```bash
git add frontend/src/features/knowledge/useCategoryTree.ts
git commit -m "feat: add exportCategory/importCategory to useCategoryTree with mode support"
```

---

## Task 6：前端 — `CategoryTreeNode` UI + `CategoryTree` 接線

**Files:**
- Modify: `frontend/src/features/knowledge/CategoryTreeNode.tsx`
- Modify: `frontend/src/features/knowledge/CategoryTree.tsx`

---

- [ ] **Step 1：更新 `CategoryTreeNode.tsx`**

將 `frontend/src/features/knowledge/CategoryTreeNode.tsx` 全部內容替換為：

```tsx
import { useState, useRef, useEffect } from 'react'
import {
  ChevronRight, ChevronDown, MoreHorizontal,
  Pencil, Plus, Trash2, Download, Upload,
} from 'lucide-react'
import { Input } from '@/components/ui/input'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { cn } from '@/lib/utils'
import type { CategoryNode } from '@/api/types'

interface Props {
  node: CategoryNode
  depth: number
  selectedId: string | null
  pendingRenameId: string | null
  onSelect: (id: string) => void
  onRename: (id: string, name: string) => void
  onAddChild: (parentId: string) => void
  onRemove: (id: string) => void
  onClearPendingRename: () => void
  onExport: (id: string) => void
  onImport: (id: string, file: File, mode: 'append' | 'replace') => void
}

export function CategoryTreeNode({
  node,
  depth,
  selectedId,
  pendingRenameId,
  onSelect,
  onRename,
  onAddChild,
  onRemove,
  onClearPendingRename,
  onExport,
  onImport,
}: Props) {
  const [expanded, setExpanded] = useState(true)
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(node.name)
  const inputRef = useRef<HTMLInputElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  // 用 ref 而非 state 避免 React 非同步更新與 onChange 之間的競態
  const pendingImportMode = useRef<'append' | 'replace'>('append')

  const isSelected = selectedId === node.id
  const hasChildren = node.children.length > 0

  useEffect(() => {
    if (pendingRenameId === node.id) {
      setEditing(true)
      onClearPendingRename()
    }
  }, [pendingRenameId, node.id, onClearPendingRename])

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [editing])

  function commitRename() {
    setEditing(false)
    if (name.trim() && name !== node.name) onRename(node.id, name.trim())
    else setName(node.name)
  }

  return (
    <li>
      {/* 隱藏 file input：選擇檔案後以 pendingImportMode.current 呼叫 onImport */}
      <input
        type="file"
        ref={fileInputRef}
        accept=".xlsx"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) {
            onImport(node.id, file, pendingImportMode.current)
            e.target.value = ''
          }
        }}
      />

      <div
        className={cn(
          'group flex items-center gap-1 py-1 px-2 rounded cursor-pointer text-sm',
          isSelected
            ? 'bg-brand-50 text-brand-700 border-l-2 border-brand-500'
            : 'hover:bg-subtle'
        )}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
        onClick={() => onSelect(node.id)}
      >
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            if (hasChildren) setExpanded(!expanded)
          }}
          className="w-4 h-4 flex items-center justify-center shrink-0"
          aria-label={expanded ? '收合' : '展開'}
        >
          {hasChildren && (
            expanded
              ? <ChevronDown className="w-3 h-3" strokeWidth={1.5} />
              : <ChevronRight className="w-3 h-3" strokeWidth={1.5} />
          )}
        </button>

        {editing ? (
          <Input
            ref={inputRef}
            value={name}
            onChange={(e) => setName(e.target.value)}
            onBlur={commitRename}
            onKeyDown={(e) => {
              if (e.key === 'Enter') { e.preventDefault(); commitRename() }
              if (e.key === 'Escape') { setEditing(false); setName(node.name) }
            }}
            onClick={(e) => e.stopPropagation()}
            className="h-6 text-sm"
          />
        ) : (
          <span
            className="flex-1 truncate"
            onDoubleClick={(e) => { e.stopPropagation(); setEditing(true) }}
          >
            {node.name}
          </span>
        )}

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              onClick={(e) => e.stopPropagation()}
              className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-white"
              aria-label="更多操作"
            >
              <MoreHorizontal className="w-3.5 h-3.5" strokeWidth={1.5} />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => setEditing(true)}>
              <Pencil className="w-3.5 h-3.5 mr-2" strokeWidth={1.5} /> 重新命名
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onAddChild(node.id)}>
              <Plus className="w-3.5 h-3.5 mr-2" strokeWidth={1.5} /> 新增子分類
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => onExport(node.id)}>
              <Download className="w-3.5 h-3.5 mr-2" strokeWidth={1.5} /> 匯出 FAQ
            </DropdownMenuItem>
            <DropdownMenuSub>
              <DropdownMenuSubTrigger>
                <Upload className="w-3.5 h-3.5 mr-2" strokeWidth={1.5} /> 匯入 FAQ
              </DropdownMenuSubTrigger>
              <DropdownMenuSubContent>
                <DropdownMenuItem
                  onClick={() => {
                    pendingImportMode.current = 'append'
                    fileInputRef.current?.click()
                  }}
                >
                  新增匯入（保留現有資料）
                </DropdownMenuItem>
                <DropdownMenuItem
                  className="text-amber-600 focus:text-amber-600"
                  onClick={() => {
                    pendingImportMode.current = 'replace'
                    fileInputRef.current?.click()
                  }}
                >
                  覆蓋匯入（先刪除全部）
                </DropdownMenuItem>
              </DropdownMenuSubContent>
            </DropdownMenuSub>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => onRemove(node.id)} className="text-red-600">
              <Trash2 className="w-3.5 h-3.5 mr-2" strokeWidth={1.5} /> 刪除
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {hasChildren && expanded && (
        <ul>
          {node.children.map((child) => (
            <CategoryTreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              selectedId={selectedId}
              pendingRenameId={pendingRenameId}
              onSelect={onSelect}
              onRename={onRename}
              onAddChild={onAddChild}
              onRemove={onRemove}
              onClearPendingRename={onClearPendingRename}
              onExport={onExport}
              onImport={onImport}
            />
          ))}
        </ul>
      )}
    </li>
  )
}
```

- [ ] **Step 2：更新 `CategoryTree.tsx`**

將 `frontend/src/features/knowledge/CategoryTree.tsx` 全部內容替換為：

```tsx
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ScrollArea } from '@/components/ui/scroll-area'
import { CategoryTreeNode } from './CategoryTreeNode'
import type { UseCategoryTreeResult } from './useCategoryTree'

interface Props {
  result: UseCategoryTreeResult
}

export function CategoryTree({ result }: Props) {
  const {
    tree, loading, selectedId, pendingRenameId,
    select, rename, addChild, remove, clearPendingRename,
    exportCategory, importCategory,
  } = result

  return (
    <aside className="h-full bg-surface flex flex-col">
      <div className="p-3 border-b border-border-default flex items-center justify-between">
        <h2 className="text-sm font-semibold">類別</h2>
        <Button variant="ghost" size="icon" onClick={() => addChild(null)} aria-label="新增根類別">
          <Plus className="w-4 h-4" strokeWidth={1.5} />
        </Button>
      </div>
      <ScrollArea className="flex-1">
        <div className="p-2">
          {loading && (
            <div className="space-y-2">
              <Skeleton className="h-6" />
              <Skeleton className="h-6" />
              <Skeleton className="h-6" />
            </div>
          )}
          {!loading && tree.length === 0 && (
            <p className="text-xs text-text-muted text-center py-8">尚無分類</p>
          )}
          {!loading && tree.length > 0 && (
            <ul>
              {tree.map((node) => (
                <CategoryTreeNode
                  key={node.id}
                  node={node}
                  depth={0}
                  selectedId={selectedId}
                  pendingRenameId={pendingRenameId}
                  onSelect={select}
                  onRename={rename}
                  onAddChild={addChild}
                  onRemove={remove}
                  onClearPendingRename={clearPendingRename}
                  onExport={exportCategory}
                  onImport={importCategory}
                />
              ))}
            </ul>
          )}
        </div>
      </ScrollArea>
    </aside>
  )
}
```

- [ ] **Step 3：確認 TypeScript 型別無誤**

```bash
cd D:\mini_test\frontend
npx tsc --noEmit
```

預期：0 errors

- [ ] **Step 4：執行前端測試**

```bash
npm test
```

預期：全部 passed（既有測試不得 regression）

- [ ] **Step 5：執行後端完整測試**

```bash
cd D:\mini_test\backend
python -m pytest -q
```

預期：307+ passed（原 295 + 新增 12 筆），0 failures

- [ ] **Step 6：commit**

```bash
git add frontend/src/features/knowledge/CategoryTreeNode.tsx \
         frontend/src/features/knowledge/CategoryTree.tsx
git commit -m "feat: add export/import FAQ buttons to CategoryTreeNode with append/replace sub-menu"
```

---

## 驗收清單

- [ ] `GET /api/v1/agents/{id}/categories/{cat_id}/export` — 回傳 xlsx，只含該分類及子分類的 FAQ
- [ ] `POST /api/v1/agents/{id}/categories/{cat_id}/import?mode=append` — 只需 question/answer 欄，保留現有資料，新增不重複 FAQ
- [ ] `POST /api/v1/agents/{id}/categories/{cat_id}/import?mode=replace` — 先刪除該分類（含子分類）全部 FAQ，再匯入
- [ ] 分類 dropdown → 「匯出 FAQ」直接觸發下載
- [ ] 分類 dropdown → 「匯入 FAQ」展開子選單，顯示「新增匯入（保留現有資料）」與「覆蓋匯入（先刪除全部）」
- [ ] 選擇匯入模式後開啟 .xlsx 檔案選擇器，上傳後 toast 顯示模式與結果
- [ ] 後端測試：`python -m pytest -q` 全 passed
- [ ] 前端 TypeScript：`npx tsc --noEmit` 0 errors
- [ ] 分類不存在時匯入/匯出均回傳 404
