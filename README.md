# Rasa RAG 知識庫管理平台

多 Agent FAQ 知識庫管理平台，提供集中化的問答編輯、審核工作流、Rasa 對話測試與一鍵同步至 `.txt` 文件並觸發使用者自訂的 ingestion script，將內容寫入 Qdrant 向量資料庫。

## 功能概覽

- 多 Agent 隔離：所有業務資料以 `agent_id` 區隔，使用者可加入多個 Agent 並分別擔任 `editor` 或 `reviewer` 角色。
- FAQ 工作流：`draft → pending → approved → synced`，含 `rejected` 退回路徑、Superadmin 直接核准。
- 編輯鎖：Lazy Expire 模式（10 分鐘逾時 + 心跳延長），避免多人併發覆寫。
- 版本歷史：每次變更寫入不可變 history 表，支援差異比對與 Rollback。
- 一鍵同步：將 `approved` / `synced` 項目匯出為 `.txt`（`[Question]` / `[Answer]` 區塊），透過 Celery 觸發使用者指定的 ingestion script。
- 對話測試：前端直連 Rasa REST webhook，驗證同步後回應。
- 稽核軌跡：所有狀態變動 / 同步 / 登入皆寫入 `audit_logs` / `sync_logs`。

## 技術棧

| 層 | 技術 |
|----|------|
| 後端 | FastAPI、SQLAlchemy、Alembic、Pydantic v2、structlog |
| 任務佇列 | Celery 5、Redis 7 |
| 資料庫 | PostgreSQL 15 |
| 前端 | React 18、Vite 5、TypeScript 5、Tailwind CSS 3、shadcn/ui (Radix)、Zustand、React Hook Form、Zod |
| 測試 | pytest、Vitest、React Testing Library、MSW、jest-axe |
| 容器化 | Docker Compose（5 服務）、nginx (frontend production)、tini |

## 快速開始

### 環境需求

- Docker Desktop（含 Docker Compose v2）
- Node 20.11 ~ 21（本機跑前端 dev server 用）
- Python 3.11+（本機執行 alembic / pytest 用，可選）

### 啟動步驟

1. 複製 `.env.example` 為 `.env`，依註解填入：
   - `POSTGRES_PASSWORD`：PostgreSQL 密碼
   - `JWT_SECRET`：JWT 簽章用，至少 64 字元隨機字串
   - `REDIS_PASSWORD`：Redis 密碼
   - `SEED_ADMIN_USERNAME` / `SEED_ADMIN_PASSWORD`：第一個 Superadmin 帳密（密碼需含大小寫與數字、至少 8 字元）
   - `TXT_OUTPUT_HOST_PATH`：主機端 `.txt` 匯出目錄絕對路徑（會 bind mount 至 worker container）
   - `CORS_ORIGIN`：前端 origin（預設 `http://localhost:5173`）
2. 啟動全部服務：

   ```bash
   docker compose up --build -d
   ```

3. 等候健康檢查全綠（約 30 ~ 60 秒）：

   ```bash
   docker compose ps
   ```

4. 開啟瀏覽器至 <http://localhost:5173>，以 Superadmin 帳號登入。

### 服務埠

| 服務 | 主機埠 | 容器埠 |
|------|--------|--------|
| frontend (nginx) | 5173 | 8080 |
| backend (FastAPI) | 8000 | 8000 |
| db (PostgreSQL) | 內部 | 5432 |
| redis | 內部 | 6379 |
| celery_worker | 內部 | 8000（不對外） |

## 專案結構

```
D:\mini_test\
├── backend/                 # FastAPI 應用 + Celery tasks + Alembic migrations
│   ├── api/
│   ├── alembic/
│   ├── tests/               # pytest（含 STYLE.md 風格規範）
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                # React + Vite + TS + Tailwind
│   ├── src/
│   │   ├── features/        # 依功能切目錄（auth / agents / knowledge / ...）
│   │   ├── components/      # 共用 UI（含 shadcn/ui 包裝）
│   │   ├── routes/          # 路由守衛 + AuthProvider
│   │   ├── store/           # zustand stores
│   │   └── mocks/           # MSW handlers
│   └── Dockerfile           # multi-stage：node build + nginx serve
├── scripts/                 # 使用者 ingestion scripts（bind mount 至 worker `:ro`）
├── docker-compose.yml
├── comprehensive-system-design.md   # 系統規格 v1.1（唯一權威）
├── implementation_plan.md           # 六階段實施計畫
└── CLAUDE.md                # Claude Code 開發指引
```

## 開發指令

### 後端

```bash
# 進入 backend container 跑測試
docker compose exec backend python -m pytest -q

# 跑 ruff / mypy
docker compose exec backend python -m ruff check .
docker compose exec backend python -m mypy api/

# 套用 migration
docker compose exec backend alembic upgrade head

# 產生新 migration
docker compose exec backend alembic revision --autogenerate -m "..."
```

### 前端

```bash
cd frontend
npm install
npm run dev          # 啟本機 vite dev server（proxy /api → :8000）
npm test             # vitest run（含 a11y smoke）
npm run lint         # eslint
npm run typecheck    # tsc --noEmit
npm run build        # production build
```

### 容器

```bash
docker compose up --build -d         # 啟動
docker compose ps                    # 健康檢查
docker compose logs -f backend       # 看後端日誌
docker compose down -v               # 全部關閉並刪除 volume
```

## 文件

- [`comprehensive-system-design.md`](./comprehensive-system-design.md) — 完整系統規格 v1.1，唯一權威，含 ERD / API / 安全策略
- [`implementation_plan.md`](./implementation_plan.md) — 六階段實施計畫
- [`CLAUDE.md`](./CLAUDE.md) — Claude Code 開發指引與排版規範
- [`backend/tests/STYLE.md`](./backend/tests/STYLE.md) — 後端測試碼風格規範

## 安全要點

- JWT 一律以 HttpOnly Cookie 儲存（Access 15 分鐘 / Refresh 7 天 + Rotation + Redis `jti` 黑名單）。
- Bcrypt cost factor = 12；登入採 Redis 計數器防爆破（同 IP + 帳號 5 次失敗鎖定 15 分鐘）。
- Cookie `SameSite=Strict` 已涵蓋 CSRF 防護。
- `ingest_script_path` 僅 Superadmin 可設定；`subprocess` 禁用 `shell=True`，以 `shlex.split()` 處理。
- Pydantic schema 嚴格驗證；ORM 全程使用 parameterized query。

## 授權

Internal use only.
