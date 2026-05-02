# 分類獨立同步（Category-Level Sync）實施計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓特定分類（含子孫分類）可獨立觸發向量同步，Qdrant 向量攜帶 `category_path` metadata，同步時精準刪除同路徑舊向量。

**Architecture:** 新增 `backend/api/utils/category_path.py` 共用工具；擴充 `ingest_kb.py` 支援 `[Category]` txt 格式與 `--delete-category-paths` 刪除參數；在 `tasks.py` 新增 `run_category_sync` Celery task；在 `sync.py` 新增 `POST /api/v1/agents/{agent_id}/categories/{category_id}/sync` 端點。全局同步（`run_ingestion_sync`）不修改。

**Tech Stack:** Python 3.11、FastAPI、Celery、SQLAlchemy（同步）、qdrant-client（`Filter` / `FieldCondition` / `MatchAny` / `FilterSelector`）、pytest + MagicMock

---

## 檔案清單

| 動作 | 路徑 | 說明 |
|------|------|------|
| 新建 | `backend/api/utils/__init__.py` | 空模組初始化 |
| 新建 | `backend/api/utils/category_path.py` | `build_category_path` / `collect_category_subtree` |
| 修改 | `backend/api/routes/import_export.py` | 改用 utils 取代本地函式 |
| 修改 | `ingest_kb.py` | 擴充格式 / 刪除函式 / CLI 參數 |
| 修改 | `backend/tasks.py` | 新增 `run_category_sync` |
| 修改 | `backend/api/routes/sync.py` | 新增分類同步端點 |
| 新建 | `backend/tests/test_category_sync.py` | 端點 + task + utils 測試 |

---

## Task 1：建立共用工具模組 `api/utils/category_path.py`

`import_export.py` 中的 `_build_category_path` / `_collect_category_ids` 與 `tasks.py` 需要共用，先抽出成獨立模組。

**Files:**
- Create: `backend/api/utils/__init__.py`
- Create: `backend/api/utils/category_path.py`

- [ ] **Step 1: 撰寫失敗測試（`test_category_sync.py` 中的 utils 區段）**

在 `backend/tests/test_category_sync.py` 新增：

```python
"""
分類同步功能測試：utils、endpoint、task。
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from tests.conftest import AGENT_ID

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
```

- [ ] **Step 2: 執行測試確認失敗**

```
cd D:\mini_test\backend
python -m pytest tests/test_category_sync.py::TestBuildCategoryPath tests/test_category_sync.py::TestCollectCategorySubtree -v
```

預期：`ImportError: cannot import name 'build_category_path' from 'api.utils.category_path'`

- [ ] **Step 3: 建立 `backend/api/utils/__init__.py`**

```python
```
（空檔案）

- [ ] **Step 4: 建立 `backend/api/utils/category_path.py`**

