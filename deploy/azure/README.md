# Azure VM 部署（Docker + docker-compose 整包）

單一 Azure VM 跑整套：API + PostgreSQL + Redis。

## 前置

- Azure VM：Ubuntu 22.04/24.04（其他 Linux 亦可），有 SSH 登入。
- 本機（你的開發機）：`rsync`、`ssh` 已安裝。

## 步驟

### 1. VM 首次初始化（在 VM 上跑一次）

```bash
# 把 bootstrap.sh 複製到 VM 或用 scp，然後：
bash bootstrap.sh
# 重新登入讓 docker 群組生效
```

### 2. 在 VM 上準備環境檔

```bash
cd ~/aev-v2c                       # deploy.sh 會把專案同步到這裡
cp deploy/azure/.env.production.example deploy/azure/.env.production
# 編輯，至少改：POSTGRES_PASSWORD、SECRET_KEY（openssl rand -hex 32）、API keys
```

### 3. 從本機部署

```bash
cd <專案根目錄>
deploy/azure/deploy.sh <VM_IP> azureuser
```

之後每次改完程式碼，重跑同一行即可（rsync 同步 + rebuild）。

## 存取

- API：`http://<VM_IP>:8000`（`/health`、`/docs`、`/api/v1/...`）
- Azure NSG 需放行 8000/tcp。

## 上線前再補

- **HTTPS**：加 Nginx + Let's Encrypt（或 Azure 前面掛 Application Gateway / Front Door）。
- **監控**：需要時再啟用 `docker-compose.prod.yml` 裡的 Prometheus/Grafana。
- **DB 備份**：定期 `pg_dump`，或改接 Azure Database for PostgreSQL 托管。
- **首次種入 2330 範例財務資料**（選用）：
  ```bash
  docker compose -f docker-compose.azure.yml --env-file deploy/azure/.env.production exec financial-api python scripts/init_db.py
  ```
