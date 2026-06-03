# Rasa Manager 客戶部署 SOP

本文件給客戶端 IT 人員使用，涵蓋「有 internet」與「無 internet」兩種部署情境。

---

## 一、系統需求

| 項目 | 規格 |
|------|------|
| 作業系統 | Linux x86_64（Ubuntu 22.04 / RHEL 9 / Rocky 9 經測試） |
| CPU | 4 核以上 |
| 記憶體 | 8 GB 以上（Postgres + Redis + 後端 + Celery + 前端 nginx） |
| 硬碟 | 30 GB 以上空閒（其中 Postgres data + Qdrant 文件視資料量） |
| Docker | 20.10+（含 `docker compose` v2 子命令） |
| 對外連線 | **若採線上模式**需可拉 Docker Hub / GitHub；**離線模式**完全不需 |
| 必要外部服務 | Qdrant 向量資料庫、Rasa Server、地端或 OpenAI Embedding |

> 確認 docker compose v2：`docker compose version`（不是 `docker-compose`）

---

## 二、兩種部署模式

| 模式 | 適用 | 取得方式 |
|------|------|---------|
| **A. 線上模式** | 客戶端可連網 | git clone 或 source tar.gz |
| **B. 離線模式** | 客戶端無 internet | `rasa_manager-<version>-offline.tar.gz` |

---

## 三、模式 A：線上部署

### A.1 取得專案

```bash
sudo mkdir -p /opt/rasa_manager
sudo chown -R "$USER":"$USER" /opt/rasa_manager
cd /opt/rasa_manager
git clone https://github.com/cobainatwork/rasa_manager.git .
```

或從供應商收到 source tar.gz：

```bash
tar xzf rasa_manager-<version>-source.tar.gz -C /opt/rasa_manager --strip-components=1
cd /opt/rasa_manager
```

### A.2 建立 .txt 匯出目錄（主機端）

```bash
sudo mkdir -p /var/lib/rasa_docs
sudo chown -R "$USER":"$USER" /var/lib/rasa_docs
```

### A.3 建立 .env

```bash
cp .env.example .env
```

依「五、環境變數對照表」填入。**必填欄位若漏會啟動失敗**。

### A.4 啟動

```bash
docker compose up --build -d
```

首次 build 約 5–10 分鐘（需拉 base image + npm install + pip install）。

### A.5 驗證

```bash
docker compose ps                                       # 五服務應全 healthy
curl http://localhost:8050/api/v1/health                # {"status":"ok",...}
```

瀏覽器開啟 `http://<server-ip>:5173`，以 `.env` 內的 `SEED_ADMIN_USERNAME` / `SEED_ADMIN_PASSWORD` 登入。

---

## 四、模式 B：離線部署

### B.1 取得離線包

供應商透過 SFTP / 隨身碟 / 加密郵件提供：

```
rasa_manager-<version>-offline.tar.gz
```

內容：
- `images/` 4 個 docker image（backend / frontend / postgres / redis）已 `docker save`
- `docker-compose.yml`、`.env.example`
- `install.sh`、`uninstall.sh`、`README.md`、`VERSION`

### B.2 部署

```bash
# 解壓
sudo mkdir -p /opt/rasa_manager
cd /opt/rasa_manager
tar xzf /path/to/rasa_manager-<version>-offline.tar.gz --strip-components=1

# 建立 .txt 匯出目錄
sudo mkdir -p /var/lib/rasa_docs
sudo chown -R "$USER":"$USER" /var/lib/rasa_docs

# 執行安裝腳本（首次會建立 .env 並停止，請編輯 .env 後再執行一次）
sudo ./install.sh

# 編輯 .env 填入必要欄位（見「五、環境變數對照表」）
nano .env

# 再次執行 install.sh 啟動服務
sudo ./install.sh
```

install.sh 自動處理：
- 環境檢查
- `docker load` 載入離線 image
- 首次部署產生隨機 `POSTGRES_PASSWORD` / `REDIS_PASSWORD` / `JWT_SECRET`
- `docker compose up -d` + 健康檢查

### B.3 驗證

同 A.5。

---

## 五、環境變數對照表（.env）