```python
"""
分類路徑工具函式，供 import_export.py 與 tasks.py 共用。
"""
from __future__ import annotations

from typing import Any


def build_category_path(
    category_id: Any, cat_map: dict[Any, Any]
) -> str:
    """
    從 category_id 向上追溯組合完整路徑字串（/ 分隔）。
    使用預先載入的 cat_map（id -> Category）避免 N+1 query。
    category_id 不在 cat_map 中時回傳空字串。
    """
    parts: list[str] = []
    current_id = category_id
    visited: set[Any] = set()
    while current_id is not None:
        if current_id in visited:
            break
        visited.add(current_id)
        cat = cat_map.get(current_id)
        if cat is None:
            break
        parts.insert(0, str(cat.name))
        current_id = cat.parent_id
    return "/".join(parts)


def collect_category_subtree(
    root_id: Any, cat_map: dict[Any, Any]
) -> set[Any]:
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

- [ ] **Step 5: 執行測試確認通過**

```
python -m pytest tests/test_category_sync.py::TestBuildCategoryPath tests/test_category_sync.py::TestCollectCategorySubtree -v
```

預期：8 passed

- [ ] **Step 6: Commit**

```bash
git add backend/api/utils/__init__.py backend/api/utils/category_path.py backend/tests/test_category_sync.py
git commit -m "feat: add category_path utility module with build_category_path and collect_category_subtree"
```

---

## Task 2：重構 `import_export.py` 改用共用工具

`import_export.py` 中本地的 `_build_category_path` 與 `_collect_category_ids` 改由 `api.utils.category_path` 提供，刪除重複定義。

**Files:**
- Modify: `backend/api/routes/import_export.py:79-116`

- [ ] **Step 1: 確認既有 import_export 測試全過（基線）**

```
python -m pytest tests/test_import_export.py -v -q
```

預期：所有測試通過（記錄通過數量）

- [ ] **Step 2: 修改 `import_export.py`**

移除第 79–116 行的 `_build_category_path` 與 `_collect_category_ids`，改為從 utils 匯入，並更新呼叫點：

在檔案頂部 import 區段加入：
```python
from api.utils.category_path import build_category_path, collect_category_subtree
```

刪除 `def _build_category_path(...)` 與 `def _collect_category_ids(...)` 兩個函式（約第 79–116 行）。

找出原本呼叫 `_build_category_path(...)` 的地方（使用 grep 確認位置），全部改為 `build_category_path(...)`；原本呼叫 `_collect_category_ids(...)` 改為 `collect_category_subtree(...)`。

- [ ] **Step 3: 執行測試確認 import_export 測試依然全過**

```
python -m pytest tests/test_import_export.py -v -q
```

預期：通過數量與 Step 1 基線相同

- [ ] **Step 4: Commit**

```bash
git add backend/api/routes/import_export.py
git commit -m "refactor: import_export.py uses shared api.utils.category_path"
```

---

## Task 3：擴充 `ingest_kb.py`

新增三項能力：
1. 支援含 `[Category]` 區塊的擴充 txt 格式（`parse_kb()` 向後相容）
2. `delete_by_category_paths()` 函式：依 `metadata.category_path` 精準刪除向量
3. `--delete-category-paths` CLI 參數：由 Celery task 傳入，即使 txt 為空也執行刪除

**Files:**
- Modify: `ingest_kb.py`

- [ ] **Step 1: 撰寫失敗測試（加入 `test_category_sync.py`）**

在 `backend/tests/test_category_sync.py` 末尾新增：

```python
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

        qdrant = MagicMock()
        qdrant.get_collections.return_value.collections = []

        delete_by_category_paths(qdrant, "not_exist", ["path/A"])

        qdrant.delete.assert_not_called()
```

- [ ] **Step 2: 執行測試確認失敗**

```
cd D:\mini_test\backend
python -m pytest tests/test_category_sync.py::TestParsKbWithCategoryBlocks tests/test_category_sync.py::TestDeleteByCategoryPaths -v
```

預期：`ImportError` 或 `AssertionError`（`category_path` key 不存在）

- [ ] **Step 3: 修改 `ingest_kb.py`**

**3a. 在頂部 import 區段新增：**

```python
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchAny,
    PointStruct,
    VectorParams,
)
```

（取代原有的 `from qdrant_client.models import Distance, PointStruct, VectorParams`）

**3b. 在 `_BLOCK_RE` 定義後新增 `_CAT_BLOCK_RE`：**

```python
_CAT_BLOCK_RE = re.compile(
    r"\[Category\]\s*\n(.*?)\n\s*\n\[Question\]\s*\n(.*?)\n\s*\n\[Answer\]\s*\n(.*)",
    re.S,
)
```

**3c. 替換 `parse_kb()` 函式（完整替換）：**

```python
def parse_kb(path: str | Path) -> list[dict]:
    """
    解析匯出 .txt。
    優先嘗試含 [Category] 的新格式，其次 [Question]/[Answer] 舊格式，
    最後退回舊版 Q:/A: 格式。
    回傳 records，每筆含 question / answer / text，新格式另含 category_path。
    """
    text = Path(path).read_text(encoding="utf-8")
    records: list[dict] = []

    # ── 優先：含 [Category] 的新格式 ──────────────────────────────────
    if "[Category]" in text:
        parts = text.split("\n\n[Category]")
        blocks: list[str] = []
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
            if i == 0:
                if not part.startswith("[Category]"):
                    blocks = []
                    break
                blocks.append(part)
            else:
                blocks.append("[Category]\n" + part.lstrip("\n"))

        for block in blocks:
            m = _CAT_BLOCK_RE.match(block)
            if not m:
                continue
            category_path = m.group(1).strip()
            q = _restore_reserved(m.group(2).strip())
            a = _restore_reserved(m.group(3).strip())
            records.append(
                {
                    "question": q,
                    "answer": a,
                    "text": f"問題：{q}\n答案：{a}",
                    "category_path": category_path,
                }
            )
        if records:
            return records

    # ── 次選：[Question]/[Answer] 無 [Category]（全局同步格式）──────────
    parts = text.split("\n\n[Question]")
    blocks = []
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        if i == 0:
            if not part.startswith("[Question]"):
                blocks = []
                break
            blocks.append(part)
        else:
            blocks.append("[Question]\n" + part.lstrip("\n"))

    for block in blocks:
        m = _BLOCK_RE.match(block)
        if not m:
            continue
        q = _restore_reserved(m.group(1).strip())
        a = _restore_reserved(m.group(2).strip())
        records.append({"question": q, "answer": a, "text": f"問題：{q}\n答案：{a}"})

    if records:
        return records

    # ── 向後相容：Q:/A: 格式 ─────────────────────────────────────────────
    for q, a in _LEGACY_RE.findall(text):
        q = q.strip()
        a = a.strip()
        records.append({"question": q, "answer": a, "text": f"問題：{q}\n答案：{a}"})
    return records
