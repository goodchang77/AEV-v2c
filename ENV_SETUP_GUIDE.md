# 環境變數設定指南
# Environment Variables Setup Guide

本指南說明如何設定 AEV-v2c 財務分析系統所需的環境變數。

---

## 📋 快速檢查清單

您的 `.env` 檔案已經包含以下必要設定：

- ✅ **DATABASE_URL** - PostgreSQL 資料庫連線
- ✅ **REDIS_URL** - Redis 快取連線
- ✅ **ANTHROPIC_API_KEY** - Claude AI API 金鑰
- ✅ **MCP Server 設定** - MCP 伺服器配置

---

## 🔧 當前設定狀態

### 1. 資料庫設定
```env
DATABASE_URL=postgresql://postgres:dev_password_2024@localhost:5432/financial_analysis
TIMESERIES_DATABASE_URL=postgresql://postgres:dev_password_2024@localhost:5433/timeseries_financial
```

**說明**:
- `DATABASE_URL`: 主要 PostgreSQL 資料庫
- `TIMESERIES_DATABASE_URL`: 時序資料資料庫 (用於股價等時間序列資料)

**檢查方式**:
```bash
# 測試資料庫連線
psql $DATABASE_URL -c "SELECT 1;"
```

### 2. Redis 設定
```env
REDIS_URL=redis://:dev_redis_2024@localhost:6379
```

**說明**: Redis 用於快取和工具執行結果的暫存

**檢查方式**:
```bash
# 測試 Redis 連線
redis-cli -u $REDIS_URL ping
# 應該返回: PONG
```

### 3. AI Agent 設定
```env
ANTHROPIC_API_KEY=sk-ant-api03-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

**說明**:
- `ANTHROPIC_API_KEY`: 您的 Claude API 金鑰 ✅ **已設定**
- `ANTHROPIC_MODEL`: 使用的 Claude 模型版本

**檢查方式**:
```bash
# 測試 API 金鑰
python -c "
import os
import anthropic
client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
print('API Key is valid!')
"
```

### 4. MCP Server 設定
```env
MCP_MAX_CONCURRENT_TOOLS=5
MCP_CACHE_ENABLED=true
MCP_CACHE_TTL_SECONDS=3600
```

**說明**:
- `MCP_MAX_CONCURRENT_TOOLS`: 最大並發工具執行數量
- `MCP_CACHE_ENABLED`: 是否啟用工具執行結果快取
- `MCP_CACHE_TTL_SECONDS`: 快取有效時間 (秒)

---

## 🚀 快速驗證

執行以下腳本驗證所有環境變數：

```bash
python << 'VERIFY'
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 70)
print("環境變數驗證")
print("=" * 70)

required_vars = {
    "DATABASE_URL": "資料庫連線",
    "REDIS_URL": "Redis 快取",
    "ANTHROPIC_API_KEY": "Claude AI API",
    "ANTHROPIC_MODEL": "AI 模型",
    "MCP_MAX_CONCURRENT_TOOLS": "MCP 並發數",
    "MCP_CACHE_ENABLED": "MCP 快取",
}

all_ok = True

for var, desc in required_vars.items():
    value = os.getenv(var)
    if value:
        # 隱藏敏感資訊
        if "KEY" in var or "PASSWORD" in var:
            display_value = value[:10] + "..." if len(value) > 10 else "***"
        else:
            display_value = value[:50]
        print(f"✅ {var:30} {desc:20} = {display_value}")
    else:
        print(f"❌ {var:30} {desc:20} = 未設定")
        all_ok = False

print("=" * 70)
if all_ok:
    print("✅ 所有必要環境變數已正確設定！")
else:
    print("⚠️ 部分環境變數缺失，請檢查 .env 檔案")
VERIFY
```

---

## 📝 如何修改環境變數

### 方法 1: 編輯 .env 檔案 (推薦)

1. 使用文字編輯器打開 `.env` 檔案:
   ```bash
   code .env  # VS Code
   # 或
   notepad .env  # Windows 記事本
   ```

2. 修改相應的值:
   ```env
   # 範例：更改 AI 模型
   ANTHROPIC_MODEL=claude-sonnet-4-20250514

   # 範例：調整 MCP 設定
   MCP_MAX_CONCURRENT_TOOLS=10
   ```

3. 儲存檔案並重新啟動應用程式

### 方法 2: 使用 Shell 設定 (臨時)

**Windows (PowerShell)**:
```powershell
$env:ANTHROPIC_MODEL="claude-sonnet-4-20250514"
$env:MCP_MAX_CONCURRENT_TOOLS="10"
```

**Linux/Mac (Bash)**:
```bash
export ANTHROPIC_MODEL="claude-sonnet-4-20250514"
export MCP_MAX_CONCURRENT_TOOLS="10"
```

**注意**: 這種方式設定的環境變數只在當前終端機會話有效。

---

## 🔒 安全性建議

### 1. 保護 API 金鑰
```bash
# .env 檔案應該加入 .gitignore
echo ".env" >> .gitignore

