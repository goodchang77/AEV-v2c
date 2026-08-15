"""
MCP Server 核心實作
===================

實作 Model Context Protocol Server，提供8個財務分析工具給AI Agent使用。

架構設計:
1. MCPServer - 主伺服器類，處理工具註冊和請求路由
2. ToolExecutor - 工具執行器，管理工具生命週期
3. ContextManager - 上下文管理器，維護資料庫連接和快取
"""

import asyncio
import base64
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import json
import time
from contextlib import asynccontextmanager

from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from src.mcp_server.tools import (
    MCPTool, ToolResponse,
    FinancialRatiosInput, FinancialRatiosOutput,
    DCFValuationInput, DCFValuationOutput,
    RiskAssessmentInput, RiskAssessmentOutput,
    PeerComparisonInput, PeerComparisonOutput,
    DataFetcherInput, DataFetcherOutput,
    ReportGeneratorInput, ReportGeneratorOutput,
    DocumentProcessorInput, DocumentProcessorOutput,
    AlertMonitorInput, AlertMonitorOutput,
    MCP_TOOLS_REGISTRY
)

# 引入業務邏輯服務
from src.services.valuation_models import DCFParameters, DCFValuationModel
from src.services.risk_assessment import RiskAssessmentEngine
from src.services.data_service import CompanyDataService, FinancialDataService, IndustryDataService
from src.services.report_service import ReportService
from src.services.pdf_processor import FinancialPDFProcessor
from src.services.alert_monitor import AlertMonitor
from src.core.database import get_sync_session as get_db


# ============================================================================
# 日誌配置
# ============================================================================

logger = structlog.get_logger(__name__)


# ============================================================================
# MCP Server 核心類
# ============================================================================

