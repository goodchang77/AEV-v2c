# AI Agent + MCP Server 專案整合指南

**目標**: 將設計好的AI Agent + MCP Server架構整合到現有的AEV-v2c專案中

---

## 📦 已完成的檔案清單

我已經為你建立了以下7個核心檔案:

### 1. 核心實作檔案 (3個)

| 檔案 | 行數 | 用途 | 下一步 |
|------|------|------|--------|
| `mcp_server_tools.py` | 800+ | MCP工具定義(8個工具的Schema) | 複製到 `src/mcp_server/tools.py` |
| `mcp_server_core.py` | 900+ | MCP Server核心邏輯 | 複製到 `src/mcp_server/server.py` |
| `ai_agent_coordinator.py` | 700+ | AI Agent協調器 | 複製到 `src/ai_agent/agent.py` |

### 2. 範例和測試檔案 (1個)

| 檔案 | 行數 | 用途 | 下一步 |
|------|------|------|--------|
| `complete_usage_examples.py` | 600+ | 6個完整使用場景 | 複製到 `examples/` |

### 3. 文件檔案 (3個)

| 檔案 | 大小 | 用途 | 閱讀優先級 |
|------|------|------|-----------|
| `ARCHITECTURE_SUMMARY.md` | 17KB | 架構總結和快速入門 | ⭐⭐⭐ 必讀 |
| `AI_AGENT_MCP_ARCHITECTURE.md` | 23KB | 完整技術文件 | ⭐⭐ 詳細參考 |
| `IMPLEMENTATION_CHECKLIST.md` | 11KB | 4週實作檢查清單 | ⭐⭐⭐ 執行指南 |

---

## 🚀 整合步驟 (30分鐘完成基礎整合)

### Step 1: 建立目錄結構 (2分鐘)

```bash
cd /path/to/aev-v2c

# 建立新目錄
mkdir -p src/mcp_server
mkdir -p src/ai_agent
mkdir -p examples
mkdir -p docs/architecture

# 建立__init__.py
touch src/mcp_server/__init__.py
touch src/ai_agent/__init__.py
```

### Step 2: 複製核心檔案 (5分鐘)

```bash
# 從臨時目錄複製到專案
cp /tmp/mcp_server_tools.py src/mcp_server/tools.py
cp /tmp/mcp_server_core.py src/mcp_server/server.py
cp /tmp/ai_agent_coordinator.py src/ai_agent/agent.py
cp /tmp/complete_usage_examples.py examples/usage_examples.py

# 複製文件
cp /tmp/ARCHITECTURE_SUMMARY.md docs/architecture/
cp /tmp/AI_AGENT_MCP_ARCHITECTURE.md docs/architecture/
cp /tmp/IMPLEMENTATION_CHECKLIST.md docs/
```

### Step 3: 修復Import路徑 (10分鐘)

需要修改的Import語句:

#### `src/mcp_server/server.py`
```python
# 修改前
from mcp_server_tools import (...)

# 修改後
from src.mcp_server.tools import (...)
```

#### `src/ai_agent/agent.py`
```python
# 修改前
from mcp_server_core import MCPServer

# 修改後
from src.mcp_server.server import MCPServer
```

### Step 4: 安裝額外依賴 (3分鐘)

```bash
# 更新 requirements.txt
cat >> requirements.txt << EOF

# AI Agent + MCP Server依賴
anthropic>=0.18.0
structlog>=23.2.0
pydantic>=2.5.0
redis>=5.0.1
slowapi>=0.1.9  # API速率限制
EOF

# 安裝
pip install -r requirements.txt
```

### Step 5: 配置環境變數 (2分鐘)

```bash
# 在 .env 中新增
cat >> .env << EOF

# AI Agent配置
ANTHROPIC_API_KEY=your-api-key-here
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# MCP Server配置
MCP_MAX_CONCURRENT_TOOLS=5
MCP_CACHE_ENABLED=true
MCP_CACHE_TTL_SECONDS=3600
EOF
```

### Step 6: 建立API端點 (8分鐘)

建立新檔案 `src/api/endpoints/agent.py`:

