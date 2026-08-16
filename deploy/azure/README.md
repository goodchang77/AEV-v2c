# Azure VM 部署（Docker + docker-compose 整包）

單一 Azure VM 跑整套：API + PostgreSQL + Redis。

提供兩種方式：(A) Terraform 佈建（推薦）與 (B) 手動建 VM。

## 前置

- Azure 訂閱 + [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)（`az login`）。
- [Terraform](https://developer.hashicorp.com/terraform/install) ≥ 1.0。
- 本機（你的開發機）：`rsync`、`ssh`、SSH 金鑰（`~/.ssh/id_rsa.pub`）。

---

## A. Terraform 佈建（推薦）

Terraform 會自動建立：資源群組、VNet/子網路、NSG、公用 IP、Ubuntu 22.04 VM，
並用 cloud-init 在 VM 開機時裝好 Docker。

```bash
cd deploy/azure/terraform

# 1. 準備變數
cp terraform.tfvars.example terraform.tfvars
#    編輯：location、admin_username、ssh_public_key_path、
#    ssh_source_cidr（建議改成自己的對外 IP，例如 1.2.3.4/32）

# 2. 登入 Azure
az login

# 3. 佈建
terraform init
terraform plan          # 預覽會建立的資源
terraform apply         # 輸入 yes 確認

# 4. 取得 VM IP
terraform output vm_public_ip
```

> ⚠️ `terraform.tfvars` 與 `terraform.tfstate` 可能含機敏資訊，已在 `.gitignore` 防護，勿 commit。

## B. 部署應用程式（兩種方式共用）

佈建完 VM（或手動建好 VM）後，從本機部署程式碼：

```bash
cd <專案根目錄>

# 1. 在 VM 上準備環境檔（第一次）
ssh azureuser@<VM_IP> "mkdir -p ~/aev-v2c && cd ~/aev-v2c 2>/dev/null; exit 0"
#   先跑一次 deploy.sh，它會把專案 rsync 上去；或手動：
#   rsync -az --exclude .git --exclude venv ./ azureuser@<VM_IP>:~/aev-v2c/
ssh azureuser@<VM_IP> "cd ~/aev-v2c && cp deploy/azure/.env.production.example deploy/azure/.env.production"
#   編輯 ~/aev-v2c/deploy/azure/.env.production：
#   至少改 POSTGRES_PASSWORD、SECRET_KEY（openssl rand -hex 32）、API keys

# 2. 部署
deploy/azure/deploy.sh <VM_IP> azureuser
```

之後每次改完程式碼，重跑 `deploy/azure/deploy.sh <VM_IP> azureuser` 即可（rsync 同步 + rebuild）。

## 存取

- API：`http://<VM_IP>:8000`（`/health`、`/docs`、`/api/v1/...`）
- Azure NSG 需放行 8000/tcp。

## 上線前再補

- **HTTPS**：加 Nginx + Let's Encrypt（或 Azure 前面掛 Application Gateway / Front Door）。
- **監控**：需要時再啟用 `docker-compose.prod.yml` 裡的 Prometheus/Grafana。
- **首次種入 2330 範例財務資料**（選用）：
  ```bash
  docker compose -f docker-compose.azure.yml --env-file deploy/azure/.env.production exec financial-api python scripts/init_db.py
  ```

## 資料庫每日備份（建議上線必做）

```bash
# VM 上手動跑一次
cd ~/aev-v2c && bash deploy/azure/backup.sh

# 排程：每天凌晨 2 點自動備份（保留 14 天）
crontab -e
# 加入這行：
# 0 2 * * * cd ~/aev-v2c && bash deploy/azure/backup.sh >> ~/backups/backup.log 2>&1

# 還原（例如災難復原時）
bash deploy/azure/restore.sh ~/backups/aev_backup_20260816_020000.sql.gz
```