```

**3d. 新增 `delete_by_category_paths()` 函式（放在 `init_collection` 後）：**

```python
def delete_by_category_paths(
    qdrant: QdrantClient, collection_name: str, category_paths: list[str]
) -> None:
    """
    刪除 Qdrant collection 中 metadata.category_path 符合任一指定路徑的向量。
    collection 不存在時靜默跳過。
    """
    existing = {c.name for c in qdrant.get_collections().collections}
    if collection_name not in existing:
        print(f"Qdrant collection {collection_name!r} 不存在，略過刪除。")
        return
    qdrant.delete(
        collection_name=collection_name,
        points_selector=FilterSelector(
            filter=Filter(
                must=[
                    FieldCondition(
                        key="metadata.category_path",
                        match=MatchAny(any=category_paths),
                    )
                ]
            )
        ),
    )
    print(f"已刪除 category_path 符合 {category_paths} 的向量")
```

**3e. 修改 `upload()` 函式，加入 `category_path` 至 payload：**

將 payload 中的 `metadata` 字典由：
```python
"metadata": {
    "type": "faq",
    "doc_id": doc_id,
    "source": source,
    "answer": r["answer"],
},
```

改為：
```python
_meta: dict[str, str] = {
    "type": "faq",
    "doc_id": doc_id,
    "source": source,
    "answer": r["answer"],
}
if r.get("category_path"):
    _meta["category_path"] = r["category_path"]
```

並更新 `payload` 為：
```python
payload={
    "page_content": r["question"],
    "metadata": _meta,
},
```

**3f. 在 `_build_parser()` 新增 `--delete-category-paths` 參數：**

在 `--clear` argument 之後加入：
```python
parser.add_argument(
    "--delete-category-paths",
    default="",
    dest="delete_category_paths",
    help="逗號分隔的 category_path 清單，同步前精準刪除對應向量（分類同步用）",
)
```

**3g. 修改 `main()` 的刪除邏輯（完整替換 `init_collection` 呼叫區段）：**

將原本的：
```python
init_collection(qdrant, openai_client, args.collection, clear=args.clear)
upload(...)
```

改為：
```python
# 計算 records 中的 category_path（若有）
unique_paths_from_records = list(
    {r["category_path"] for r in records if r.get("category_path")}
)

# 決定刪除策略
explicit_paths = [
    p.strip()
    for p in args.delete_category_paths.split(",")
    if p.strip()
]

if args.clear:
    # 全局同步：刪整個 collection 再重建
    init_collection(qdrant, openai_client, args.collection, clear=True)
elif explicit_paths:
    # 分類同步（Celery task 明確傳入）：確保 collection 存在 + 精準刪除
    init_collection(qdrant, openai_client, args.collection, clear=False)
    delete_by_category_paths(qdrant, args.collection, explicit_paths)
elif unique_paths_from_records:
    # 從 records 自動偵測（手動執行新格式 txt 時使用）
    init_collection(qdrant, openai_client, args.collection, clear=False)
    delete_by_category_paths(qdrant, args.collection, unique_paths_from_records)
else:
    # 無 --clear 也無 category_path：確保 collection 存在即可
    init_collection(qdrant, openai_client, args.collection, clear=False)

