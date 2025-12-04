# 🚀 GCP 財務分析系統部署指南

## 快速開始

### 📋 準備工作

1. **安裝必要工具**
   ```bash
   # 安裝 Google Cloud SDK
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   
   # 安裝 Terraform
   wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
   echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
   sudo apt update && sudo apt install terraform
   ```

2. **建立 GCP 專案**
   ```bash
   # 建立新專案 (可選)
   gcloud projects create YOUR-PROJECT-ID --name="Financial Analysis System"
   
   # 選擇專案
   gcloud config set project YOUR-PROJECT-ID
   
   # 啟用計費 (必須)
   # 請到 GCP Console 手動啟用計費帳戶
   ```

### 🚀 一鍵部署

```bash
# 1. 設定環境變數
export PROJECT_ID="your-gcp-project-id"

# 2. 執行自動化部署腳本
cd /mnt/d/Project/AEV-v2c
./deploy/gcp/deploy.sh
```

### 📋 部署步驟說明

腳本會自動執行以下步驟：

1. ✅ **檢查部署工具** - 驗證 gcloud, terraform, docker
2. ✅ **設定 GCP 專案** - 配置專案和身份認證
3. ✅ **啟用必要 API** - 自動啟用所需的 GCP 服務
4. ✅ **建立基礎設施** - 使用 Terraform 創建資源
5. ✅ **建構 Docker 映像** - 建構並推送到 GCR
6. ✅ **部署到 App Engine** - 自動化應用程式部署
7. ✅ **設定監控** - 配置 Cloud Monitoring
8. ✅ **驗證部署** - 檢查應用程式健康狀態

### 🏗️ 建立的 GCP 資源

| 服務 | 規格 | 用途 |
|------|------|------|
| **App Engine Flexible** | 1 CPU, 2GB RAM | 主應用程式託管 |
| **Cloud SQL PostgreSQL** | db-f1-micro (0.6GB RAM) | 主資料庫 |
| **Memory Store Redis** | 1GB | 快取服務 |
| **VPC Network** | 10.0.0.0/16 | 私有網路 |
| **Secret Manager** | - | API 金鑰管理 |
| **Cloud Monitoring** | - | 監控和告警 |
| **Container Registry** | - | Docker 映像儲存 |

### 💰 預估成本 (開發環境)

- **App Engine**: ~$30-50/月
- **Cloud SQL**: ~$15-25/月  
- **Memory Store Redis**: ~$25/月
- **其他服務**: ~$5-10/月
- **總計**: ~$75-110/月

### 🔍 部署後檢查

```bash
# 檢查應用程式狀態
gcloud app instances list

# 查看應用程式日誌
gcloud app logs tail -s default

# 檢查健康狀態
curl https://YOUR-PROJECT-ID.appspot.com/health

# 測試 API 端點
curl https://YOUR-PROJECT-ID.appspot.com/api/v1/market/v2/quote/2330
```

### 🔧 管理指令

```bash
# 更新應用程式
gcloud app deploy

# 查看服務狀態
gcloud app services list

# 停止舊版本
gcloud app versions stop VERSION_ID

# 查看監控指標
gcloud alpha monitoring metrics list
```

### 📊 存取服務

- **應用程式**: https://YOUR-PROJECT-ID.appspot.com
- **API 文檔**: https://YOUR-PROJECT-ID.appspot.com/docs
- **健康檢查**: https://YOUR-PROJECT-ID.appspot.com/health
- **GCP Console**: https://console.cloud.google.com/appengine?project=YOUR-PROJECT-ID

### 🛠️ 故障排除

#### 部署失敗
```bash
# 檢查 Cloud Build 日誌
gcloud builds log --region=asia-east1

# 檢查 App Engine 日誌
gcloud app logs tail -s default --level=error
```

#### 資料庫連線問題
```bash
# 檢查 Cloud SQL 狀態
gcloud sql instances describe financial-db-instance

# 測試資料庫連線
gcloud sql connect financial-db-instance --user=financial_user
```

#### API 回應慢
```bash
# 檢查實例狀態
gcloud app instances list

# 查看監控指標
gcloud alpha monitoring metrics list --filter="metric.type:appengine"
```

### 🔒 安全性檢查

- ✅ 私有 VPC 網路配置
- ✅ SSL/TLS 加密傳輸
- ✅ Secret Manager 金鑰管理
- ✅ IAM 最小權限原則
- ✅ 定期安全更新

### 📈 擴展選項

當需要升級到生產環境時：

1. **垂直擴展**: 增加 CPU/記憶體
2. **水平擴展**: 增加實例數量
3. **資料庫升級**: 使用高可用配置
4. **CDN**: 配置 Cloud CDN
5. **多區域**: 跨區域部署

---

## 🎉 恭喜！

您的財務分析系統現在已經在 GCP 上運行！

**下一步建議**:
1. 配置自定義域名
2. 設定 SSL 憑證
3. 配置 CI/CD 流程
4. 增加更多監控指標
5. 設定定期備份策略