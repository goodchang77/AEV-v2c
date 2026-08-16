---
name: aev-deploy
description: 部署 AEV-v2c 到 Azure VM（rsync 同步 + docker compose 重建 + 驗證）的標準步驟
whenToUse: 當使用者要求部署、更新或重啟 Azure VM 上的 AEV-v2c 服務時使用
---

# AEV-v2c Azure 部署流程

目標 VM：`azureuser@20.46.165.115`（可用時更新）。

## 標準部署（程式碼有變更時）

1. 從本機專案根目錄（`~/AEV-v2c` 或 `/home/gc/Project`）執行：
   ```bash
   rsync -az --delete \
     --exclude '.git/' --exclude 'venv/' --exclude '__pycache__/' \
     --exclude '.pytest_cache/' --exclude '.env' --exclude '.env.local' \
     --exclude '.env.production' \
     ./ azureuser@20.46.165.115:~/aev-v2c/
   ```
2. 在 VM 上重建並啟動：
   ```bash
   ssh azureuser@20.46.165.115 'cd ~/aev-v2c && sudo docker compose -f docker-compose.azure.yml --env-file deploy/azure/.env.production up -d --build'
   ```
3. 健康檢查（API 剛啟動可能被 reset，重試幾次）：
   ```bash
   curl http://20.46.165.115:8000/health
   ```

## 資料庫種子（首次或新增樣本時）

```bash
ssh azureuser@20.46.165.115 'cd ~/aev-v2c && sudo docker compose -f docker-compose.azure.yml --env-file deploy/azure/.env.production exec financial-api python scripts/init_db.py'
```

## 排障

- container 狀態：`ssh ... 'sudo docker compose -f docker-compose.azure.yml --env-file deploy/azure/.env.production ps'`
- API 錯誤日誌：`ssh ... 'sudo docker compose -f docker-compose.azure.yml --env-file deploy/azure/.env.production logs financial-api --tail 30'`
- SSH 連不上：通常是家用動態 IP 變了 → `MYIP=$(curl -s ifconfig.me) && az network nsg rule update -g aev-rg --nsg-name aev-nsg --name SSH --source-address-prefix "${MYIP}/32"`

## 注意

- VM 上的 `~/aev-v2c` 是 rsync 過去的，**沒有 `.git`**，不要在上面跑 git 指令。
- 備份：`bash deploy/azure/backup.sh`（建議加每日 cron）。
