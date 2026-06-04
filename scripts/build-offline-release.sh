#!/usr/bin/env bash
# build-offline-release.sh — 在開發機產出客戶部署離線包。
#
# Usage:
#   ./scripts/build-offline-release.sh v1.0.0
#
# 產物：dist/rasa_manager-<version>-offline.tar.gz
#   ├─ images/{backend,frontend,db,redis}.tar  ← docker save 過的 image
#   ├─ docker-compose.yml                       ← production 用
#   ├─ .env.example                             ← 環境變數範本
#   ├─ install.sh                               ← 客戶端執行的安裝腳本
#   ├─ uninstall.sh                             ← 反向操作
#   └─ README.md                                ← 客戶部署 SOP（DEPLOY-CUSTOMER.md）
#
# 客戶端只需：
#   tar xzf rasa_manager-v1.0.0-offline.tar.gz
#   cd rasa_manager-v1.0.0
#   sudo ./install.sh
set -euo pipefail

VERSION="${1:?usage: $0 <version>  例：$0 v1.0.0}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_NAME="rasa_manager-${VERSION}"
OUT_DIR="${ROOT}/dist/${OUT_NAME}"

echo "== 1/5 Build docker images（含 frontend + backend）=="
cd "$ROOT"
docker compose build --pull

echo "== 2/5 整理輸出目錄 ${OUT_DIR} =="
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR/images"

echo "== 3/5 docker save 四個 image（含 base image，避免客戶 pull）=="
# 專案自建 image（local build）
docker save -o "$OUT_DIR/images/backend.tar"  rasa_rag-backend:latest
docker save -o "$OUT_DIR/images/frontend.tar" rasa_rag-frontend:latest
# 基礎 image（從 hub pull）— 客戶 load 後 compose pull 不會打外網
docker save -o "$OUT_DIR/images/postgres.tar" postgres:15
docker save -o "$OUT_DIR/images/redis.tar"    redis:7

echo "== 4/5 複製部署檔案 =="
cp "$ROOT/docker-compose.yml" "$OUT_DIR/"
cp "$ROOT/.env.example"       "$OUT_DIR/.env.example"
cp "$ROOT/scripts/install.sh"   "$OUT_DIR/install.sh"
cp "$ROOT/scripts/uninstall.sh" "$OUT_DIR/uninstall.sh" 2>/dev/null || true
cp "$ROOT/DEPLOY-CUSTOMER.md"  "$OUT_DIR/README.md"
chmod +x "$OUT_DIR/install.sh"
[ -f "$OUT_DIR/uninstall.sh" ] && chmod +x "$OUT_DIR/uninstall.sh"

# 寫入版本資訊
cat > "$OUT_DIR/VERSION" <<EOF
RASA_MANAGER_VERSION=${VERSION}
BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF

echo "== 5/5 打包 tar.gz =="
cd "${ROOT}/dist"
tar czf "${OUT_NAME}-offline.tar.gz" "${OUT_NAME}"
RELEASE="${ROOT}/dist/${OUT_NAME}-offline.tar.gz"
echo ""
echo "完成：${RELEASE}"
echo "大小：$(du -h "$RELEASE" | cut -f1)"
echo ""
echo "客戶部署指令："
echo "  scp ${OUT_NAME}-offline.tar.gz root@customer-host:/opt/"
echo "  ssh root@customer-host 'cd /opt && tar xzf ${OUT_NAME}-offline.tar.gz && cd ${OUT_NAME} && sudo ./install.sh'"
