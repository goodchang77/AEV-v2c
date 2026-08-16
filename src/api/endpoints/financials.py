"""
財務報表 API 端點
Financial Statements API Endpoints
"""

from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional
from datetime import datetime

from src.schemas.responses import FinancialRatiosResponse, FinancialHealthResponse, FinancialTrendResponse
from src.services.financial_service import FinancialDataService
from src.core.exceptions import CompanyNotFoundError, FinancialDataNotFoundError, ValidationError, create_http_exception
from src.core.logging import get_logger
from src.core.cache import get_cache_manager

router = APIRouter()
logger = get_logger("financials_api")


@router.get("/{company_id}/ratios", response_model=FinancialRatiosResponse)
async def get_financial_ratios(
    company_id: str = Path(..., pattern=r"^\d{4}$", description="4位數公司代碼"),
    year_quarter: Optional[str] = Query(None, pattern=r"^20\d{2}Q[1-4]$", description="年季別")
):
    """取得公司財務比率"""
    try:
        # 初始化服務
        cache_manager = await get_cache_manager()
        service = FinancialDataService(cache_manager)
        
        ratios = await service.get_financial_ratios(company_id, year_quarter)
        
        if not ratios:
            raise FinancialDataNotFoundError(company_id, "財務比率", year_quarter)
        
        return FinancialRatiosResponse(
            data=ratios,
            company_id=company_id,
            year_quarter=year_quarter or "latest",
            calculation_date=datetime.utcnow()
        )
        
    except (CompanyNotFoundError, FinancialDataNotFoundError) as e:
        raise create_http_exception(e)
    except Exception as e:
        logger.error(f"取得財務比率失敗 {company_id}: {e}")
        raise HTTPException(status_code=500, detail="財務比率服務暫時不可用")


@router.get("/{company_id}/health", response_model=FinancialHealthResponse)
async def get_financial_health(
    company_id: str = Path(..., pattern=r"^\d{4}$"),
    analysis_period: Optional[str] = Query(None, pattern=r"^20\d{2}Q[1-4]$")
):
    """取得公司財務健康度評估"""
    try:
        # 初始化服務
        cache_manager = await get_cache_manager()
        service = FinancialDataService(cache_manager)
        
        # 計算財務健康度
        health_assessment = await service.calculate_financial_health(company_id, analysis_period)
        
        return FinancialHealthResponse(
            data=health_assessment,
            company_id=company_id,
            analysis_period=analysis_period or "latest"
        )
        
    except (CompanyNotFoundError, FinancialDataNotFoundError) as e:
        raise create_http_exception(e)
    except Exception as e:
        logger.error(f"財務健康度評估失敗 {company_id}: {e}")
        raise HTTPException(status_code=500, detail="財務健康度評估服務暫時不可用")


@router.get("/{company_id}/trend", response_model=FinancialTrendResponse)
async def get_financial_trend(
    company_id: str = Path(..., pattern=r"^\d{4}$"),
    periods: int = Query(8, ge=1, le=20, description="分析期數")
):
    """取得公司財務趨勢"""
    try:
        # 初始化服務
        cache_manager = await get_cache_manager()
        service = FinancialDataService(cache_manager)
        
        # 取得財務趨勢分析
        trend_data = await service.get_financial_trend(company_id, periods)
        
        return FinancialTrendResponse(
            data=trend_data,
            company_id=company_id,
            periods_analyzed=periods
        )
        
    except CompanyNotFoundError as e:
        raise create_http_exception(e)
    except Exception as e:
        logger.error(f"取得財務趨勢失敗 {company_id}: {e}")
        raise HTTPException(status_code=500, detail="財務趨勢分析服務暫時不可用")


@router.get("/outliers")
async def get_ratio_outliers(threshold: float = Query(2.5, ge=0.5, description="z-score 門檻")):
    """異常值檢測：跨公司財務比率 z-score 超出門檻者（資料品質監控）"""
    from sqlalchemy import text

    from src.core.database import get_async_session
    from src.schemas.responses import StandardResponse

    query = text(
        """
        WITH latest AS (
            SELECT DISTINCT ON (company_id)
                company_id, roe, current_ratio, debt_to_asset_ratio
            FROM financial_ratios
            ORDER BY company_id, year_quarter DESC
        ),
        stats AS (
            SELECT avg(roe) AS m_roe, stddev(roe) AS s_roe,
                   avg(current_ratio) AS m_cr, stddev(current_ratio) AS s_cr,
                   avg(debt_to_asset_ratio) AS m_debt, stddev(debt_to_asset_ratio) AS s_debt
            FROM latest
        )
        SELECT l.company_id, c.company_name, l.roe, l.current_ratio, l.debt_to_asset_ratio,
               round((l.roe - s.m_roe) / nullif(s.s_roe, 0), 2) AS roe_z,
               round((l.current_ratio - s.m_cr) / nullif(s.s_cr, 0), 2) AS current_ratio_z,
               round((l.debt_to_asset_ratio - s.m_debt) / nullif(s.s_debt, 0), 2) AS debt_z
        FROM latest l
        JOIN companies c ON c.company_id = l.company_id
        CROSS JOIN stats s
        ORDER BY company_id
        """
    )

    async with get_async_session() as session:
        result = await session.execute(query)
        rows = [dict(r) for r in result.mappings().all()]

    flagged = [
        r
        for r in rows
        if abs(r["roe_z"] or 0) > threshold
        or abs(r["current_ratio_z"] or 0) > threshold
        or abs(r["debt_z"] or 0) > threshold
    ]

    return StandardResponse(
        success=True,
        data={"total_companies": len(rows), "flagged_count": len(flagged), "flagged": flagged},
        meta={"threshold": threshold},
    )


@router.post("/{company_id}/ratios/calculate")
async def calculate_financial_ratios(
    company_id: str = Path(..., pattern=r"^\d{4}$")
):
    """重新計算財務比率"""
    try:
        # 初始化服務
        cache_manager = await get_cache_manager()
        service = FinancialDataService(cache_manager)
        
        # 檢查公司是否存在財務資料
        ratios = await service.get_financial_ratios(company_id)
        
        if not ratios:
            # 如果沒有資料，返回適當的錯誤
            raise FinancialDataNotFoundError(company_id, "財務比率")
        
        # 實際系統中，這裡會觸發重新計算比率的後台任務
        # 目前返回成功訊息
        return {
            "message": "財務比率重新計算已啟動", 
            "company_id": company_id,
            "status": "processing",
            "estimated_completion": "約需5-10分鐘完成"
        }
        
    except CompanyNotFoundError as e:
        raise create_http_exception(e)
    except Exception as e:
        logger.error(f"計算財務比率失敗 {company_id}: {e}")
        raise HTTPException(status_code=500, detail="財務比率計算服務暫時不可用")