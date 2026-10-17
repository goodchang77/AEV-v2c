#!/usr/bin/env bash
# 部署 AEV-v2c 到 Azure VM（Docker + docker-compose 整包）
#
# 前置：VM 上已跑過 bootstrap.sh（或 Terraform cloud-init）裝好 Docker
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
# 安全：絕不同步本機的環境檔 / 金鑰 / Terraform 狀態 / 備份 / 上傳檔。
# 注意 --delete 會刪除遠端多出的檔案，但「被 exclude 的路徑」不會被刪除，
# 因此 VM 上的 deploy/azure/.env.production 會被保留。
# rsync 規則「先符合者優先」：範本檔的 --include 必須放在 '.env.*' 的 --exclude 之前。
rsync -az --delete \
  --include '.env.example' \
  --include '.env.production.example' \
  --exclude '.git/' \
  --exclude '.github/' \
  --exclude '.claude/' \
  --exclude '.dsh/' \
  --exclude 'venv/' \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '.pytest_cache/' \
  --exclude 'node_modules/' \
  --exclude '.env' \
  --exclude '.env.*' \
  --exclude '.env.production' \
  --exclude '*.pem' \
  --exclude '*.key' \
  --exclude '.terraform/' \
  --exclude '*.tfstate' \
  --exclude '*.tfstate.*' \
  --exclude '*.tfvars' \
  --exclude '*.tfvars.json' \
  --exclude 'tfplan' \
  --exclude '*.tfplan' \
  --exclude 'backups/' \
  --exclude '*.sql.gz' \
  --exclude '*.dump' \
  --exclude 'uploads/' \
  --exclude 'logs/' \
  "$PROJECT_ROOT/" "${SSH_USER}@${VM}:${REMOTE_DIR}/"

echo "==> 確認環境檔存在（deploy/azure/.env.production）"
ssh "${SSH_USER}@${VM}" "test -f ${REMOTE_DIR}/deploy/azure/.env.production" || {
  echo "❌ 缺少 deploy/azure/.env.production"
  echo "   請先在 VM 上執行:"
  echo "     cd ${REMOTE_DIR} && cp deploy/azure/.env.production.example deploy/azure/.env.production"
  echo "     chmod 600 deploy/azure/.env.production"
  echo "   然後編輯填入 SECRET_KEY / POSTGRES_PASSWORD / REDIS_PASSWORD / ALLOWED_HOSTS / ALLOWED_ORIGINS"
  exit 1
}

echo "==> 建置並啟動服務（--build）"
ssh "${SSH_USER}@${VM}" "cd ${REMOTE_DIR} && \
  docker compose -f docker-compose.azure.yml --env-file deploy/azure/.env.production up -d --build"

HEALTH_RETRIES="${HEALTH_RETRIES:-12}"
HEALTH_INTERVAL="${HEALTH_INTERVAL:-5}"
echo "==> 健康檢查（VM 本機 127.0.0.1:8000，最多重試 ${HEALTH_RETRIES} 次）"
ok=0
for i in $(seq 1 "$HEALTH_RETRIES"); do
  if ssh "${SSH_USER}@${VM}" "curl -fsS --max-time 5 http://127.0.0.1:8000/health" > /dev/null; then
    ok=1
    break
  fi
  echo "    第 ${i}/${HEALTH_RETRIES} 次失敗，${HEALTH_INTERVAL}s 後重試..."
  sleep "$HEALTH_INTERVAL"
done

if [ "$ok" -ne 1 ]; then
  echo "❌ 健康檢查失敗。請在 VM 上查看：" >&2
  echo "   cd ${REMOTE_DIR} && docker compose -f docker-compose.azure.yml --env-file deploy/azure/.env.production logs --tail=100 financial-api" >&2
  exit 1
fi

echo "✅ 部署完成（API 只監聽 VM 的 127.0.0.1:8000）。"
echo "   管理存取：ssh -N -L 8000:127.0.0.1:8000 ${SSH_USER}@${VM}  → 本機開 http://127.0.0.1:8000/docs"
echo "   對外存取：請在 VM 上設定 TLS 反向代理（443 → 127.0.0.1:8000），並用 https://<你的網域>"