# 檢查是否已加入
git check-ignore .env
# 應該顯示: .env
```

### 2. 使用 .env.example 作為範本
`.env.example` 檔案已經建立，包含所有必要的環境變數範本但不含敏感資訊：
```bash
cp .env.example .env.local
# 然後編輯 .env.local 填入真實的值
```

### 3. 不同環境使用不同設定

**開發環境** (`.env.development`):
```env
DEBUG=true
DATABASE_URL=postgresql://localhost/financial_dev
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

**測試環境** (`.env.test`):
```env
DEBUG=true
DATABASE_URL=postgresql://localhost/financial_test
MCP_CACHE_ENABLED=false  # 測試時關閉快取
```

**生產環境** (`.env.production`):
```env
DEBUG=false
DATABASE_URL=postgresql://prod-server/financial_prod
MCP_MAX_CONCURRENT_TOOLS=20
```

載入特定環境設定:
```bash
# 開發環境
python -m src.main --env development

# 或手動載入
export ENV_FILE=.env.production
python -m src.main
```

---

## 🧪 測試連線

### 1. 測試資料庫連線
```bash
python << 'TEST_DB'
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

try:
    engine = create_engine(os.getenv("DATABASE_URL"))
    with engine.connect() as conn:
        result = conn.execute("SELECT version();")
        print("✅ 資料庫連線成功!")
        print(f"   PostgreSQL 版本: {result.fetchone()[0]}")
except Exception as e:
    print(f"❌ 資料庫連線失敗: {e}")
TEST_DB
```

### 2. 測試 Redis 連線
```bash
python << 'TEST_REDIS'
import redis
import os
from dotenv import load_dotenv

load_dotenv()

try:
    r = redis.from_url(os.getenv("REDIS_URL"))
    r.ping()
    print("✅ Redis 連線成功!")
    print(f"   Redis 版本: {r.info()['redis_version']}")
except Exception as e:
    print(f"❌ Redis 連線失敗: {e}")
TEST_REDIS
```

### 3. 測試 Claude API
```bash
python << 'TEST_CLAUDE'
import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

try:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    # 簡單的測試請求
    message = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL"),
        max_tokens=10,
        messages=[{"role": "user", "content": "Hello"}]
    )
    print("✅ Claude API 連線成功!")
    print(f"   模型: {os.getenv('ANTHROPIC_MODEL')}")
    print(f"   回應: {message.content[0].text}")
except Exception as e:
    print(f"❌ Claude API 連線失敗: {e}")
TEST_CLAUDE
```

---

## 🔥 常見問題

### Q1: 環境變數沒有載入？
**解決方法**:
```python
# 確保在程式開始時載入 .env
from dotenv import load_dotenv
load_dotenv()  # 預設載入 .env

# 或指定檔案
load_dotenv(".env.production")
```

### Q2: API 金鑰無效？
**檢查**:
1. 確認金鑰沒有多餘的空格或換行
2. 確認金鑰沒有過期
3. 確認 API 額度未用盡

### Q3: 資料庫連線失敗？
**檢查**:
```bash
# 確認 PostgreSQL 服務正在運行
# Windows
Get-Service postgresql*

# Linux
systemctl status postgresql
```

### Q4: 如何在 Docker 中使用環境變數？
```yaml
# docker-compose.yml
services:
  api:
    env_file:
      - .env
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
```

---

## 📚 參考資源

- [python-dotenv 文件](https://github.com/theskumar/python-dotenv)
- [Anthropic API 文件](https://docs.anthropic.com/)
- [PostgreSQL 連線字串格式](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING)
- [Redis 連線 URL 格式](https://redis.io/docs/reference/clients/)

---

## ✅ 完成檢查清單

在啟動系統前，請確認：

- [x] `.env` 檔案存在
- [x] 所有必要環境變數已設定
- [ ] 資料庫連線測試通過
- [ ] Redis 連線測試通過
- [ ] Claude API 測試通過
- [ ] `.env` 已加入 `.gitignore`

---

**提示**: 您的環境變數已經完整設定，可以直接啟動系統！

```bash
# 啟動開發伺服器
uvicorn src.main:app --reload --port 8000

# 或使用生產模式
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker
```
