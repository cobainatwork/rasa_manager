#!/bin/bash
# PostgreSQL 還原腳本
#
# 使用方式：
#   bash scripts/restore.sh <備份檔路徑>
#
# 範例：
#   bash scripts/restore.sh data/backups/rasa_knowledge_20240428_120000.sql.gz
#
# 警告：此操作會先 DROP 並重建目標資料庫，現有資料將被覆蓋！

set -euo pipefail

BACKUP_FILE="${1:-}"

if [ -z "$BACKUP_FILE" ]; then
  echo "用法：bash scripts/restore.sh <備份檔路徑>"
  exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
  echo "錯誤：找不到備份檔 $BACKUP_FILE"
  exit 1
fi

# ── 載入 .env ────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"
if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  set -a && source "$ENV_FILE" && set +a
fi

POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-rasa_admin}"
POSTGRES_DB="${POSTGRES_DB:-rasa_knowledge}"

echo "[restore] 警告：即將還原 $POSTGRES_DB 資料庫，現有資料將被覆蓋！"
read -r -p "確定要繼續？(yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "[restore] 取消操作。"
  exit 0
fi

echo "[restore] 開始還原 $BACKUP_FILE → ${POSTGRES_DB}@${POSTGRES_HOST}:${POSTGRES_PORT}"

# ── 判斷使用 Docker 或直接連線 ───────────────────────────────────────────────
if docker compose ps db 2>/dev/null | grep -q "Up\|running"; then
  # 透過 Docker 容器還原
  docker compose exec -T db psql \
    -U "$POSTGRES_USER" \
    -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};" postgres

  docker compose exec -T db psql \
    -U "$POSTGRES_USER" \
    -c "CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER};" postgres

  zcat "$BACKUP_FILE" | docker compose exec -T db psql \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB"
else
  # 直接呼叫 psql
  PGPASSWORD="${POSTGRES_PASSWORD:-}" psql \
    -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};" postgres

  PGPASSWORD="${POSTGRES_PASSWORD:-}" psql \
    -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -c "CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER};" postgres

  zcat "$BACKUP_FILE" | PGPASSWORD="${POSTGRES_PASSWORD:-}" psql \
    -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB"
fi

echo "[restore] 還原完成。執行 Alembic 確認 schema 狀態..."
if docker compose ps backend 2>/dev/null | grep -q "Up\|running"; then
  docker compose exec -T backend alembic current
fi

echo "[restore] 完成。"
