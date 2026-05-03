# Backend Tests Style Guide

供 backend/tests/ 開發者參考。違反規則時不會自動阻擋（CI 不檢查），純文件性質。

## 測試碼基本規則

1. **AAA 三段以空行分隔**
   - Arrange（準備）/ Act（執行）/ Assert（驗證）三段間加空行
   - 簡短測試（<5 行）可省略

2. **Helper 一律 module-level 或 conftest fixture**
   - 不在 `class TestXxx` 內定義 helper（除非僅該類別使用）
   - 跨檔共用 helper 放 conftest.py（私有：`_xxx`）或 `_xxx_helpers.py`

3. **每個 test 必加 `-> None`**
   - 連 helper 與 fixture 也要加（除非有具體 return type）

4. **Mock 偏好**
   - 共用 mock 走 conftest fixture（`agent_factory`、`mock_db`、`build_agent_access_query_se`）
   - 深層 ORM call chain mock（>5 層）標 `# TODO(test-refactor): consider sqlite in-memory`
   - `db.query.side_effect` 計數器模式：能用 `build_agent_access_query_se` 就不要 hand-roll

5. **命名**
   - 行為描述：`test_xxx_returns_xxx`、`test_xxx_does_yyy`
   - 函式名 < 50 字元，超過就拆 docstring 說明
   - 類別 docstring 第一行寫業務範圍；regression 類別加 `# Regression: <ID> (<reason>)`

6. **assert 風格**
   - 純 `assert`，不用 `unittest.assertEqual`
   - 失敗訊息加自訂：`assert resp.status_code == 200, resp.json()`

7. **patch 風格**
   - `with patch(...)` context manager 為主
   - 不混用 decorator
