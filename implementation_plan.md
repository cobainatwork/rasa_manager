# Rasa 知識庫管理系統 - 實施計劃 (Implementation Plan)

## 實作狀態（2026-05 更新）

> [!NOTE]
> 全六階段已完成（含 Plan 3 Phase 0 ~ 20 收尾品質提升）。
>
> | 階段 | 狀態 |
> |------|------|
> | 第一階段：專案初始化與結構設定 | 完成 |
> | 第二階段：資料庫模型 + Alembic（head = 002） | 完成 |
> | 第三階段：後端核心 API（pytest 293 passed） | 完成 |
> | 第四階段：前端管理介面（vitest 全綠，含 a11y smoke） | 完成 |
> | 第五階段：匯入匯出 / 對話 / 同步補足 | 完成 |
> | 第六階段：Docker Compose 部署（5 服務 healthy） | 完成 |
>
> 後續維運以本檔之既有規範與 `comprehensive-system-design.md` v1.1 為依據。

---

## 背景描述 (Goal Description)
開發一套完整的 Rasa RAG 系統知識庫管理介面（FAQ）。該平台支援多 Rasa 代理專案（Multi-Agent），允許編輯員和審核員於獨立介面中執行常見的新增/刪除/修改 (CRUD) 以及類別樹狀繼承邏輯。資料經核准後，管理者可「一鍵觸發同步」，將存放於 PostgreSQL 的核准文本匯出成 `.txt` 並呼叫 CLI ingestion script 來實作 Qdrant 的自動同步。同時，平台需自帶版本紀錄（Audit Log/History）與前端直接與 Rasa Server 的對話驗證，最後透過 Docker Compose 完成前後端及任務調度器的一體化部署。

## 使用者審查項目 (User Review Required)
> [!IMPORTANT]
> - 本計畫書基於先前的架構文件（FastAPI + React/Vite + Celery + PostgreSQL）將任務分解為 6 個階段。
> - 第 5 階段的部署與整合，會使用本機 Docker Compose 自動架起前端、後端與 Celery worker。
> - 由於有「多 Rasa Agent」架構，登入後首頁將是「Agent 選擇器」，後續所有操作均受限於所選專案。
> - 具備**歷史版本拉回 (Rollback)**、**多人併發編輯鎖 (Concurrency Lock)** 及 **對話驗證 Endpoint** 等高階機能。

---

## 建議變更 (Proposed Changes)

這份計畫切分了全端專案結構的初始化到最後的容器化佈署，區分為六個主要實施階段。所有程式碼皆會實作於 `D:\mini_test` 下方。

### 第一階段：專案初始化與結構設定
建立基礎的專案檔案夾，確保所有前後端服務都在專屬目錄底下發展，且配備共用的 Docker Compose。
#### [NEW] `D:\mini_test\docker-compose.yml`
配置 `postgres`（含 volume 與初始化帳密）、`redis`（Celery 券商）、`backend`（FastAPI）、`celery_worker`（執行任務排程）及 `frontend`（Vite 建置靜態伺服或開發模式）。含 db/redis/backend 健康檢查（詳見規格書 §10.4）、`depends_on` 條件依賴、rasa_docs bind mount volume。**各服務須加入 `env_file: .env`（`backend`、`celery_worker`），確保容器讀取到環境變數（詳見規格書 §10.5）。`celery_worker` 啟動命令：`celery -A backend.tasks.celery_app worker --concurrency=2 --loglevel=info`（詳見規格書 §1.3）。**
#### [NEW] `D:\mini_test\backend\requirements.txt`
後端所需的 dependencies，如 `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `psycopg2-binary`, `celery`, `redis`, `passlib`, `python-jose`, `python-multipart` 及檔案處理套件。
#### [NEW] `D:\mini_test\frontend\package.json`
使用 `npm create vite@latest frontend -- --template react-ts` 初始化前端，引入狀態管理（Zustand）、UI 庫（Tailwind CSS + shadcn/ui）與 API 客戶端（Axios）。
#### [NEW] `D:\mini_test\frontend\vite.config.ts`
Vite 配置：API proxy（`/api` → **`http://localhost:8000`**，主機跑 `vite dev` 時目標為 localhost，不可用 `backend:8000`，詳見規格書 §8.4）、ESM 模組設定。
#### [NEW] `D:\mini_test\frontend\tailwind.config.js`
Tailwind CSS 配置：內容路徑、shadcn/ui 所需 plugins。
#### [NEW] `D:\mini_test\frontend\tsconfig.json`
TypeScript 配置：嚴格模式、路徑別名 `@/*` → `src/*`。
#### [NEW] `D:\mini_test\frontend\.eslintrc.cjs`
ESLint 配置：React + TypeScript rules、prettier 整合。
#### [NEW] `D:\mini_test\.env.example`
環境變數範本檔（不含實際密鑰），包含 `DATABASE_URL`、`JWT_SECRET`、`JWT_ACCESS_MINUTES`、`JWT_REFRESH_DAYS`、`REDIS_URL`、`CORS_ORIGIN`、`APP_HOST`、`APP_PORT`、`QDRANT_HOST`、`LOG_LEVEL`、`SEED_ADMIN_USERNAME`、`SEED_ADMIN_PASSWORD`（完整清單見規格書 §9.1）。
#### [NEW] `D:\mini_test\backend\Dockerfile`
基於 python:3.11-slim，安裝 requirements.txt，COPY source code，EXPOSE 8000，CMD uvicorn。
#### [NEW] `D:\mini_test\frontend\Dockerfile`
多階段建置：Stage 1 (node:18-alpine 執行 npm install + npm run build)，Stage 2 (nginx:alpine COPY dist + nginx.conf)。**注意**：`nginx.conf` 的完整內容在第六階段定義，建立此 Dockerfile 時需同步建立 `nginx.conf` 的基礎版本（或預留 placeholder），避免 build 失敗。
#### [NEW] `D:\mini_test\scripts\` (directory)
使用者將 ingestion scripts 放置於此目錄（如 `scripts/customer_service/ingest.py`），透過 docker-compose volume 掛載進入 Worker 容器（`./scripts:/opt/scripts:ro`）。Superadmin 在 Agent 設定中指定 `ingest_script_path` 為相對於 `./scripts/` 的路徑。

