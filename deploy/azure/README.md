# Azure VM 部署（Docker + docker-compose 整包）

單一 Azure VM 跑整套：API + PostgreSQL + Redis。

提供兩種方式：(A) Terraform 佈建（推薦）與 (B) 手動建 VM。

## 安全預設（請先讀）

- **API 只監聽 VM 的 `127.0.0.1:8000`**，不再以明文 HTTP 對外公開。對外存取必須經由 VM 上的
  **TLS 反向代理**（Nginx / Caddy，443 → `127.0.0.1:8000`）或 Azure Application Gateway / Front Door；
  管理者可用 **SSH tunnel** 存取。
- **NSG 預設只放行 SSH**，且 `ssh_source_cidr` **必填**、不可為 `0.0.0.0/0` / `*`。
  443 需以 `https_source_cidrs` 明確指定來源（`[]` = 不開）；80 預設不開。
- PostgreSQL / Redis **不發布任何 host port**；Redis 啟用密碼。
- 生產環境變數 **`ENVIRONMENT=production`**（compose 已固定）。缺少 `SECRET_KEY`、`POSTGRES_PASSWORD`、
  `REDIS_PASSWORD`、`ALLOWED_HOSTS`、`ALLOWED_ORIGINS` 任一項時 `docker compose` 會直接報錯；
  應用程式在 production 下也會拒絕以缺漏 / 過短 / 預設值的 `SECRET_KEY` 啟動。
- 資料庫首次初始化**只載入結構 SQL**（`01`、`03`、`04`），**不載入 `02_sample_data.sql`**
  （其中含啟用中的示範 admin/analyst 帳號與固定密碼雜湊）。
- Docker 以官方**已簽章 APT 套件庫**安裝（不再 `curl | sh`）。⚠️ `docker` 群組成員等同 root。

## 前置

