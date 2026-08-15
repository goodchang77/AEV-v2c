"""
AI Agent 協調層 (Financial Analyst Agent)
==========================================

使用 Claude API 作為推理引擎，透過 MCP Server 調用財務分析工具。

核心功能:
1. 任務規劃 (Task Planning) - 分析使用者問題，決定需要調用哪些工具
2. 工具編排 (Tool Orchestration) - 按依賴關係執行工具
3. 結果合成 (Result Synthesis) - 整合多個工具的輸出，生成最終答案
4. 對話管理 (Conversation Management) - 維護多輪對話上下文
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum

import anthropic
from pydantic import BaseModel, Field

from src.mcp_server.server import MCPServer, ToolResponse
import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# Agent 配置和狀態管理
# ============================================================================

class AgentRole(str, Enum):
    """Agent 角色"""
    FINANCIAL_ANALYST = "financial_analyst"  # 財務分析師
    RISK_MANAGER = "risk_manager"            # 風險管理師
    VALUATION_EXPERT = "valuation_expert"    # 估值專家
    PORTFOLIO_ADVISOR = "portfolio_advisor"  # 投資組合顧問


class TaskType(str, Enum):
    """任務類型"""
    COMPANY_ANALYSIS = "company_analysis"          # 公司分析
    VALUATION = "valuation"                        # 估值
    RISK_ASSESSMENT = "risk_assessment"            # 風險評估
    PEER_COMPARISON = "peer_comparison"            # 同業比較
    PORTFOLIO_REVIEW = "portfolio_review"          # 投資組合檢視
    DOCUMENT_ANALYSIS = "document_analysis"        # 文件分析
    MARKET_MONITORING = "market_monitoring"        # 市場監控
    Q_AND_A = "q_and_a"                           # 問答


class AgentState(BaseModel):
    """Agent 狀態"""
    task_id: str
    task_type: TaskType
    current_step: int = 0
    total_steps: int = 0
    tools_to_execute: List[str] = Field(default_factory=list)
    executed_tools: List[str] = Field(default_factory=list)
    tool_results: Dict[str, Any] = Field(default_factory=dict)
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    intermediate_thoughts: List[str] = Field(default_factory=list)


# ============================================================================
# Financial Analyst Agent 主類
# ============================================================================

class FinancialAnalystAgent:
    """
    財務分析師 AI Agent
    
    特點:
    1. 使用 Claude Sonnet 4 作為推理引擎
    2. 透過 MCP Server 調用 8 個財務分析工具
    3. 支援多步驟推理和工具編排
    4. 提供結構化的分析報告
    """
    
    def __init__(
        self,
        anthropic_api_key: str,
        mcp_server: MCPServer,
        model: str = "claude-sonnet-4-20250514",
        role: AgentRole = AgentRole.FINANCIAL_ANALYST
    ):
        self.client = anthropic.AsyncAnthropic(api_key=anthropic_api_key)
        self.mcp_server = mcp_server
        self.model = model
        self.role = role
        
        # Agent系統提示詞
        self.system_prompt = self._build_system_prompt()
        
        logger.info(
            "Financial Analyst Agent initialized",
            model=model,
            role=role.value,
            available_tools=len(mcp_server.tools)
        )
    
    def _build_system_prompt(self) -> str:
        """構建Agent系統提示詞"""
        
        # 獲取所有可用工具的說明
        tools_description = self._generate_tools_description()
        
        return f"""你是一位專業的財務分析師AI助手，專精於台灣股市的企業財務分析與估值。

## 你的專業能力

1. **財務分析**: 深入分析公司財務報表，計算30+項財務比率
2. **估值建模**: 使用DCF、DDM、本益比、股價淨值比等方法進行估值
3. **風險評估**: 評估公司財務風險，包括破產預測(Altman Z-Score)
4. **同業比較**: 與同業公司進行多維度比較，生成SWOT分析
5. **報告生成**: 產出專業的財務分析報告

## 可用工具

你可以調用以下8個專業工具來輔助分析:

{tools_description}

## 工作流程

