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
import logging
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
from src.services.financial_calculator import FinancialCalculator
from src.services.valuation_models import DCFValuationModel
from src.services.risk_assessment import RiskAssessmentEngine
from src.services.peer_analysis import PeerAnalyzer
from src.services.data_service import CompanyDataService, FinancialDataService
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
    ) -> FinancialRatiosOutput:
        """執行財務比率計算"""
        calculator = FinancialCalculator(self.db)
        
        # 計算指定類別的比率
        if input_data.ratio_categories:
            ratios = {}
            for category in input_data.ratio_categories:
                category_ratios = calculator.calculate_ratio_category(
                    company_id=input_data.company_id,
                    category=category,
                    period=input_data.period
                )
                ratios.update(category_ratios)
        else:
            # 計算所有比率
            ratios = calculator.calculate_all_ratios(
                company_id=input_data.company_id,
                period=input_data.period
            )
        
        # 計算綜合評分
        health_score = calculator.calculate_financial_health_score(ratios)
        
        # 評級
        if health_score >= 90:
            rating = "Excellent"
        elif health_score >= 75:
            rating = "Good"
        elif health_score >= 60:
            rating = "Average"
        elif health_score >= 40:
            rating = "Below Average"
        else:
            rating = "Poor"
        
        return FinancialRatiosOutput(
            company_id=input_data.company_id,
            company_name=calculator.get_company_name(input_data.company_id),
            period=input_data.period,
            period_date=calculator.get_period_date(input_data.company_id, input_data.period),
            financial_structure=ratios.get("financial_structure", {}),
            liquidity_ratios=ratios.get("liquidity", {}),
            efficiency_ratios=ratios.get("efficiency", {}),
            profitability_ratios=ratios.get("profitability", {}),
            cash_flow_ratios=ratios.get("cash_flow", {}),
            financial_health_score=health_score,
            rating=rating
        )
    
    async def _execute_dcf_valuation(
        self,
        input_data: DCFValuationInput
    ) -> DCFValuationOutput:
        """執行DCF估值"""
        model = DCFValuationModel(self.db)
        
        # 計算估值
        valuation = model.calculate_enterprise_value(
            company_id=input_data.company_id,
            revenue_growth_rates=input_data.revenue_growth_rates,
            terminal_growth_rate=input_data.terminal_growth_rate,
            discount_rate=input_data.discount_rate
        )
        
        # 敏感性分析
        sensitivity = None
        if input_data.perform_sensitivity_analysis:
            sensitivity = model.perform_sensitivity_analysis(
                base_result=valuation,
                discount_rate_range=(-0.02, 0.02),
                growth_rate_range=(-0.01, 0.01)
            )
        
        # 獲取當前市價
        current_price = model.get_current_market_price(input_data.company_id)
        current_market_cap = model.get_current_market_cap(input_data.company_id)
        
        # 計算上漲/下跌空間
        upside = ((valuation["fair_value_per_share"] - current_price) / current_price) * 100
        
        # 投資建議
        if upside > 30:
            recommendation = "強力買入"
        elif upside > 15:
            recommendation = "買入"
        elif upside > -15:
            recommendation = "持有"
        elif upside > -30:
            recommendation = "賣出"
        else:
            recommendation = "強力賣出"
        
        return DCFValuationOutput(
            company_id=input_data.company_id,
            company_name=model.get_company_name(input_data.company_id),
            valuation_date=datetime.now(),
            enterprise_value=valuation["enterprise_value"] / 100_000_000,  # 轉換為億元
            equity_value=valuation["equity_value"] / 100_000_000,
            fair_value_per_share=valuation["fair_value_per_share"],
            current_market_price=current_price,
            current_market_cap=current_market_cap / 100_000_000,
            upside_downside_percentage=round(upside, 2),
            investment_recommendation=recommendation,
            valuation_details=valuation,
            sensitivity_analysis=sensitivity
        )
    
    async def _execute_risk_assessment(
        self,
        input_data: RiskAssessmentInput
    ) -> RiskAssessmentOutput:
        """執行風險評估"""
        engine = RiskAssessmentEngine(self.db)
        
        # 綜合風險評估
        risk_result = engine.assess_overall_risk(
            company_id=input_data.company_id,
            assessment_scope=input_data.assessment_scope
        )
        
        # 產業比較 (如果需要)
        industry_comparison = None
        if input_data.include_industry_comparison:
            industry_comparison = engine.compare_risk_with_industry(
                company_id=input_data.company_id
            )
        
        return RiskAssessmentOutput(
            company_id=input_data.company_id,
            company_name=engine.get_company_name(input_data.company_id),
            assessment_date=datetime.now(),
            overall_risk_score=risk_result["overall_risk_score"],
            overall_risk_level=risk_result["risk_level"],
            risk_grade=risk_result["risk_grade"],
            risk_breakdown=risk_result["risk_breakdown"],
            altman_z_score=risk_result["risk_breakdown"]["financial_distress"]["z_score"],
            bankruptcy_probability=risk_result["risk_breakdown"]["financial_distress"]["probability_of_bankruptcy"],
            key_concerns=risk_result["key_concerns"],
            risk_trend=risk_result["risk_trend"],
            industry_comparison=industry_comparison,
            recommendations=risk_result["recommendations"]
        )
    
    async def _execute_peer_comparison(
        self,
        input_data: PeerComparisonInput
    ) -> PeerComparisonOutput:
        """執行同業比較"""
        analyzer = PeerAnalyzer(self.db)
        
        # 執行同業比較
        comparison = analyzer.analyze_peer_comparison(
            company_id=input_data.company_id,
            peer_selection_method=input_data.peer_selection_method,
            manual_peer_ids=input_data.manual_peer_ids,
            num_peers=input_data.num_peers
        )
        
        return PeerComparisonOutput(
            company_id=input_data.company_id,
            company_name=comparison["company_name"],
            industry=comparison["industry"],
            comparison_date=datetime.now(),
            peers=comparison["peers"],
            rankings=comparison["rankings"],
            composite_score=comparison["composite_score"],
            performance_rating=comparison["performance_rating"],
            comparison_analysis=comparison["comparison_analysis"],
            swot_analysis=comparison["swot_analysis"],
            relative_valuation=comparison["relative_valuation"]
        )
    
    async def _execute_data_fetcher(
        self,
        input_data: DataFetcherInput
    ) -> DataFetcherOutput:
        """執行資料擷取"""
        service = CompanyDataService(self.db)
        
        fetched_data = {}
        data_sources = []
        fetch_stats = {
            "successful": 0,
            "failed": 0,
            "total_time_ms": 0
        }
        
        for data_type in input_data.data_types:
            try:
                start = time.time()
                data = service.fetch_data(
                    company_id=input_data.company_id,
                    data_type=data_type,
                    start_date=input_data.start_date,
                    end_date=input_data.end_date
                )
                elapsed = (time.time() - start) * 1000
                
                fetched_data[data_type] = data
                data_sources.extend(data.get("sources", []))
                fetch_stats["successful"] += 1
                fetch_stats["total_time_ms"] += elapsed
                
            except Exception as e:
                logger.error(f"Failed to fetch {data_type}", error=str(e))
                fetched_data[data_type] = {"error": str(e)}
                fetch_stats["failed"] += 1
        
        # 計算資料完整性
        completeness = {}
        for data_type, data in fetched_data.items():
            if isinstance(data, dict) and "error" not in data:
                completeness[data_type] = 1.0
            else:
                completeness[data_type] = 0.0
        
        return DataFetcherOutput(
            company_id=input_data.company_id,
            company_name=service.get_company_name(input_data.company_id),
            fetch_date=datetime.now(),
            fetched_data=fetched_data,
            data_completeness=completeness,
            data_sources=list(set(data_sources)),
            fetch_statistics=fetch_stats
        )
    
    async def _execute_report_generator(
        self,
        input_data: ReportGeneratorInput
    ) -> ReportGeneratorOutput:
        """執行報告生成"""
        service = ReportService(self.db)
        
        report = service.generate_report(
            company_id=input_data.company_id,
            report_type=input_data.report_type,
            report_format=input_data.report_format,
            include_sections=input_data.include_sections,
            language=input_data.language,
            custom_parameters=input_data.custom_parameters
        )
        
        return ReportGeneratorOutput(
            report_id=report["report_id"],
            company_id=input_data.company_id,
            company_name=report["company_name"],
            report_type=input_data.report_type,
            generation_date=datetime.now(),
            report_content=report.get("content"),
            report_file_path=report.get("file_path"),
            report_download_url=report.get("download_url"),
            executive_summary=report["executive_summary"],
            report_statistics=report["statistics"]
        )
    
    async def _execute_document_processor(
        self,
        input_data: DocumentProcessorInput
    ) -> DocumentProcessorOutput:
        """執行文件處理"""
        processor = PDFProcessor()  # 或其他處理器
        
        result = processor.process_document(
            document_type=input_data.document_type,
            document_source=input_data.document_source,
            document_data=input_data.document_data,
            extraction_targets=input_data.extraction_targets,
            ocr_enabled=input_data.ocr_enabled
        )
        
        return DocumentProcessorOutput(
            document_id=result["document_id"],
            document_type=input_data.document_type,
            processing_date=datetime.now(),
            extracted_data=result["extracted_data"],
            financial_statements=result.get("financial_statements"),
            key_numbers=result["key_numbers"],
            text_content=result.get("text_content"),
            processing_statistics=result["statistics"],
            confidence_scores=result["confidence_scores"]
        )
    
    async def _execute_alert_monitor(
        self,
        input_data: AlertMonitorInput
    ) -> AlertMonitorOutput:
        """執行警報監控"""
        monitor = AlertMonitor(self.db)
        
        alerts = monitor.check_alerts(
            company_ids=input_data.company_ids,
            alert_types=input_data.alert_types,
            alert_thresholds=input_data.alert_thresholds,
            lookback_period_days=input_data.lookback_period_days
        )
        
        return AlertMonitorOutput(
            monitoring_date=datetime.now(),
            lookback_period_days=input_data.lookback_period_days,
            alerts=alerts["alerts"],
            alert_summary=alerts["summary"],
            companies_requiring_attention=alerts["attention_required"],
            monitoring_status=alerts["status"]
        )
    
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
