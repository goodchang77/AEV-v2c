"""
財務比率 API 端點（相容路由）
Financial Ratios API Endpoints

真實資料邏輯在 FinancialDataService；本路由作為 /ratios 的相容進入點，
回傳與 /financials/{company_id}/ratios 相同的資料，避免與真端點打架。
"""

from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional
from datetime import datetime

from src.schemas.responses import FinancialRatiosResponse
from src.services.financial_service import FinancialDataService
from src.core.exceptions import CompanyNotFoundError, FinancialDataNotFoundError, create_http_exception
from src.core.logging import get_logger
from src.core.cache import get_cache_manager

router = APIRouter()
logger = get_logger("ratios_api")


@router.get("/")
async def list_ratios():
    """列出支援的財務比率指標"""
    return {
        "endpoint": "/api/v1/ratios/{company_id}",
        "description": "取得公司最新財務比率（資料與 /financials/{company_id}/ratios 相同）",
        "metrics": [
            "debt_to_asset_ratio", "debt_to_equity_ratio", "equity_ratio",
            "current_ratio", "quick_ratio", "cash_ratio", "interest_coverage_ratio",
            "receivables_turnover", "inventory_turnover", "total_asset_turnover",
            "days_sales_outstanding", "roa", "roe", "roic", "gross_margin",
            "operating_margin", "net_margin", "operating_cash_ratio",
            "free_cash_flow_yield", "pe_ratio", "pb_ratio", "ev_ebitda",
        ],
    }


@router.get("/{company_id}", response_model=FinancialRatiosResponse)
async def get_company_ratios(
    company_id: str = Path(..., pattern=r"^\d{4}$", description="4位數公司代碼"),
    year_quarter: Optional[str] = Query(None, pattern=r"^20\d{2}Q[1-4]$", description="年季別"),
):
    """取得公司財務比率（與 /financials/{company_id}/ratios 相同）"""
    try:
        cache_manager = await get_cache_manager()
        service = FinancialDataService(cache_manager)

        ratios = await service.get_financial_ratios(company_id, year_quarter)

        if not ratios:
            raise FinancialDataNotFoundError(company_id, "財務比率", year_quarter)

        return FinancialRatiosResponse(
            data=ratios,
            company_id=company_id,
            year_quarter=year_quarter or "latest",
            calculation_date=datetime.utcnow(),
        )

    except (CompanyNotFoundError, FinancialDataNotFoundError) as e:
        raise create_http_exception(e)
    except Exception as e:
        logger.error(f"取得財務比率失敗 {company_id}: {e}")
        raise HTTPException(status_code=500, detail="財務比率服務暫時不可用")