面對使用者的問題時，請按以下步驟思考:

1. **理解需求**: 分析使用者問題，確定任務類型
2. **規劃步驟**: 決定需要調用哪些工具，以及調用順序
3. **執行工具**: 按計畫調用工具，收集數據
4. **合成答案**: 整合工具結果，生成專業的分析報告
5. **提供建議**: 基於分析結果，給出明確的投資建議

## 輸出格式

請始終以結構化的方式回答:

### 📊 分析摘要
[簡潔的總結，3-5句話]

### 💡 關鍵發現
- [發現1]
- [發現2]
- [發現3]

### 📈 詳細分析
[詳細的分析內容，引用工具數據]

### ⚠️ 風險提示
[關鍵風險警示]

### 🎯 投資建議
[明確的投資建議: 買入/持有/賣出，附帶理由]

## 重要原則

1. **數據驅動**: 所有結論必須基於工具返回的實際數據
2. **專業嚴謹**: 使用專業術語，但確保清晰易懂
3. **風險警示**: 主動指出潛在風險，不做過度樂觀預測
4. **可操作性**: 提供具體可執行的建議
5. **誠實謙遜**: 遇到不確定的情況，明確說明限制

現在，請準備好協助使用者進行財務分析。"""
    
    def _generate_tools_description(self) -> str:
        """生成工具說明"""
        tools = self.mcp_server.list_tools()
        
        descriptions = []
        for i, tool in enumerate(tools, 1):
            desc = f"""
{i}. **{tool['name']}**
   - 說明: {tool['description']}
   - 類別: {tool['category']}
   - 預估執行時間: {tool['estimated_execution_time_ms']}ms
