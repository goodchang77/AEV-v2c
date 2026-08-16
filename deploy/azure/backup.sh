#!/usr/bin/env bash
# 資料庫每日備份（在 Azure VM 上執行）
# 用法:
#   bash deploy/azure/backup.sh
# 環境變數:
#   BACKUP_DIR      備份目錄（預設 ~/backups）
#   RETENTION_DAYS  保留天數（預設 14）
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-$HOME/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-financial_analysis}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

mkdir -p "$BACKUP_DIR"
TS=$(date +%Y%m%d_%H%M%S)
OUT="$BACKUP_DIR/aev_backup_${TS}.sql.gz"

echo "==> 備份 $POSTGRES_DB 到 $OUT"
cd "$PROJECT_ROOT"
docker compose -f docker-compose.azure.yml --env-file deploy/azure/.env.production \
  exec -T postgres pg_dump -U "$POSTGRES_USER" --clean --if-exists "$POSTGRES_DB" \
  | gzip > "$OUT"

echo "✅ 備份完成: $OUT ($(du -h "$OUT" | cut -f1))"

# 清理超過保留天數的備份
find "$BACKUP_DIR" -name 'aev_backup_*.sql.gz' -mtime "+${RETENTION_DAYS}" -delete
echo "    保留最近 ${RETENTION_DAYS} 天，目前:"
ls -lh "$BACKUP_DIR" | tail -n +2

# （選用）上傳 Azure Blob（先建 container：az storage container create -n db-backups --account-name <name>）
# az storage blob upload --account-name <storage_name> --container-name db-backups \
#   --name "aev_backup_${TS}.sql.gz" --file "$OUT" --auth-mode login
