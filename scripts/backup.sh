#!/bin/bash
# PostgreSQL 每日備份腳本（保留最近 7 天）
#
# 使用方式：
#   bash scripts/backup.sh
#
# 環境變數（可由 .env 提供）：
#   BACKUP_DIR     備份目錄（預設：./data/backups）
#   POSTGRES_HOST  DB host（預設：localhost）
#   POSTGRES_PORT  DB port（預設：5432）
#   POSTGRES_USER  DB user
#   POSTGRES_PASSWORD  DB password
#   POSTGRES_DB    DB 名稱
#   RETAIN_DAYS    保留天數（預設：7）
#   BACKUP_GPG_RECIPIENT  GPG 收件人 Key ID 或 Email（設定後啟用加密，產生 .sql.gz.gpg）

set -euo pipefail

# ── 載入 .env（若存在）────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"
if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  set -a && source "$ENV_FILE" && set +a
fi

# ── 設定預設值 ────────────────────────────────────────────────────────────────
BACKUP_DIR="${BACKUP_DIR:-./data/backups}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-rasa_admin}"
POSTGRES_DB="${POSTGRES_DB:-rasa_knowledge}"
RETAIN_DAYS="${RETAIN_DAYS:-7}"
BACKUP_GPG_RECIPIENT="${BACKUP_GPG_RECIPIENT:-}"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="rasa_knowledge_${TIMESTAMP}.sql.gz"
FILEPATH="$BACKUP_DIR/$FILENAME"

# ── 建立備份目錄 ────────────────────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"

echo "[backup] 開始備份 ${POSTGRES_DB}@${POSTGRES_HOST}:${POSTGRES_PORT} → $FILEPATH"

# ── 執行備份（透過 Docker 容器或直接呼叫 pg_dump）────────────────────────────
if docker compose ps db 2>/dev/null | grep -q "Up\|running"; then
  docker compose exec -T db pg_dump \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    | gzip > "$FILEPATH"
else
  PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_dump \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    | gzip > "$FILEPATH"
fi

SIZE=$(du -sh "$FILEPATH" | cut -f1)
echo "[backup] 完成：$FILENAME（$SIZE）"

# ── GPG 加密（若有設定 BACKUP_GPG_RECIPIENT）────────────────────────────────
FINAL_FILEPATH="$FILEPATH"
if [ -n "$BACKUP_GPG_RECIPIENT" ]; then
  echo "[backup] 使用 GPG 加密（收件人：$BACKUP_GPG_RECIPIENT）..."
  gpg --batch --yes --trust-model always \
    --recipient "$BACKUP_GPG_RECIPIENT" \
    --output "${FILEPATH}.gpg" \
    --encrypt "$FILEPATH"
  rm -f "$FILEPATH"
  FINAL_FILEPATH="${FILEPATH}.gpg"
  echo "[backup] 加密完成：$(basename "$FINAL_FILEPATH")"
fi

# ── 產生 sha256sum 完整性校驗檔 ─────────────────────────────────────────────
CHECKSUM_FILE="${FINAL_FILEPATH}.sha256"
sha256sum "$FINAL_FILEPATH" > "$CHECKSUM_FILE"
echo "[backup] 校驗碼已寫入：$(basename "$CHECKSUM_FILE")"

# ── 驗證剛寫入的備份完整性 ────────────────────────────────────────────────
if sha256sum --check "$CHECKSUM_FILE" > /dev/null 2>&1; then
  echo "[backup] 完整性驗證通過。"
else
  echo "[backup] 錯誤：完整性驗證失敗，備份可能已損壞！" >&2
  exit 1
fi

# ── 清除超過保留天數的舊備份 ────────────────────────────────────────────────
echo "[backup] 清除 ${RETAIN_DAYS} 天前的舊備份..."
find "$BACKUP_DIR" -name "rasa_knowledge_*.sql.gz" -mtime +"$RETAIN_DAYS" -delete
find "$BACKUP_DIR" -name "rasa_knowledge_*.sql.gz.gpg" -mtime +"$RETAIN_DAYS" -delete
find "$BACKUP_DIR" -name "rasa_knowledge_*.sha256" -mtime +"$RETAIN_DAYS" -delete
REMAINING=$(find "$BACKUP_DIR" \( -name "rasa_knowledge_*.sql.gz" -o -name "rasa_knowledge_*.sql.gz.gpg" \) | wc -l)
echo "[backup] 目前保留 ${REMAINING} 個備份檔案。"
