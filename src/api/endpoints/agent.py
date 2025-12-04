"""
AI Agent API端點
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
import os

from src.core.database import get_sync_session as get_db
from src.mcp_server.server import MCPServer
from src.ai_agent.agent import FinancialAnalystAgent
from src.schemas.requests import AgentAnalysisRequest
from src.schemas.responses import StandardResponse

router = APIRouter(tags=["AI Agent"])

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