```python
"""
AI Agent API端點
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
import os

from src.core.database import get_db
from src.mcp_server.server import MCPServer
from src.ai_agent.agent import FinancialAnalystAgent
from src.schemas.requests import AgentAnalysisRequest
from src.schemas.responses import StandardResponse

router = APIRouter(prefix="/api/v1/agent", tags=["AI Agent"])

# 初始化(單例模式)
_mcp_server = None
_agent = None

def get_agent(db: Session = Depends(get_db)) -> FinancialAnalystAgent:
    """獲取AI Agent實例"""
    global _mcp_server, _agent
    
    if _mcp_server is None:
        _mcp_server = MCPServer(
            db_session=db,
            cache_enabled=os.getenv("MCP_CACHE_ENABLED", "true") == "true",
            max_concurrent_tools=int(os.getenv("MCP_MAX_CONCURRENT_TOOLS", "5"))
        )
    
    if _agent is None:
        _agent = FinancialAnalystAgent(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            mcp_server=_mcp_server,
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        )
    
    return _agent


@router.post("/analyze", response_model=StandardResponse)
async def analyze_company(
    request: AgentAnalysisRequest,
    agent: FinancialAnalystAgent = Depends(get_agent)
):
    """
    執行AI Agent分析
    
    - **user_query**: 使用者問題
    - **company_id**: 公司代號(可選)
    - **context**: 額外上下文(可選)
    """
    try:
        result = await agent.analyze(
            user_query=request.user_query,
            company_id=request.company_id,
            context=request.context
        )
        
        return StandardResponse(
            success=True,
            data=result,
            meta={
                "task_id": result["task_id"],
                "task_type": result["task_type"],
                "tools_executed": len(result["metadata"]["tools_executed"])
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}", response_model=StandardResponse)
async def get_task_status(task_id: str):
    """獲取任務狀態 (未來實作)"""
    # TODO: 實作任務狀態查詢
    return StandardResponse(
        success=False,
        error="Not implemented yet"
    )


@router.get("/tools", response_model=StandardResponse)
async def list_available_tools(
    agent: FinancialAnalystAgent = Depends(get_agent)
):
    """列出所有可用工具"""
    tools = agent.mcp_server.list_tools()
    
    return StandardResponse(
        success=True,
        data={"tools": tools},
        meta={"count": len(tools)}
    )
```

在 `src/api/main.py` 中註冊路由:

```python
# src/api/main.py
from src.api.endpoints import agent  # 新增

app.include_router(agent.router)  # 新增
```

---

## 🧪 測試整合 (驗證是否成功)

### 測試 1: 單元測試

建立 `tests/test_mcp_integration.py`:

```python
import pytest
from src.mcp_server.server import MCPServer
from src.core.database import get_db

@pytest.mark.asyncio
async def test_mcp_server_initialization():
    """測試MCP Server初始化"""
    db = next(get_db())
    server = MCPServer(db_session=db)
    
    assert server is not None
    assert len(server.tools) == 8
    print(f"✓ MCP Server初始化成功, 註冊了{len(server.tools)}個工具")

@pytest.mark.asyncio
async def test_financial_ratios_tool():
    """測試財務比率工具"""
    db = next(get_db())
    server = MCPServer(db_session=db)
    
    response = await server.execute_tool(
        tool_name="calculate_financial_ratios",
        input_data={
            "company_id": "2330",
            "period": "latest"
        }
    )
    
    assert response.success == True
    assert "financial_health_score" in response.data
    print(f"✓ 財務比率計算成功, 健康度評分: {response.data['financial_health_score']}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

執行測試:
```bash
pytest tests/test_mcp_integration.py -v
```

### 測試 2: API端點測試

```bash
# 啟動服務
uvicorn src.api.main:app --reload --port 8000

# 在另一個終端機測試
curl -X POST http://localhost:8000/api/v1/agent/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "台積電的財務健康度如何?",
    "company_id": "2330"
  }'