if records:
    upload(
        qdrant,
        openai_client,
        records,
        collection_name=args.collection,
        doc_id=args.doc_id,
        source=str(source_path),
    )
    print(f"完成向量化並寫入 Qdrant collection={args.collection}（Upsert / 可重跑）")
else:
    print("無資料可上傳，結束。")

return 0
```

- [ ] **Step 4: 執行測試確認通過**

```
cd D:\mini_test\backend
python -m pytest tests/test_category_sync.py::TestParsKbWithCategoryBlocks tests/test_category_sync.py::TestDeleteByCategoryPaths -v
```

預期：5 passed

- [ ] **Step 5: 確認既有 tasks 測試未受影響**

```
python -m pytest tests/test_tasks.py -v -q
```

預期：全數通過（無回歸）

- [ ] **Step 6: Commit**

```bash
git add ingest_kb.py backend/tests/test_category_sync.py
git commit -m "feat: ingest_kb.py supports [Category] block format, delete_by_category_paths, --delete-category-paths CLI"
```

---

## Task 4：新增 `run_category_sync` Celery task

**Files:**
- Modify: `backend/tasks.py`（在檔案末尾新增函式）

- [ ] **Step 1: 撰寫失敗測試（加入 `test_category_sync.py`）**

在 `backend/tests/test_category_sync.py` 末尾新增：

```python
# ── run_category_sync task ────────────────────────────────────────────────────

