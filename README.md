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
   - `SEED_ADMIN_USERNAME` / `SEED_ADMIN_PASSWORD`：第一個 Superadmin 帳密
     - **密碼必須符合**：8 字元以上、含大寫字母、含小寫字母、含數字（規格 §五.6）
     - 違規時 seed 會 ERROR 結束，後續無法登入；必須改 `.env` 後再 `docker compose down -v && docker compose up -d` 重新 seed
   - `TXT_OUTPUT_HOST_PATH`：主機端 `.txt` 匯出目錄絕對路徑（會 bind mount 至 worker container）
     - Windows 範例：`D:/SAP`
     - Linux 範例：`/var/lib/rasa_docs`
     - **此目錄必須事先存在於主機**，否則 docker compose up 會失敗
   - `CORS_ORIGIN`：前端 origin（預設 `http://localhost:5173`）
   - `OPENAI_API_KEY`：OpenAI API Key（一鍵同步觸發 `ingest_kb.py` 時需要）
     - 若僅測試 `.txt` 匯出而不接 Qdrant，可填占位字串如 `sk-test-placeholder`，並把 Agent 的 `ingest_script_path` 留空
   - `QDRANT_URL`：Qdrant 向量資料庫 URL，例 `http://10.2.66.88:6333`
     - 若僅測 `.txt` 不接 Qdrant，同樣可填占位 URL；Agent.ingest_script_path 留空即不會觸發
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
| backend (FastAPI) | 8050 | 8050 |
| db (PostgreSQL) | 內部 | 5432 |
| redis | 內部 | 6379 |
| celery_worker | 內部 | 8050（不對外） |

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
npm run dev          # 啟本機 vite dev server（proxy /api → :8050）
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

## 主機路徑與容器路徑對應

理解此表，可避免「容器內路徑」與「主機檔案位置」混淆造成的部署問題：

| 容器內路徑 | 主機端對應位置 | 用途 |
|------------|----------------|------|
| `/opt/sap/*` | `${TXT_OUTPUT_HOST_PATH}/*` | **匯出 `.txt` 的最終位置**，可從主機直接讀寫 |
| `/opt/rasa_docs/*` | `${TXT_OUTPUT_HOST_PATH}/*` | 同上（向後相容舊的 `txt_output_path` 設定） |
| `/opt/scripts/*` | `./scripts/*` | 使用者 ingestion scripts，唯讀 |
| `/opt/project/*` | `${PROJECT_ROOT}/*` | 整個專案根目錄，內含 `ingest_kb.py`，唯讀 |

範例：Agent.txt_output_path 設為 `/opt/sap/agent1`，匯出後主機端可看到 `${TXT_OUTPUT_HOST_PATH}/agent1/faq_export.txt`。

## 常見問題

### Q1：admin 帳密錯誤無法登入

通常是 seed 失敗導致 admin 沒被建立。檢查順序：

```bash
# 1. 看 seed log 找原因
docker compose logs backend | grep -i "seed"

# 2. 確認 DB 是否實際有 admin
docker compose exec db psql -U rasa_admin -d rasa_knowledge -c "SELECT username, is_superadmin FROM users;"
```

最常見原因：`SEED_ADMIN_PASSWORD` 不符規格（§五.6）。改 `.env` 後須重建（清資料）：

```bash
docker compose down -v && docker compose up -d
```

### Q2：本機只想測 `.txt` 匯出，不接真實 Qdrant

1. `.env` 的 `OPENAI_API_KEY` 與 `QDRANT_URL` 填占位字串即可（不會真連線）
2. UI 進入 Agent 設定頁，把 `ingest_script_path` **留空**
3. 觸發一鍵同步時，後端只寫 `.txt`、不呼叫 ingest，sync_log 立即標 `completed`
4. `.txt` 會出現在 `${TXT_OUTPUT_HOST_PATH}/<txt_output_path 的最後一段>/faq_export.txt`

### Q3：同步任務一直顯示「執行中」卡住

通常是 `ingest_script_path` 設了但 `OPENAI_API_KEY` / `QDRANT_URL` 為占位值。診斷：

```bash
# 看 celery_worker 日誌找 RuntimeError
docker compose logs celery_worker --tail 50

# 看 sync_logs 狀態
docker compose exec db psql -U rasa_admin -d rasa_knowledge -c \
  "SELECT id, status, stderr FROM sync_logs ORDER BY created_at DESC LIMIT 3;"
```

修復：先按 Q2 步驟清空 `ingest_script_path`，把卡住的 sync_log 手動標 failed：

```bash
docker compose exec db psql -U rasa_admin -d rasa_knowledge -c \
  "UPDATE sync_logs SET status='failed', finished_at=NOW() WHERE status='running';"
```

### Q4：docker compose up 失敗，提示 mount volume 失敗

通常是 `.env` 的 `TXT_OUTPUT_HOST_PATH` 指向的目錄主機端不存在。先建立：

```bash
# Linux
sudo mkdir -p /var/lib/rasa_docs
sudo chown -R $USER:$USER /var/lib/rasa_docs

# Windows PowerShell
New-Item -ItemType Directory -Path "D:/SAP" -Force
```

## 部署到 Linux 主機（內部測試）

### 主機端準備

```bash
sudo mkdir -p /opt/rasa_rag /var/lib/rasa_docs
sudo chown -R $USER:$USER /var/lib/rasa_docs
cd /opt/rasa_rag
git clone <repo_url> .
git checkout <branch>
```

### `.env` 設定（Linux 範例）

```bash
POSTGRES_USER=rasa_admin
POSTGRES_PASSWORD=$(openssl rand -base64 24)
POSTGRES_DB=rasa_knowledge
REDIS_PASSWORD=$(openssl rand -base64 24)
JWT_SECRET=$(openssl rand -hex 32)
SEED_ADMIN_USERNAME=admin
SEED_ADMIN_PASSWORD=Admin2026Pass            # 符合 §五.6 規則
PROJECT_ROOT=/opt/rasa_rag
TXT_OUTPUT_HOST_PATH=/var/lib/rasa_docs
CORS_ORIGIN=http://<linux-host>:5173
DATABASE_URL=postgresql://rasa_admin:<同 POSTGRES_PASSWORD>@db:5432/rasa_knowledge
REDIS_URL=redis://:<同 REDIS_PASSWORD>@redis:6379/0
OPENAI_API_KEY=sk-...
QDRANT_URL=http://<qdrant-host>:6333
```

### 啟動與驗收

```bash
docker compose up --build -d
docker compose ps
curl http://localhost:8050/api/v1/health     # 期望 {"status":"ok",...}
docker compose exec backend alembic current  # 期望 002 (head)
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
