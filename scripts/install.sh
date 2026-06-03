#!/usr/bin/env bash
# install.sh — 在客戶 Linux 主機執行的離線部署腳本。
#
# 流程：
#   1. 環境檢查（docker / docker compose v2）
#   2. 載入離線 image（docker load）
#   3. 首次部署：產生 .env（隨機 secrets）並引導使用者填入剩餘欄位
#   4. 啟動服務（docker compose up -d）
#   5. 健康檢查
#
# 同目錄需有：images/*.tar、docker-compose.yml、.env.example
set -euo pipefail

cd "$(dirname "$0")"

echo "==> 1/5 環境檢查"
command -v docker >/dev/null 2>&1 || { echo "錯誤：未安裝 docker"; exit 1; }
docker compose version >/dev/null 2>&1 || {
    echo "錯誤：未安裝 docker compose v2（請升級 Docker 至 20.10+）"
    exit 1
}
echo "    docker $(docker --version | awk '{print $3}' | tr -d ',')、compose v2 OK"

echo "==> 2/5 載入離線 docker images"
for img in images/*.tar; do
    name=$(basename "$img" .tar)
    echo "    載入 $name ..."
    docker load -i "$img" >/dev/null
done
echo "    完成"

echo "==> 3/5 .env 設定"
if [ ! -f .env ]; then
    echo "    首次部署：複製 .env.example → .env 並產生隨機 secrets"
    cp .env.example .env

    POSTGRES_PASS=$(openssl rand -base64 24 | tr -d '/+=' | cut -c 1-24)
    REDIS_PASS=$(openssl rand -base64 24 | tr -d '/+=' | cut -c 1-24)
    JWT=$(openssl rand -hex 32)

    # macOS/Linux sed -i 相容寫法
    sed -i.bak \
        -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${POSTGRES_PASS}|" \
        -e "s|^REDIS_PASSWORD=.*|REDIS_PASSWORD=${REDIS_PASS}|" \
        -e "s|^JWT_SECRET=.*|JWT_SECRET=${JWT}|" \
        .env
    rm -f .env.bak

    cat <<EOF

    .env 已建立，請編輯以下必填欄位後再次執行 ./install.sh：

      OPENAI_API_KEY              （Embedding 雲端使用，若全走地端可留空）
      LOCAL_EMBEDDING_BASE_URL    （Embedding 地端 OpenAI-compatible URL）
      QDRANT_URL                  （向量資料庫 URL，例 http://10.x.x.x:6333）
      SEED_ADMIN_USERNAME         （首位 Superadmin 帳號）
      SEED_ADMIN_PASSWORD         （需符合 8 字元 / 大小寫 / 數字）
      TXT_OUTPUT_HOST_PATH        （匯出 .txt 主機目錄絕對路徑，需事先存在）
      CORS_ORIGIN                 （前端 origin，例 http://server-ip:5173）
      PROJECT_ROOT                （此目錄絕對路徑：$(pwd)）

    自動產生隨機值（已寫入 .env）：
      POSTGRES_PASSWORD / REDIS_PASSWORD / JWT_SECRET

EOF
    exit 0
fi
echo "    .env 已存在，沿用"

echo "==> 4/5 啟動服務（docker compose up -d）"
docker compose up -d
echo "    等候健康檢查 30 秒..."
sleep 30

echo "==> 5/5 服務狀態"
docker compose ps

cat <<EOF

部署完成。

驗收：
  curl http://localhost:8050/api/v1/health
  瀏覽器開啟 http://<本機 IP>:5173

排錯：
  docker compose logs backend
  docker compose logs celery_worker
EOF