import os
from unittest.mock import mock_open, patch

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
                q.filter.return_value.filter.return_value.all.return_value = items
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
```

- [ ] **Step 2: 執行測試確認失敗**

```
cd D:\mini_test\backend
python -m pytest tests/test_category_sync.py::TestRunCategorySyncTask -v
```

預期：`ImportError: cannot import name 'run_category_sync' from 'tasks'`

- [ ] **Step 3: 在 `backend/tasks.py` 末尾新增 `run_category_sync`**

```python
@celery_app.task(bind=True, max_retries=TASK_MAX_RETRIES, default_retry_delay=TASK_RETRY_DELAY_SEC)
def run_category_sync(self, agent_id: str, category_id: str, sync_log_id: str) -> None:  # type: ignore[misc]
    """
    分類同步：針對指定分類（含子孫分類）的 FAQ 進行向量化同步。
    1. 收集分類樹（目標 + 所有子孫）
    2. 取出 approved/synced 的 FAQ
    3. 寫入含 [Category] 區塊的 txt
    4. 執行 ingest_script_path（不帶 --clear，帶 --delete-category-paths）
    5. 標記同步項目為 synced
    6. 更新 sync_logs
    """
    from api.database.models import Agent, Category, KnowledgeItem, SyncLog  # noqa: PLC0415
    from api.database.session import SessionLocal  # noqa: PLC0415
    from api.utils.category_path import build_category_path, collect_category_subtree  # noqa: PLC0415

    db = SessionLocal()
    sync_log = None

    try:
        sync_log = db.query(SyncLog).filter(
            SyncLog.id == uuid.UUID(sync_log_id)
        ).first()
        if not sync_log:
            return

        agent = db.query(Agent).filter(Agent.id == uuid.UUID(agent_id)).first()
        if not agent:
            sync_log.status = "failed"
            sync_log.stderr = "Agent 不存在"
            db.commit()
            return

        target_cat = db.query(Category).filter(
            Category.id == uuid.UUID(category_id),
            Category.agent_id == uuid.UUID(agent_id),
        ).first()
        if not target_cat:
            sync_log.status = "failed"
            sync_log.stderr = "分類不存在"
            db.commit()
            return

        sync_log.status = "running"
        sync_log.started_at = datetime.now(timezone.utc)
        db.commit()

        # 載入此 agent 的全部分類
        all_cats = db.query(Category).filter(
            Category.agent_id == uuid.UUID(agent_id)
        ).all()
        cat_map = {c.id: c for c in all_cats}

        # 收集目標分類的子樹 ID（含自身）
        subtree_ids = collect_category_subtree(uuid.UUID(category_id), cat_map)

        # 計算子樹內每個分類的 category_path（供 --delete-category-paths 使用）
        subtree_paths = list({
            build_category_path(cid, cat_map)
            for cid in subtree_ids
            if build_category_path(cid, cat_map)
        })

        # 取出 approved/synced 的 FAQ
        items = (
            db.query(KnowledgeItem)
            .filter(
                KnowledgeItem.agent_id == uuid.UUID(agent_id),
                KnowledgeItem.category_id.in_(subtree_ids),
                KnowledgeItem.status.in_(["approved", "synced"]),
            )
            .all()
        )

        # 組合含 [Category] 區塊的 txt
        blocks: list[str] = []
        for item in items:
            cat_path = build_category_path(item.category_id, cat_map)
            question = (
                item.question.replace("[Question]", "【Question】")
                .replace("[Answer]", "【Answer】")
            )
            answer = (
                item.answer.replace("[Question]", "【Question】")
                .replace("[Answer]", "【Answer】")
            )
            blocks.append(
                f"[Category]\n{cat_path}\n\n[Question]\n{question}\n\n[Answer]\n{answer}"
            )

        txt_content = "\n\n".join(blocks)
        output_path = (
            str(agent.txt_output_path).rstrip("/")
            + f"/category_{category_id}_export.txt"
        )
        sync_log.output_file = output_path

        import os as _os  # noqa: PLC0415

        _os.makedirs(_os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(txt_content)

        stdout_data = ""
        stderr_data = ""

        if agent.ingest_script_path:
            script_path = str(agent.ingest_script_path)
            if ".." in script_path:
                raise RuntimeError(
                    f"ingest_script_path 包含不允許的上級目錄引用：{script_path}"
                )
            if not _os.path.isfile(script_path):
                raise RuntimeError(
                    f"Ingestion script 不存在或無法存取：{script_path}"
                )

            qdrant_url = os.environ.get("QDRANT_URL")
            if not qdrant_url:
                raise RuntimeError("QDRANT_URL 未設定，無法執行 ingest")

            agent_id_str = str(agent.id)
            cmd = [
                "python",
                script_path,
                "--source", output_path,
                "--qdrant-url", qdrant_url,
                "--collection", f"agent_{agent_id_str}",
                "--doc-id", f"agent_{agent_id_str}_v1",
                "--delete-category-paths", ",".join(subtree_paths),
                # 不帶 --clear：精準刪除指定 category_path 的向量
            ]
            popen_kwargs: dict = {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "text": True,
            }
            if sys.platform != "win32":
                popen_kwargs["start_new_session"] = True
            proc = subprocess.Popen(cmd, **popen_kwargs)  # noqa: S603
            try:
                stdout_data, stderr_data = proc.communicate(
                    timeout=INGEST_SUBPROCESS_TIMEOUT_SEC
                )
                returncode = proc.returncode
                if returncode != 0:
                    sync_log.stdout = stdout_data
                    sync_log.stderr = stderr_data[:STDERR_MAX_CHARS]
                    stderr_snippet = (stderr_data.strip() or stdout_data.strip())[:300]
                    detail = f"\nstderr: {stderr_snippet}" if stderr_snippet else ""
                    raise RuntimeError(
                        f"Ingestion script 退出碼 {returncode}{detail}"
                    )
            except subprocess.TimeoutExpired:
                if sys.platform != "win32":
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except (ProcessLookupError, PermissionError):
                        proc.kill()
                else:
                    proc.kill()
                try:
                    proc.wait(timeout=INGEST_KILL_GRACE_SEC)
                except subprocess.TimeoutExpired:
                    pass
                raise RuntimeError(
                    f"Ingestion script 執行逾時（{INGEST_SUBPROCESS_TIMEOUT_SEC} 秒）"
                )

        for item in items:
            item.status = "synced"

        finished_at = datetime.now(timezone.utc)
        started_at = sync_log.started_at
        if started_at and started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)

        sync_log.status = "completed"
        sync_log.items_count = len(items)
        sync_log.stdout = stdout_data
        sync_log.stderr = stderr_data
        sync_log.finished_at = finished_at
        sync_log.duration_sec = (
            int((finished_at - started_at).total_seconds()) if started_at else None
        )
        db.commit()

    except (RuntimeError, OSError, subprocess.SubprocessError, IOError) as exc:
        logger.exception(
            "category_sync_task_failed",
            agent_id=agent_id,
            category_id=category_id,
            sync_log_id=sync_log_id,
            error=str(exc),
        )
        max_retries = self.max_retries if self.max_retries is not None else TASK_MAX_RETRIES
        if self.request.retries >= max_retries:
            if sync_log:
                sync_log.status = "failed"
                sync_log.stderr = str(exc)[:STDERR_MAX_CHARS]
                sync_log.finished_at = datetime.now(timezone.utc)
                db.commit()
            raise
        countdown = RETRY_BACKOFF_BASE_SEC * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)
    finally:
        db.close()
