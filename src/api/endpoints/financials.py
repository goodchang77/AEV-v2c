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