"""
            descriptions.append(desc)
        
        return "\n".join(descriptions)
    
    async def analyze(
        self,
        user_query: str,
        company_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        主要分析方法
        
        Args:
            user_query: 使用者問題
            company_id: 公司代號(可選)
            context: 額外上下文(可選)
        
        Returns:
            Dict: 包含分析結果、工具調用記錄、AI回應等
        """
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(
            "Analysis started",
            task_id=task_id,
            user_query=user_query,
            company_id=company_id
        )
        
        # 初始化Agent狀態
        state = AgentState(
            task_id=task_id,
            task_type=await self._classify_task(user_query),
            conversation_history=[
                {"role": "user", "content": user_query}
            ]
        )
        
        # 第一步: 規劃任務
        plan = await self._plan_task(user_query, company_id, context, state)
        state.tools_to_execute = plan["tools"]
        state.total_steps = len(plan["tools"])
        state.intermediate_thoughts.append(plan["reasoning"])
        
        logger.info(
            "Task planned",
            task_id=task_id,
            tools_to_execute=plan["tools"],
            reasoning=plan["reasoning"]
        )
        
        # 第二步: 執行工具
        tool_results = await self._execute_tools(plan["tools"], plan["tool_inputs"], state)
        state.tool_results = tool_results
        
        # 第三步: 合成最終答案
        final_answer = await self._synthesize_answer(
            user_query=user_query,
            tool_results=tool_results,
            plan=plan,
            state=state
        )
        
        logger.info(
            "Analysis completed",
            task_id=task_id,
            tools_executed=len(state.executed_tools)
        )
        
        return {
            "task_id": task_id,
            "task_type": state.task_type.value,
            "user_query": user_query,
            "company_id": company_id,
            "plan": plan,
            "tool_results": tool_results,
            "final_answer": final_answer,
            "metadata": {
                "tools_executed": state.executed_tools,
                "total_steps": state.total_steps,
                "intermediate_thoughts": state.intermediate_thoughts,
                "timestamp": datetime.now().isoformat()
            }
        }
    
    async def _classify_task(self, user_query: str) -> TaskType:
        """分類任務類型"""
        
        classification_prompt = f"""請分類以下使用者問題的任務類型:

使用者問題: {user_query}

可選任務類型:
- company_analysis: 公司整體分析
- valuation: 估值相關問題
- risk_assessment: 風險評估
- peer_comparison: 同業比較
- portfolio_review: 投資組合檢視
- document_analysis: 文件分析
- market_monitoring: 市場監控
- q_and_a: 一般問答

請只回答任務類型代碼(例如: company_analysis)，不要有其他文字。"""
        
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=50,
            messages=[{"role": "user", "content": classification_prompt}]
        )
        
        task_type_str = response.content[0].text.strip()
        
        try:
            return TaskType(task_type_str)
        except ValueError:
            return TaskType.Q_AND_A
    
    async def _plan_task(
        self,
        user_query: str,
        company_id: Optional[str],
        context: Optional[Dict[str, Any]],
        state: AgentState
    ) -> Dict[str, Any]:
        """
        規劃任務執行步驟
        
        Returns:
            Dict: 包含工具列表、工具輸入、推理過程
        """
        
        planning_prompt = f"""請為以下使用者問題規劃分析步驟:

使用者問題: {user_query}
公司代號: {company_id if company_id else "未指定"}
任務類型: {state.task_type.value}

你需要決定:
1. 應該調用哪些工具 (從上面的8個工具中選擇)
2. 每個工具的輸入參數
3. 工具調用的順序

請以JSON格式回答:
{{
    "reasoning": "你的推理過程",
    "tools": ["tool_name_1", "tool_name_2", ...],
    "tool_inputs": {{
        "tool_name_1": {{...輸入參數...}},
        "tool_name_2": {{...輸入參數...}}
    }}
}}

範例:
如果使用者問"分析台積電的財務健康度和估值"，你可能需要:
1. calculate_financial_ratios - 計算財務比率
2. assess_company_risk - 評估風險
3. perform_dcf_valuation - DCF估值

請確保:
- 工具調用順序合理(有依賴關係的工具要按順序)
- 輸入參數完整且符合工具定義
- 只選擇必要的工具，不要過度調用"""
        
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": planning_prompt}]
        )
        
        # 解析JSON回應
        response_text = response.content[0].text
        
        # 提取JSON (可能被```json包裹)
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end]
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end]
        
        try:
            plan = json.loads(response_text.strip())
            
            # 如果沒有指定company_id但工具需要，使用用戶提供的
            if company_id:
                for tool_name, inputs in plan["tool_inputs"].items():
                    if "company_id" in inputs and not inputs["company_id"]:
                        inputs["company_id"] = company_id
            
            return plan
        except json.JSONDecodeError as e:
            logger.error("Failed to parse plan JSON", error=str(e), response=response_text)
            
            # 回退計畫: 基於任務類型的預設工具
            return self._get_default_plan(state.task_type, company_id)
    
    def _get_default_plan(self, task_type: TaskType, company_id: Optional[str]) -> Dict[str, Any]:
        """獲取預設計畫 (當AI規劃失敗時使用)"""
        
        default_plans = {
            TaskType.COMPANY_ANALYSIS: {
                "reasoning": "公司綜合分析需要計算財務比率和評估風險",
                "tools": ["calculate_financial_ratios", "assess_company_risk"],
                "tool_inputs": {
                    "calculate_financial_ratios": {
                        "company_id": company_id or "2330",
                        "period": "latest"
                    },
                    "assess_company_risk": {
                        "company_id": company_id or "2330"
                    }
                }
            },
            TaskType.VALUATION: {
                "reasoning": "估值分析需要DCF模型和同業比較",
                "tools": ["perform_dcf_valuation", "compare_with_peers"],
                "tool_inputs": {
                    "perform_dcf_valuation": {
                        "company_id": company_id or "2330",
                        "revenue_growth_rates": [0.10, 0.10, 0.08, 0.08, 0.05],
                        "terminal_growth_rate": 0.03
                    },
                    "compare_with_peers": {
                        "company_id": company_id or "2330",
                        "num_peers": 5
                    }
                }
            },
            TaskType.RISK_ASSESSMENT: {
                "reasoning": "風險評估需要專門的風險分析工具",
                "tools": ["assess_company_risk"],
                "tool_inputs": {
                    "assess_company_risk": {
                        "company_id": company_id or "2330",
                        "assessment_scope": ["all"]
                    }
                }
            }
        }
        
        return default_plans.get(task_type, default_plans[TaskType.COMPANY_ANALYSIS])
    
    async def _execute_tools(
        self,
        tools: List[str],
        tool_inputs: Dict[str, Dict],
        state: AgentState
    ) -> Dict[str, Any]:
        """執行工具列表"""
        
        results = {}
        
        for i, tool_name in enumerate(tools, 1):
            state.current_step = i
            
            logger.info(
                "Executing tool",
                task_id=state.task_id,
                step=f"{i}/{state.total_steps}",
                tool_name=tool_name
            )
            
            # 執行工具
            response = await self.mcp_server.execute_tool(
                tool_name=tool_name,
                input_data=tool_inputs.get(tool_name, {})
            )
            
            if response.success:
                results[tool_name] = response.data
                state.executed_tools.append(tool_name)
                
                logger.info(
                    "Tool executed successfully",
                    tool_name=tool_name,
                    execution_time_ms=response.metadata.get("execution_time_ms")
                )
            else:
                results[tool_name] = {
                    "error": response.error
                }
                
                logger.error(
                    "Tool execution failed",
                    tool_name=tool_name,
                    error=response.error
                )
        
        return results
    
    async def _synthesize_answer(
        self,
        user_query: str,
        tool_results: Dict[str, Any],
        plan: Dict[str, Any],
        state: AgentState
    ) -> str:
        """合成最終答案"""
        
        # 構建上下文
        context_parts = [
            f"## 使用者問題\n{user_query}",
            f"\n## 分析計畫\n{plan['reasoning']}",
            f"\n## 工具執行結果\n"
        ]
        
        for tool_name, result in tool_results.items():
            context_parts.append(f"\n### {tool_name}\n")
            context_parts.append(f"```json\n{json.dumps(result, indent=2, ensure_ascii=False)}\n```\n")
        
        context = "\n".join(context_parts)
        
        synthesis_prompt = f"""{context}

請基於以上工具執行結果，為使用者生成一份專業的財務分析報告。

要求:
1. 使用繁體中文
2. 結構化輸出(按照系統提示詞中的格式)
3. 引用具體數據支持結論
4. 提供明確的投資建議
5. 指出關鍵風險

請開始撰寫報告:"""
        
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            system=self.system_prompt,
            messages=[{"role": "user", "content": synthesis_prompt}]
        )
        
        return response.content[0].text


