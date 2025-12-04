# 🚀 如何啟動 AEV-v2c 系統

## ⚠️ 重要提示

**錯誤:** `Attribute "app" not found in module "src.main"`
**原因:** 工作目錄不正確或 PYTHONPATH 未設定

## ✅ 正確啟動方式

### 方法 1: 使用啟動腳本（最簡單）

這是**最推薦**的方式，腳本會自動處理所有設定：

```bash
# Linux/Mac/WSL
cd /d/Project/AEV-v2c
./start_server.sh

# Windows
cd D:\Project\AEV-v2c
start_server.bat
```

### 方法 2: 手動啟動

如果您想手動啟動，**必須**遵循以下步驟：

#### Linux/Mac/WSL:
```bash
# 步驟 1: 切換到專案根目錄（非常重要！）
cd /d/Project/AEV-v2c

# 步驟 2: 設定 PYTHONPATH
export PYTHONPATH="${PWD}:${PYTHONPATH}"

# 步驟 3: 啟動伺服器
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

#### Windows PowerShell:
```powershell
# 步驟 1: 切換到專案根目錄（非常重要！）
cd D:\Project\AEV-v2c

# 步驟 2: 設定 PYTHONPATH
$env:PYTHONPATH = "${PWD};$env:PYTHONPATH"

# 步驟 3: 啟動伺服器
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

#### Windows CMD:
```cmd
REM 步驟 1: 切換到專案根目錄（非常重要！）
cd /d D:\Project\AEV-v2c

REM 步驟 2: 設定 PYTHONPATH
set PYTHONPATH=%CD%;%PYTHONPATH%

REM 步驟 3: 啟動伺服器
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 方法 3: 使用 Python 模組方式

```bash
cd /d/Project/AEV-v2c
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## 🔍 如何診斷問題

如果啟動仍然失敗，執行診斷腳本：

```bash
cd /d/Project/AEV-v2c
./diagnose.sh
```

這會檢查：
- ✓ Python 環境
- ✓ 必要檔案
- ✓ 依賴套件
- ✓ 環境變數
- ✓ 資料庫連線
- ✓ Redis 連線
- ✓ 應用程式導入

## ❌ 常見錯誤

### 錯誤 1: 在錯誤的目錄執行命令

```bash
gc@GL-NB-HX370:~$ uvicorn src.main:app --reload --port 8000
ERROR: Error loading ASGI app. Attribute "app" not found in module "src.main".
```

**原因:** 您在 `/home/gc` 目錄執行，但專案在 `/d/Project/AEV-v2c`

**解決方案:** 先切換到專案目錄
```bash
cd /d/Project/AEV-v2c
```

### 錯誤 2: PYTHONPATH 未設定

即使在正確目錄，Python 可能仍找不到模組。

**解決方案:** 使用啟動腳本或手動設定 PYTHONPATH

### 錯誤 3: 依賴套件未安裝

```bash
ModuleNotFoundError: No module named 'fastapi'
```

**解決方案:**
```bash
pip install -r requirements.txt
```

## ✅ 成功啟動的標誌

當伺服器成功啟動，您會看到：

```
INFO:     Will watch for changes in these directories: ['/d/Project/AEV-v2c']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [XXXX] using StatReload
INFO:     Started server process [XXXX]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

然後訪問：
- API 文件: http://localhost:8000/docs
- ReDoc 文件: http://localhost:8000/redoc
- 健康檢查: http://localhost:8000/health

## 🧪 測試 AI Agent

伺服器啟動後，測試 AI Agent API：

```bash
curl -X POST http://localhost:8000/api/v1/agent/analyze \
  -H 'Content-Type: application/json' \
  -d '{
    "user_query": "分析台積電的財務狀況",
    "company_id": "2330"
  }'
```

## 📚 更多資訊

- **TROUBLESHOOTING.md** - 詳細的故障排除指南
- **QUICK_START.md** - 完整的啟動文檔
- **STARTUP_SUCCESS.md** - 整合完成報告
- **ENV_SETUP_GUIDE.md** - 環境設定指南

## 💡 快速檢查清單

啟動前確認：

- [ ] 在專案根目錄 (`/d/Project/AEV-v2c`)
- [ ] Python 3.11+ 已安裝
- [ ] 所有依賴已安裝 (`pip install -r requirements.txt`)
- [ ] `.env` 檔案存在且包含必要設定
- [ ] PostgreSQL 服務正在運行
- [ ] Redis 服務正在運行
- [ ] 端口 8000 未被佔用

## 🆘 需要幫助？

1. 執行診斷: `./diagnose.sh`
2. 查看日誌輸出
3. 檢查 TROUBLESHOOTING.md
4. 確認環境變數設定

---

**最後更新:** 2025-12-04
**狀態:** 所有整合已完成，系統可以正常啟動
