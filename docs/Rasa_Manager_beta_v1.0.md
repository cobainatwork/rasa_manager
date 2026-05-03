# Rasa Manager Beta v1.0 — 完整專案說明文件

> **文件版本**：Rasa_Manager_beta_v1.0
> **最後更新**：2026-05-03
> **目標讀者**：接手本專案的工程師，可依本文件直接進行環境建置與功能開發
> **部署環境**：Linux（Ubuntu 22.04 LTS / Debian 12 推薦）；Windows 作為本機開發輔助環境

---

## 目錄

1. [專案概覽](#1-專案概覽)
2. [系統架構](#2-系統架構)
3. [功能列表](#3-功能列表)
4. [後端架構詳解](#4-後端架構詳解)
5. [前端架構詳解](#5-前端架構詳解)
6. [資料庫設計](#6-資料庫設計)
7. [Qdrant 向量庫整合](#7-qdrant-向量庫整合)
8. [環境建置——Linux 部署（正式環境）](#8-環境建置linux-部署正式環境)
9. [環境建置——Windows 本機開發](#9-環境建置windows-本機開發)
10. [實施計劃書](#10-實施計劃書)
11. [設計陷阱與已知坑](#11-設計陷阱與已知坑)
12. [API 快速參考](#12-api-快速參考)

---

## 1. 專案概覽

**Rasa Manager** 是一套多 Agent Rasa Enterprise Search（FAQ 模式）的知識庫管理平台。

### 1.1 核心用途

| 面向 | 說明 |
|------|------|
| 知識管理 | 以分類樹組織 FAQ，支援編輯、審核、版本回溯 |
| 多代理隔離 | 每個 Rasa Agent 的資料完全隔離，統一以 `agent_id` 分區 |
| 向量同步 | 審核通過的 FAQ 透過 Celery 非同步推送至 Qdrant |
| 權限管理 | Superadmin 全域控制；各 Agent 內分 `reviewer` / `editor` 二角色 |

### 1.2 技術棧一覽

| 層 | 技術 |
|----|------|
| 後端 API | Python 3.11、FastAPI 0.136、SQLAlchemy 2.0（同步） |
| 資料庫 | PostgreSQL 15 |
| 非同步任務 | Celery 5.6 + Redis 7（Broker） |
| 向量資料庫 | Qdrant（外部服務，獨立部署） |
| 前端 | React 18 + Vite + TypeScript 5 + Tailwind CSS 3 |
| UI 元件 | shadcn/ui（Radix UI 原語 + Tailwind） |
| 容器化 | Docker Compose（5 個服務） |
| 反向代理 | Nginx（含於 frontend 容器） |

---

## 2. 系統架構

### 2.1 Docker Compose 五服務架構

```
┌─────────────────────────────────────────────────────────┐
│  Docker Compose 網路                                     │
│                                                          │
│  ┌──────────┐       ┌────────────────┐                  │
│  │ frontend │──80──▶│ backend:8000   │                  │
│  │ :5173    │       │ FastAPI        │                  │
│  │ (nginx)  │       │ + uvicorn      │                  │
│  └──────────┘       └───────┬────────┘                  │
│                             │                           │
│               ┌─────────────┼─────────────┐            │
│               ▼             ▼             ▼            │
│           ┌───────┐   ┌─────────┐  ┌──────────────┐   │
│           │  db   │   │  redis  │  │celery_worker │   │
│           │ PG 15 │   │ Redis 7 │  │              │   │
│           └───────┘   └─────────┘  └──────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
            ▼                           ▼
       Rasa Server                   Qdrant
      (外部服務)                    (外部服務)
```

**網路隔離設計：**

- `app` 網路：`backend`、`celery_worker`、`frontend` 互通（前端到後端、後端到 Celery）
- `data` 網路（`internal: true`）：`db`、`redis`、`backend`、`celery_worker` 使用；外部無法直連 DB / Redis

### 2.2 請求流程

```
使用者瀏覽器
    │
    ▼
frontend:8080 (nginx)
    ├── /         → React SPA (本地 dist/)
    └── /api/ ──▶ backend:8000 (FastAPI)
                      │
                      ├── 查詢 → PostgreSQL
                      ├── 快取 → Redis
                      └── 推任務 → Redis Broker → celery_worker
                                                      │
                                          執行 ingest_kb.py
                                                      │
                                              寫入 Qdrant
```

### 2.3 非同步同步任務流程

```
POST /sync 或 /categories/{id}/sync
    │
    ▼
API 建立 SyncLog (status=pending)
    │
    ▼
推入 Redis Broker → Celery Task 執行
    │
    ├── 從 DB 查詢 approved/synced FAQ
    ├── 寫出 .txt（[Question]/[Answer] 格式）
    ├── 執行 ingest_kb.py（帶 --delete-category-paths 或 --clear）
    └── 更新 SyncLog (status=completed/failed)
            │
            ▼
前端輪詢 GET /sync/tasks/{id} 取得狀態
```

---

## 3. 功能列表

### 3.1 身分驗證與授權

| 功能 | 說明 |
|------|------|
| JWT 登入 | HttpOnly Cookie 儲存（Access 15 分鐘 / Refresh 7 天） |
| Refresh Token Rotation | 換發時撤銷舊 Token（Redis jti 黑名單） |
| 防爆破鎖定 | 同 IP + 帳號 5 次失敗 → 鎖定 15 分鐘（Redis 計數器） |
| 多層 RBAC | `is_superadmin` 全域 + 各 Agent 內 `reviewer` / `editor` |
| 自動 Token 刷新 | 前端 401 interceptor 自動換發，pending queue 防競態 |

### 3.2 知識庫管理（FAQ）

| 功能 | 說明 |
|------|------|
| FAQ CRUD | 建立、讀取、更新、刪除；支援 Question / Answer / Tags / Category |
| 狀態工作流 | `draft → pending → approved → synced`；含 `rejected` 退回 |
| Superadmin 直接核准 | Superadmin 建立的 FAQ 直接進入 `approved` 狀態 |
| 自動降級 | `approved` / `synced` FAQ 被編輯後自動降回 `draft` |
| 編輯鎖 | Lazy Expire 10 分鐘；取鎖、心跳延長、釋放；防 TOCTOU |
| 版本歷史 | 每次狀態轉移自動建立不可變歷史快照 |
| 版本回溯 | Rollback 至任意歷史版本（自動降回 `draft`） |
| 批次操作 | 批次送審、批次核准、批次刪除（含確認對話框） |
| 全選分頁 | 全選本頁 / 部分選取（indeterminate checkbox） |
| 多維篩選 | 依 status、category、關鍵字（防抖 300ms）篩選 + 分頁 |

### 3.3 分類管理

| 功能 | 說明 |
|------|------|
| 分類樹 | Adjacency List 自參照；最多兩層（root + children） |
| 新增 / 重新命名 / 刪除 | 含重新命名自動聚焦；有 FAQ 時拒絕刪除 |
| 匯入 FAQ（分類層） | append（保留現有）/ replace（先刪全部）兩種模式 |
| 匯出 FAQ（分類層） | 下載指定分類（含子孫）的 .xlsx |
| 分類獨立同步 | 觸發分類子樹精準向量替換，不影響其他分類資料 |

### 3.4 向量庫同步

| 功能 | 說明 |
|------|------|
| 全量同步 | 匯出全部 `approved`/`synced` FAQ → 清空並重建向量庫 |
| 分類精準同步 | 依 `category_path` metadata 精準刪除再寫入，範圍最小化 |
| 同步歷史 | 記錄每次同步的狀態、耗時、stdout/stderr |
| 任務輪詢 | 前端輪詢 task 狀態，顯示 running / completed / failed |

### 3.5 Excel 匯入匯出

| 功能 | 說明 |
|------|------|
| 全域匯入 | 拖放 .xlsx；自動依 `category_path` 欄建立分類樹；重複 Q 跳過 |
| 全域匯出 | 下載所有 FAQ 為 .xlsx（StreamingResponse，無記憶體壓力） |
| 分類匯入 | 對特定分類進行 append 或 replace 匯入 |
| 分類匯出 | 下載指定分類（含子孫）FAQ |
| 匯入結果回饋 | 成功筆數、跳過筆數、失敗列號 toast 通知 |

### 3.6 其他功能

| 功能 | 說明 |
|------|------|
| 儀表板 | FAQ 狀態統計 KPI、待辦事項、近期活動 |
| 稽核日誌 | 所有狀態轉移與重要操作記錄，支援多維篩選 |
| 測試對話 | 呼叫 Rasa REST Webhook，驗證向量化結果 |
| 使用者管理 | 新增帳號、重設密碼、指派 Agent 角色（Superadmin 限定） |
| Agent 設定 | 設定 `txt_output_path`、`rasa_rest_url`、`ingest_script_path` |
| 健康檢查 | `GET /api/v1/health` 回傳 DB + Redis 狀態（503 on error） |

---

## 4. 後端架構詳解

### 4.1 專案目錄結構

```
backend/
├── main.py                     # FastAPI 入口，路由掛載，CORS，健康檢查
├── tasks.py                    # Celery app 定義 + run_ingestion_sync + run_category_sync
├── entrypoint.sh               # 啟動序列：alembic migrate → seed → uvicorn
├── requirements.txt
├── Dockerfile
├── api/
│   ├── database/
│   │   ├── session.py          # SQLAlchemy engine、SessionLocal、get_db
│   │   └── models.py           # 8 個 ORM 模型
│   ├── routes/
│   │   ├── auth.py             # /auth/* (login, logout, refresh, me)
│   │   ├── users.py            # /users/* (Superadmin 限定)
│   │   ├── agents.py           # /agents/* (CRUD + roles + stats + admin)
│   │   ├── categories.py       # /agents/{id}/categories/*
│   │   ├── faqs.py             # /agents/{id}/faqs/*
│   │   ├── import_export.py    # /faqs/import + /faqs/export + /categories/{id}/import|export
│   │   ├── sync.py             # /sync + /categories/{id}/sync + /sync/history
│   │   ├── audit.py            # /audit-logs
│   │   └── chat.py             # /chat/test
│   ├── schemas.py              # 全部 Pydantic v2 schema（單檔）
│   ├── dependencies.py         # 依賴注入：get_db、get_current_user、require_superadmin 等
│   ├── security/
│   │   ├── jwt.py              # create_access_token、create_refresh_token、verify_token
│   │   └── password.py         # hash_password、verify_password（bcrypt cost=12）
│   ├── utils/
│   │   └── category_path.py    # build_category_path、collect_category_subtree
│   └── seed.py                 # Superadmin 初始建立（幂等）
└── alembic/
    ├── env.py                  # 從 DATABASE_URL 讀取連線
    ├── versions/
    │   ├── 001_initial.py      # 8 張表 + 13 個索引
    │   ├── 002_hardening.py    # constraint 補強
    │   └── 003_fix_history_fk.py  # history FK 修正
    └── alembic.ini
```

### 4.2 核心設計模式

#### 認證流程

```
POST /auth/login
  → 驗證帳密（bcrypt）
  → 檢查 Redis login_attempts:{ip}:{username}（≥5 → 429）
  → 建立 Access Token（15 分鐘，HS256）+ Refresh Token（7 天）
  → 寫入 HttpOnly Cookie（SameSite=Strict）
  → 清除 Redis 失敗計數器

POST /auth/refresh
  → 讀取 HttpOnly Cookie 的 Refresh Token
  → 驗證 Token 簽名與有效期
  → 檢查 Redis revoked_refresh:{jti} 黑名單
  → 舊 jti 加入黑名單（Rotation）
  → 發出新 Access + Refresh Token 對

POST /auth/logout
  → jti 加入 Redis 黑名單（TTL = 剩餘有效期）
  → 清除 Cookie
```

#### 角色依賴注入（dependencies.py）

```python
# 層層嵌套設計
get_db()                     # Session
get_current_user(db, token)  # 驗 JWT，查 DB 取 User
require_agent_access(user, agent_id, db)  # 驗使用者是否有此 Agent 的 role
require_editor(role)         # role in (editor, reviewer) + superadmin
require_reviewer(role)       # role == reviewer + superadmin
require_superadmin(user)     # user.is_superadmin
```

#### 編輯鎖機制（Lazy Expire）

```
GET /faqs/{id}
  → 若 locked_at < now - 10min，同 transaction 清除鎖欄位
  → 回傳 locked_by_username（可為 null）

POST /faqs/{id}/lock
  → with_for_update() 鎖定 row
  → 若已被他人鎖定且未逾時 → 409
  → 寫入 locked_by + locked_at

PUT /faqs/{id}/lock (心跳)
  → 更新 locked_at = now（延長 10 分鐘）
```

### 4.3 Celery 任務設定

```python
# tasks.py 關鍵設定
celery_app = Celery(
    broker=REDIS_URL,
    task_ignore_result=True,   # 狀態寫 sync_logs，不用 Celery backend
)

# 全量同步任務
@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    soft_time_limit=300,
)
def run_ingestion_sync(self, sync_log_id, agent_id): ...

# 分類精準同步任務
@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    soft_time_limit=300,
)
def run_category_sync(self, sync_log_id, agent_id, category_id): ...
```

**Subprocess 安全執行（禁止 shell=True）：**

```python
cmd = [sys.executable, script_path, "--source", txt_path, ...]
proc = subprocess.Popen(
    cmd,
    start_new_session=True,   # 建立新 process group 以便 SIGKILL 孫進程
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
try:
    stdout, stderr = proc.communicate(timeout=280)
except subprocess.TimeoutExpired:
    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
```

---

## 5. 前端架構詳解

### 5.1 專案目錄結構

```
frontend/
├── src/
│   ├── main.tsx                # React 入口，QueryClientProvider（若需）
│   ├── App.tsx                 # 路由設定（react-router-dom v6）
│   ├── components/
│   │   ├── AppShell.tsx        # 主殼層：sidebar + header + outlet
│   │   ├── EmptyState.tsx
│   │   ├── ProtectedRoute.tsx  # 需登入
│   │   ├── AdminRoute.tsx      # 需 Superadmin
│   │   └── ui/                 # shadcn/ui 元件（button, input, checkbox...)
│   ├── features/
│   │   ├── auth/               # 登入頁、PasswordInput
│   │   ├── agents/             # Agent 選擇頁、設定頁
│   │   ├── dashboard/          # KPI、待辦、活動
│   │   ├── knowledge/          # 分類樹 + FAQ 列表 + FAQ 詳情
│   │   ├── sync/               # 同步觸發 + 歷史
│   │   ├── import-export/      # 拖放上傳 + 匯出
│   │   ├── audit/              # 稽核日誌
│   │   ├── chat/               # 測試對話
│   │   └── users/              # 使用者管理
│   ├── api/
│   │   ├── client.ts           # Axios instance、interceptors
│   │   ├── request.ts          # unwrap 工具（解包 {success, data}）
│   │   └── endpoints/
│   │       ├── auth.ts
│   │       ├── agents.ts
│   │       ├── categories.ts
│   │       ├── faqs.ts
│   │       ├── sync.ts
│   │       ├── audit.ts
│   │       └── users.ts
│   ├── store/
│   │   ├── useAuthStore.ts     # Zustand：user、login、logout、fetchMe
│   │   ├── useAgentContext.ts  # Zustand + persist：currentAgent
│   │   └── useUiPreferences.ts # Zustand + persist：sidebar、panel width
│   ├── hooks/
│   │   └── useDebounce.ts      # 300ms 防抖
│   └── lib/
│       └── utils.ts            # cn()（clsx + tailwind-merge）
├── tailwind.config.ts          # 品牌色票 + shadcn HSL 色票
├── vite.config.ts              # proxy /api → localhost:8000
├── nginx.conf                  # 生產反向代理設定
└── Dockerfile                  # 多階段 build（node:20 → nginx-unprivileged:alpine）
```

### 5.2 前端路由

| 路徑 | 元件 | 權限 |
|------|------|------|
| `/login` | `LoginPage` | 公開 |
| `/agents` | `AgentSelectPage` | 需登入 |
| `/admin/users` | `UserManagementPage` | 需 Superadmin |
| `/agents/:id/dashboard` | `DashboardPage` | 需登入 + 該 Agent 角色 |
| `/agents/:id/knowledge` | `KnowledgePage` | 需登入 + 該 Agent 角色 |
| `/agents/:id/sync` | `SyncPage` | 需登入 + 該 Agent 角色 |
| `/agents/:id/import-export` | `ImportExportPage` | 需登入 + 該 Agent 角色 |
| `/agents/:id/test-chat` | `TestChatPage` | 需登入 + 該 Agent 角色 |
| `/agents/:id/audit` | `AuditPage` | 需登入 + 該 Agent 角色 |
| `/agents/:id/settings` | `AgentSettingsPage` | 需 Superadmin |

### 5.3 狀態管理架構

```
┌──────────────────────────────────────────┐
│           Zustand Stores                  │
│                                          │
│  useAuthStore          useAgentContext   │
│  ├── user              ├── currentAgent  │
│  ├── isLoading         └── (persist)     │
│  ├── login()                             │
│  ├── logout()          useUiPreferences  │
│  └── fetchMe()         ├── sidebarOpen  │
│                         └── panelWidth  │
└──────────────────────────────────────────┘

各 Feature Hook（Local React State + useEffect + API calls）
  useCategoryTree    useFaqList      useFaqDetail
  useFaqFilter       useSyncTrigger  useSyncHistory
  useAuditLog        useChat         useUserManagement
```

### 5.4 API 層 401 自動刷新

```typescript
// client.ts 核心邏輯
let refreshPromise: Promise<void> | null = null

axiosInstance.interceptors.response.use(null, async (error) => {
  if (error.response?.status !== 401) throw error
  if (isAuthEndpoint(error.config.url)) throw error  // /login, /refresh 不重試

  if (!refreshPromise) {
    refreshPromise = authApi.refresh().finally(() => (refreshPromise = null))
  }

  await refreshPromise           // 多個並發請求共用同一個 refresh
  return axiosInstance(error.config)  // 重送原始請求
})
```

### 5.5 KnowledgePage 高度鏈（react-resizable-panels）

**關鍵限制**：react-resizable-panels v4 的 `className` prop 套用在 inner wrapper 元素，`[&>div]:h-full` 這種父選擇器無效，必須直接設定。

```tsx
// KnowledgePage.tsx 正確寫法
<ResizablePanelGroup direction="horizontal" className="h-full">
  <ResizablePanel className="h-full !overflow-hidden">
    {/* 內容元件需自帶 h-full */}
  </ResizablePanel>
</ResizablePanelGroup>

// AppShell.tsx 需建立完整高度繼承鏈
<div className="h-screen overflow-hidden flex flex-col">
  <header />
  <main className="flex-1 overflow-hidden">
    <Outlet />  {/* 子頁面 h-full 才有效 */}
  </main>
</div>
```

---

## 6. 資料庫設計

### 6.1 資料表關係圖（ERD 文字版）

```
users ──┬── user_agent_roles ── agents ──┬── categories (自參照)
        │                                │
        ├── knowledge_items (locked_by)  ├── knowledge_items
        │                                │
        ├── knowledge_item_histories     ├── audit_logs
        │   (saved_by)                   │
        └── audit_logs (performed_by)   └── sync_logs (triggered_by)
```

### 6.2 資料表說明

| 資料表 | 主鍵 | 說明 |
|--------|------|------|
| `users` | UUID | `is_superadmin`、`is_active` 旗標；`username` 全域唯一 |
| `agents` | UUID | `txt_output_path`（UUID 子目錄）、`ingest_script_path`（相對 ./scripts/）；`name` 唯一 |
| `user_agent_roles` | (user_id, agent_id) | `role` ENUM（reviewer / editor）；Composite PK |
| `categories` | UUID | `parent_id` 自參照；含 uq_cat_agent_parent_name 防同層重名 |
| `knowledge_items` | UUID | `status` ENUM（draft/pending/approved/rejected/synced）；`locked_by` + `locked_at` 編輯鎖 |
| `knowledge_item_histories` | UUID | Immutable；`item_id ON DELETE SET NULL`（刪主條目後保留歷史） |
| `audit_logs` | UUID | `diff` JSONB（`{before: {...}, after: {...}}`）；`item_id ON DELETE SET NULL` |
| `sync_logs` | UUID | `status` ENUM（pending/running/completed/failed）；含 stdout/stderr 欄位 |

### 6.3 索引清單（13 個）

| 索引名 | 資料表 | 欄位 | 說明 |
|--------|--------|------|------|
| `idx_ki_agent_id` | knowledge_items | agent_id | 主要過濾條件 |
| `idx_ki_status` | knowledge_items | status | 狀態篩選 |
| `idx_ki_category_id` | knowledge_items | category_id | 分類篩選 |
| `idx_ki_locked_by` | knowledge_items | locked_by | Partial（IS NOT NULL） |
| `idx_cat_agent_id` | categories | agent_id | - |
| `idx_cat_parent_id` | categories | parent_id | 分類樹查詢 |
| `idx_al_agent_id` | audit_logs | agent_id | - |
| `idx_al_item_id` | audit_logs | item_id | - |
| `idx_al_created_at` | audit_logs | created_at DESC | 最新優先排序 |
| `idx_sl_agent_id` | sync_logs | agent_id | - |
| `idx_sl_started_at` | sync_logs | started_at DESC | 最新優先排序 |
| `idx_uar_user_id` | user_agent_roles | user_id | - |
| `idx_uar_agent_id` | user_agent_roles | agent_id | - |

### 6.4 FAQ 狀態機

```
                  ┌──────────────────────────────┐
                  │         (Superadmin 直接核准)  │
                  ▼                              │
  建立 ──▶ draft ──▶ pending ──▶ approved ──▶ synced
                      │             │
                      ▼             ▼
                  rejected ◀──── rejected
                  (可重新提交)

狀態轉移規則：
  Editor   可做：draft → pending（submit）
  Reviewer 可做：pending → approved（approve）、pending → rejected（reject）
                approved → rejected（unapprove）
  Superadmin 可做：任意轉移（含直接 draft → approved）
  編輯 approved/synced 時：自動降回 draft
  sync 完成時：approved → synced（Celery 任務執行）
```

---

## 7. Qdrant 向量庫整合

### 7.1 整體設計

Qdrant 為**外部服務**，不納入 Docker Compose。`ingest_kb.py` 腳本負責所有 Qdrant 操作，由 Celery Worker 在容器內執行。

### 7.2 向量寫入格式

每個 FAQ 以以下格式寫入 Qdrant：

```json
{
  "id": "uuid5(NAMESPACE_DNS, '{source}|{question}')",
  "vector": "[text-embedding-3-small 向量]",
  "payload": {
    "doc_id": "knowledgebase_v1",
    "question": "...",
    "answer": "...",
    "category_path": "根分類/子分類",
    "agent_id": "...",
    "status": "approved"
  }
}
```

**向量 ID 以 `uuid5` 計算**，相同問題重跑為 Upsert，不重複寫入。

### 7.3 刪除策略

| 場景 | 參數 | 刪除範圍 |
|------|------|---------|
| 全量同步 | `--clear` | 清空整個 collection |
| 分類精準同步 | `--delete-category-paths 根分類/子分類` | 只刪 `category_path` 相符的向量 |
| 自動偵測 | 無 `--clear`，有 `[Category]` 區塊 | 同分類精準同步 |

### 7.4 .txt 格式規範

**全量同步 .txt 格式（一個 FAQ）：**

```
[Question]
問題文字

[Answer]
回答文字

```

**分類同步 .txt 格式（含 Category 標頭）：**

```
[Category]
根分類/子分類

[Question]
問題文字

[Answer]
回答文字

```

**保留字元轉換**：若 Question/Answer 內容包含 `[Question]`、`[Answer]`、`[Category]`，自動改寫為全形 `【Question】`、`【Answer】`、`【Category】`，防止解析衝突。

### 7.5 ingest_kb.py CLI 參數

```bash
python ingest_kb.py \
  --source /path/to/faq_export.txt \
  --qdrant-url http://qdrant-host:6333 \
  --collection rasa_demo \
  --doc-id knowledgebase_v1 \
  [--clear]                               # 全量同步用
  [--delete-category-paths "路徑1,路徑2"]  # 分類同步用
```

---

## 8. 環境建置——Linux 部署（正式環境）

> 本節以 **Ubuntu 22.04 LTS** 為範例，Debian 12 同理。

### 8.1 前置需求

```bash
# Docker Engine 安裝（官方安裝法）
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Docker Compose Plugin（已含於新版 Docker Engine）
docker compose version  # 確認版本 >= 2.20

# Git
sudo apt install -y git
```

### 8.2 取得原始碼

```bash
git clone <your-repo-url> /opt/rasa-manager
cd /opt/rasa-manager
```

### 8.3 設定環境變數

```bash
cp .env.example .env
nano .env  # 填入以下必填欄位
```

**必填環境變數說明：**

```dotenv
# 資料庫
POSTGRES_USER=rasa_admin
POSTGRES_PASSWORD=<強密碼，至少 20 字元>
POSTGRES_DB=rasa_knowledge
DATABASE_URL=postgresql+psycopg2://rasa_admin:<密碼>@db:5432/rasa_knowledge

# JWT 密鑰（必須 64 字元以上，使用以下指令生成）
# openssl rand -hex 64
JWT_SECRET=<64 字元以上隨機字串>
JWT_ACCESS_MINUTES=15
JWT_REFRESH_DAYS=7

# Redis
REDIS_PASSWORD=<強密碼>
REDIS_URL=redis://:<密碼>@redis:6379/0

# 路徑映射（Linux 部署）
PROJECT_ROOT=/opt/rasa-manager
TXT_OUTPUT_HOST_PATH=/opt/rasa-docs      # .txt 輸出目錄（主機）
TXT_OUTPUT_CONTAINER_PATH=/opt/rasa-docs # 容器內映射路徑（保持一致）

# 向量庫
QDRANT_URL=http://<qdrant-server-ip>:6333
OPENAI_API_KEY=sk-...

# CORS（生產環境填正式域名）
CORS_ORIGIN=https://your-domain.com

# 初始 Superadmin
SEED_ADMIN_USERNAME=admin
SEED_ADMIN_PASSWORD=<需含大寫+小寫+數字，至少 8 字元>

# 日誌
LOG_LEVEL=INFO
```

### 8.4 建立必要目錄

```bash
# .txt 輸出目錄（需與 TXT_OUTPUT_HOST_PATH 一致）
sudo mkdir -p /opt/rasa-docs
sudo chown $USER:$USER /opt/rasa-docs

# ingest scripts 目錄（掛載至 celery_worker）
mkdir -p /opt/rasa-manager/scripts
# 將 ingest_kb.py 放入此目錄
cp ingest_kb.py /opt/rasa-manager/scripts/
```

### 8.5 啟動服務

```bash
cd /opt/rasa-manager

# 首次建置並啟動（含 migration + seed）
docker compose up --build -d

# 確認所有服務健康
docker compose ps
```

**預期輸出（所有服務 Status 為 healthy）：**

```
NAME                       STATUS
rasa_rag-db-1              healthy
rasa_rag-redis-1           healthy
rasa_rag-backend-1         healthy
rasa_rag-celery_worker-1   running
rasa_rag-frontend-1        healthy
```

**容器啟動順序（depends_on）：**

```
db & redis（healthy）→ backend（healthy）→ celery_worker & frontend
```

後端啟動時自動執行：
1. `alembic upgrade head`（建立/更新 schema）
2. `python -m api.seed`（建立 Superadmin，幂等）
3. `uvicorn main:app --host 0.0.0.0 --port 8000`

### 8.6 驗收檢查

```bash
# 健康檢查
curl http://localhost:8000/api/v1/health
# 預期：{"status":"ok","db":"ok","redis":"ok"}

# 前端存取（本機瀏覽器）
curl http://localhost:5173

# 確認資料表已建立
docker compose exec db psql -U rasa_admin -d rasa_knowledge -c "\dt"
# 應看到 8 張資料表

# 確認索引
docker compose exec db psql -U rasa_admin -d rasa_knowledge -c "\di"
# 應看到 13 個自訂索引

# Superadmin seed 幂等性驗證
docker compose exec backend python -m api.seed
# 應顯示：[seed] users 表已有 1 筆資料，跳過 seed
```

### 8.7 Nginx 反向代理（可選，對外暴露）

若需在 Linux 主機前加一層 Nginx 做 SSL termination：

```nginx
# /etc/nginx/sites-available/rasa-manager
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate     /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass         http://127.0.0.1:5173;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}
```

更新 `.env` 中的 `CORS_ORIGIN=https://your-domain.com`，重啟 backend 服務：

```bash
docker compose restart backend
```

### 8.8 日常運維指令

```bash
# 查看所有服務日誌
docker compose logs -f

# 查看特定服務日誌
docker compose logs -f backend
docker compose logs -f celery_worker

# 重啟單一服務
docker compose restart backend

# 更新程式碼並重新部署
git pull
docker compose up --build -d

# 停止並清除 volumes（危險！會清除 DB 資料）
docker compose down -v

# 備份 PostgreSQL
docker compose exec db pg_dump -U rasa_admin rasa_knowledge > backup_$(date +%Y%m%d).sql
```

---

## 9. 環境建置——Windows 本機開發

> Windows 主要用於本機開發與測試，不建議作為生產環境。

### 9.1 前置需求

| 工具 | 版本 | 說明 |
|------|------|------|
| Docker Desktop | 4.x | 啟用 WSL2 Backend |
| Node.js | 20 LTS | 前端開發 |
| Python | 3.11 | 後端開發（選用，可直接用容器） |
| Git | latest | 版控 |

### 9.2 路徑注意事項（Windows 特有）

`.env` 中路徑需使用 Windows 格式：

```dotenv
PROJECT_ROOT=.
TXT_OUTPUT_HOST_PATH=D:/rasa-docs   # 注意：正斜線，含磁碟機代號
TXT_OUTPUT_CONTAINER_PATH=/opt/rasa-docs
```

Docker Desktop 會自動將 `D:/rasa-docs` 映射至容器的 `/opt/rasa-docs`。

### 9.3 前端開發

```powershell
cd D:\mini_test\frontend
npm install
npm run dev      # http://localhost:5173（proxy /api → localhost:8000）
npm run lint
npx tsc --noEmit
```

### 9.4 後端開發（搭配 Docker 資料庫）

```powershell
# 只啟動 DB 與 Redis（不需完整 compose）
docker compose up db redis -d

# 本機安裝依賴
cd D:\mini_test\backend
pip install -r requirements.txt

# 跑 migration
$env:DATABASE_URL="postgresql+psycopg2://rasa_admin:pass@localhost:5432/rasa_knowledge"
alembic upgrade head

# 啟動後端
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 9.5 完整 Docker 模式（Windows）

```powershell
cd D:\mini_test
docker compose up --build -d
```

**注意**：`entrypoint.sh` 需以 LF 換行儲存，不可為 CRLF。確認方式：

```powershell
# 確認換行符
(Get-Content -Raw .\backend\entrypoint.sh) -match "`r" && "CRLF（需修正）" || "LF（正確）"
```

若為 CRLF，在 `.gitattributes` 加入：

```
backend/entrypoint.sh text eol=lf
```

---

## 10. 實施計劃書

> 以下為六個開發階段，每階段均包含可驗收的輸出。

### 第一階段：基礎設施建置（已完成）

**目標**：Docker Compose 五服務可啟動，健康檢查通過

| 工作項目 | 說明 |
|---------|------|
| docker-compose.yml | 定義 5 服務、2 網路、volumes |
| .env.example | 完整環境變數範本 |
| backend/Dockerfile | python:3.11-slim，tini PID 1 |
| frontend/Dockerfile | node:20 多階段 build → nginx-unprivileged |
| nginx.conf | SPA fallback + /api/ 反代 |
| entrypoint.sh | migrate → seed → uvicorn 序列 |

**驗收**：`docker compose ps` 全部 healthy，`GET /api/v1/health` 回 200

---

### 第二階段：資料庫模型與 Migration（已完成）

**目標**：8 張資料表 + 13 索引 + Superadmin seed

| 工作項目 | 說明 |
|---------|------|
| models.py | 8 個 ORM 模型（含 ENUM、關聯、索引） |
| 001_initial.py | 初始 migration |
| 002_hardening.py | constraint 補強 |
| 003_fix_history_fk.py | history FK 修正 |
| seed.py | 幂等建立 Superadmin |

**驗收**：`\dt` 顯示 8 張表、`\di` 顯示 13 個自訂索引

---

### 第三階段：後端 API 開發（已完成）

**目標**：全部 API 端點實作完成，pytest 通過

| 工作項目 | 端點數 |
|---------|--------|
| auth 模組 | 4 個端點 |
| users 模組 | 4 個端點 |
| agents 模組 | 9 個端點 |
| categories 模組 | 4 個端點 |
| faqs 模組 | 11 個端點 |
| import_export 模組 | 4 個端點 |
| sync 模組 | 4 個端點 |
| audit 模組 | 1 個端點 |
| chat 模組 | 1 個端點 |

**基線**：293 個 pytest 通過

---

### 第四階段：前端基礎框架（已完成）

**目標**：路由、認證、狀態管理、AppShell、API 層完成

| 工作項目 | 說明 |
|---------|------|
| 路由設定 | react-router-dom v6，ProtectedRoute + AdminRoute |
| Zustand stores | useAuthStore、useAgentContext、useUiPreferences |
| API 客戶端 | Axios instance + 401 refresh interceptor（pending queue） |
| AppShell | h-screen 高度繼承鏈、ResizablePanel 正確套用 |
| tailwind.config.ts | 品牌色 + shadcn HSL 色票 |

---

### 第五階段：前端功能模組（已完成）

**目標**：全部 Feature 頁面完成，與後端 API 整合

| Feature | 關鍵挑戰 |
|---------|---------|
| knowledge | ResizablePanel 高度鏈、Checkbox indeterminate、分類選單 z-index |
| sync | 任務輪詢、分類精準同步入口 |
| import-export | react-dropzone、StreamingResponse 下載 |
| audit | 多維篩選、稽核項目展開 |
| chat | Rasa REST Webhook 串接 |
| users | 多 Agent 角色管理 |

---

### 第六階段：向量庫整合（已完成）

**目標**：ingest_kb.py 實作完成，全量同步與分類精準同步均可運作

| 工作項目 | 說明 |
|---------|------|
| ingest_kb.py | `--clear`、`--delete-category-paths`、upsert 策略 |
| run_ingestion_sync Celery task | 全量同步 |
| run_category_sync Celery task | 分類精準同步 |
| category_path.py | `build_category_path`、`collect_category_subtree` |

---

### 後續待開發功能（Backlog）

| 優先級 | 功能 |
|--------|------|
| 高 | 前端 FAQ 搜尋結果高亮 |
| 高 | 同步進度 WebSocket 推送（取代輪詢） |
| 中 | 分類多選批次移動 FAQ |
| 中 | Excel 匯出加入更多欄位（tags、status、histories） |
| 低 | 深色模式完整支援 |
| 低 | Playwright E2E 測試補齊 |

---

## 11. 設計陷阱與已知坑

> 以下是開發過程中遭遇的真實問題，接手人員務必閱讀。

### 坑 1：react-resizable-panels className 套用層級

**問題**：在 `ResizablePanel` 加 `[&>div]:h-full` 無效，高度不繼承。

**根因**：`className` prop 被套在 inner wrapper 元素本身，`[&>div]` 選到的是 inner wrapper 的子元素，不是意圖元素。

**正確做法**：

```tsx
// 錯誤
<ResizablePanel className="[&>div]:h-full">

// 正確：直接在 inner wrapper 套 h-full + !overflow-hidden
<ResizablePanel className="h-full !overflow-hidden">
```

AppShell 也必須建立完整高度鏈：`h-screen → flex-1 overflow-hidden → Outlet`，中間任何一層若缺少 `overflow-hidden`，高度就會穿透到頁面外，出現雙捲軸。

---

### 坑 2：shadcn/ui 色票未定義導致透明背景

**問題**：Dropdown Menu、Popover、Command 元件背景透明，下方內容透出。

**根因**：shadcn/ui 元件使用 `bg-popover`、`bg-muted`、`bg-accent` 等 token，需在 `tailwind.config.ts` 透過 CSS 變數定義，否則 Tailwind 不認識這些 class，輸出為空（等同透明）。

**正確做法**：在 `tailwind.config.ts` 加入：

```typescript
colors: {
  popover: { DEFAULT: 'hsl(var(--popover))', foreground: 'hsl(var(--popover-foreground))' },
  muted:   { DEFAULT: 'hsl(var(--muted))',   foreground: 'hsl(var(--muted-foreground))' },
  accent:  { DEFAULT: 'hsl(var(--accent))',  foreground: 'hsl(var(--accent-foreground))' },
  // ... 其他 shadcn 色票
}
```

---

### 坑 3：Radix UI Checkbox indeterminate 視覺狀態

**問題**：`checked='indeterminate'` 時外框顏色有變，但內部圖示仍顯示勾勾（Check），視覺無法區分「全選」與「部分選取」。

**根因**：原始 `checkbox.tsx` 只用 `<Check />`，未針對 indeterminate 狀態切換圖示；且缺少 `data-[state=indeterminate]:bg-primary` class。

**正確做法**：

```tsx
// checkbox.tsx
<CheckboxPrimitive.Indicator>
  {checked === 'indeterminate'
    ? <Minus className="h-3 w-3" />
    : <Check className="h-4 w-4" />
  }
</CheckboxPrimitive.Indicator>
// className 加上：
"data-[state=indeterminate]:bg-primary data-[state=indeterminate]:text-primary-foreground"
```

---

### 坑 4：全選 Checkbox 與個別行 Checkbox 互相干擾

**問題**：勾選個別行時，頂部全選 Checkbox 也跟著被選起；或反之。

**根因**：`pageIds` 與 `pageCheckedCount` 每次 render 都重算，但 `data` 物件參考在每次 API 回傳後都是新物件，導致不必要的重算引發非預期狀態更新。

**正確做法**：

```typescript
// FaqList.tsx
const pageIds = useMemo(() => data?.items.map((f) => f.id) ?? [], [data])
const pageCheckedCount = useMemo(
  () => pageIds.filter((id) => checked.has(id)).length,
  [pageIds, checked],
)
```

---

### 坑 5：Blob URL 競態（下載失效）

**問題**：匯出下載偶爾失敗，瀏覽器提示 URL 無效。

**根因**：`URL.revokeObjectURL(url)` 在 `a.click()` 之後**同步**執行，瀏覽器尚未完成非同步下載即撤銷 Blob URL。

**正確做法**：

```typescript
a.click()
setTimeout(() => URL.revokeObjectURL(url), 100)  // 延遲 100ms
```

---

### 坑 6：Radix DropdownMenu submenu 動畫與原生檔案對話框衝突

**問題**：點「匯入 FAQ」子選單項目後，系統檔案對話框無法開啟（Chromium）。

**根因**：Radix submenu 關閉動畫尚未結束前，Chromium 攔截 user gesture，導致 `input[type=file].click()` 失效。

**正確做法**：

```typescript
function triggerFileImport(mode: 'append' | 'replace') {
  pendingImportMode.current = mode
  setTimeout(() => fileInputRef.current?.click(), 0)  // 讓動畫完成後再觸發
}
```

---

### 坑 7：Alembic ENUM 型態重複建立

**問題**：`alembic autogenerate` 有時在已有 ENUM 的情況下再次嘗試 `CREATE TYPE`，導致 migration 失敗。

**正確做法**：

1. Migration 頂端手動 `op.execute("CREATE TYPE ... AS ENUM (...)")`
2. Column 定義使用 `create_type=False`：

```python
sa.Column("role", sa.Enum("reviewer", "editor", name="user_agent_role", create_type=False))
```

---

### 坑 8：entrypoint.sh CRLF 換行符（Windows 開發環境特有）

**問題**：在 Windows 上編輯後的 `entrypoint.sh` 若儲存為 CRLF，Docker 容器（Linux）執行時報 `/bin/bash^M: bad interpreter`。

**解法**：在 `.gitattributes` 強制 LF：

```
backend/entrypoint.sh text eol=lf
*.sh text eol=lf
```

---

### 坑 9：前端翻頁時 checked Set 殘留

**問題**：在第 1 頁勾選幾筆後翻至第 2 頁，批次操作列仍顯示舊的勾選數。

**正確做法**：

```typescript
// FaqList.tsx
useEffect(() => { setChecked(new Set()) }, [filters.page])
```

---

### 坑 10：categories 同層重名衝突

**問題**：快速雙擊「新增子分類」會建立兩個名稱碰撞的分類，後端回 409。

**根因**：DB 層有 `uq_cat_agent_parent_name` unique constraint。

**前端對策**：預設名稱加入毫秒 timestamp + 4 位亂數後綴，降低碰撞機率：

```typescript
const suffix = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`
const name = `新分類_${suffix}`
```

即使碰撞，後端 409 時前端 toast.error 顯示友善訊息。

---

### 坑 11：Celery Worker 路徑映射（Linux vs. Windows）

**問題**：`ingest_script_path` 在容器內是相對於 `/opt/scripts/`，但 Agent 設定儲存的路徑必須和容器內路徑一致。

**規則**：
- `ingest_script_path` 儲存相對路徑（如 `ingest_kb.py`）
- Worker 在執行時拼接為 `/opt/scripts/ingest_kb.py`
- 主機的 `./scripts/` 目錄以 `:ro` bind mount 至 `/opt/scripts/`

**Linux 部署**：`scripts/` 目錄位於 `PROJECT_ROOT/scripts/`，需確保 `docker-compose.yml` 的 volume 映射正確。

---

### 坑 12：`updated_at` onupdate 在 Alembic autogenerate 的盲點

**問題**：`Column(DateTime, onupdate=func.now())` 是 ORM 層的 Python 觸發，Alembic autogenerate 偵測不到，不會自動產生 migration。

**影響**：若手動更新 DB 記錄（非透過 ORM），`updated_at` 不會自動更新。

**解法**：
1. migration 中手動加 `server_onupdate=FetchedValue()` 或 PostgreSQL trigger
2. 所有更新一律透過 ORM（目前實作方式，符合此設計）

---

## 12. API 快速參考

### 12.1 認證

所有需認證的端點：Cookie 已自動帶 `access_token`（HttpOnly，瀏覽器自動附帶）

### 12.2 端點速查表

**Auth**

| Method | Path | 說明 |
|--------|------|------|
| POST | `/api/v1/auth/login` | 帳密登入 |
| POST | `/api/v1/auth/logout` | 登出 |
| POST | `/api/v1/auth/refresh` | 換發 Token |
| GET | `/api/v1/auth/me` | 取得目前使用者 |

**Agents**

| Method | Path | 說明 |
|--------|------|------|
| GET | `/api/v1/agents` | 列出可存取 Agent |
| POST | `/api/v1/agents` | 建立 Agent（Superadmin） |
| PATCH | `/api/v1/agents/{id}` | 更新 Agent（Superadmin） |
| GET | `/api/v1/agents/{id}/stats` | FAQ 統計 |
| POST | `/api/v1/agents/{id}/roles` | 指派角色（Superadmin） |

**Categories**

| Method | Path | 說明 |
|--------|------|------|
| GET | `/api/v1/agents/{id}/categories` | 取得分類樹（巢狀） |
| POST | `/api/v1/agents/{id}/categories` | 建立分類 |
| PATCH | `/api/v1/agents/{id}/categories/{cat_id}` | 更新分類 |
| DELETE | `/api/v1/agents/{id}/categories/{cat_id}` | 刪除分類 |
| GET | `/api/v1/agents/{id}/categories/{cat_id}/export` | 匯出分類 FAQ |
| POST | `/api/v1/agents/{id}/categories/{cat_id}/import` | 匯入分類 FAQ |
| POST | `/api/v1/agents/{id}/categories/{cat_id}/sync` | 觸發分類精準同步 |

**FAQs**

| Method | Path | 說明 |
|--------|------|------|
| GET | `/api/v1/agents/{id}/faqs` | 列表（支援 page/status/category_id/q） |
| POST | `/api/v1/agents/{id}/faqs` | 建立 FAQ |
| GET | `/api/v1/agents/{id}/faqs/{faq_id}` | 取得單筆（含鎖狀態） |
| PATCH | `/api/v1/agents/{id}/faqs/{faq_id}` | 更新內容 |
| DELETE | `/api/v1/agents/{id}/faqs/{faq_id}` | 刪除 |
| PATCH | `/api/v1/agents/{id}/faqs/{faq_id}/status` | 狀態轉移 |
| POST | `/api/v1/agents/{id}/faqs/{faq_id}/lock` | 取得編輯鎖 |
| PUT | `/api/v1/agents/{id}/faqs/{faq_id}/lock` | 心跳延長鎖 |
| DELETE | `/api/v1/agents/{id}/faqs/{faq_id}/lock` | 釋放鎖 |
| GET | `/api/v1/agents/{id}/faqs/{faq_id}/histories` | 版本歷史 |
| POST | `/api/v1/agents/{id}/faqs/{faq_id}/rollback` | 版本回溯 |

**Sync**

| Method | Path | 說明 |
|--------|------|------|
| POST | `/api/v1/agents/{id}/sync` | 觸發全量同步 |
| GET | `/api/v1/agents/{id}/sync/history` | 同步歷史 |
| GET | `/api/v1/sync/tasks/{sync_log_id}` | 輪詢任務狀態 |

**Import / Export**

| Method | Path | 說明 |
|--------|------|------|
| POST | `/api/v1/agents/{id}/faqs/import` | 全域 Excel 匯入 |
| GET | `/api/v1/agents/{id}/faqs/export` | 全域 Excel 匯出 |

**Health**

| Method | Path | 說明 |
|--------|------|------|
| GET | `/api/v1/health` | DB + Redis 健康狀態 |

### 12.3 Pydantic Schema 速查

**請求 Body（常用）**

```json
// POST /auth/login
{ "username": "admin", "password": "Admin123" }

// POST /agents
{ "name": "銷售機器人", "txt_output_path": "/opt/rasa-docs/uuid-subdir" }

// POST /faqs
{ "question": "問題", "answer": "回答", "category_id": "uuid", "tags": [] }

// PATCH /faqs/{id}/status
{ "status": "pending", "action_reason": null }

// POST /categories/{id}/import?mode=append  (multipart/form-data)
file: <xlsx file>
```

**回應格式**

```json
// 成功
{ "success": true, "data": { ... } }

// 分頁列表
{ "success": true, "data": { "items": [...], "total": 42, "page": 1, "per_page": 20 } }

// 錯誤
{ "detail": "錯誤訊息" }
```

---

## 附錄：專案檔案結構（頂層）

```
D:\mini_test\                    (或 /opt/rasa-manager/ on Linux)
├── docker-compose.yml
├── .env.example
├── .env                         (本機，不入 git)
├── .gitattributes               (強制 .sh LF 換行)
├── comprehensive-system-design.md   (唯一權威規格書 v1.1)
├── implementation_plan.md           (六階段實施計劃)
├── ingest_kb.py                     (向量化腳本，部署時複製至 scripts/)
├── docs/
│   └── Rasa_Manager_beta_v1.0.md   (本文件)
├── backend/
│   ├── main.py
│   ├── tasks.py
│   ├── entrypoint.sh
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── api/
│   │   ├── database/
│   │   ├── routes/
│   │   ├── schemas.py
│   │   ├── dependencies.py
│   │   ├── security/
│   │   ├── utils/
│   │   └── seed.py
│   └── alembic/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── features/
│   │   ├── api/
│   │   ├── store/
│   │   ├── hooks/
│   │   └── lib/
│   ├── tailwind.config.ts
│   ├── vite.config.ts
│   ├── nginx.conf
│   ├── Dockerfile
│   └── package.json
└── scripts/
    └── ingest_kb.py             (bind mount 至 celery_worker:/opt/scripts/)
```

---

*本文件由 Claude 根據 Rasa Manager Beta v1.0 專案原始碼自動整理生成，版本鎖定於 2026-05-03。後續功能開發請同步更新本文件。*