---

### 第二階段：資料庫模型建立與 Alembic 遷移 (Backend - Database)
建置 PostgreSQL 的實體模型與 Alembic 版本控制。
#### [NEW] `D:\mini_test\backend\api\database\models.py`
定義以下表格，支援多 Rasa 環境：
* `User` / `Agent` / `UserAgentRole` (權限映射)
* `Category`（樹狀分類節點，含 `created_at` / `updated_at`）
* `KnowledgeItem`（FAQ 條目，含鎖定欄位 `locked_by` / `locked_at` 及 `created_at`）
* `KnowledgeItemHistory`（存放歷史版本號以供 Rollback；`action = 'rejected'` 時 `action_reason` 必填）
* `AuditLog`（操作軌跡，`diff` 欄位格式：`{"field": {"before": ..., "after": ...}}`）與 `SyncLog`（同步紀錄）
#### [NEW] `D:\mini_test\backend\api\database\session.py`
建立 SQLAlchemy 的 Database URL、Engine 與 Session dependency。
#### [NEW] `D:\mini_test\backend\alembic.ini`
設定 Alembic 並產生 initial migrations，確保開發環境能隨時利用 `alembic upgrade head` 完成表格與關聯鎖建置。
#### [NEW] `D:\mini_test\backend\alembic\versions\001_initial.py`
初始 migration，建立 8 張核心資料表（users, agents, user_agent_roles, categories, knowledge_items, knowledge_item_histories, audit_logs, sync_logs）與全部索引（共 11 個索引，含部分索引 `idx_ki_locked_by`）。**注意**：`categories` 新增 `created_at` / `updated_at`；`knowledge_items` 新增 `created_at`；JWT 模型含 `jti` 欄位（不存 DB，由簽發邏輯產生，Redis 黑名單 key 格式：`revoked_refresh:{jti}`）。
#### [NEW] `D:\mini_test\backend\api\seed.py`
初始 Superadmin 建立腳本，支援兩種方式：
- 環境變數初始化：`SEED_ADMIN_USERNAME` + `SEED_ADMIN_PASSWORD`（僅在 users 表為空時執行）
- CLI 命令：`python -m api.seed --username admin --password secret123`
- 密碼驗證：最小 8 字元，需含大寫/小寫/數字
- Bcrypt cost factor = 12
#### [NEW] `D:\mini_test\backend\alembic\scripts\post_migration_seed.py`
Migration 完成後自動檢查並 seed 第一個 Superadmin（讀取環境變數）

---

