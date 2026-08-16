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
import statistics

from fastapi import APIRouter, HTTPException

from src.core.exceptions import FinancialDataNotFoundError
from src.schemas.requests import (
    AutoPeerComparisonRequest,
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
from src.services.data_service import CompanyDataService, FinancialDataService

router = APIRouter()


def _to_peer_company(d) -> PeerCompanyData:
    """將 Pydantic 輸入轉為 PeerCompanyData dataclass"""
    return PeerCompanyData(**d.model_dump())


def _to_industry_benchmark(d) -> IndustryBenchmark:
    """將 Pydantic 輸入轉為 IndustryBenchmark dataclass"""
    return IndustryBenchmark(**d.model_dump())


@router.post("/dcf", response_model=StandardResponse)
async def calculate_dcf_valuation(request: DCFValuationRequest):
    """DCF 現金流折現評價（含敏感性分析；缺 base_revenue/shares 時自動由 DB 取得）"""
    base_revenue = request.base_revenue
    shares_outstanding = request.shares_outstanding

    # 自動補齊基期營收與流通股數
    if base_revenue is None or shares_outstanding is None:
        statements = await FinancialDataService().get_latest_financial_statements(request.company_id)
        if statements is None or not statements.revenue:
            raise HTTPException(status_code=404, detail=f"找不到公司 {request.company_id} 的財務資料")
        if base_revenue is None:
            # DB 財務資料以「千元」為單位，DCF 模型以「元」為單位
            base_revenue = statements.revenue * 1000
        if shares_outstanding is None:
            info = await CompanyDataService().get_company_basic_info(request.company_id)
            shares_outstanding = (info or {}).get("outstanding_shares") or 1_000_000

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

    base_revenue = float(base_revenue)
    net_debt = float(request.net_debt) if request.net_debt is not None else 0.0
    shares_outstanding = int(shares_outstanding or 1_000_000)

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


@router.post("/peer-comparison/auto", response_model=StandardResponse)
async def auto_peer_comparison(request: AutoPeerComparisonRequest):
    """同業比較分析（自動由 DB 抓取目標與同業的財務資料）"""
    fin_svc = FinancialDataService()
    comp_svc = CompanyDataService()

    def _pct(v):
        return round((v or 0) * 100, 2)

    def _entry(cid, info, stmts, ratios) -> PeerCompanyData:
        return PeerCompanyData(
            company_id=cid,
            company_name=info.get("company_name", cid),
            market_cap=float(info.get("capital_amount") or 0) * 1000,
            revenue=float(stmts.revenue or 0) * 1000,
            net_income=float(stmts.net_income or 0) * 1000,
            total_assets=float(stmts.total_assets or 0) * 1000,
            shareholders_equity=float(stmts.shareholders_equity or 0) * 1000,
            roe=_pct(ratios.get("roe")),
            roa=_pct(ratios.get("roa")),
            current_ratio=round(ratios.get("current_ratio") or 0, 2),
            debt_ratio=_pct(ratios.get("debt_to_asset_ratio")),
            net_margin=_pct(ratios.get("net_margin")),
            pe_ratio=round(ratios["pe_ratio"], 2) if ratios.get("pe_ratio") else None,
            pb_ratio=round(ratios["pb_ratio"], 2) if ratios.get("pb_ratio") else None,
            ev_ebitda=round(ratios["ev_ebitda"], 2) if ratios.get("ev_ebitda") else None,
        )

    entries = {}
    for cid in [request.target_company_id] + list(request.peer_company_ids):
        info = await comp_svc.get_company_basic_info(cid)
        stmts = await fin_svc.get_latest_financial_statements(cid)
        ratios = await fin_svc.get_financial_ratios(cid)
        if info is None or stmts is None or not ratios:
            raise HTTPException(status_code=404, detail=f"找不到公司 {cid} 的財務資料")
        entries[cid] = _entry(cid, info, stmts, ratios)

    target = entries[request.target_company_id]
    peers = [entries[c] for c in request.peer_company_ids]

    def _avg(vals):
        return round(sum(vals) / len(vals), 2) if vals else 0.0

    def _med(vals):
        return round(statistics.median(vals), 2) if vals else 0.0

    def _pctile(vals, p):
        if len(vals) < 2:
            return round(vals[0], 2) if vals else 0.0
        return round(statistics.quantiles(sorted(vals), n=100)[p - 1], 2)

    def _std(vals):
        return round(statistics.stdev(vals), 2) if len(vals) > 1 else 0.0

    roe_l = [p.roe for p in peers]
    roa_l = [p.roa for p in peers]
    cr_l = [p.current_ratio for p in peers]
    debt_l = [p.debt_ratio for p in peers]
    nm_l = [p.net_margin for p in peers]
    pe_l = [p.pe_ratio for p in peers if p.pe_ratio is not None]
    pb_l = [p.pb_ratio for p in peers if p.pb_ratio is not None]

    benchmark = IndustryBenchmark(
        industry_code=(
            await comp_svc.get_company_basic_info(request.target_company_id)
        ).get("industry_code", "AUTO"),
        industry_name="自動同業群組",
        company_count=len(peers),
        avg_roe=_avg(roe_l),
        avg_roa=_avg(roa_l),
        avg_current_ratio=_avg(cr_l),
        avg_debt_ratio=_avg(debt_l),
        avg_gross_margin=0.0,
        avg_net_margin=_avg(nm_l),
        avg_pe_ratio=_avg(pe_l),
        avg_pb_ratio=_avg(pb_l),
        median_roe=_med(roe_l),
        median_roa=_med(roa_l),
        median_current_ratio=_med(cr_l),
        median_debt_ratio=_med(debt_l),
        roe_25_percentile=_pctile(roe_l, 25),
        roe_75_percentile=_pctile(roe_l, 75),
        pe_25_percentile=_pctile(pe_l, 25),
        pe_75_percentile=_pctile(pe_l, 75),
        debt_25_percentile=_pctile(debt_l, 25),
        debt_75_percentile=_pctile(debt_l, 75),
        roe_std_dev=_std(roe_l),
        roa_std_dev=_std(roa_l),
    )

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