```

- [ ] **Step 4: 執行測試確認通過**

```
cd D:\mini_test\backend
python -m pytest tests/test_category_sync.py::TestRunCategorySyncTask -v
```

預期：5 passed

- [ ] **Step 5: 確認全體測試無回歸**

```
python -m pytest tests/ -q
```

預期：全數通過

- [ ] **Step 6: Commit**

```bash
git add backend/tasks.py backend/tests/test_category_sync.py
git commit -m "feat: add run_category_sync Celery task for category-level vector sync"
```

---

## Task 5：新增分類同步 API 端點

**Files:**
- Modify: `backend/api/routes/sync.py`

- [ ] **Step 1: 撰寫失敗測試（加入 `test_category_sync.py`）**

在 `backend/tests/test_category_sync.py` 末尾新增：

```python
# ── trigger_category_sync 端點 ────────────────────────────────────────────────

from tests.conftest import build_agent_access_query_se

SYNC_CAT_LOG_ID = uuid.UUID("00000000-0000-0000-0000-000000000052")


class TestTriggerCategorySync:
    ENDPOINT = f"/api/v1/agents/{AGENT_ID}/categories/{CATEGORY_ID}/sync"

    def _setup_db(self, mock_db, agent, category, uar_role=None):
        """
        query 序列：
        idx 0: Agent（require_reviewer_or_superadmin → require_agent_access）
        idx 1: UAR（require_reviewer_or_superadmin）
        idx 2: Category（confirm category belongs to agent）
        idx 3+: SyncLog add/refresh
        """
        counter = [0]

        def se(*args):
            q = MagicMock()
            idx = counter[0]
            counter[0] += 1
            if idx == 0:
                q.filter.return_value.first.return_value = agent
            elif idx == 1:
                if uar_role is None:
                    q.filter.return_value.first.return_value = None
                else:
                    uar = MagicMock()
                    uar.role = uar_role
                    q.filter.return_value.first.return_value = uar
            elif idx == 2:
                q.filter.return_value.first.return_value = category
            else:
                q.filter.return_value.first.return_value = None
            return q

        mock_db.query.side_effect = se

    def test_superadmin_returns_202(self, client_superadmin, mock_db, agent_factory) -> None:
        agent = agent_factory()
        cat = _make_category()
        self._setup_db(mock_db, agent, cat)
        mock_db.refresh.return_value = None

        with patch("tasks.run_category_sync") as mock_celery:
            mock_celery.delay.return_value.id = "cat-task-id"
            resp = client_superadmin.post(self.ENDPOINT)

        assert resp.status_code == 202
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["status"] == "pending"
        assert data["data"]["task_id"] == "cat-task-id"

    def test_reviewer_can_trigger(self, client_reviewer, mock_db, agent_factory) -> None:
        agent = agent_factory()
        cat = _make_category()
        self._setup_db(mock_db, agent, cat, uar_role="reviewer")
        mock_db.refresh.return_value = None

        with patch("tasks.run_category_sync") as mock_celery:
            mock_celery.delay.return_value.id = "task-id"
            resp = client_reviewer.post(self.ENDPOINT)

        assert resp.status_code == 202

    def test_editor_returns_403(self, client_editor, mock_db, agent_factory) -> None:
        agent = agent_factory()
        self._setup_db(mock_db, agent, None, uar_role="editor")

        resp = client_editor.post(self.ENDPOINT)
        assert resp.status_code == 403

    def test_category_not_found_returns_404(self, client_superadmin, mock_db, agent_factory) -> None:
        agent = agent_factory()
        self._setup_db(mock_db, agent, category=None)  # category not found
        mock_db.refresh.return_value = None

        resp = client_superadmin.post(self.ENDPOINT)
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "NOT_FOUND"

    def test_celery_unavailable_still_returns_202(self, client_superadmin, mock_db, agent_factory) -> None:
        agent = agent_factory()
        cat = _make_category()
        self._setup_db(mock_db, agent, cat)
        mock_db.refresh.return_value = None

        with patch("tasks.run_category_sync") as mock_celery:
            mock_celery.delay.side_effect = ConnectionError("broker down")
            resp = client_superadmin.post(self.ENDPOINT)

        assert resp.status_code == 202
        assert resp.json()["data"]["task_id"] is None
