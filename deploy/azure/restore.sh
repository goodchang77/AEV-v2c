#!/usr/bin/env bash
# 資料庫還原（在 Azure VM 上執行）
# 用法:
#   bash deploy/azure/restore.sh ~/backups/aev_backup_20260816_020000.sql.gz
set -euo pipefail

BACKUP_FILE="${1:?用法: bash deploy/azure/restore.sh <backup.sql.gz>}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-financial_analysis}"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "❌ 找不到備份檔: $BACKUP_FILE"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "==> 還原 $BACKUP_FILE 到 $POSTGRES_DB"
gunzip -c "$BACKUP_FILE" | docker compose -f docker-compose.azure.yml \
  --env-file deploy/azure/.env.production \
  exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

echo "✅ 還原完成"