| 變數 | 必填 | 說明 |
|------|------|------|
| `POSTGRES_USER` | 是 | Postgres 帳號（建議 `rasa_admin`） |
| `POSTGRES_PASSWORD` | 是 | install.sh 自動產生 |
| `POSTGRES_DB` | 是 | DB 名稱（建議 `rasa_knowledge`） |
| `REDIS_PASSWORD` | 是 | install.sh 自動產生 |
| `JWT_SECRET` | 是 | install.sh 自動產生（≥64 字元） |
| `DATABASE_URL` | 是 | `postgresql://rasa_admin:<同上>@db:5432/rasa_knowledge` |
| `REDIS_URL` | 是 | `redis://:<同上>@redis:6379/0` |
| `SEED_ADMIN_USERNAME` | 是 | 首位 Superadmin 帳號 |
| `SEED_ADMIN_PASSWORD` | 是 | 需 8 字元 + 大小寫 + 數字 |
| `TXT_OUTPUT_HOST_PATH` | 是 | 主機端匯出目錄絕對路徑（如 `/var/lib/rasa_docs`），需事先存在 |
| `PROJECT_ROOT` | 是 | 本專案絕對路徑（如 `/opt/rasa_manager`） |
| `CORS_ORIGIN` | 是 | 前端 origin（如 `http://<server-ip>:5173`） |
| `QDRANT_URL` | 是 | Qdrant 向量資料庫（如 `http://10.x.x.x:6333`） |
| `OPENAI_API_KEY` | 條件 | 若任一 agent 用 `embedding_provider=openai` 必填 |
| `LOCAL_EMBEDDING_BASE_URL` | 條件 | 若任一 agent 用 `embedding_provider=local` 必填，OpenAI-compatible 端點 |
| `LOCAL_EMBEDDING_API_KEY` | 條件 | 地端 server 多數不檢查，但 SDK 要求非空 |
| `APP_PORT` | 否 | 後端 port（預設 8050） |
| `LOG_LEVEL` | 否 | INFO / DEBUG / WARNING（預設 INFO） |

---

## 六、Agent 與 Embedding 設定

部署完成後，登入 UI → Agent 設定頁可為每個 Agent 獨立選擇 embedding provider：

- **OpenAI 雲端**：走 `.env` 的 `OPENAI_API_KEY`
- **Local 地端**：走 `.env` 的 `LOCAL_EMBEDDING_BASE_URL`

**重要**：切換 provider 或 model 後，下次同步必須選「清空重建」（避免向量 dim 不一致）。

---

## 七、日常維運

### 7.1 重啟

```bash
docker compose restart backend celery_worker     # 不停 DB / Redis
```

### 7.2 看日誌

```bash
docker compose logs -f backend
docker compose logs -f celery_worker
docker compose logs --tail 100 frontend
```

### 7.3 備份

```bash
./scripts/backup.sh                              # 產生 dump 到 ./backups/
```

### 7.4 升級（取得新版本）

線上模式：
```bash
git pull
docker compose up --build -d
```

離線模式：取得新離線包後：
```bash
docker compose down                              # 不加 -v 保留資料
tar xzf rasa_manager-<新版本>-offline.tar.gz --strip-components=1
sudo ./install.sh
```

### 7.5 完全移除（含資料）

```bash
sudo ./uninstall.sh --purge                      # 不可逆，會清 volume + image
```

---

## 八、常見問題排錯

### 8.1 啟動後 backend `unhealthy`

```bash
docker compose logs backend --tail 50
```

- `password authentication failed` → `DATABASE_URL` 內的密碼與 `POSTGRES_PASSWORD` 不一致
- `Connection refused at redis` → `REDIS_URL` 內的密碼與 `REDIS_PASSWORD` 不一致
- `[seed] ERROR: 密碼太短` → `SEED_ADMIN_PASSWORD` 不符（8 字元 + 大小寫 + 數字）

### 8.2 一鍵同步卡在「執行中」

通常是 `LOCAL_EMBEDDING_BASE_URL` 不通或 OpenAI API key 失效：

```bash
docker compose logs celery_worker --tail 100
```

### 8.3 對話測試沒回應

「重新對話」或「清除對話」按鈕會換 sender，自然從乾淨狀態重開。仍無回應請看 Rasa Server 端日誌。

### 8.4 docker compose up 失敗：`mount volume failed`

`TXT_OUTPUT_HOST_PATH` 指向的目錄不存在：

```bash
sudo mkdir -p /var/lib/rasa_docs
sudo chown -R "$USER":"$USER" /var/lib/rasa_docs
```

---

## 九、技術支援

| 項目 | 提供方式 |
|------|---------|
| 緊急 issue（系統無法啟動） | 帶上 `docker compose ps` + `docker compose logs backend --tail 200` 截圖回報 |
| 功能性 bug | 由供應商透過 GitHub issue 回報 |
| 升級 | 新版本由供應商通知 |
