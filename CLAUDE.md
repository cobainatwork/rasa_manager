# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 一、倉庫性質

此目錄為 **Rasa RAG 知識庫管理平台** 的工作目錄，目前處於「規格已完成、程式碼尚未開始」的階段。

| 檔案 | 角色 |
|------|------|
| `comprehensive-system-design.md` | 系統架構與詳細規格書（v1.0，唯一權威） |
| `implementation_plan.md` | 六階段實施計畫書，依 v1.0 規格拆解 |

實作將就地進行於本目錄 `D:\mini_test\` 下方，未來會新增 `backend/`、`frontend/`、`scripts/`、`docker-compose.yml`、`.env` 等子目錄與檔案（見 `implementation_plan.md` 第一階段）。本目錄即為最終的程式碼倉庫根目錄。

目前尚無 `.git`、無 `package.json`、無 `requirements.txt`、無 Dockerfile、無原始碼；建議在開始實作前先 `git init`。

---

## 二、文件權威性

1. `comprehensive-system-design.md` v1.0 為**唯一權威規格**。
2. v1.0 已**完全取代** `design-knowledge-base-management.md` v0.2（見規格書 §20「廢止宣告」），不可再引用 v0.2。
3. 若 `implementation_plan.md` 與規格書出現衝突，**一律以 v1.0 規格書為準**，並應建議使用者同步修正 implementation_plan。

---

## 三、系統架構快覽

摘錄自規格書 §1，避免重複閱讀完整文件：

- **五服務 Docker Compose 架構**：FastAPI（backend）、PostgreSQL 15、Redis 7、Celery Worker、React + Vite 前端。
- **外部依賴**：Rasa Server（REST webhook 對話測試）、Qdrant（向量資料庫）。
- **非同步解耦**：一鍵同步透過 Celery 推入 Redis broker，由 Worker 容器內執行使用者的 ingestion script。
- **掛載機制**：
  - 使用者 ingestion scripts 透過 `./scripts/` 以 `:ro` bind mount 至 Worker 容器的 `/opt/scripts/`。
  - 匯出的 `.txt` 透過 `rasa_docs` volume 共享至 `/opt/rasa_docs/{agent_name}/`。
- **多 Agent 隔離**：所有業務資料以 `agent_id` 隔離；API 路徑統一為 `/api/v1/agents/{agent_id}/...`。

---

## 四、核心領域模型

僅列關鍵實體與必須掌握的特性，完整 schema 見規格書 §2：

- `users` × `agents` × `user_agent_roles`：權限體系採 `is_superadmin` 旗標 + 每 Agent 內 `reviewer` / `editor` 二角色。
- `categories`：採 Adjacency List 模型，以 `parent_id` 自參照支援無限層級。
- `knowledge_items`：FAQ 主檔，含編輯鎖欄位 `locked_by` 與 `locked_at`。
- `knowledge_item_histories`：不可變（immutable）版本紀錄表，支援 Rollback。
- `audit_logs`、`sync_logs`：稽核軌跡與同步任務紀錄。
- **狀態機**：`draft → pending → approved → synced`，含 `rejected` 退回路徑與 Superadmin 直接核准的跳躍路徑（見規格書 §3.1）。

---

## 五、關鍵設計約束

下列為實作或調整規格時必守的硬性規則，不可任意放寬：

1. **JWT 儲存**：一律以 HttpOnly Cookie 儲存；Access 15 分鐘、Refresh 7 天；角色**不**寫入 JWT payload（角色會異動，僅以身分驗證為準）。
2. **編輯鎖**：採 Lazy Expire 模式，10 分鐘逾時，於 `GET /faq/:id` 或 `PATCH /faq/:id` 時於同一 transaction 內惰性清除，不依賴背景排程。
3. **Ingestion script 安全性**：`ingest_script_path` 僅 Superadmin 可設定；`subprocess` 禁止 `shell=True`，需以 `shlex.split()` 處理；超時強制終止。
4. **匯出 `.txt` 格式**：採 `[Question]` / `[Answer]` 區塊以雙換行分隔；內容若含保留字串需改寫為全形 `【Question】` / `【Answer】` 防止解析衝突。
5. **一鍵同步條件**：取出 `status IN ('approved', 'synced')` 的 FAQ 進行匯出；同步成功後將項目標記為 `synced`；`approved` 或 `synced` 項目被編輯時自動降級為 `draft`。
6. **密碼策略**：最小 8 字元、需含大寫 / 小寫 / 數字；Bcrypt cost factor = 12；登入採 Redis 計數器防爆破（同 IP + 帳號 5 次失敗鎖定 15 分鐘）。

---

## 六、實作前必修的規格缺陷

下列項目為「審查可實作性」時識別出的阻斷或高風險問題，**動工前須先與使用者確認修正方向**，否則實作會踩坑：

### 6.1 規格書 v1.1 已解決的全部問題

以下問題均已在 `comprehensive-system-design.md` v1.1 修正，無需再追蹤：

| 項目 | 修正位置 |
|------|---------|
| [A1] Cookie SameSite=Strict 澄清 + CORS 完整配置 | §15.4 |
| [A2] CSRF 防護說明（SameSite=Strict 已覆蓋） | §15.4 |
| [A3] Vite proxy 目標 `http://localhost:8000` | §8.4 |
| [A4] Compose `env_file: .env` 注入機制 | §10.5 |
| [B1] `{agent_name}` 路徑改用 `txt_output_path`（推薦 UUID 子目錄） | §1.2、§10.2、§12.3、§15.6 |
| [B2] Refresh Token Rotation + Redis `jti` 黑名單 | §6.1、§6.2、§6.3 |
| [B3] 編輯鎖延長 `PUT /lock` 心跳端點 | §4.2 |
| [B4] `.txt` 固定單檔策略，刪除多檔切分曖昧說法 | §5 |
| [B5] Axios 401 refresh 競態 pending promise queue | §8.5 |
| [C1] sync_logs 狀態值統一為 `pending` | §4.4 |
| [C2] Celery task_id 說明修正（UUID4） | §4.4 |
| [C4] ERD 已含 sync_logs（原評為誤報） | §2.1 |
| [C5/C6] categories 加 `created_at`/`updated_at`；knowledge_items 加 `created_at` | §2.2 |
| [D1] audit_logs.diff JSONB 結構規範 | §2.2 |
| [D2/D3] Excel 匯入：一律 draft、category_path 自動建立、重複跳過 | §4.3 |
| [D4] action_reason `rejected` 時後端必填驗證 | §2.2 |
| [D5] `GET /health` 端點 + backend docker healthcheck | §4.0、§10.4 |
| [D6] `GET /api/v1/users` 列出帳號端點 | §6.2 |
| [D7] structlog 結構化日誌標準 | §16.5 |
| [D8] GET /faq/:id 回傳 `locked_by_username` | §4.2 |
| [D9] chat sender 格式改為 `{agent_id}_{user_id}` | §4.3 |
| [D10] nginx.conf 順序問題（計畫 §1 加 NOTE） | implementation_plan §第一階段 |
| [D11] `.txt` 可從 DB 重新觸發同步重建 | §19.2 |

