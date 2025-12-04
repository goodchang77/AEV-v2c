#!/bin/bash
#
# AEV-v2c 應用程式啟動腳本
#

# 設定顏色輸出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 獲取腳本所在目錄（專案根目錄）
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${GREEN}=== AEV-v2c 財務分析系統 ===${NC}"
echo -e "${YELLOW}專案目錄: ${SCRIPT_DIR}${NC}"
echo ""

# 檢查 Python 環境
if ! command -v python &> /dev/null; then
    echo -e "${RED}錯誤: 找不到 Python${NC}"
    exit 1
fi

PYTHON_VERSION=$(python --version 2>&1)
echo -e "${GREEN}✓${NC} Python 版本: ${PYTHON_VERSION}"

# 檢查必要檔案
if [ ! -f "src/main.py" ]; then
    echo -e "${RED}錯誤: 找不到 src/main.py${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} 找到 src/main.py"

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}警告: 找不到 .env 檔案${NC}"
    echo -e "${YELLOW}請確保環境變數已正確設定${NC}"
fi

# 檢查 uvicorn
if ! python -c "import uvicorn" &> /dev/null; then
    echo -e "${RED}錯誤: 找不到 uvicorn${NC}"
    echo -e "${YELLOW}請執行: pip install uvicorn[standard]${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} uvicorn 已安裝"

# 設定 PYTHONPATH
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH}"
echo -e "${GREEN}✓${NC} PYTHONPATH 已設定"

echo ""
echo -e "${GREEN}正在啟動伺服器...${NC}"
echo -e "${YELLOW}訪問 http://localhost:8000/docs 查看 API 文件${NC}"
echo -e "${YELLOW}按 CTRL+C 停止伺服器${NC}"
echo ""

# 啟動伺服器
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
