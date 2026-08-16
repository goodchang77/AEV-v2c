"""
評價模型 API 端點
Valuation API Endpoints
=======================

- POST /valuation/ddm          股利折現模型（DDM）
- POST /valuation/relative     PE/PB 相對評價
- POST /valuation/peg          PEG 成長性評價
- POST /valuation/monte-carlo  蒙地卡羅 DCF 風險模擬
"""

from dataclasses import asdict
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.schemas.responses import StandardResponse
from src.services.monte_carlo import MonteCarloDCF
from src.services.valuation_models import (
    DDMParameters,
    DDMValuationModel,
    RelativeValuationModel,
    RelativeValuationParameters,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# 請求模型
# ---------------------------------------------------------------------------
class DDMRequest(BaseModel):
    company_id: str = Field(..., pattern=r"^\d{4}$")
    current_dividend: float = Field(..., gt=0, description="當前每股股利")
    dividend_growth_rate: float = Field(0.05, ge=0, le=0.2)
    discount_rate: float = Field(0.10, ge=0.01, le=0.3)
    stable_growth_rate: float = Field(0.03, ge=0, le=0.1)
    shares_outstanding: Optional[int] = Field(None, gt=0)


class RelativeValuationRequest(BaseModel):
    company_id: str = Field(..., pattern=r"^\d{4}$")
    target_eps: Optional[float] = Field(None, gt=0, description="目標公司每股盈餘")
    target_bvps: Optional[float] = Field(None, gt=0, description="目標公司每股淨值")
    peer_pe_ratios: Optional[List[float]] = Field(None, description="同業本益比列表")
    peer_pb_ratios: Optional[List[float]] = Field(None, description="同業股價淨值比列表")
    shares_outstanding: Optional[int] = Field(None, gt=0)


class PEGRequest(BaseModel):
    company_id: str = Field(..., pattern=r"^\d{4}$")
    pe_ratio: float = Field(..., gt=0)
    eps_growth_rate: float = Field(..., gt=0, description="EPS 成長率（百分比，如 15 代表 15%）")


class MonteCarloRequest(BaseModel):
    company_id: str = Field(..., pattern=r"^\d{4}$")
    base_revenue: Optional[float] = Field(None, gt=0, description="基期營收（元）；省略則由 DB 取得")
    discount_rate_mean: float = Field(0.10, ge=0.03, le=0.3)
    discount_rate_std: float = Field(0.01, ge=0)
    growth_rate_mean: float = Field(0.05)
    growth_rate_std: float = Field(0.02, ge=0)
    shares_outstanding: Optional[int] = Field(None, gt=0, description="流通股數；省略則由 DB 取得")
    simulations: int = Field(1000, ge=100, le=20000)
    current_price: Optional[float] = Field(None, gt=0)
    seed: Optional[int] = Field(42, description="固定種子可重現結果")


# ---------------------------------------------------------------------------
# 端點
# ---------------------------------------------------------------------------
@router.post("/ddm", response_model=StandardResponse)
def ddm_valuation(request: DDMRequest):
    """股利折現模型評價"""
    params = DDMParameters(
        dividend_growth_rate=request.dividend_growth_rate,
        discount_rate=request.discount_rate,
        stable_growth_rate=request.stable_growth_rate,
    )
    model = DDMValuationModel(params)
    try:
        result = model.calculate_fair_value(
            request.current_dividend, request.shares_outstanding or 1_000_000
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return StandardResponse(
        success=True,
        data=asdict(result),
        meta={
            "company_id": request.company_id,
            "model_type": "DDM",
            "calculation_date": datetime.utcnow().isoformat(),
        },
    )


@router.post("/relative", response_model=StandardResponse)
def relative_valuation(request: RelativeValuationRequest):
    """PE/PB 相對評價"""
    params = RelativeValuationParameters()
    model = RelativeValuationModel(params)
    results = {}

    if request.target_eps is not None and request.peer_pe_ratios:
        pe = model.calculate_pe_valuation(
            request.target_eps, request.peer_pe_ratios, request.shares_outstanding or 1_000_000
        )
        results["pe"] = asdict(pe)

    if request.target_bvps is not None and request.peer_pb_ratios:
        pb = model.calculate_pb_valuation(
            request.target_bvps, request.peer_pb_ratios, request.shares_outstanding or 1_000_000
        )
        results["pb"] = asdict(pb)

    if not results:
        raise HTTPException(
            status_code=422,
            detail="請提供 target_eps+peer_pe_ratios 或 target_bvps+peer_pb_ratios",
        )

    return StandardResponse(
        success=True,
        data=results,
        meta={
            "company_id": request.company_id,
            "model_type": "relative",
            "calculation_date": datetime.utcnow().isoformat(),
        },
    )


@router.post("/peg", response_model=StandardResponse)
def peg_valuation(request: PEGRequest):
    """PEG 成長性評價（PEG = 本益比 / EPS 成長率）"""
    peg = request.pe_ratio / request.eps_growth_rate
    if peg < 1:
        rating = "低估"
    elif peg < 2:
        rating = "合理"
    else:
        rating = "高估"

    return StandardResponse(
        success=True,
        data={
            "peg": round(peg, 2),
            "rating": rating,
            "pe_ratio": request.pe_ratio,
            "eps_growth_rate": request.eps_growth_rate,
        },
        meta={"company_id": request.company_id, "model_type": "PEG"},
    )


@router.post("/monte-carlo", response_model=StandardResponse)
async def monte_carlo_valuation(request: MonteCarloRequest):
    """蒙地卡羅 DCF 風險模擬"""
    base_revenue = request.base_revenue
    shares_outstanding = request.shares_outstanding
    if base_revenue is None or shares_outstanding is None:
        from src.services.data_service import CompanyDataService, FinancialDataService

        if base_revenue is None:
            statements = await FinancialDataService().get_latest_financial_statements(
                request.company_id
            )
            if statements is None or not statements.revenue:
                raise HTTPException(status_code=404, detail=f"找不到公司 {request.company_id} 的財務資料")
            base_revenue = float(statements.revenue) * 1000  # 千元 → 元
        if shares_outstanding is None:
            info = await CompanyDataService().get_company_basic_info(request.company_id)
            shares_outstanding = (info or {}).get("outstanding_shares") or 1_000_000

    mc = MonteCarloDCF(
        base_revenue=base_revenue,
        discount_rate_mean=request.discount_rate_mean,
        discount_rate_std=request.discount_rate_std,
        growth_rate_mean=request.growth_rate_mean,
        growth_rate_std=request.growth_rate_std,
        shares_outstanding=int(shares_outstanding),
        current_price=request.current_price,
        seed=request.seed,
    )
    stats = mc.simulate(request.simulations)

    return StandardResponse(
        success=True,
        data=stats,
        meta={
            "company_id": request.company_id,
            "model_type": "MonteCarlo-DCF",
            "calculation_date": datetime.utcnow().isoformat(),
        },
    )
