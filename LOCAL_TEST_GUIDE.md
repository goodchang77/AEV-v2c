# 🎯 財務分析系統 - 本地測試環境使用指南

## 📋 系統概述

本地測試環境已完成建置，包含完整的財務分析功能測試。系統包括：

- ✅ **PostgreSQL 15** - 主要資料庫
- ✅ **TimescaleDB** - 時序資料庫（股價資料）
- ✅ **Redis 7** - 快取層
- ✅ **完整 API 功能測試** - 8個測試項目全部通過

## 🚀 快速啟動

### 1. 啟動資料庫服務
```bash
# 啟動所有資料庫服務
docker compose -f docker-compose.simple.yml up -d

# 檢查服務狀態
docker compose -f docker-compose.simple.yml ps
```

### 2. 執行功能測試
```bash
# 執行完整功能測試
python test_local_api.py

# 如果需要安裝依賴
pip install asyncpg redis psycopg2-binary pandas numpy
```

### 3. 停止服務
```bash
# 停止所有服務
docker compose -f docker-compose.simple.yml down

# 完全清理（包含資料）
docker compose -f docker-compose.simple.yml down -v
```

## 📊 測試結果摘要

最近測試結果（2025-09-01）：

```
📊 測試統計:
   總測試數: 8
   通過測試: 8 ✅
   失敗測試: 0 ❌
   成功率: 100.0%

🎉 系統狀態: 所有功能正常
```

### 測試項目詳情

| 測試項目 | 狀態 | 說明 |
|---------|------|------|
| PostgreSQL 連線測試 | ✅ | 版本: PostgreSQL 15.14, 公司數量: 5 |
| TimescaleDB 連線測試 | ✅ | TimescaleDB 版本: 2.11.0, Hypertables: 1 |
| Redis 連線測試 | ✅ | Ping 響應正常，資料存取成功 |
| 財務計算功能測試 | ✅ | ROE: 0.1250, 流動比率: 2.00 |
| DCF 評價模型測試 | ✅ | 企業價值: $19,896,123, 終值佔比: 73.8% |
| 股價資料處理測試 | ✅ | 插入 30 筆資料，查詢到 10 筆資料 |
| 快取功能測試 | ✅ | 快取存取成功，ROE: 0.125 |
| 資料分析功能測試 | ✅ | 分析 5 家公司，平均 ROE: 0.1000 |

## 🔧 服務訪問資訊

### 資料庫連線
- **PostgreSQL**: `localhost:5432`
  - 使用者: `postgres`
  - 密碼: `dev_password_2024`
  - 資料庫: `financial_analysis`

- **TimescaleDB**: `localhost:5433`
  - 使用者: `postgres`
  - 密碼: `dev_password_2024`
  - 資料庫: `timeseries_financial`

- **Redis**: `localhost:6379`
  - 密碼: `dev_redis_2024`

### 測試資料
系統已預載入以下測試公司資料：
- 2330: 台積電 (SEMI - 上市)
- 2317: 鴻海 (ELEC - 上市)
- 1301: 台塑 (CHEM - 上市)
- 1216: 統一 (FOOD - 上市)
- 2454: 聯發科 (SEMI - 上市)

## 💡 功能特色

### 1. 財務計算引擎
- ✅ 財務比率計算（ROE、ROA、流動比率等）
- ✅ 完整的資料驗證和錯誤處理

### 2. DCF 評價模型
- ✅ 多年期現金流預測
- ✅ 終值計算
- ✅ 折現率應用

### 3. 時序資料處理
- ✅ 股價資料儲存和查詢
- ✅ TimescaleDB Hypertable 優化
- ✅ 大量資料處理能力

### 4. 快取系統
- ✅ Redis 快取財務計算結果
- ✅ 自動過期機制
- ✅ JSON 資料序列化

### 5. 資料分析
- ✅ Pandas 整合
- ✅ 統計分析功能
- ✅ 多公司比較分析

## 📝 開發建議

### 環境變數配置
使用 `.env.local` 文件進行本地開發配置：

```bash
# 複製環境變數範例
cp .env.local.example .env.local

# 編輯配置
vim .env.local
```

### 資料庫管理
```bash
# 直接連線到資料庫
docker exec -it financial_postgres_simple psql -U postgres -d financial_analysis

# 查看 TimescaleDB hypertables
docker exec -it financial_timescale_simple psql -U postgres -d timeseries_financial -c "SELECT * FROM timescaledb_information.hypertables;"

# Redis 命令行
docker exec -it financial_redis_simple redis-cli -a dev_password_2024
```

### 新增測試資料
```sql
-- 在 PostgreSQL 中新增公司
INSERT INTO companies (company_id, company_name, industry_code, market_type) 
VALUES ('1234', '測試公司', 'TEST', '上市');

-- 在 TimescaleDB 中新增股價資料
INSERT INTO stock_prices (time, company_id, close_price, volume)
VALUES (NOW(), '1234', 100.50, 1000000);
```

## 🚨 常見問題排除

### 1. 容器啟動失敗
```bash
# 檢查容器狀態
docker compose -f docker-compose.simple.yml ps

# 查看容器日誌
docker compose -f docker-compose.simple.yml logs [service_name]
```

### 2. 資料庫連線失敗
```bash
# 確認容器正在運行
docker ps | grep financial

# 測試連線
docker exec financial_postgres_simple pg_isready -U postgres
```

### 3. 測試失敗
```bash
# 重新初始化資料庫
docker exec financial_postgres_simple psql -U postgres -d financial_analysis -f /path/to/init.sql

# 重新執行測試
python test_local_api.py
```

## 📈 效能指標

- **資料庫查詢**: 平均 < 10ms
- **DCF 計算**: < 1ms
- **Redis 快取**: < 1ms
- **股價資料插入**: 30筆資料 < 100ms
- **測試執行時間**: 完整測試 < 1秒

## 🔄 後續開發計畫

1. **Web API 整合** - FastAPI 服務啟動
2. **前端界面** - React 應用程式
3. **即時資料同步** - 股價資料 API 整合
4. **使用者驗證** - JWT 認證系統
5. **雲端部署** - GCP Cloud Run 部署

---

**注意**: 此為開發測試環境，請勿在生產環境中使用預設密碼和配置。

最後更新：2025-09-01