### 第三階段：後端核心 API 開發 (Backend - API)
撰寫各項 CRUD 操作及背景邏輯。
#### [NEW] `D:\mini_test\backend\api\main.py`
FastAPI 應用入口：匯入所有 Router（auth、users、agents、categories、faq、chat、sync）、配置 CORS middleware、挂载 lifespan event（啟動時執行 seed 檢查）。
#### [NEW] `D:\mini_test\backend\api\dependencies.py`
實作 JWT Auth（HttpOnly Cookie 認證，Access/Refresh 雙 Token），以及「Agent 上下文」權限的攔截器（RBAC）。
- 包含 Rate Limiting：登入端點（同 IP 5 次失敗後鎖定 15 分鐘、同 IP 每分鐘最多 20 次請求）
- 登入帳密失敗次數追蹤（使用 Redis 計數器，key: `login_attempts:{ip}:{username}`，TTL 15 分鐘）
#### [NEW] `D:\mini_test\backend\api\routes\auth.py`
認證路由：`/login`、`/logout`、`/refresh`、`/me`。Cookie 設定：Secure, HttpOnly, SameSite=Strict。Access Token 15 分鐘、Refresh Token 7 天（含 `jti`）。`/logout` 與 `/refresh` 須將舊 refresh token `jti` 寫入 Redis 黑名單（Rotation + Revocation，詳見規格書 §6.1）。
#### [NEW] `D:\mini_test\backend\api\routes\users.py`
使用者管理路由（Superadmin 專用）：`GET /users`（帳號清單）、`POST /users`、`PATCH /users/{id}`、`PATCH /users/{id}/reset-password`。
#### [NEW] `D:\mini_test\backend\api\routes\agents.py`
建立 Agent 專案 CRUD、角色分配路由。`POST/GET/PUT/DELETE agents`、`GET single`、`GET stats`、`POST/DELETE roles`。Superadmin 建立/修改 Agent 配置（含 `txt_output_path`、`rasa_rest_url`、`ingest_script_path`）。
#### [NEW] `D:\mini_test\backend\api\routes\categories.py`
分類 CRUD：`GET`（CTE 遞迴查詢返回嵌套 JSON 樹）、`POST`（建立節點）、`PATCH`（改名/移動/排序）、`DELETE`（有 FAQ 關聯時回 422）。Reviewer/Superadmin 權限。
#### [NEW] `D:\mini_test\backend\api\routes\faq.py`
CRUD FAQ，包含：綁定類別、狀態切換、歷史紀錄退回 (Rollback)，鎖定 API `POST /lock`（取鎖）、`PUT /lock`（心跳延長，每 60 秒）、`DELETE /lock`（釋放）；GET 詳細需 JOIN users 回傳 `locked_by_username`；健康檢查路由 `GET /health`（不需認證）。
#### [NEW] `D:\mini_test\backend\api\routes\chat.py`
打通對話測試：接收前端字串，調度對應 `Agent` 之原生 `HTTP POST /webhooks/rest/webhook` API，sender 格式為 `{agent_id}_{user_id}`，即時返回 RAG 結果陣列。
#### [NEW] `D:\mini_test\backend\api\routes\sync.py`
API 端點呼叫 Celery 推入非同步任務；包含透過對應 agent_id 調用主機上的 Ingestion Command，並回傳運行狀態與 Log 供前端查看。
#### [NEW] `D:\mini_test\backend\tasks.py`
Celery 具體實作：提取已核准 (Approved + Synced) 資料，輸出正確格式寫入 **單一** `{agent.txt_output_path}/faq_export.txt`（直接使用 DB 欄位值，不拼接 agent_name），容器內執行 ingest script（`/opt/scripts/{ingest_script_path}`），捕獲 stdout/stderr 回寫至 `sync_logs` 表。同步成功後標記所有項為 `synced`。重試 3 次指數退避（10s/20s/40s），超時 300 秒，Worker 並發數 2。
#### [NEW] `D:\mini_test\backend\api\middleware\cors.py`
CORS 中間件設定，開發環境允許 `http://localhost:5173`，Production 可配。`credentials: true` 支援 Cookie 跨域。
#### [NEW] `D:\mini_test\backend\api\schemas.py`
Pydantic schema 定義，統一 API 回應格式 `{ success, data/message, error: { code, message } }`，含 HTTP Status Code 映射（200/201/400/401/403/404/409/422/500）。

---

