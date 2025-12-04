# 財務分析與企業評價系統

基於 IFRS 13 公允價值衡量原則和台灣市場實務的企業級財務分析與評價系統。

## 🚀 快速開始

### 1. 系統需求

- **Docker & Docker Compose** (必要)
- **Python 3.11+**
- **Node.js 18+** (前端開發用)
- **Git**

### 2. 環境設置

```bash
# 克隆專案
git clone <repository-url>
cd AEV-v2c

# 啟動系統
./start.sh
```

### 3. 訪問系統

- **API 服務**: http://localhost:8000
- **API 文檔**: http://localhost:8000/docs  
- **健康檢查**: http://localhost:8000/health
- **資料庫管理**: http://localhost:5050 (pgAdmin)

### 4. 預設帳號

| 角色 | 帳號 | 密碼 |
|------|------|------|
| 系統管理員 | admin@financial-analysis.com | password |
| 財務分析師 | analyst@financial-analysis.com | password |
| 示範用戶 | demo@financial-analysis.com | password |

## 📋 專案結構

```
AEV-v2c/
├── src/                    # 應用程式原始碼
│   ├── api/               # API 路由與端點
│   ├── core/              # 核心功能 (設定、資料庫、日誌)
│   ├── models/            # 資料模型
│   ├── services/          # 業務邏輯服務
│   └── utils/             # 工具函數
├── database/              # 資料庫腳本
│   ├── init/             # 初始化 SQL 腳本
│   └── timescale_init/   # TimescaleDB 初始化腳本
├── tests/                 # 測試程式
├── docs/                  # 技術文檔
└── docker-compose.dev.yml # 開發環境容器配置
```

## 🛠️ 開發指令

```bash
# 啟動完整系統
./start.sh start

# 僅啟動資料庫
./start.sh db

# 僅啟動 API 服務
./start.sh api

# 查看服務狀態
./start.sh status

# 查看服務日誌
./start.sh logs

# 停止所有服務
./start.sh stop

# 重新啟動
./start.sh restart
```

## 🏗️ 架構設計

### 技術棧

- **後端框架**: FastAPI
- **資料庫**: PostgreSQL + TimescaleDB
- **快取**: Redis
- **容器化**: Docker & Docker Compose
- **API 文檔**: OpenAPI/Swagger

### 資料庫設計

#### 主要資料表

1. **companies** - 公司基本資料
2. **financial_statements** - 財務報表資料  
3. **financial_ratios** - 財務比率計算結果
4. **stock_prices** - 股價時序資料 (TimescaleDB)
5. **users** - 用戶管理
6. **user_watchlists** - 用戶追蹤清單

### API 設計

```
/api/v1/
├── /auth          # 認證相關
├── /companies     # 公司資料
├── /financials    # 財務報表  
├── /ratios        # 財務比率
└── /health        # 系統監控
```

## 📊 核心功能

### 1. 財務報表分析
- 資產負債表、損益表、現金流量表
- 財務報表自動驗證與品質檢查
- 多期間財務資料比較

### 2. 財務比率計算
- **償債能力**: 流動比率、速動比率、利息保障倍數
- **獲利能力**: ROE、ROA、毛利率、淨利率
- **經營效率**: 總資產週轉率、存貨週轉率
- **財務結構**: 負債比率、權益比率

### 3. 企業評價模型
- **DCF 模型**: 自由現金流量折現
- **相對評價**: PE、PB、EV/EBITDA
- **股利評價**: DDM 股利折現模型

### 4. 同業比較分析
- 產業基準比較
- 同業排名分析
- 財務指標分位數分析

### 5. 風險評估
- Altman Z-Score 財務危機預警
- 財務風險指標監控
- 資料品質評分

## 🧪 測試

```bash
# 安裝開發依賴
pip install -r requirements-dev.txt

# 運行單元測試
pytest tests/

# 測試覆蓋率
pytest --cov=src tests/

# 程式碼品質檢查
black src/
isort src/
flake8 src/
```

## 📈 監控與日誌

### 健康檢查端點
- `/health` - 基本健康狀態
- `/health/detailed` - 詳細系統狀態

### 日誌記錄
- 結構化日誌 (JSON 格式)
- 請求追蹤
- 效能指標記錄
- 錯誤監控

## 🔒 安全性

### 認證與授權
- JWT Token 認證
- 角色權限控制
- API 請求限流

### 資料安全
- 資料庫連線加密
- 輸入驗證與 SQL 注入防護
- 敏感資料遮罩

## 📝 開發計畫

查看詳細的開發計畫: [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)

### 當前階段: Sprint 1-2 (MVP 基礎架構)

✅ **已完成:**
- [x] Docker 開發環境設置
- [x] 核心資料表架構設計  
- [x] FastAPI 基礎架構建立
- [x] 台股前50大公司資料初始化

🔄 **進行中:**
- [ ] 財務比率計算引擎
- [ ] DCF 評價模型基礎版本
- [ ] 資料驗證與清洗模組
- [ ] 基礎 API 端點實作

## 🤝 貢獻指南

1. Fork 專案
2. 創建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交變更 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 開啟 Pull Request

## 📄 授權

本專案採用 MIT 授權 - 詳見 [LICENSE](LICENSE) 檔案

## 📞 聯絡資訊

- **專案負責人**: [姓名]
- **Email**: [email@example.com]
- **技術文檔**: [連結]

---

*基於現代軟體工程最佳實務與 IFRS 13 準則開發*# AEV-v2c
# AEV-v2c
# AEV-v2c
# AEV-v2c
