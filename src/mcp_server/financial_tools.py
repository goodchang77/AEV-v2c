# src/mcp_server/financial_tools.py
from mcp import Tool, Context
from src.services.financial_calculator import FinancialCalculator

class FinancialMCPServer:
    """
    MCP Server for Financial Analysis Tools
    
    提供給AI Agent的工具:
    - calculate_financial_ratios
    - perform_dcf_valuation
    - assess_company_risk
    - compare_with_peers
    """
    
    @Tool(
        name="calculate_financial_ratios",
        description="計算公司的30+財務比率,包括流動性、獲利能力、效率、槓桿等指標"
    )
    async def calculate_ratios(
        self,
        ctx: Context,
        company_id: str,
        period: str = "latest"
    ) -> Dict:
        """計算財務比率工具"""
        calculator = FinancialCalculator(ctx.db)
        ratios = calculator.calculate_all_ratios(company_id, period)
        return {
            "company_id": company_id,
            "period": period,
            "ratios": ratios,
            "financial_health_score": calculator.calculate_financial_health_score(ratios)
        }
    
    @Tool(
        name="assess_company_risk",
        description="評估公司風險,包括Altman Z-Score破產預測、流動性風險、槓桿風險等"
    )
    async def assess_risk(
        self,
        ctx: Context,
        company_id: str
    ) -> Dict:
        """風險評估工具"""
        engine = RiskAssessmentEngine(ctx.db)
        return engine.assess_overall_risk(company_id)
    
    @Tool(
        name="perform_dcf_valuation",
        description="執行DCF現金流折現估值,計算公司內在價值"
    )
    async def dcf_valuation(
        self,
        ctx: Context,
        company_id: str,
        discount_rate: float = 0.10,
        terminal_growth_rate: float = 0.03
    ) -> Dict:
        """DCF估值工具"""
        model = DCFValuationModel(ctx.db)
        return model.calculate_enterprise_value(
            company_id=company_id,
            discount_rate=discount_rate,
            terminal_growth_rate=terminal_growth_rate
        )