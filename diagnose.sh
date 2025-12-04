#!/bin/bash
#
# AEV-v2c 系統診斷腳本
#

# 設定顏色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== AEV-v2c 系統診斷 ===${NC}"
echo ""

# 1. 當前目錄
echo -e "${YELLOW}1. 當前目錄:${NC}"
pwd
echo ""

# 2. Python 版本
echo -e "${YELLOW}2. Python 版本:${NC}"
if command -v python &> /dev/null; then
    python --version
    echo -e "${GREEN}✓ Python 已安裝${NC}"
else
    echo -e "${RED}✗ Python 未安裝${NC}"
fi
echo ""

# 3. 專案結構
echo -e "${YELLOW}3. 專案結構檢查:${NC}"
if [ -f "src/main.py" ]; then
    echo -e "${GREEN}✓ src/main.py 存在${NC}"
else
    echo -e "${RED}✗ src/main.py 不存在${NC}"
fi

if [ -f "src/__init__.py" ]; then
    echo -e "${GREEN}✓ src/__init__.py 存在${NC}"
else
    echo -e "${YELLOW}⚠ src/__init__.py 不存在（可能不影響）${NC}"
fi

if [ -f ".env" ]; then
    echo -e "${GREEN}✓ .env 存在${NC}"
else
    echo -e "${YELLOW}⚠ .env 不存在${NC}"
fi
echo ""

# 4. 關鍵依賴
echo -e "${YELLOW}4. 關鍵依賴檢查:${NC}"
PACKAGES=("fastapi" "uvicorn" "anthropic" "sqlalchemy" "redis" "pydantic")
for pkg in "${PACKAGES[@]}"; do
    if python -c "import $pkg" 2>/dev/null; then
        version=$(python -c "import $pkg; print($pkg.__version__)" 2>/dev/null)
        echo -e "${GREEN}✓ $pkg${NC} ${version}"
    else
        echo -e "${RED}✗ $pkg 未安裝${NC}"
    fi
done
echo ""

# 5. 環境變數
echo -e "${YELLOW}5. 環境變數:${NC}"
if [ -f ".env" ]; then
    source .env 2>/dev/null
fi

if [ ! -z "$DATABASE_URL" ]; then
    echo -e "${GREEN}✓ DATABASE_URL:${NC} ${DATABASE_URL:0:40}..."
else
    echo -e "${RED}✗ DATABASE_URL 未設定${NC}"
fi

if [ ! -z "$REDIS_URL" ]; then
    echo -e "${GREEN}✓ REDIS_URL:${NC} ${REDIS_URL:0:40}..."
else
    echo -e "${RED}✗ REDIS_URL 未設定${NC}"
fi

if [ ! -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${GREEN}✓ ANTHROPIC_API_KEY:${NC} ${ANTHROPIC_API_KEY:0:20}..."
else
    echo -e "${RED}✗ ANTHROPIC_API_KEY 未設定${NC}"
fi
echo ""

# 6. 資料庫連線測試
echo -e "${YELLOW}6. PostgreSQL 連線測試:${NC}"
if command -v psql &> /dev/null; then
    # 從 DATABASE_URL 解析連線資訊
    if [ ! -z "$DATABASE_URL" ]; then
        if psql "$DATABASE_URL" -c "SELECT 1" &> /dev/null; then
            echo -e "${GREEN}✓ PostgreSQL 連線成功${NC}"
        else
            echo -e "${RED}✗ PostgreSQL 連線失敗${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ DATABASE_URL 未設定，跳過測試${NC}"
    fi
else
    echo -e "${YELLOW}⚠ psql 未安裝，跳過測試${NC}"
fi
echo ""

# 7. Redis 連線測試
echo -e "${YELLOW}7. Redis 連線測試:${NC}"
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        echo -e "${GREEN}✓ Redis 連線成功${NC}"
    else
        echo -e "${RED}✗ Redis 連線失敗${NC}"
    fi
else
    echo -e "${YELLOW}⚠ redis-cli 未安裝，跳過測試${NC}"
fi
echo ""

# 8. 測試 app 導入
echo -e "${YELLOW}8. 測試應用程式導入:${NC}"
IMPORT_TEST=$(python << 'EOF'
import sys
sys.path.insert(0, '.')
try:
    from src.main import app
    print("SUCCESS")
except Exception as e:
    print(f"ERROR: {e}")
EOF
)

if [[ "$IMPORT_TEST" == "SUCCESS" ]]; then
    echo -e "${GREEN}✓ app 導入成功${NC}"
else
    echo -e "${RED}✗ app 導入失敗${NC}"
    echo -e "${RED}  $IMPORT_TEST${NC}"
fi
echo ""

# 9. MCP 工具檢查
echo -e "${YELLOW}9. MCP 工具註冊檢查:${NC}"
TOOLS_COUNT=$(python << 'EOF'
import sys
sys.path.insert(0, '.')
try:
    from src.mcp_server.tools import MCP_TOOLS_REGISTRY
    print(len(MCP_TOOLS_REGISTRY))
except Exception as e:
    print("0")
EOF
)

if [ "$TOOLS_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ $TOOLS_COUNT 個 MCP 工具已註冊${NC}"
else
    echo -e "${RED}✗ MCP 工具未註冊${NC}"
fi
echo ""

# 總結
echo -e "${BLUE}=== 診斷完成 ===${NC}"
echo ""
echo -e "${YELLOW}建議的啟動方式:${NC}"
echo "1. 使用啟動腳本: ./start_server.sh"
echo "2. 手動啟動: uvicorn src.main:app --reload --port 8000"
echo ""
echo -e "${YELLOW}如有問題，請查看:${NC}"
echo "- TROUBLESHOOTING.md - 故障排除指南"
echo "- QUICK_START.md - 快速啟動指南"