class MCPServer:
    """
    MCP Server 主類
    
    職責:
    1. 工具註冊和發現
    2. 請求路由和分發
    3. 錯誤處理和重試
    4. 效能監控和日誌記錄
    """
    
    def __init__(
        self,
        db_session: Session,
        cache_enabled: bool = True,
        max_concurrent_tools: int = 5
    ):
        self.db = db_session
        self.cache_enabled = cache_enabled
        self.max_concurrent_tools = max_concurrent_tools
        
        # 工具註冊表
        self.tools: Dict[str, MCPTool] = {}
        self.tool_executors: Dict[str, Callable] = {}
        
        # 效能統計
        self.execution_stats: Dict[str, List[float]] = {}
        
        # 註冊所有工具
        self._register_all_tools()
        
        logger.info(
            "MCP Server initialized",
            num_tools=len(self.tools),
            cache_enabled=cache_enabled
        )
    
    def _register_all_tools(self):
        """註冊所有MCP工具"""
        for tool in MCP_TOOLS_REGISTRY:
            self.register_tool(
                tool=tool,
                executor=self._get_executor_for_tool(tool.name)
            )
    
    def register_tool(self, tool: MCPTool, executor: Callable):
        """註冊單個工具"""
        self.tools[tool.name] = tool
        self.tool_executors[tool.name] = executor
        self.execution_stats[tool.name] = []
        
        logger.info(
            "Tool registered",
            tool_name=tool.name,
            category=tool.category
        )
    
    def _get_executor_for_tool(self, tool_name: str) -> Callable:
        """根據工具名稱返回對應的執行器"""
        executor_map = {
            "calculate_financial_ratios": self._execute_financial_ratios,
            "perform_dcf_valuation": self._execute_dcf_valuation,
            "assess_company_risk": self._execute_risk_assessment,
            "compare_with_peers": self._execute_peer_comparison,
            "fetch_company_data": self._execute_data_fetcher,
            "generate_analysis_report": self._execute_report_generator,
            "process_financial_document": self._execute_document_processor,
            "monitor_company_alerts": self._execute_alert_monitor
        }
        return executor_map.get(tool_name, self._execute_unknown_tool)
    
    async def execute_tool(
        self,
        tool_name: str,
        input_data: Dict[str, Any],
        timeout_seconds: Optional[int] = None
    ) -> ToolResponse:
        """
        執行工具
        
        Args:
            tool_name: 工具名稱
            input_data: 輸入資料
            timeout_seconds: 超時時間(秒)，若為None則使用預設值
        
        Returns:
            ToolResponse: 標準化的工具響應
        """
        start_time = time.time()
        
        # 檢查工具是否存在
        if tool_name not in self.tools:
            return ToolResponse(
                success=False,
                error=f"Unknown tool: {tool_name}",
                metadata={"available_tools": list(self.tools.keys())}
            )
        
        tool = self.tools[tool_name]
        
        # 驗證輸入
        try:
            validated_input = tool.input_schema(**input_data)
        except Exception as e:
            return ToolResponse(
                success=False,
                error=f"Input validation failed: {str(e)}",
                metadata={"tool_name": tool_name}
            )
        
        # 設定超時時間
        if timeout_seconds is None:
            timeout_seconds = tool.estimated_execution_time_ms / 1000 * 2  # 2倍預估時間
        
        # 執行工具 (帶超時控制)
        try:
            executor = self.tool_executors[tool_name]
            result = await asyncio.wait_for(
                executor(validated_input),
                timeout=timeout_seconds
            )
            
            execution_time = (time.time() - start_time) * 1000  # 毫秒
            self.execution_stats[tool_name].append(execution_time)
            
            logger.info(
                "Tool executed successfully",
                tool_name=tool_name,
                execution_time_ms=round(execution_time, 2)
            )
            
            return ToolResponse(
                success=True,
                data=result.dict() if hasattr(result, 'dict') else result,
                metadata={
                    "tool_name": tool_name,
                    "execution_time_ms": round(execution_time, 2),
                    "tool_version": tool.version
                }
            )
            
        except asyncio.TimeoutError:
            logger.error(
                "Tool execution timeout",
                tool_name=tool_name,
                timeout_seconds=timeout_seconds
            )
            return ToolResponse(
                success=False,
                error=f"Tool execution timeout after {timeout_seconds}s",
                metadata={"tool_name": tool_name}
            )
            
        except Exception as e:
            logger.error(
                "Tool execution failed",
                tool_name=tool_name,
                error=str(e),
                exc_info=True
            )
            return ToolResponse(
                success=False,
                error=f"Tool execution failed: {str(e)}",
                metadata={"tool_name": tool_name}
            )
    
    async def execute_multiple_tools(
        self,
        tool_requests: List[Dict[str, Any]]
    ) -> List[ToolResponse]:
        """
        並行執行多個工具
        
        Args:
            tool_requests: 工具請求列表，每個請求包含tool_name和input_data
        
        Returns:
            List[ToolResponse]: 工具響應列表
        """
        # 限制並發數量
        semaphore = asyncio.Semaphore(self.max_concurrent_tools)
        
        async def execute_with_semaphore(request: Dict[str, Any]):
            async with semaphore:
                return await self.execute_tool(
                    tool_name=request["tool_name"],
                    input_data=request["input_data"]
                )
        
        tasks = [execute_with_semaphore(req) for req in tool_requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 處理異常
        responses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                responses.append(ToolResponse(
                    success=False,
                    error=f"Execution failed: {str(result)}",
                    metadata={"request_index": i}
                ))
            else:
                responses.append(result)
        
        return responses
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """獲取工具資訊"""
        if tool_name not in self.tools:
            return None
        
        tool = self.tools[tool_name]
        stats = self.execution_stats.get(tool_name, [])
        
        return {
            "name": tool.name,
            "description": tool.description,
            "category": tool.category,
            "version": tool.version,
            "estimated_execution_time_ms": tool.estimated_execution_time_ms,
            "input_schema": tool.input_schema.schema(),
            "output_schema": tool.output_schema.schema(),
            "execution_stats": {
                "total_executions": len(stats),
                "avg_execution_time_ms": round(sum(stats) / len(stats), 2) if stats else 0,
                "min_execution_time_ms": round(min(stats), 2) if stats else 0,
                "max_execution_time_ms": round(max(stats), 2) if stats else 0
            }
        }
    
    def list_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出所有工具"""
        tools = MCP_TOOLS_REGISTRY
        if category:
            tools = [t for t in tools if t.category == category]
        
        return [self.get_tool_info(t.name) for t in tools]
    
    # ========================================================================
    # 工具執行器實作
    # ========================================================================

    async def _execute_financial_ratios(
        self,
        input_data: FinancialRatiosInput
    ) -> Dict[str, Any]:
        """執行財務比率計算（對齊 FinancialDataService）"""
        service = FinancialDataService()
        ratios = await service.get_financial_ratios(input_data.company_id)
        if not ratios:
            raise ValueError(f"找不到公司 {input_data.company_id} 的財務比率")
        return ratios

    async def _execute_dcf_valuation(
        self,
        input_data: DCFValuationInput
    ) -> Dict[str, Any]:
        """執行DCF估值（對齊 DCFValuationModel）"""
        fin_svc = FinancialDataService()
        statements = await fin_svc.get_latest_financial_statements(input_data.company_id)
        if statements is None or not statements.revenue:
            raise ValueError(f"找不到公司 {input_data.company_id} 的財務資料")

        params = DCFParameters(
            revenue_growth_rates=input_data.revenue_growth_rates,
            terminal_growth_rate=input_data.terminal_growth_rate,
            discount_rate=input_data.discount_rate or 0.10,
        )
        model = DCFValuationModel(params)
        result = await asyncio.to_thread(
            model.calculate_enterprise_value, float(statements.revenue)
        )
        return _to_dict(result)

    async def _execute_risk_assessment(
        self,
        input_data: RiskAssessmentInput
    ) -> Dict[str, Any]:
        """執行風險評估（對齊 RiskAssessmentEngine）"""
        engine = RiskAssessmentEngine()
        result = await asyncio.to_thread(
            engine.assess_overall_risk, input_data.company_id
        )
        return result

    async def _execute_peer_comparison(
        self,
        input_data: PeerComparisonInput
    ) -> Dict[str, Any]:
        """執行同業比較"""
        basic = await CompanyDataService().get_company_basic_info(input_data.company_id)
        if not basic:
            raise ValueError(f"找不到公司 {input_data.company_id}")

        industry_code = basic.get("industry_code")
        peers = []
        if industry_code:
            peers = await IndustryDataService().get_peer_companies_data(
                industry_code, limit=input_data.num_peers
            )

        return {
            "company_id": input_data.company_id,
            "company_name": basic.get("company_name"),
            "industry": industry_code,
            "peers": _to_dict(peers),
        }

    async def _execute_data_fetcher(
        self,
        input_data: DataFetcherInput
    ) -> Dict[str, Any]:
        """執行資料擷取"""
        basic = await CompanyDataService().get_company_basic_info(input_data.company_id)
        fin_svc = FinancialDataService()

        fetched: Dict[str, Any] = {"company": basic}
        if "ratios" in input_data.data_types:
            fetched["ratios"] = await fin_svc.get_financial_ratios(input_data.company_id)
        if "financials" in input_data.data_types:
            stmts = await fin_svc.get_latest_financial_statements(input_data.company_id)
            fetched["financials"] = _to_dict(stmts)

        return fetched

    async def _execute_report_generator(
        self,
        input_data: ReportGeneratorInput
    ) -> Dict[str, Any]:
        """執行報告生成"""
        service = ReportService()
        return await service.generate_financial_report(
            company_id=input_data.company_id,
            report_type=input_data.report_type,
            format=input_data.report_format,
        )

    async def _execute_document_processor(
        self,
        input_data: DocumentProcessorInput
    ) -> Dict[str, Any]:
        """執行文件處理（對齊 FinancialPDFProcessor）"""
        processor = FinancialPDFProcessor()
        if input_data.document_source == "file_path":
            content = Path(input_data.document_data).read_bytes()
        elif input_data.document_source == "base64":
            content = base64.b64decode(input_data.document_data)
        else:
            raise ValueError("document_source 僅支援 file_path/base64")
        return await processor.process_pdf(content, "document.pdf")

    async def _execute_alert_monitor(
        self,
        input_data: AlertMonitorInput
    ) -> Dict[str, Any]:
        """執行警報監控"""
        monitor = AlertMonitor()
        alerts: List[Dict[str, Any]] = []
        for company_id in input_data.company_ids:
            alerts.extend(await monitor.check_financial_alerts(company_id))
        return {
            "alerts": alerts,
            "alert_summary": {},
            "companies_requiring_attention": [],
            "monitoring_status": {"checked": input_data.company_ids},
        }

    async def _execute_unknown_tool(self, input_data: Any) -> Dict:
        """未知工具的處理"""
        raise ValueError("Unknown tool executor")


# ============================================================================
# 使用範例
# ============================================================================

async def example_usage():
    """MCP Server使用範例"""
    
    # 初始化資料庫連接
    db = next(get_db())
    
    # 建立MCP Server
    server = MCPServer(db_session=db)
    
    # 範例 1: 執行單個工具
    print("=== 範例 1: 計算財務比率 ===")
    response = await server.execute_tool(
        tool_name="calculate_financial_ratios",
        input_data={
            "company_id": "2330",
            "period": "latest",
            "ratio_categories": ["liquidity", "profitability"]
        }
    )
    print(json.dumps(response.dict(), indent=2, ensure_ascii=False))
    
    # 範例 2: 並行執行多個工具
    print("\n=== 範例 2: 並行執行多個工具 ===")
    responses = await server.execute_multiple_tools([
        {
            "tool_name": "calculate_financial_ratios",
            "input_data": {"company_id": "2330", "period": "latest"}
        },
        {
            "tool_name": "assess_company_risk",
            "input_data": {"company_id": "2330"}
        },
        {
            "tool_name": "compare_with_peers",
            "input_data": {"company_id": "2330", "num_peers": 5}
        }
    ])
    
    for i, response in enumerate(responses):
        print(f"\n工具 {i+1} 結果:")
        print(f"成功: {response.success}")
        if response.success:
            print(f"執行時間: {response.metadata.get('execution_time_ms')}ms")
    
    # 範例 3: 查詢工具資訊
    print("\n=== 範例 3: 工具資訊 ===")
    tool_info = server.get_tool_info("calculate_financial_ratios")
    print(json.dumps(tool_info, indent=2, ensure_ascii=False))
    
    # 範例 4: 列出所有工具
    print("\n=== 範例 4: 所有工具列表 ===")
    tools = server.list_tools()
    for tool in tools:
        print(f"- {tool['name']} ({tool['category']})")


if __name__ == "__main__":
    asyncio.run(example_usage())


def _to_dict(obj: Any) -> Any:
    """將服務回傳物件（dict/dataclass/pydantic/list）轉為可序列化 dict"""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_to_dict(x) for x in obj]
    if hasattr(obj, "dict"):
        return obj.dict()
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in vars(obj).items() if not k.startswith("_")}
    return str(obj)
