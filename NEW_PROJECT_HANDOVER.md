# AEV-v2c 新專案部署交接（2026-08-16）

> ⚠️ 本文件含機敏資訊（VM DB 密碼、SECRET_KEY），僅供自己使用，勿外流。
> 用途：貼到新專案（另一份 AEV-v2c）的 DSH 會話當起始 prompt，進行新的 Azure VM 部署與認證狀態確認。

## 0. 給新會話的起始 prompt（直接複製貼上）

```
你是 AEV-v2c 的開發 agent。請閱讀本交接內容後，依序完成：
1. 在此專案目錄建好環境（git clone / venv / requirements）
2. 用 Terraform 佈建一台「新」的 Azure VM（project_name 用 aev2 避免與舊資源衝突）
3. 部署應用程式 + 初始化資料庫
4. 確認兩層認證狀態：Azure CLI 登入 與 應用層 JWT 認證（register/login/me 實測）
5. 回報基線（import_smoke_test / pytest / api_db_test）
```

## 1. 帳號與認證現況

| 項目 | 值 |
|---|---|
| GitHub 帳號 | `goodchang77` |
| Repo | `https://github.com/goodchang77/AEV-v2c.git`（private，main 分支，HEAD=`353fb07`） |
| gh 登入 | ✅ 已登入（`gho_` token，已含 workflow scope，可 push `.github/workflows/`） |
| Azure 訂閱 | `Azure subscription 1` = `1259c653-26f1-454f-8713-25d143896a0c`，tenant `b857b170-973e-4438-b2a8-14129e43311a` |
| Azure CLI | ✅ 已登入（WSL 無瀏覽器，用 `az login --use-device-code` 登入） |
| 本機 SSH | ✅ 可連 `azureuser@20.46.165.115`（金鑰認證） |
| ⚠️ 待撤銷 | 曾外洩一組 classic PAT（`ghp_N1fK5jue...`，Note=`aev-push`）→ 到 https://github.com/settings/tokens 撤銷 |

## 2. 現有環境（參考，新專案不要動它）

- **舊 VM**：`20.46.165.115`（resource group `aev-rg`，japaneast，Standard_D2s_v3，Premium SSD 64GB）
  - Docker 29.7.2 + compose v5.4.0；三個容器 healthy：financial-api / financial-postgres / financial-redis
  - 程式碼在 VM `~/aev-v2c`（rsync 上去的，**沒有 .git**）
  - VM env 檔 `deploy/azure/.env.production`：`POSTGRES_PASSWORD=9c337e5db6d1b0a1f888de4a3c4d32c3`、`SECRET_KEY=f8c611e39508716bc6f1f9d4a7ce6c9d09bbe4dbbe7b6b256a846e15428d1cf1`（新 VM 可用相同值，或重產一組新的）
- **開發工作區**：`/home/gc/Project`（venv Python 3.11.15、基線全綠）
- **基線**：import_smoke_test **51/51**、pytest **104 passed, 2 skipped**、api_db_test **9/9**
- **前端**：`/static/index.html`（Palantir 風格儀表板，含登入/投資組合/報告/蒙地卡羅等 7 工作區）

## 3. 新專案目錄設定

```bash
git clone https://github.com/goodchang77/AEV-v2c.git ~/AEV-v2c-new   # 或你的新目錄名
cd ~/AEV-v2c-new
python3.11 -m venv venv && source venv/bin/activate   # WSL 需先裝 python3.11（uv python install 3.11）
python -m pip install -r requirements.txt             # 注意 bcrypt==4.0.1 已 pin（passlib 相容性）
cp .env.example .env 2>/dev/null; ls
```

## 4. 新 Azure VM（Terraform）——關鍵：project_name 改 `aev2`

舊資源用了 `aev-*` 名稱，新部署**一定要改 project_name**，否則 Terraform 會撞名：

```bash
cd deploy/azure/terraform
cp terraform.tfvars.example terraform.tfvars
# 編輯 terraform.tfvars：
#   project_name = "aev2"          ← 必改！
#   location     = "japaneast"     # 或試 southeastasia/eastasia
#   vm_size      = "Standard_D2s_v3"   # B2ms 在 japaneast 曾缺容量；先 az vm list-skus 確認
#   ssh_public_key_path = "~/.ssh/id_rsa.pub"
#   ssh_source_cidr = "<你的對外IP>/32"   # curl -s ifconfig.me 查

az login --use-device-code            # 若還沒登入
az account set -s 1259c653-26f1-454f-8713-25d143896a0c
terraform init
terraform plan
terraform apply
terraform output vm_public_ip        # 新 VM IP
```

注意：cloud-init 只有裝 apt 套件，**Docker 常沒裝成功**，開機後手動補：

```bash
ssh azureuser@<新IP> 'bash -s' <<'EOF'
curl -fsSL https://get.docker.com | sudo sh
sudo apt-get update -y && sudo apt-get install -y docker-compose-plugin
sudo usermod -aG docker azureuser
docker --version && docker compose version
EOF
```

