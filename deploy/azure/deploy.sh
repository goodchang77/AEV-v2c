#!/usr/bin/env bash
# 部署 AEV-v2c 到 Azure VM（Docker + docker-compose 整包）
#
# 前置：VM 上已跑過 bootstrap.sh（裝好 Docker）
# 用法：
#   ./deploy.sh <VM_IP或主機別名> [ssh使用者]
# 例：
#   ./deploy.sh 20.123.45.67 azureuser
set -euo pipefail

VM="${1:?用法: ./deploy.sh <VM_IP|host> [ssh使用者]}"
SSH_USER="${2:-azureuser}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REMOTE_DIR="~/aev-v2c"

echo "==> 同步專案到 ${SSH_USER}@${VM}:${REMOTE_DIR}"
rsync -az --delete \
  --exclude '.git/' \
  --exclude 'venv/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '.pytest_cache/' \
  --exclude '.env' \
  --exclude '.env.production' \
  "$PROJECT_ROOT/" "${SSH_USER}@${VM}:${REMOTE_DIR}/"

echo "==> 確認環境檔存在（deploy/azure/.env.production）"
ssh "${SSH_USER}@${VM}" "test -f ${REMOTE_DIR}/deploy/azure/.env.production" || {
  echo "❌ 缺少 deploy/azure/.env.production"
  echo "   請先在 VM 上執行:"
  echo "     cd ${REMOTE_DIR} && cp deploy/azure/.env.production.example deploy/azure/.env.production"
  echo "   然後編輯填入 POSTGRES_PASSWORD / SECRET_KEY / API keys"
  exit 1
}

echo "==> 建置並啟動服務（--build）"
ssh "${SSH_USER}@${VM}" "cd ${REMOTE_DIR} && \
  docker compose -f docker-compose.azure.yml --env-file deploy/azure/.env.production up -d --build"

echo "==> 健康檢查"
ssh "${SSH_USER}@${VM}" "curl -fsS http://localhost:8000/health && echo || true"

echo "✅ 部署完成。外部存取: http://${VM}:8000"
