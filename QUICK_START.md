# AEV-v2c 快速啟動指南

## ✅ 您的環境變數已經完整設定！

根據檢查，您的 `.env` 檔案已包含所有必要的環境變數：

```env
✓ DATABASE_URL=postgresql://postgres:dev_password_2024@localhost:5432/financial_analysis
✓ REDIS_URL=redis://:dev_redis_2024@localhost:6379
✓ ANTHROPIC_API_KEY=sk-ant-api03-... (已設定)
✓ ANTHROPIC_MODEL=claude-sonnet-4-20250514
✓ MCP_MAX_CONCURRENT_TOOLS=5
✓ MCP_CACHE_ENABLED=true
✓ MCP_CACHE_TTL_SECONDS=3600
```

---

## 🚀 立即啟動系統

### 1. 確認服務正在運行

**PostgreSQL**:
```bash
# Windows (PowerShell)
Get-Service postgresql*

# Linux
systemctl status postgresql
```

**Redis**:
```bash
# Windows
redis-cli ping

# Linux
systemctl status redis
```

### 2. 啟動開發伺服器

#### ⭐ 方式 1: 使用啟動腳本（最簡單，推薦）

**Linux/Mac:**
```bash
cd /d/Project/AEV-v2c
./start_server.sh
```

**Windows:**
```cmd
cd D:\Project\AEV-v2c
start_server.bat
```

啟動腳本會自動：
- ✓ 檢查 Python 環境
- ✓ 驗證必要檔案
- ✓ 設定 PYTHONPATH
- ✓ 啟動伺服器

#### 方式 2: 手動啟動（需要正確的工作目錄）

**重要: 必須在專案根目錄執行！**

```bash
# 1. 切換到專案根目錄
cd /d/Project/AEV-v2c  # Linux/Mac
# 或
cd D:\Project\AEV-v2c  # Windows

# 2. 設定 PYTHONPATH（Linux/Mac）
export PYTHONPATH="${PWD}:${PYTHONPATH}"

# 2. 設定 PYTHONPATH（Windows PowerShell）
$env:PYTHONPATH = "${PWD};$env:PYTHONPATH"

# 3. 啟動伺服器
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

#### 方式 3: 使用 Python 模組方式

```bash
cd /d/Project/AEV-v2c
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

#### 方式 4: 後台運行
nohup uvicorn src.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```

### 3. 訪問 API 文檔

啟動後，開啟瀏覽器訪問：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **健康檢查**: http://localhost:8000/health

---

## 🧪 測試 AI Agent API

### 使用 curl 測試

```bash
# 1. 列出可用工具
curl http://localhost:8000/api/v1/agent/tools

# 2. 執行簡單查詢
curl -X POST http://localhost:8000/api/v1/agent/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "什麼是 ROE?",
    "analysis_depth": "quick"
  }'

# 3. 分析特定公司
curl -X POST http://localhost:8000/api/v1/agent/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "分析台積電的財務健康度",
    "company_id": "2330",
    "analysis_depth": "standard",
    "include_recommendations": true
  }'
```

### 使用 Python 測試

```python
import requests

# API 端點
BASE_URL = "http://localhost:8000/api/v1"

# 1. 列出可用工具
response = requests.get(f"{BASE_URL}/agent/tools")
print(response.json())

# 2. 執行分析
response = requests.post(
    f"{BASE_URL}/agent/analyze",
    json={
        "user_query": "台積電的財務狀況如何?",
        "company_id": "2330",
        "analysis_depth": "standard"
    }
)
result = response.json()
print(result["data"]["response"])
```

### 使用範例程式

```bash
# 執行互動式範例
python examples/usage_examples.py
```

---

## 📊 系統監控

### 查看日誌

```bash
# 即時查看日誌
tail -f server.log

# 搜尋錯誤
grep ERROR server.log

# 查看最近 100 行
tail -100 server.log
```

### 監控指標

訪問 Prometheus 指標端點（如果啟用）:
```
http://localhost:8000/metrics
```

---

## 🔧 常見操作

### 重新啟動服務

```bash
# 找到進程 ID
ps aux | grep uvicorn

# 停止服務
kill <PID>

# 重新啟動
uvicorn src.main:app --reload --port 8000
```

### 清除快取

```bash
# 連接到 Redis
redis-cli

# 清除所有快取
FLUSHDB

# 查看快取鍵
KEYS *

# 退出
exit
```

### 檢查資料庫

```bash
# 連接到 PostgreSQL
psql postgresql://postgres:dev_password_2024@localhost:5432/financial_analysis

# 列出所有表格
\dt

# 查看公司資料
SELECT * FROM companies LIMIT 10;

# 退出
\q
```

---

## 🐛 故障排除

### 問題 1: Port 8000 已被占用

```bash
# 找到占用 port 的進程
# Windows
netstat -ano | findstr :8000

# Linux/Mac
lsof -i :8000

# 使用不同 port
uvicorn src.main:app --port 8001
```

### 問題 2: 資料庫連線失敗

檢查連線字串和服務狀態:
```bash
# 測試連線
psql "postgresql://postgres:dev_password_2024@localhost:5432/financial_analysis" -c "SELECT 1"

# 如果失敗，檢查 PostgreSQL 是否運行
Get-Service postgresql*  # Windows
systemctl status postgresql  # Linux
```

### 問題 3: Claude API 錯誤

檢查 API Key:
```python
import os
from dotenv import load_dotenv
load_dotenv()

print("API Key:", os.getenv("ANTHROPIC_API_KEY")[:20] + "...")
```

### 問題 4: 模組導入錯誤

重新安裝依賴:
```bash
pip install -r requirements.txt --upgrade
```

---

## 📝 下一步

1. **閱讀 API 文檔**: http://localhost:8000/docs
2. **執行測試**: `pytest tests/test_mcp_integration.py -v`
3. **查看整合報告**: `INTEGRATION_COMPLETE.md`
4. **環境設定詳情**: `ENV_SETUP_GUIDE.md`

---

## 🎯 API 端點總覽

### Agent API (新增)
- `POST /api/v1/agent/analyze` - AI Agent 分析
- `GET /api/v1/agent/tools` - 列出可用工具
- `GET /api/v1/agent/tasks/{task_id}` - 查詢任務狀態

### 公司資料
- `GET /api/v1/companies` - 公司列表
- `GET /api/v1/companies/{company_id}` - 公司詳情

### 財務資料
- `GET /api/v1/financials/{company_id}` - 財務報表
- `GET /api/v1/ratios/{company_id}` - 財務比率

### 市場資料
- `GET /api/v1/market/prices/{company_id}` - 股價資料
- `GET /api/v1/market/indicators/{company_id}` - 技術指標

### 系統
- `GET /health` - 健康檢查
- `GET /metrics` - 監控指標

---

**系統狀態**: ✅ 就緒
**環境設定**: ✅ 完成
**API 端點**: ✅ 已註冊

現在您可以啟動系統了！ 🚀

```bash
uvicorn src.main:app --reload --port 8000
```
