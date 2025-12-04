# AI Agent + MCP Server 架構完整說明

**版本**: 1.0  
**日期**: 2024-12-04  
**專案**: AEV-v2c 企業財務分析系統

---

## 📋 目錄

1. [系統概覽](#系統概覽)
2. [核心組件](#核心組件)
3. [工作流程](#工作流程)
4. [API規格](#api規格)
5. [部署指南](#部署指南)
6. [測試策略](#測試策略)
7. [最佳實踐](#最佳實踐)

---

## 系統概覽

### 🎯 設計目標

建立一個**智能財務分析系統**，讓AI Agent能夠:
- 🧠 **自主規劃**: 根據使用者問題自動決定分析步驟
- 🔧 **工具調用**: 透過MCP Server調用8個財務分析工具
- 📊 **結果合成**: 整合多個工具輸出，生成專業分析報告
- 💬 **對話互動**: 支援多輪對話，逐步深入分析

### 🏗️ 三層架構

```
┌─────────────────────────────────────────────────────┐
│          使用者介面層 (User Interface)                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │   CLI    │ │ Web API  │ │ Chat Bot │           │
│  └──────────┘ └──────────┘ └──────────┘           │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│         AI Agent層 (Intelligent Orchestration)       │
│  ┌────────────────────────────────────────────┐    │
│  │  FinancialAnalystAgent                      │    │
│  │  ┌──────────────┐ ┌────────────────────┐  │    │
│  │  │ Task Planner │ │ Tool Orchestrator  │  │    │
│  │  └──────────────┘ └────────────────────┘  │    │
│  │  ┌──────────────┐ ┌────────────────────┐  │    │
│  │  │Result Synth. │ │ Conv. Manager      │  │    │
│  │  └──────────────┘ └────────────────────┘  │    │
│  └────────────────────────────────────────────┘    │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│         MCP Server層 (Tool Execution)                │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐      │
│  │ Ratios │ │  DCF   │ │  Risk  │ │  Peer  │      │
│  │  Tool  │ │  Tool  │ │  Tool  │ │  Tool  │      │
│  └────────┘ └────────┘ └────────┘ └────────┘      │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐      │
│  │  Data  │ │ Report │ │  Doc   │ │ Alert  │      │
│  │  Tool  │ │  Tool  │ │  Tool  │ │  Tool  │      │
│  └────────┘ └────────┘ └────────┘ └────────┘      │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│      業務邏輯層 (Business Logic Services)            │
│  FinancialCalculator │ DCFValuationModel           │
│  RiskAssessmentEngine │ PeerAnalyzer                │
│  DataService │ ReportService │ PDFProcessor         │
└─────────────────────────────────────────────────────┘
```

---

## 核心組件

### 1️⃣ MCP Server (工具執行層)

**檔案**: `mcp_server_core.py`

#### 核心類別

```python
class MCPServer:
    """MCP Server主類"""
    
    def __init__(
        self,
        db_session: Session,
        cache_enabled: bool = True,
        max_concurrent_tools: int = 5
    )
    
    async def execute_tool(
        self,
        tool_name: str,
        input_data: Dict[str, Any],
        timeout_seconds: Optional[int] = None
    ) -> ToolResponse
    
    async def execute_multiple_tools(
        self,
        tool_requests: List[Dict[str, Any]]
    ) -> List[ToolResponse]
```

#### 8個核心工具

| 工具名稱 | 功能 | 預估時間 |
|---------|------|---------|
| `calculate_financial_ratios` | 計算30+財務比率 | 500ms |
| `perform_dcf_valuation` | DCF現金流折現估值 | 2000ms |
| `assess_company_risk` | 風險評估(Altman Z-Score) | 1500ms |
| `compare_with_peers` | 同業比較與SWOT分析 | 3000ms |
| `fetch_company_data` | 多源資料擷取 | 5000ms |
| `generate_analysis_report` | 報告生成(PDF/Excel) | 10000ms |
| `process_financial_document` | 文件處理(PDF/Excel) | 8000ms |
| `monitor_company_alerts` | 警報監控 | 2000ms |

#### 工具定義範例

```python
class FinancialRatiosInput(BaseModel):
    """財務比率計算輸入"""
    company_id: str = Field(..., regex=r"^\d{4}$")
    period: Literal["latest", "annual", "quarterly"] = "latest"
    ratio_categories: Optional[List[str]] = None

class FinancialRatiosOutput(BaseModel):
    """財務比率計算輸出"""
    company_id: str
    company_name: str
    period_date: date
    
    financial_structure: Dict[str, float]
    liquidity_ratios: Dict[str, float]
    efficiency_ratios: Dict[str, float]
    profitability_ratios: Dict[str, float]
    cash_flow_ratios: Dict[str, float]
    
    financial_health_score: float  # 0-100
    rating: Literal["Excellent", "Good", "Average", "Below Average", "Poor"]
```

### 2️⃣ AI Agent (智能協調層)

**檔案**: `ai_agent_coordinator.py`

#### 核心類別

```python
class FinancialAnalystAgent:
    """財務分析師AI Agent"""
    
    def __init__(
        self,
        anthropic_api_key: str,
        mcp_server: MCPServer,
        model: str = "claude-sonnet-4-20250514",
        role: AgentRole = AgentRole.FINANCIAL_ANALYST
    )
    
    async def analyze(
        self,
        user_query: str,
        company_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]
```

#### Agent工作流程

```
1. 任務分類
   └─> classify_task() → TaskType

2. 任務規劃
   └─> plan_task() → {tools: [...], tool_inputs: {...}}
       │
       ├─ 分析使用者問題
       ├─ 決定需要哪些工具
       ├─ 確定工具調用順序
       └─ 準備輸入參數

3. 工具執行
   └─> execute_tools() → {tool_name: result, ...}
       │
       ├─ 按順序執行工具
       ├─ 處理依賴關係
       └─ 收集所有結果

4. 結果合成
   └─> synthesize_answer() → final_report
       │
       ├─ 整合所有工具輸出
       ├─ 生成結構化報告
       └─ 提供投資建議
```

#### Agent系統提示詞結構

```python
system_prompt = """
你是一位專業的財務分析師AI助手...

## 你的專業能力
1. 財務分析: 深入分析財務報表，計算30+項財務比率
2. 估值建模: DCF、DDM、PE、PB等方法
3. 風險評估: Altman Z-Score破產預測
4. 同業比較: SWOT分析
5. 報告生成: 專業財務分析報告

## 可用工具
{8個工具的詳細說明}

## 工作流程
1. 理解需求 → 2. 規劃步驟 → 3. 執行工具 → 4. 合成答案 → 5. 提供建議

## 輸出格式
📊 分析摘要
💡 關鍵發現
📈 詳細分析
⚠️ 風險提示
🎯 投資建議
"""
```

---

## 工作流程

### 完整分析流程範例

```python
# 使用者查詢
user_query = "分析台積電(2330)的投資價值，包括財務健康度、風險評估和估值"

# 1. 初始化
agent = FinancialAnalystAgent(api_key="...", mcp_server=server)

# 2. 執行分析
result = await agent.analyze(
    user_query=user_query,
    company_id="2330"
)

# 3. 分析流程 (Agent自動完成)
"""
Step 1: 任務分類
  └─> TaskType.COMPANY_ANALYSIS

Step 2: 任務規劃 (AI決策)
  └─> Tools: [
        "calculate_financial_ratios",  # 財務健康度
        "assess_company_risk",         # 風險評估
        "perform_dcf_valuation"        # 估值
      ]

Step 3: 工具執行 (並行)
  ├─> calculate_financial_ratios(company_id="2330")
  │   └─> {health_score: 92, rating: "Excellent", ...}
  │
  ├─> assess_company_risk(company_id="2330")
  │   └─> {z_score: 5.21, risk_level: "LOW", ...}
  │
  └─> perform_dcf_valuation(company_id="2330", ...)
      └─> {fair_value: 650, upside: 15.2%, ...}

Step 4: 結果合成 (AI生成報告)
  └─> Claude API 調用，整合所有數據
      └─> 生成結構化分析報告
"""

# 4. 輸出結果
print(result['final_answer'])
```

### 多輪對話範例

```python
# 第1輪
result1 = await agent.analyze("台積電的財務健康度如何?")
# Agent規劃: calculate_financial_ratios
# 回答: "台積電財務健康度評分92分，屬於Excellent等級..."

# 第2輪 (基於上一輪上下文)
result2 = await agent.analyze("它的主要風險是什麼?")
# Agent規劃: assess_company_risk
# 回答: "台積電Altman Z-Score為5.21，屬於低風險等級..."

# 第3輪
result3 = await agent.analyze("現在適合買入嗎?")
# Agent規劃: perform_dcf_valuation, compare_with_peers
# 回答: "根據DCF估值，公允價值650元，目前有15%上漲空間..."
```

---

## API規格

### REST API 端點

```python
# 1. 執行分析
POST /api/v1/agent/analyze
Content-Type: application/json

{
  "user_query": "分析台積電的投資價值",
  "company_id": "2330",
  "context": {
    "risk_tolerance": "medium",
    "investment_horizon_years": 3
  }
}

Response:
{
  "task_id": "task_20241204_153045",
  "task_type": "company_analysis",
  "final_answer": "...",
  "tool_results": {...},
  "metadata": {
    "tools_executed": ["calculate_financial_ratios", "assess_company_risk"],
    "execution_time_seconds": 5.2
  }
}

# 2. 獲取任務狀態
GET /api/v1/agent/tasks/{task_id}

# 3. 列出可用工具
GET /api/v1/mcp/tools

# 4. 執行單一工具
POST /api/v1/mcp/tools/{tool_name}/execute
```

### WebSocket API (即時分析)

```python
# 連接
ws://localhost:8000/api/v1/agent/ws

# 訊息格式
{
  "type": "analyze",
  "payload": {
    "user_query": "...",
    "company_id": "2330"
  }
}

# 串流回應
{
  "type": "progress",
  "step": 1,
  "total_steps": 3,
  "message": "正在計算財務比率..."
}

{
  "type": "tool_result",
  "tool_name": "calculate_financial_ratios",
  "result": {...}
}

{
  "type": "final_answer",
  "answer": "..."
}
```

---

## 部署指南

### Docker Compose 部署

```yaml
# docker-compose.yml
version: '3.8'

services:
  # AI Agent 服務
  ai-agent:
    build: .
    image: aev-ai-agent:latest
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - DATABASE_URL=postgresql://user:pass@postgres:5432/aev
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    ports:
      - "8000:8000"
    command: uvicorn src.api.main:app --host 0.0.0.0 --port 8000
  
  # MCP Server (可選，作為獨立服務)
  mcp-server:
    build: .
    image: aev-mcp-server:latest
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/aev
    ports:
      - "8001:8001"
    command: python -m src.mcp_server.main
  
  # PostgreSQL
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=aev
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  # Redis (快取)
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Kubernetes 部署

```yaml
# k8s/ai-agent-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-agent
  template:
    metadata:
      labels:
        app: ai-agent
    spec:
      containers:
      - name: ai-agent
        image: aev-ai-agent:latest
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: anthropic-key
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: ai-agent-service
spec:
  selector:
    app: ai-agent
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

---

## 測試策略

### 1. 單元測試 (Unit Tests)

```python
# tests/test_mcp_server.py
import pytest
from mcp_server_core import MCPServer
from mcp_server_tools import FinancialRatiosInput

@pytest.mark.asyncio
async def test_financial_ratios_tool(test_db):
    """測試財務比率計算工具"""
    server = MCPServer(db_session=test_db)
    
    response = await server.execute_tool(
        tool_name="calculate_financial_ratios",
        input_data={
            "company_id": "2330",
            "period": "latest"
        }
    )
    
    assert response.success == True
    assert response.data["financial_health_score"] > 0
    assert response.data["rating"] in ["Excellent", "Good", "Average", "Below Average", "Poor"]

# tests/test_ai_agent.py
@pytest.mark.asyncio
async def test_agent_task_classification():
    """測試Agent任務分類"""
    agent = FinancialAnalystAgent(api_key="test", mcp_server=mock_server)
    
    task_type = await agent._classify_task("台積電的風險評估")
    assert task_type == TaskType.RISK_ASSESSMENT

@pytest.mark.asyncio
async def test_agent_tool_planning():
    """測試Agent工具規劃"""
    agent = FinancialAnalystAgent(api_key="test", mcp_server=mock_server)
    
    plan = await agent._plan_task(
        user_query="分析台積電的投資價值",
        company_id="2330",
        context=None,
        state=AgentState(task_id="test", task_type=TaskType.COMPANY_ANALYSIS)
    )
    
    assert "calculate_financial_ratios" in plan["tools"]
    assert "assess_company_risk" in plan["tools"]
```

### 2. 整合測試 (Integration Tests)

```python
# tests/integration/test_end_to_end_analysis.py
@pytest.mark.asyncio
async def test_complete_analysis_workflow(test_db):
    """測試完整分析流程"""
    # 初始化
    mcp_server = MCPServer(db_session=test_db)
    agent = FinancialAnalystAgent(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        mcp_server=mcp_server
    )
    
    # 執行分析
    result = await agent.analyze(
        user_query="分析台積電的財務健康度和風險等級",
        company_id="2330"
    )
    
    # 驗證結果
    assert result["task_type"] in ["company_analysis", "risk_assessment"]
    assert len(result["metadata"]["tools_executed"]) >= 2
    assert "final_answer" in result
    assert len(result["final_answer"]) > 100  # 至少100字的報告
```

### 3. 效能測試 (Performance Tests)

```python
# tests/performance/test_tool_execution_speed.py
@pytest.mark.asyncio
async def test_tool_execution_performance():
    """測試工具執行效能"""
    server = MCPServer(db_session=test_db)
    
    # 單一工具執行應在1秒內完成
    start = time.time()
    response = await server.execute_tool(
        "calculate_financial_ratios",
        {"company_id": "2330", "period": "latest"}
    )
    elapsed = time.time() - start
    
    assert elapsed < 1.0  # 應在1秒內完成
    assert response.metadata["execution_time_ms"] < 1000

@pytest.mark.asyncio
async def test_parallel_tool_execution():
    """測試並行工具執行效能"""
    server = MCPServer(db_session=test_db, max_concurrent_tools=5)
    
    tool_requests = [
        {"tool_name": "calculate_financial_ratios", "input_data": {"company_id": "2330"}},
        {"tool_name": "assess_company_risk", "input_data": {"company_id": "2330"}},
        {"tool_name": "compare_with_peers", "input_data": {"company_id": "2330"}}
    ]
    
    start = time.time()
    responses = await server.execute_multiple_tools(tool_requests)
    elapsed = time.time() - start
    
    # 並行執行應比順序執行快至少50%
    assert elapsed < 3.0  # 3個工具並行應在3秒內完成
```

---

## 最佳實踐

### 1. 錯誤處理

```python
# 工具執行時的錯誤處理
async def execute_tool_with_retry(
    server: MCPServer,
    tool_name: str,
    input_data: Dict,
    max_retries: int = 3
) -> ToolResponse:
    """帶重試機制的工具執行"""
    for attempt in range(max_retries):
        try:
            response = await server.execute_tool(tool_name, input_data)
            if response.success:
                return response
            
            logger.warning(
                "Tool execution failed, retrying",
                tool_name=tool_name,
                attempt=attempt + 1,
                error=response.error
            )
            
            await asyncio.sleep(2 ** attempt)  # 指數退避
            
        except Exception as e:
            logger.error("Tool execution error", error=str(e))
            if attempt == max_retries - 1:
                raise
    
    raise Exception(f"Tool {tool_name} failed after {max_retries} attempts")
```

### 2. 快取策略

```python
# 使用Redis快取工具結果
from functools import wraps
import hashlib
import json

def cache_tool_result(ttl_seconds: int = 3600):
    """快取工具執行結果的裝飾器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, input_data: Dict, *args, **kwargs):
            # 生成快取鍵
            cache_key = f"tool:{func.__name__}:{hashlib.md5(json.dumps(input_data, sort_keys=True).encode()).hexdigest()}"
            
            # 檢查快取
            cached = await self.redis.get(cache_key)
            if cached:
                logger.info("Cache hit", cache_key=cache_key)
                return json.loads(cached)
            
            # 執行工具
            result = await func(self, input_data, *args, **kwargs)
            
            # 儲存到快取
            await self.redis.setex(
                cache_key,
                ttl_seconds,
                json.dumps(result, ensure_ascii=False)
            )
            
            return result
        return wrapper
    return decorator
```

### 3. 監控和日誌

```python
# 結構化日誌記錄
import structlog

logger = structlog.get_logger(__name__)

async def execute_tool(self, tool_name: str, input_data: Dict):
    """執行工具並記錄詳細日誌"""
    
    # 開始執行
    logger.info(
        "Tool execution started",
        tool_name=tool_name,
        input_data=input_data,
        task_id=self.current_task_id
    )
    
    start_time = time.time()
    
    try:
        result = await self._execute_tool_internal(tool_name, input_data)
        
        execution_time = time.time() - start_time
        
        # 成功日誌
        logger.info(
            "Tool execution completed",
            tool_name=tool_name,
            execution_time_seconds=execution_time,
            result_size_bytes=len(json.dumps(result))
        )
        
        # 記錄到Prometheus
        TOOL_EXECUTION_TIME.labels(tool_name=tool_name).observe(execution_time)
        TOOL_EXECUTION_COUNT.labels(tool_name=tool_name, status="success").inc()
        
        return result
        
    except Exception as e:
        execution_time = time.time() - start_time
        
        # 錯誤日誌
        logger.error(
            "Tool execution failed",
            tool_name=tool_name,
            execution_time_seconds=execution_time,
            error=str(e),
            exc_info=True
        )
        
        # 記錄錯誤
        TOOL_EXECUTION_COUNT.labels(tool_name=tool_name, status="failure").inc()
        
        raise
```

### 4. 安全性

```python
# 輸入驗證和清理
from pydantic import validator

class ToolInput(BaseModel):
    """工具輸入基類"""
    
    @validator("*", pre=True)
    def sanitize_input(cls, v):
        """清理輸入，防止注入攻擊"""
        if isinstance(v, str):
            # 移除潛在危險字元
            v = v.replace("<", "&lt;").replace(">", "&gt;")
            # 限制長度
            if len(v) > 10000:
                raise ValueError("Input too long")
        return v

# API速率限制
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/agent/analyze")
@limiter.limit("10/minute")  # 每分鐘最多10次請求
async def analyze_endpoint(request: Request):
    ...
```

---

## 📚 參考資料

1. **Model Context Protocol (MCP)**  
   - [MCP Specification](https://modelcontextprotocol.io/introduction)
   - [Anthropic MCP Documentation](https://docs.anthropic.com/claude/docs/model-context-protocol)

2. **Claude API**  
   - [Claude API Documentation](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)
   - [Tool Use (Function Calling)](https://docs.anthropic.com/claude/docs/tool-use)

3. **財務分析理論**  
   - IFRS 13 公允價值衡量
   - Altman Z-Score 破產預測模型
   - DCF估值方法論

4. **專案相關文件**  
   - `CLAUDE.md` - 完整系統開發規格
   - `COMPREHENSIVE_TEST_REPORT.md` - 測試報告
   - `QC_TEST_REPORT.md` - 品質控制報告

---

## 📞 支援

如有問題，請聯繫:
- 技術支援: tech-support@example.com
- 文件問題: docs@example.com
- GitHub Issues: https://github.com/your-org/aev-v2c/issues

---

**最後更新**: 2024-12-04  
**版本**: 1.0.0  
**授權**: MIT License