### 第四階段：前端管理介面開發 (Frontend - UI)
以 React 建構知識本體管理介面，依權限封鎖功能按鈕。
#### [NEW] `D:\mini_test\frontend\src\App.tsx`
React Router v7 路由配置：掛載全部 10+ 路由至對應 Page 元件，含 ProtectedRoute 包裝。
#### [NEW] `D:\mini_test\frontend\src\pages\Dashboard.tsx`
Agent 儀表板頁面：統計卡片（待審核件數、已核准/已同步件數、今日新增）、各分類 FAQ 數量分佈圖表。
#### [NEW] `D:\mini_test\frontend\src\pages\Categories.tsx`
分類管理頁面：樹狀結構 UI、拖曳排序、新增/編輯/刪除節點（RecursiveTree 元件）。
#### [NEW] `D:\mini_test\frontend\src\pages\FaqDetail.tsx`
FAQ 詳細/編輯頁面（路由 `/agents/:id/faqs/:faq_id`）：獨立於清單頁，含編輯器、版本歷史列表、Rollback 操作。
#### [NEW] `D:\mini_test\frontend\src\api\client.ts`
Axios 設定檔：Base URL（空字串，走 Vite proxy）、`withCredentials: true` 全域設定、Request/Response 攔截器；401 自動 Refresh Token 重試需實作 **pending promise queue**（避免多個 401 同時觸發多次 refresh，詳見規格書 §8.5）；錯誤統一處理（映射至 `{ code, message }` 格式）。
#### [NEW] `D:\mini_test\frontend\src\store\useAuthStore.ts`
Zustand 認證狀態管理：使用者資訊、角色、當前 Agent context、登入/登出動作。
#### [NEW] `D:\mini_test\frontend\src\routes\ProtectedRoute.tsx`
受保護路由元件：檢查 JWT 是否有效、是否有該 Agent 權限，無權限則重定向至 `/login` 或 `/agents`。
#### [NEW] `D:\mini_test\frontend\src\pages\Login.tsx`
登入畫面（帳密表單），JWT 全部以 HttpOnly Cookie 儲存，前端不需本地管理 token。登入後重定向至 `/agents`。使用 React Hook Form + Zod 驗證表單。
#### [NEW] `D:\mini_test\frontend\src\pages\AgentSelect.tsx`
讓具有多專案權限的人選擇要進入的 Rasa 系統儀錶板。
#### [NEW] `D:\mini_test\frontend\src\pages\DashboardLayout.tsx`
專案核心層面：分為「文件分類」、「知識庫管理 (FAQ)」、「權限配置/軌跡追蹤」、「對話測試模擬器」與「TXT 一鍵匯入與歷史」。
#### [NEW] `D:\mini_test\frontend\src\pages\KnowledgeBase.tsx`
操作頁面，實施草稿撰寫、節點編輯。利用呼叫 `lock` 確保自己修改中不會被覆蓋，以及查詢歷史與「回復此版」。
#### [NEW] `D:\mini_test\frontend\src\pages\SyncPage.tsx`
同步管理頁面：觸發一鍵同步、顯示 sync_logs 記錄列表（轮詢每 3 秒更新任務狀態）、顯示 stdout/stderr 輸出。
#### [NEW] `D:\mini_test\frontend\src\pages\AuditLog.tsx`
軌跡追蹤頁面：查詢 audit_logs，支援按 Agent、操作類型、時間範圍過濾。
#### [NEW] `D:\mini_test\frontend\src\pages\AgentSettings.tsx`
Agent 設定頁面（Superadmin 專用）：修改 txt_output_path、rasa_rest_url、ingest_script_path。
#### [NEW] `D:\mini_test\frontend\src\pages\UserManagement.tsx`
使用者管理頁面（Superadmin 專用）：帳號列表、新增/停用帳號、重設密碼、角色分配。
#### [NEW] `D:\mini_test\frontend\src\components\FaqEditor.tsx`
FAQ 編輯器元件：含編輯鎖互動（自動 60 秒延長、導離自動釋放、10 分鐘逾時提示）、DOMPurify XSS 防護、版本歷史/Rollback UI。
#### [NEW] `D:\mini_test\frontend\src\pages\TestChat.tsx`
發送 HTTP POST 要求到 Agent 設定的對應 Rasa URL (`http://localhost:5005/webhooks/rest/webhook`) 來測試回應。

---

### 第五階段：Excel 匯入/匯出、前端補足頁面與系統對接
完善所有剩餘功能與頁面，確保與設計規格書完全對應。
#### [MODIFY] `D:\mini_test\backend\api\routes\faq.py`
新增 `/import` 與 `/export` 的 API，使用 `pandas` 與 `openpyxl` 開發批量解析與草稿條目的上架。
- 匯入欄位映射：Excel 需包含 `question`（必填）、`answer`（必填）、`category_path`（必填，以 / 分隔的路徑如「常見問題/帳號管理」）、`tags`（選填，逗號分隔）
- 錯誤處置：無效行跳過並記錄至結果報告，不中斷整批匯入
- 重複檢測：相同 question 已存在時標記為 skip
#### [MODIFY] `D:\mini_test\frontend\src\pages\KnowledgeBase.tsx`
前端整合「上傳 Excel」介面與拋出前端下載。
#### [NEW] `D:\mini_test\frontend\src\pages\ImportExport.tsx`
獨立匯入匯出頁面：Excel 上傳表單（含欄位驗證預覽）、批次匯入結果報告（成功/跳過/失敗行數）、匯出參數設定。
#### [NEW] `D:\mini_test\frontend\src\services\excelUtils.ts`
Excel 欄位驗證與 mapping 工具函數（含 Vitest 單元測試）。

