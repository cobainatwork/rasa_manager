#!/usr/bin/env bash
# uninstall.sh — 反向移除 Rasa Manager 部署。
# 注意：預設保留資料 volume；加 --purge 才會清除（不可逆）。
set -euo pipefail

cd "$(dirname "$0")"

PURGE=0
if [ "${1:-}" = "--purge" ]; then PURGE=1; fi

echo "==> 停止並移除 container"
docker compose down

if [ "$PURGE" -eq 1 ]; then
    echo "==> --purge：清除 volume + 移除 image（不可逆）"
    read -r -p "確認要清除全部資料？輸入 yes 繼續：" CONFIRM
    [ "$CONFIRM" = "yes" ] || { echo "已取消"; exit 0; }
    docker compose down -v
    docker image rm rasa_rag-backend:latest rasa_rag-frontend:latest 2>/dev/null || true
    echo "已清除"
else
    echo "資料 volume 保留（如需完全清除請執行：./uninstall.sh --purge）"
fi