- Azure 訂閱 + [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)（`az login`）。
- [Terraform](https://developer.hashicorp.com/terraform/install) ≥ 1.3。
- 本機（你的開發機）：`rsync`、`ssh`、SSH 金鑰（`~/.ssh/id_rsa.pub`）。

---

## A. Terraform 佈建（推薦）

Terraform 會自動建立：資源群組、VNet/子網路、NSG、公用 IP、Ubuntu 22.04 VM，
並用 cloud-init 在 VM 開機時從 Docker 官方簽章套件庫裝好 Docker。

```bash
cd deploy/azure/terraform

# 1. 準備變數
cp terraform.tfvars.example terraform.tfvars
#    編輯：location、admin_username、ssh_public_key_path、
#    ssh_source_cidr（必填：你自己的對外 IP，例如 203.0.113.10/32；可用 curl -4 https://ifconfig.me 查）
#    https_source_cidrs（必填：[] 只用 SSH tunnel；或限定來源；要對全網公開 TLS 站台需明確填 ["0.0.0.0/0"]）

# 2. 登入 Azure
az login

# 3. 佈建
terraform init
terraform plan          # 預覽會建立的資源
terraform apply         # 輸入 yes 確認

# 4. 取得 VM IP 與 SSH tunnel 指令
terraform output vm_public_ip
terraform output ssh_tunnel_command
```

> ⚠️ `terraform.tfvars`、`*.tfvars.json`、`terraform.tfstate*`、`tfplan` 可能含機敏資訊，已在 `.gitignore` 防護，勿 commit。

## B. 部署應用程式（兩種方式共用）

佈建完 VM（或手動建好 VM 並執行 `deploy/azure/bootstrap.sh`）後，從本機部署程式碼：

```bash
cd <專案根目錄>

# 1. 第一次：先跑 deploy.sh 把專案 rsync 上去（會因缺 .env.production 而停下並提示）
deploy/azure/deploy.sh <VM_IP> azureuser

# 2. 在 VM 上建立環境檔
ssh azureuser@<VM_IP>
cd ~/aev-v2c
cp deploy/azure/.env.production.example deploy/azure/.env.production
chmod 600 deploy/azure/.env.production
#   編輯 deploy/azure/.env.production，所有 CHANGE_ME_* 都要替換：
#   - SECRET_KEY / POSTGRES_PASSWORD / REDIS_PASSWORD：各自用 `openssl rand -hex 32` 產生
#   - ALLOWED_HOSTS：反向代理轉發的網域，例如 api.example.com（逗號分隔）
#   - ALLOWED_ORIGINS：前端來源，例如 https://app.example.com（逗號分隔）
exit

# 3. 正式部署（健康檢查失敗會以非零結束碼退出）
deploy/azure/deploy.sh <VM_IP> azureuser
```

`deploy.sh` 不會同步任何 `.env*`（範本 `*.example` 除外）、金鑰、Terraform 狀態 / 變數、備份、上傳檔與 `.git`。
之後每次改完程式碼，重跑 `deploy/azure/deploy.sh <VM_IP> azureuser` 即可（rsync 同步 + rebuild）。

## 存取

- **管理 / 測試（SSH tunnel）**：
  ```bash
  ssh -N -L 8000:127.0.0.1:8000 azureuser@<VM_IP>
  # 另開終端機或瀏覽器：http://127.0.0.1:8000/health 、/docs
  ```
- **對外（TLS）**：在 VM 上安裝 Nginx 或 Caddy，終止 TLS 後 `proxy_pass http://127.0.0.1:8000;`，
  並在 Terraform 設定 `https_source_cidrs`、在 `.env.production` 設定 `ALLOWED_HOSTS` / `ALLOWED_ORIGINS`。
  Let's Encrypt 建議用 DNS-01；若用 HTTP-01，需暫時設定 `http_source_cidrs` 開 80。
- **不要**在 NSG 或 ufw 開 8000。

## 建立管理員帳號（取代示範帳號）

生產資料庫不會有任何預設帳號。安全地建立第一個管理員：

```bash
# 1. 透過 SSH tunnel 呼叫註冊 API（密碼只在你的終端機輸入，不寫進任何檔案或 shell 歷史）
read -r -s -p "Admin password: " ADMIN_PW; echo
curl -fsS -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  --data-binary @- <<EOF
{"username": "<你的帳號>", "email": "<你的 email>", "password": "${ADMIN_PW}"}
EOF
unset ADMIN_PW

# 2. 在 VM 上把該帳號升為 admin（只動這一個帳號）
docker compose -f docker-compose.azure.yml --env-file deploy/azure/.env.production \
  exec -T postgres psql -v ON_ERROR_STOP=1 -U postgres -d financial_analysis \
  -c "UPDATE users SET role = 'admin', is_verified = true WHERE username = '<你的帳號>';"
```

（註冊欄位以 `src/api/endpoints/auth.py` 為準。）

> ⚠️ **不要在生產環境執行 `scripts/init_db.py`**：它在 `companies` 為空時會套用 `02_sample_data.sql`，
> 會建立啟用中的示範 `admin` / `analyst` / `demo_user` 帳號（固定密碼雜湊）。
> 若曾在生產環境載入過示範資料，請立即停用：
> `UPDATE users SET is_active = false WHERE username IN ('admin','analyst','demo_user');`
> （或直接刪除），並確認沒有其他未知帳號。

## 上線前再補

- **HTTPS**：Nginx/Caddy + Let's Encrypt（或 Azure Application Gateway / Front Door），見上方「存取」。
- **監控**：需要時再啟用 `docker-compose.prod.yml` 裡的 Prometheus/Grafana（只綁 127.0.0.1，用 SSH tunnel 存取；
  需設定 `GRAFANA_ADMIN_PASSWORD`；其引用的 `nginx/`、`monitoring/` 設定檔目前尚未存在於 repo）。
- **公司基本資料**：生產環境不會自動載入 `02_sample_data.sql` 的公司清單；如需參考資料，
  請另行匯入（勿連同其中的 `INSERT INTO users` 一起執行）。

## 資料庫每日備份（建議上線必做）

```bash
# VM 上手動跑一次（備份檔權限 600、目錄 700；先寫暫存檔、通過 gzip -t 後才原子性改名）
cd ~/aev-v2c && bash deploy/azure/backup.sh

# 排程：每天凌晨 2 點自動備份（保留 14 天）
crontab -e
# 加入這行：
# 0 2 * * * cd ~/aev-v2c && bash deploy/azure/backup.sh >> ~/backups/backup.log 2>&1

# 還原（例如災難復原時）：會先 gzip -t 驗證，SQL 任一錯誤即中止並整體回滾
bash deploy/azure/restore.sh ~/backups/aev_backup_20260816_020000.sql.gz
```