完整修訂說明見規格書 §21。

---

## 七、開發指令（Commands）

**目前目錄尚無程式碼**，故 `pytest`、`vitest`、`docker compose up` 等指令均無法執行。

依規格書 §16（測試策略）與 §17（Migration 策略），實作完成後預計工具鏈如下，具體呼叫方式應於程式碼建立後在本檔補齊：

- 後端：`pytest`（含 `pytest-asyncio`、`pytest-cov`）、`ruff check`、`mypy`、`alembic upgrade head`、`alembic revision --autogenerate -m "..."`
- 前端：`vitest run`、`eslint`、`tsc --noEmit`、`vite build`、`vite dev`
- E2E：Playwright
- 容器化：`docker compose up --build`、`docker compose down -v`

---

## 八、文件與實作編輯守則

1. 修改 `comprehensive-system-design.md` 時，須同步檢視 `implementation_plan.md` 對應段落，避免兩份文件互相矛盾。
2. 規格章節編號（如 §1、§16、§20）為跨文件引用基準，新增 / 刪除章節時需更新所有交叉引用。
3. 中文排版遵循台灣繁體規範：中英文 / 半形數字之間保留半形空格；統一使用全形中文標點；不混用簡體字；技術名詞遵循官方拼寫（FastAPI、TypeScript、PostgreSQL）。
4. 規格書 §20 為「v0.2 廢止宣告」，不可在新內容中復用 v0.2 命名（如 `ingest_command`、`knowledge_items_history` 單數形）。
5. 開始第一階段實作前，建議先 `git init` 並建立 `.gitignore`，將 `.env`、`node_modules/`、`__pycache__/`、`data/volumes/` 加入排除。
