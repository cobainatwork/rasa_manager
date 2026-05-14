# Backend — Rasa RAG 知識庫管理平台

FastAPI + SQLAlchemy + Celery 的後端服務，提供 REST API 並透過 Celery worker 非同步執行 ingestion script。

## 技術棧

| 分類 | 套件 |
|------|------|
| Web 框架 | FastAPI、Uvicorn |
| ORM / 遷移 | SQLAlchemy 2（同步）、Alembic 1.13+ |
| 資料庫 | PostgreSQL 15（psycopg2-binary） |
| 任務佇列 | Celery 5、Redis 7（broker + result backend） |
| 認證 | python-jose（JWT）、passlib[bcrypt]（cost=12） |
| 驗證 | Pydantic v2 |
| 日誌 | structlog |
| 測試 | pytest、pytest-mock |
| Lint / 型別 | ruff、mypy |
| 安全掃描 | bandit |

## 開發指令

```bash
# 安裝依賴（建議在 virtualenv 或 container 內）
pip install -r requirements.txt

# 執行測試（基線：293 passed）
python -m pytest -q

# 執行特定測試檔案
python -m pytest tests/test_faq.py -v

# Lint
python -m ruff check .
python -m ruff check . --fix   # 自動修正

# 型別檢查
PYTHONUTF8=1 python -m mypy api/

# 安全掃描（Low 以上）
python -m bandit -r api/ tasks.py main.py -ll

# 套用最新 migration
alembic upgrade head

# 產生新 migration（更改 models.py 後）
alembic revision --autogenerate -m "describe change"

# 啟動開發用 server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 專案結構

```
backend/
├── main.py                  # FastAPI app 入口、CORS、health endpoint
├── tasks.py                 # Celery task（sync_and_ingest）
├── entrypoint.sh            # 容器啟動序列：alembic upgrade → seed → uvicorn
├── requirements.txt
├── Dockerfile
├── alembic.ini
├── alembic/
│   ├── env.py               # 從 DATABASE_URL 環境變數讀取連線
│   └── versions/
│       ├── 001_initial.py   # 8 張表 + 13 個索引
│       └── 002_hardening.py # FK ON DELETE、immutable history trigger
├── api/
│   ├── database/
│   │   ├── models.py        # 8 個 SQLAlchemy ORM 模型
│   │   └── session.py       # SessionLocal + get_db dependency
│   ├── routes/
│   │   ├── auth.py          # login / logout / refresh / me
│   │   ├── agents.py        # CRUD + stats
│   │   ├── agent_admin.py   # Superadmin 專用（建立 / 刪除 Agent）
│   │   ├── faq.py           # FAQ CRUD + status 轉移 + 編輯鎖
│   │   ├── categories.py    # 分類 CRUD（Adjacency List）
│   │   ├── import_export.py # Excel 匯入 / 匯出
│   │   ├── sync.py          # 一鍵同步觸發 / 狀態查詢 / 歷史
│   │   ├── audit.py         # 稽核日誌查詢
│   │   ├── users.py         # 使用者管理（Superadmin）
│   │   └── chat.py          # Rasa webhook proxy
│   ├── security/
│   │   ├── auth.py          # JWT 簽發 / 驗證、HttpOnly Cookie 操作
│   │   └── rate_limit.py    # Redis 登入防爆破（5 次失敗鎖 15 分鐘）
│   ├── utils/
│   │   └── audit.py         # write_audit_log 輔助函式
│   ├── schemas.py           # Pydantic request / response schemas
│   └── seed.py              # Superadmin seed（bcrypt cost=12，密碼驗證）
└── tests/
    ├── STYLE.md             # 測試碼風格規範
    ├── conftest.py          # pytest fixtures（DB session、test client、使用者）
    └── test_*.py            # 各路由的整合測試
```

## 資料庫 Schema 概覽

| 表 | 說明 |
|----|------|
| `users` | 使用者帳號（is_superadmin 旗標） |
| `agents` | Agent 專案（含 txt_output_path / ingest_script_path） |
| `user_agent_roles` | 使用者 × Agent 角色（reviewer / editor） |
| `categories` | FAQ 分類（Adjacency List，支援無限層級） |
| `knowledge_items` | FAQ 主表（含狀態機、編輯鎖） |
| `knowledge_item_histories` | 不可變版本歷史（DB trigger 強制） |
| `audit_logs` | 所有狀態變動的稽核軌跡（diff JSONB） |
| `sync_logs` | 同步任務紀錄（Celery task 狀態） |

## 核心架構決策

### 認證

- JWT 以 HttpOnly Cookie 傳遞（`access_token` 15 分鐘 / `refresh_token` 7 天）。
- Refresh Token Rotation：每次 refresh 產生新的 `jti`，舊 jti 寫入 Redis 黑名單。
- 角色不寫入 JWT payload（角色會異動）；每次請求從 DB 查詢當前角色。

### 編輯鎖

採 Lazy Expire 模式：10 分鐘逾時，於 `GET /faq/:id` 或 `PATCH /faq/:id` 時在同一 transaction 內惰性清除，不依賴背景排程。

### 一鍵同步

1. API 呼叫 `celery.send_task('sync_and_ingest')` 並立即回傳 `sync_log_id`。
2. Worker 在隔離容器內：取出 FAQ → 寫 `.txt` → 執行 ingestion script → 更新 sync_log 狀態。
3. `subprocess.Popen` 禁止 `shell=True`，以 `shlex.split()` 處理路徑。

### 測試策略

- 每個 API 路由有對應的 `test_*.py`，採整合測試（SQLite in-memory）。
- `conftest.py` 提供 `client`（TestClient）、`db`（Session）、`admin_headers`、`editor_headers` 等 fixtures。
- 測試風格規範見 `tests/STYLE.md`。

## 環境變數

| 變數 | 用途 | 必填 |
|------|------|------|
| `DATABASE_URL` | PostgreSQL 連線字串 | 是 |
| `REDIS_URL` | Redis 連線字串 | 是 |
| `JWT_SECRET` | JWT 簽章密鑰（≥64 字元） | 是 |
| `SEED_ADMIN_USERNAME` | 初始 Superadmin 帳號 | 是 |
| `SEED_ADMIN_PASSWORD` | 初始 Superadmin 密碼（8 字元以上，含大/小寫/數字） | 是 |
| `CORS_ORIGIN` | 前端 origin（預設 `http://localhost:5173`） | 否 |
| `TXT_OUTPUT_BASE` | `.txt` 匯出的容器內基底路徑（預設 `/opt/sap`） | 否 |