```

- [ ] **Step 2: 執行測試確認失敗**

```
cd D:\mini_test\backend
python -m pytest tests/test_category_sync.py::TestTriggerCategorySync -v
```

預期：404（端點不存在）

- [ ] **Step 3: 修改 `backend/api/routes/sync.py`**

在 `get_sync_history` 函式前（第 84 行之前）插入以下新端點：

```python
@router.post(
    "/api/v1/agents/{agent_id}/categories/{category_id}/sync",
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_category_sync(
    agent_id: uuid.UUID,
    category_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    """觸發指定分類（含子孫分類）的獨立向量同步。"""
    from api.database.models import Category  # noqa: PLC0415

    require_reviewer_or_superadmin(agent_id, current_user, db)

    cat = (
        db.query(Category)
        .filter(Category.id == category_id, Category.agent_id == agent_id)
        .first()
    )
    if not cat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "分類不存在"},
        )

    sync_log = SyncLog(
        id=uuid.uuid4(),
        agent_id=agent_id,
        triggered_by=current_user.id,
        status="pending",
        items_count=0,
    )
    db.add(sync_log)
    db.commit()
    db.refresh(sync_log)

    task_id: str | None = None
    try:
        from tasks import run_category_sync  # noqa: PLC0415

        task = run_category_sync.delay(
            str(agent_id), str(category_id), str(sync_log.id)
        )
        sync_log.celery_task_id = task.id
        db.commit()
        task_id = task.id
    except (ConnectionError, OSError, TimeoutError) as exc:
        logger.warning(
            "celery_category_sync_dispatch_failed",
            agent_id=str(agent_id),
            category_id=str(category_id),
            sync_log_id=str(sync_log.id),
            error=str(exc),
        )

    logger.info(
        "category_sync_triggered",
        agent_id=str(agent_id),
        category_id=str(category_id),
        user_id=str(current_user.id),
        sync_log_id=str(sync_log.id),
        celery_task_id=task_id,
    )
    return {
        "success": True,
        "data": {
            "task_id": task_id,
            "sync_log_id": str(sync_log.id),
            "status": "pending",
        },
    }
```

- [ ] **Step 4: 執行測試確認通過**

```
cd D:\mini_test\backend
python -m pytest tests/test_category_sync.py::TestTriggerCategorySync -v
```

預期：5 passed

- [ ] **Step 5: 執行全部測試確認無回歸**

```
python -m pytest tests/ -q
```

預期：全數通過（新增約 23 個測試）

- [ ] **Step 6: Lint 與型別檢查**

```
python -m ruff check backend/ ingest_kb.py --fix
PYTHONUTF8=1 python -m mypy backend/api/ ingest_kb.py --ignore-missing-imports
```

預期：無錯誤

- [ ] **Step 7: Commit**

```bash
git add backend/api/routes/sync.py backend/tests/test_category_sync.py
git commit -m "feat: add POST /api/v1/agents/{agent_id}/categories/{category_id}/sync endpoint"
```

---

## 自我審查

**規格覆蓋確認：**
- [x] 分類或子分類可獨立觸發同步 → Task 5 endpoint
- [x] Qdrant metadata 新增 `category_path` → Task 3 `upload()` 修改
- [x] 同步前刪除 `category_path` 相同的向量 → Task 3 `delete_by_category_paths()` + `--delete-category-paths`
- [x] 全局同步不動 → 無修改 `run_ingestion_sync`

**邊界情境：**
- 分類下無 approved/synced FAQ → `items = []` → txt 為空 → 不呼叫 `upload()` → script 仍執行刪除（`--delete-category-paths` 傳入）
- 目標分類有子孫 → `subtree_ids` 收集所有子孫 → 子孫的 FAQ 也包含在 txt 中
- `ingest_script_path` 未設定 → 跳過 subprocess → 仍更新 sync_log（完成寫 txt）

**型別一致性：**
- `build_category_path` / `collect_category_subtree` 在 Task 1、4 均相同簽名
- Task 4 中 `run_category_sync` 的 `subtree_ids` 型別為 `set[Any]`，傳入 SQLAlchemy `.in_()` 相容
