#!/usr/bin/env bash
# 資料庫每日備份（在 Azure VM 上執行）
# 用法:
#   bash deploy/azure/backup.sh
# 環境變數:
#   BACKUP_DIR      備份目錄（預設 ~/backups）
#   RETENTION_DAYS  保留天數（預設 14）
set -euo pipefail
# 備份檔含完整資料庫內容：只允許擁有者讀寫
umask 077

BACKUP_DIR="${BACKUP_DIR:-$HOME/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-financial_analysis}"

# 本腳本位於 <repo>/deploy/azure/，專案根目錄是上兩層
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.azure.yml"
ENV_FILE="$PROJECT_ROOT/deploy/azure/.env.production"

[ -f "$COMPOSE_FILE" ] || { echo "❌ 找不到 $COMPOSE_FILE" >&2; exit 1; }
[ -f "$ENV_FILE" ] || { echo "❌ 找不到 $ENV_FILE" >&2; exit 1; }

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
TS=$(date +%Y%m%d_%H%M%S)
OUT="$BACKUP_DIR/aev_backup_${TS}.sql.gz"
TMP="$(mktemp "$BACKUP_DIR/.aev_backup_${TS}.XXXXXX")"
trap 'rm -f "$TMP"' EXIT

echo "==> 備份 $POSTGRES_DB 到 $OUT"
cd "$PROJECT_ROOT"
# 先寫入暫存檔；pg_dump 或 gzip 任一失敗（pipefail）就中止，不會留下不完整的正式備份檔
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" \
  exec -T postgres pg_dump -U "$POSTGRES_USER" --clean --if-exists "$POSTGRES_DB" \
  | gzip > "$TMP"

gzip -t "$TMP"
mv -f "$TMP" "$OUT"
trap - EXIT

echo "✅ 備份完成: $OUT ($(du -h "$OUT" | cut -f1))"

# 清理超過保留天數的備份
find "$BACKUP_DIR" -name 'aev_backup_*.sql.gz' -mtime "+${RETENTION_DAYS}" -delete
echo "    保留最近 ${RETENTION_DAYS} 天，目前:"
ls -lh "$BACKUP_DIR" | tail -n +2

# （選用）上傳 Azure Blob（先建 container：az storage container create -n db-backups --account-name <name>）
# az storage blob upload --account-name <storage_name> --container-name db-backups \
#   --name "aev_backup_${TS}.sql.gz" --file "$OUT" --auth-mode login
