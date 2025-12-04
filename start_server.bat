@echo off
REM AEV-v2c 應用程式啟動腳本 (Windows)

echo === AEV-v2c 財務分析系統 ===
echo.

REM 切換到腳本所在目錄（專案根目錄）
cd /d "%~dp0"
echo 專案目錄: %CD%
echo.

REM 檢查 Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 Python
    pause
    exit /b 1
)

python --version
echo [OK] Python 已安裝
echo.

REM 檢查必要檔案
if not exist "src\main.py" (
    echo [錯誤] 找不到 src\main.py
    pause
    exit /b 1
)
echo [OK] 找到 src\main.py

if not exist ".env" (
    echo [警告] 找不到 .env 檔案
    echo 請確保環境變數已正確設定
)
echo.

REM 檢查 uvicorn
python -c "import uvicorn" >nul 2>nul
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 uvicorn
    echo 請執行: pip install uvicorn[standard]
    pause
    exit /b 1
)
echo [OK] uvicorn 已安裝
echo.

REM 設定 PYTHONPATH
set PYTHONPATH=%CD%;%PYTHONPATH%
echo [OK] PYTHONPATH 已設定
echo.

echo 正在啟動伺服器...
echo 訪問 http://localhost:8000/docs 查看 API 文件
echo 按 CTRL+C 停止伺服器
echo.

REM 啟動伺服器
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
