# 故障排除指南

## 問題: "Attribute 'app' not found in module 'src.main'"

### 問題描述
當執行 `uvicorn src.main:app` 時出現以下錯誤：
```
ERROR: Error loading ASGI app. Attribute "app" not found in module "src.main".
```

### 原因分析
這個錯誤通常由以下原因造成：

1. **工作目錄不正確** - 必須在專案根目錄執行命令
2. **PYTHONPATH 未設定** - Python 無法正確找到模組
3. **模組導入錯誤** - src/main.py 中有語法或導入錯誤

### 解決方案

#### 方案 1: 使用啟動腳本（推薦）

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

#### 方案 2: 手動設定並啟動

**Linux/Mac:**
```bash
# 1. 切換到專案根目錄
cd /d/Project/AEV-v2c

# 2. 設定 PYTHONPATH
export PYTHONPATH="${PWD}:${PYTHONPATH}"

# 3. 啟動伺服器
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Windows PowerShell:**
```powershell
# 1. 切換到專案根目錄
cd D:\Project\AEV-v2c

# 2. 設定 PYTHONPATH
$env:PYTHONPATH = "${PWD};$env:PYTHONPATH"

# 3. 啟動伺服器
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Windows CMD:**
```cmd
REM 1. 切換到專案根目錄
cd /d D:\Project\AEV-v2c

REM 2. 設定 PYTHONPATH
set PYTHONPATH=%CD%;%PYTHONPATH%

REM 3. 啟動伺服器
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

#### 方案 3: 使用 Python 模組方式啟動

```bash
cd /d/Project/AEV-v2c
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

#### 方案 4: 驗證並修復導入問題

如果上述方法仍然失敗，請執行診斷腳本：

```bash
cd /d/Project/AEV-v2c
python verify_env.py
```

或者手動測試導入：

```bash
python << 'EOF'
import sys
sys.path.insert(0, '.')

try:
    from src.main import app
    print("SUCCESS: app 已成功導入")
    print(f"app type: {type(app)}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
EOF
```

### 常見錯誤檢查清單

#### ✓ 檢查項目 1: 確認當前目錄
```bash
pwd  # Linux/Mac
cd   # Windows
```
應該顯示: `/d/Project/AEV-v2c` 或 `D:\Project\AEV-v2c`

#### ✓ 檢查項目 2: 確認 src/main.py 存在
```bash
ls -la src/main.py      # Linux/Mac
dir src\main.py         # Windows
```

#### ✓ 檢查項目 3: 確認 app 變數定義
```bash
grep "^app = " src/main.py
```
應該看到: `app = FastAPI(...`

#### ✓ 檢查項目 4: 測試模組導入
```bash
python -c "import sys; sys.path.insert(0, '.'); from src.main import app; print('OK')"
```

#### ✓ 檢查項目 5: 檢查 Python 版本
```bash
python --version
```
應該是 Python 3.11 或更高版本

#### ✓ 檢查項目 6: 檢查依賴套件
```bash
pip list | grep -E "fastapi|uvicorn|anthropic"
```

## 其他常見問題

### 問題: 導入錯誤 (ImportError)

如果看到類似以下錯誤：
```
ImportError: cannot import name 'XXX' from 'YYY'
```

**解決方案:**
1. 確認所有依賴已安裝：
   ```bash
   pip install -r requirements.txt
   ```

2. 檢查具體的導入錯誤並參考 STARTUP_SUCCESS.md 中的已修復列表

### 問題: 資料庫連線錯誤

```
sqlalchemy.exc.OperationalError: could not connect to server
```

**解決方案:**
1. 確認 PostgreSQL 服務正在運行
2. 檢查 .env 中的 DATABASE_URL
3. 測試連線：
   ```bash
   psql -h localhost -U postgres -d financial_analysis
   ```

### 問題: Redis 連線錯誤

```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**解決方案:**
1. 確認 Redis 服務正在運行
2. 檢查 .env 中的 REDIS_URL
3. 測試連線：
   ```bash
   redis-cli ping
   ```

### 問題: Anthropic API 錯誤

```
anthropic.exceptions.AuthenticationError: Invalid API key
```

**解決方案:**
1. 檢查 .env 中的 ANTHROPIC_API_KEY
2. 確認 API 金鑰有效且有足夠額度
3. 測試 API 金鑰：
   ```bash
   curl https://api.anthropic.com/v1/messages \
     -H "x-api-key: $ANTHROPIC_API_KEY" \
     -H "anthropic-version: 2023-06-01" \
     -H "content-type: application/json" \
     -d '{"model":"claude-3-sonnet-20240229","max_tokens":1024,"messages":[{"role":"user","content":"Hello"}]}'
   ```

### 問題: 端口被佔用

```
ERROR: [Errno 48] error while attempting to bind on address ('0.0.0.0', 8000): address already in use
```

**解決方案:**

**Linux/Mac:**
```bash
# 查找佔用端口的進程
lsof -i :8000

# 終止進程
kill -9 <PID>

# 或使用不同端口
uvicorn src.main:app --reload --port 8001
```

**Windows:**
```cmd
REM 查找佔用端口的進程
netstat -ano | findstr :8000

REM 終止進程
taskkill /PID <PID> /F

REM 或使用不同端口
uvicorn src.main:app --reload --port 8001
```

## 日誌檢查

### 啟用詳細日誌

在 .env 中設定：
```
DEBUG=true
LOG_LEVEL=DEBUG
```

### 查看應用程式日誌

應用程式啟動後，日誌會輸出到終端。關鍵日誌包括：

- `✓ Database connection successful` - 資料庫連線成功
- `✓ Redis connection successful` - Redis 連線成功
- `MCP Server initialized with 8 tools` - MCP Server 初始化
- `Uvicorn running on http://...` - 伺服器啟動成功

## 獲取更多幫助

1. 查看詳細文件：
   - STARTUP_SUCCESS.md - 啟動成功報告
   - QUICK_START.md - 快速啟動指南
   - ENV_SETUP_GUIDE.md - 環境設定指南

2. 執行診斷腳本：
   ```bash
   python verify_env.py
   ```

3. 檢查 GitHub Issues（如果適用）

4. 查看 FastAPI 官方文件：
   https://fastapi.tiangolo.com/

## 快速診斷命令

執行以下命令進行快速診斷：

```bash
#!/bin/bash
echo "=== 系統診斷 ==="
echo ""
echo "1. 當前目錄:"
pwd
echo ""
echo "2. Python 版本:"
python --version
echo ""
echo "3. 專案結構:"
ls -la src/main.py src/__init__.py
echo ""
echo "4. 關鍵依賴:"
pip list | grep -E "fastapi|uvicorn|anthropic|sqlalchemy|redis"
echo ""
echo "5. 環境變數:"
echo "DATABASE_URL: ${DATABASE_URL:0:30}..."
echo "REDIS_URL: ${REDIS_URL:0:30}..."
echo "ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:0:20}..."
echo ""
echo "6. 測試導入:"
python -c "import sys; sys.path.insert(0, '.'); from src.main import app; print('✓ app 導入成功')" 2>&1
echo ""
echo "=== 診斷完成 ==="
```

保存為 `diagnose.sh` 並執行：
```bash
chmod +x diagnose.sh
./diagnose.sh
```