---

### 第六階段：部署配置、備份策略與 CI/CD
#### [NEW] `D:\mini_test\.dockerignore`
排除 node_modules、__pycache__、.git、*.env 等不必要的 build 檔案。
#### [NEW] `D:\mini_test\frontend\nginx.conf`
Nginx 反向代理配置（生產環境）：root /usr/share/nginx/html、try_files 支援 SPA routing、/api 反向代理至 backend:8000。
#### [NEW] `D:\mini_test\.github\workflows\ci.yml`
GitHub Actions CI/CD pipeline：
- Trigger：push 到 main/develop, PR
- Steps：lint → type check（前端） → pytest（後端） → vitest（前端） → build docker images → health check
#### [NEW] `D:\mini_test\scripts\backup.sh`
後備本策略：每日 PostgreSQL dump（`pg_dump`），保留最近 7 天，透過 cron 或 docker compose schedule 執行。
#### [NEW] `D:\mini_test\scripts\restore.sh`
還原腳本：從備份檔案還原 PostgreSQL。

---

## 驗證計畫 (Verification Plan)

### Phase 完成定義 (Definition of Done)

| Phase | 完成標準 |
|-------|---------|
| 1 | `docker compose up --build` 成功啟動全部 5 個服務，健康檢查通過，無錯誤日誌 |
| 2 | `alembic upgrade head` 成功建立 8 張表 + 11 個索引，`python -m api.seed` 成功建立第一個 Superadmin |
| 3 | 所有 API endpoint 可透過 Swagger UI 測試，RBAC 權限矩陣驗證通過 |
| 4 | 前端 10+ 路由全部可存取，CRUD 流程完成走透 |
| 5 | Excel 匯入/匯出正確處理有效/無效資料，前端補足頁面完成 |
| 6 | CI pipeline 全部綠色，backup/restore 流程驗證通過 |

### 後端自動化測試
1. **認證測試** (`tests/test_auth.py`)：登入/登出、Token 過期、Rate Limiting（5 次失敗鎖定）
2. **RBAC 測試** (`tests/test_rbac.py`)：3 角色 × 11 權限全部驗證、編輯鎖競態/逾時
3. **Celery 測試** (`tests/test_tasks.py`)：Mock DB 驗證 txt 格式、sync_logs 正確記錄、重試/超時
4. **匯入/匯出測試** (`tests/test_import_export.py`)：欄位映射驗證、無效資料容錯、重複檢測
5. **Seed 測試** (`tests/test_seed.py`)：首次建立正確、二次執行跳過、密碼驗證

### 前端自動化測試
6. **組件測試** (`frontend/src/**/*.test.tsx`)：Vitest + React Testing Library
   - Login.tsx：表單驗證、錯誤處理
   - KnowledgeBase.tsx：CRUD 操作、編輯鎖 UI 狀態
   - Dashboard.tsx：統計數字渲染、過濾器
7. **E2E 測試** (`frontend/e2e/`)：Playwright
   - 完整流程：登入 → 選擇 Agent → 建立 FAQ → 送審 → 核准 → 同步
   - 多 Agent 隔離驗證

### 人工驗證檢查清單
| # | 檢查項目 | 預期輸入 | 預期結果 |
|---|---------|---------|---------|
| 1 | 前端登入 | 輸入 admin/密碼 | 登入成功，跳轉 /agents |
| 2 | Agent 選擇 | 點擊任一 Agent | 進入該 Agent 的 Dashboard |
| 3 | FAQ 完整流程 | 建立草稿 → 送審 → 核准 → 同步 | 各階段狀態正確更新，txt 檔案產生 |
| 4 | 多 Agent 隔離 | 在 Agent A 操作 | 無法看見 Agent B 的資料 |
| 5 | Excel 匯入 | 上傳含 10 條（2 條無效）的 xlsx | 8 成功、2 跳過，統計正確 |
| 6 | 對話測試 | 在 TestChat 發送訊息 | Rasa 回覆正確顯示 |
