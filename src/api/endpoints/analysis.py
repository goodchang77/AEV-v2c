"""
分析 API 端點
Analysis API Endpoints
=====================

對齊真實服務層簽名的分析端點：
- POST /analysis/dcf             DCF 現金流折現評價（無狀態，不需 DB）
- POST /analysis/peer-comparison 同業比較（顯式提供資料，不需 DB）
- POST /analysis/risk-assessment 綜合風險評估（DB-backed，需公司財務資料）
"""

from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, HTTPException

from src.core.exceptions import FinancialDataNotFoundError
from src.schemas.requests import (
    DCFValuationRequest,
    PeerComparisonDataRequest,
    RiskAssessmentRequest,
)
from src.schemas.responses import StandardResponse
from src.services.peer_analysis import (
    IndustryBenchmark,
    PeerAnalyzer,
    PeerCompanyData,
)
from src.services.risk_assessment import RiskAssessmentEngine
from src.services.valuation_models import DCFParameters, DCFValuationModel

router = APIRouter()


def _to_peer_company(d) -> PeerCompanyData:
    """將 Pydantic 輸入轉為 PeerCompanyData dataclass"""
    return PeerCompanyData(**d.model_dump())


def _to_industry_benchmark(d) -> IndustryBenchmark:
    """將 Pydantic 輸入轉為 IndustryBenchmark dataclass"""
    return IndustryBenchmark(**d.model_dump())


@router.post("/dcf", response_model=StandardResponse)
async def calculate_dcf_valuation(request: DCFValuationRequest):
    """DCF 現金流折現評價（含敏感性分析）"""
    if request.base_revenue is None:
        raise HTTPException(status_code=422, detail="base_revenue 為必填（基期營收）")

    params = DCFParameters(
        forecast_years=request.forecast_years,
        revenue_growth_rates=request.revenue_growth_rates,
        ebitda_margin=request.ebitda_margin,
        tax_rate=request.tax_rate,
        capex_rate=request.capex_rate,
        working_capital_rate=request.working_capital_rate,
        discount_rate=request.discount_rate,
        terminal_growth_rate=request.terminal_growth_rate,
    )

    base_revenue = float(request.base_revenue)
    net_debt = float(request.net_debt) if request.net_debt is not None else 0.0
    shares_outstanding = request.shares_outstanding or 1_000_000

    model = DCFValuationModel(params)
    result = model.calculate_enterprise_value(base_revenue, net_debt, shares_outstanding)

    sensitivity = None
    if request.sensitivity_analysis:
        sensitivity = model.perform_sensitivity_analysis(
            base_revenue, net_debt, shares_outstanding
        )

    return StandardResponse(
        success=True,
        data={"valuation": asdict(result), "sensitivity_analysis": sensitivity},
        meta={
            "company_id": request.company_id,
            "model_type": "DCF",
            "calculation_date": datetime.utcnow().isoformat(),
        },
    )


@router.post("/peer-comparison", response_model=StandardResponse)
async def peer_comparison_analysis(request: PeerComparisonDataRequest):
    """同業比較分析（顯式提供目標公司、同業與產業基準資料）"""
    target = _to_peer_company(request.target)
    peers = [_to_peer_company(p) for p in request.peers]
    benchmark = _to_industry_benchmark(request.industry_benchmark)

    analyzer = PeerAnalyzer()
    result = analyzer.analyze_peer_comparison(target, peers, benchmark)
    report = analyzer.generate_peer_comparison_report(result)

    return StandardResponse(
        success=True,
        data=report,
        meta={
            "company_id": target.company_id,
            "num_peers": len(peers),
            "analysis_date": datetime.utcnow().isoformat(),
        },
    )


@router.post("/risk-assessment", response_model=StandardResponse)
async def risk_assessment(request: RiskAssessmentRequest):
    """綜合風險評估（需資料庫中的公司財務資料）"""
    try:
        engine = RiskAssessmentEngine()
        result = engine.assess_overall_risk(company_id=request.company_id)
    except FinancialDataNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message)

    return StandardResponse(
        success=True,
        data=result,
        meta={
            "company_id": request.company_id,
            "assessment_date": datetime.utcnow().isoformat(),
            "risk_grade": result.get("risk_grade"),
        },
    )
