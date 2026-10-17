#!/usr/bin/env bash
# 資料庫還原（在 Azure VM 上執行）
# 用法:
#   bash deploy/azure/restore.sh ~/backups/aev_backup_20260816_020000.sql.gz
set -euo pipefail

BACKUP_FILE="${1:?用法: bash deploy/azure/restore.sh <backup.sql.gz>}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-financial_analysis}"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "❌ 找不到備份檔: $BACKUP_FILE" >&2
  exit 1
fi

echo "==> 驗證備份檔完整性（gzip -t）"
if ! gzip -t "$BACKUP_FILE"; then
  echo "❌ 備份檔損毀或不是有效的 gzip，中止還原: $BACKUP_FILE" >&2
  exit 1
fi

# 本腳本位於 <repo>/deploy/azure/，專案根目錄是上兩層
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.azure.yml"
ENV_FILE="$PROJECT_ROOT/deploy/azure/.env.production"

[ -f "$COMPOSE_FILE" ] || { echo "❌ 找不到 $COMPOSE_FILE" >&2; exit 1; }
[ -f "$ENV_FILE" ] || { echo "❌ 找不到 $ENV_FILE" >&2; exit 1; }
cd "$PROJECT_ROOT"

echo "==> 還原 $BACKUP_FILE 到 $POSTGRES_DB"
# ON_ERROR_STOP=1：任何 SQL 錯誤立即中止並回傳非零；--single-transaction：失敗時整體回滾
if ! gunzip -c "$BACKUP_FILE" | docker compose -f "$COMPOSE_FILE" \
  --env-file "$ENV_FILE" \
  exec -T postgres psql -v ON_ERROR_STOP=1 --single-transaction -U "$POSTGRES_USER" -d "$POSTGRES_DB"; then
  echo "❌ 還原失敗（已回滾，資料庫維持原狀）" >&2
  exit 1
fi

echo "✅ 還原完成"