## 5. 部署應用 + 資料庫種子

```bash
# 本機（新專案根目錄）
rsync -az --delete \
  --exclude '.git/' --exclude 'venv/' --exclude '__pycache__/' \
  --exclude '.pytest_cache/' --exclude '.env' --exclude '.env.local' \
  --exclude '.env.production' \      # ← 必加！否則 --delete 會把 VM 的 env 檔刪掉（踩過雷）
  ./ azureuser@<新IP>:~/aev-v2c/

# VM 上建 env 檔（可沿用上面舊值或新產：openssl rand -hex 16 / 32）
ssh azureuser@<新IP> 'bash -s' <<'EOF'
cd ~/aev-v2c
cp deploy/azure/.env.production.example deploy/azure/.env.production
nano deploy/azure/.env.production   # 填 POSTGRES_PASSWORD、SECRET_KEY、ALPHA_VANTAGE_API_KEY
EOF

# 啟動 + 種子
ssh azureuser@<新IP> 'cd ~/aev-v2c && sudo docker compose -f docker-compose.azure.yml --env-file deploy/azure/.env.production up -d --build'
ssh azureuser@<新IP> 'cd ~/aev-v2c && sudo docker compose -f docker-compose.azure.yml --env-file deploy/azure/.env.production exec financial-api python scripts/init_db.py'

curl http://<新IP>:8000/health   # {"status":"healthy",...}
```

## 6. 應用層認證（JWT）狀態確認

```bash
IP=<新IP>

# 1) 健康檢查
curl http://$IP:8000/health

# 2) 註冊（回 JWT）
curl -s -X POST http://$IP:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"tester","email":"tester@example.com","password":"password123"}' | head -c 300

# 3) 登入並存 token
TOKEN=$(curl -s -X POST http://$IP:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"tester","password":"password123"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
echo $TOKEN

# 4) /me（帶 token → 200；不帶 → 401）
curl -s http://$IP:8000/api/v1/auth/me -H "Authorization: Bearer $TOKEN"
curl -s -o /dev/null -w "%{http_code}\n" http://$IP:8000/api/v1/auth/me   # 期望 401

# 5) RBAC：一般用戶存取 admin 端點 → 期望 403
curl -s -o /dev/null -w "%{http_code}\n" http://$IP:8000/api/v1/auth/users -H "Authorization: Bearer $TOKEN"

# 6) 投資組合（需登入）增刪查
curl -s -X POST http://$IP:8000/api/v1/portfolio/positions -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"company_id":"2330","shares":1000,"cost_basis":500,"current_price":1000}'
curl -s http://$IP:8000/api/v1/portfolio/summary -H "Authorization: Bearer $TOKEN" | head -c 400
```

預期：register/login/me=200、me 無 token=401、users 一般用戶=403、portfolio 正常。

## 7. 基線驗證（新專案本機）

```bash
python scripts/import_smoke_test.py        # 51/51
python -m pytest tests/ -q -W ignore       # 104 passed, 2 skipped
python scripts/api_db_test.py              # 9/9（需本機 DB；或用 VM 的）
```

## 8. 安全待辦（新舊專案都適用）

1. **撤銷外洩 PAT**：https://github.com/settings/tokens（`aev-push`）——已貼在對話中過，必須撤。
2. **輪替 Alpha Vantage key**：歷史已抹除但 key 曾公開；到 Alpha Vantage 停舊發新，更新 `.env` 與 VM 的 `.env.production` 的 `ALPHA_VANTAGE_API_KEY`。
3. 新 VM 的 SSH 規則別用 `0.0.0.0/0`（舊 VM 目前是開的）；用你自己的 IP `/32`。
4. 每日備份：VM 上 `bash deploy/azure/backup.sh` + crontab（README 有寫法）。

## 9. 排障速查

- **SSH timeout**：家用動態 IP 變了 → `MYIP=$(curl -s ifconfig.me) && az network nsg rule update -g <rg> --nsg-name <project>-nsg --name SSH --source-address-prefix "${MYIP}/32"`
- **VM 上 git 指令失敗**：VM 的 `~/aev-v2c` 沒有 `.git`（rsync 上去的），程式碼一律 rsync 更新。
- **`docker compose` not found**：compose plugin 沒裝（cloud-init 沒成功）→ 手動裝，見 §4。
- **SkuNotAvailable**：該區缺容量 → `az vm list-skus --location <region> --size <SKU> -o table` 查，換 `Standard_D2s_v3` 或 `Standard_D2as_v4`。
- **API 500「Event loop is closed」**：Redis 快取跨 event loop bug——已在 `src/core/cache.py` 修復（loop-aware 重連），新程式碼已含此修正。
- **`api_db_test` 8/9**：檢查 404 case 用的公司是否有財務資料（現用 1301，無資料→404 正確）。