# ============================================================================
# 使用範例
# ============================================================================

async def example_agent_usage():
    """Agent 使用範例"""
    
    from sqlalchemy.orm import Session
    from src.core.database import get_db
    
    # 初始化
    db = next(get_db())
    mcp_server = MCPServer(db_session=db)
    
    agent = FinancialAnalystAgent(
        anthropic_api_key="your-api-key-here",
        mcp_server=mcp_server
    )
    
    # 範例 1: 分析台積電
    print("=== 範例 1: 公司分析 ===")
    result = await agent.analyze(
        user_query="請分析台積電(2330)的財務健康度，並評估其投資價值",
        company_id="2330"
    )
    
    print(f"任務ID: {result['task_id']}")
    print(f"任務類型: {result['task_type']}")
    print(f"執行的工具: {', '.join(result['metadata']['tools_executed'])}")
    print(f"\n最終答案:\n{result['final_answer']}")
    
    # 範例 2: 風險評估
    print("\n=== 範例 2: 風險評估 ===")
    result = await agent.analyze(
        user_query="台積電目前面臨哪些主要風險?",
        company_id="2330"
    )
    
    print(f"\n最終答案:\n{result['final_answer']}")
    
    # 範例 3: 估值分析
    print("\n=== 範例 3: 估值分析 ===")
    result = await agent.analyze(
        user_query="台積電的合理股價應該是多少? 現在是買入時機嗎?",
        company_id="2330"
    )
    
    print(f"\n最終答案:\n{result['final_answer']}")


if __name__ == "__main__":
    asyncio.run(example_agent_usage())