```

### 測試 3: 完整場景測試

```bash
# 執行範例程式
python examples/usage_examples.py
```

---

## 🔍 整合檢查清單

在繼續開發前，確認以下項目:

### 檔案結構 ✅
- [ ] `src/mcp_server/tools.py` 存在
- [ ] `src/mcp_server/server.py` 存在
- [ ] `src/ai_agent/agent.py` 存在
- [ ] `src/api/endpoints/agent.py` 存在
- [ ] `examples/usage_examples.py` 存在

### 依賴安裝 ✅
- [ ] `anthropic` 套件已安裝
- [ ] `structlog` 套件已安裝
- [ ] `pydantic` 版本 >= 2.5
- [ ] `redis` 套件已安裝

### 環境配置 ✅
- [ ] `ANTHROPIC_API_KEY` 已設定
- [ ] `DATABASE_URL` 正確
- [ ] `REDIS_URL` 正確

### 功能測試 ✅
- [ ] MCP Server可以初始化
- [ ] 至少1個工具可以執行
- [ ] API端點返回200
- [ ] Claude API可以正常調用

---

## 🎯 下一步行動建議

### 立即行動 (今天完成)

1. **閱讀文件** (30分鐘)
   - 先讀 `ARCHITECTURE_SUMMARY.md` (快速理解)
   - 再讀 `IMPLEMENTATION_CHECKLIST.md` (了解實作計畫)

2. **執行整合步驟** (30分鐘)
   - 按照上面的6個步驟操作
   - 執行測試驗證

3. **實作缺失模組** (1小時)
   - 最優先: `src/services/risk_assessment.py` (從Code Review報告得知這是缺失的)
   - 參考 `mcp_server_core.py` 中的 `_execute_risk_assessment()` 方法

### 本週完成 (Week 1)

按照 `IMPLEMENTATION_CHECKLIST.md` 的 Week 1 計畫:
- Day 1-2: 完成基礎整合
- Day 3-5: 實作8個工具的執行器
- Day 6-7: 加入快取和監控

### 未來2-3週

按照檢查清單完成:
- Week 2: AI Agent完整功能
- Week 3: API和介面
- Week 4: 測試和部署

---

## 📊 專案目錄結構 (整合後)

```
aev-v2c/
├── src/
│   ├── mcp_server/           # 新增 ✨
│   │   ├── __init__.py
│   │   ├── tools.py          # 8個工具定義
│   │   ├── server.py         # MCP Server核心
│   │   ├── cache.py          # 快取策略 (待實作)
│   │   └── monitoring.py     # 監控指標 (待實作)
│   │
│   ├── ai_agent/             # 新增 ✨
│   │   ├── __init__.py
│   │   ├── agent.py          # AI Agent協調器
│   │   ├── prompts.py        # 提示詞模板 (待實作)
│   │   └── conversation.py   # 對話管理 (待實作)
│   │
│   ├── api/
│   │   ├── endpoints/
│   │   │   ├── agent.py      # 新增 ✨
│   │   │   ├── companies.py  # 現有
│   │   │   └── ...
│   │   ├── main.py           # 更新路由註冊
│   │   └── websocket.py      # WebSocket (待實作)
│   │
│   ├── services/             # 現有 + 需補充
│   │   ├── financial_calculator.py  # 已存在 ✅
│   │   ├── valuation_models.py      # 已存在 ✅
│   │   ├── risk_assessment.py       # 需要新增 ⚠️
│   │   ├── peer_analysis.py         # 已存在 ✅
│   │   └── ...
│   │
│   └── schemas/
│       ├── requests.py       # 新增AgentAnalysisRequest
│       └── responses.py      # 已存在
│
├── examples/                 # 新增 ✨
│   └── usage_examples.py     # 6個使用場景
│
├── tests/
│   ├── test_mcp_integration.py   # 新增 ✨
│   ├── test_ai_agent.py          # 新增 ✨
│   └── integration/
│       └── test_scenarios.py     # 新增 ✨
│
├── docs/
│   ├── architecture/             # 新增 ✨
│   │   ├── ARCHITECTURE_SUMMARY.md
│   │   └── AI_AGENT_MCP_ARCHITECTURE.md
│   └── IMPLEMENTATION_CHECKLIST.md
│
├── requirements.txt          # 更新依賴
├── .env                      # 新增AI Agent配置
└── README.md                 # 更新使用說明
```

---

## 🆘 常見問題和解決方案

### Q1: Import錯誤 `ModuleNotFoundError: No module named 'mcp_server_tools'`
**解決**: 修改import路徑
```python
# 錯誤
from mcp_server_tools import ...

# 正確
from src.mcp_server.tools import ...
```

### Q2: Claude API呼叫失敗
**檢查**:
1. API Key是否正確設定
2. 網路連接是否正常
3. 是否超過速率限制

### Q3: 工具執行超時
**解決**:
```python
# 增加超時時間
response = await server.execute_tool(
    tool_name="...",
    input_data={...},
    timeout_seconds=30  # 增加到30秒
)
```

### Q4: 資料庫連接錯誤
**檢查**:
1. PostgreSQL是否運行
2. DATABASE_URL是否正確
3. 資料表是否已建立

---

## 📞 需要幫助?

### 技術支援
- 查看文件: `docs/architecture/`
- 執行範例: `examples/usage_examples.py`
- 參考測試: `tests/test_mcp_integration.py`

### 下一步建議
1. 先完成基礎整合(上面的6個步驟)
2. 執行測試確認運作正常
3. 開始按照 `IMPLEMENTATION_CHECKLIST.md` Week 1的計畫實作

---

**祝你整合順利! 🚀**

如果遇到問題,請隨時回來查閱這份文件或詢問我。