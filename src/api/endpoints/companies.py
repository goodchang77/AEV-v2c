"""
公司資料 API 端點
Companies API Endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional

from src.schemas.requests import CompanySearchRequest, CompanyListRequest
from src.schemas.responses import CompanyDetailResponse, CompanyListResponse, CompanySearchResponse
from src.services.company_service import CompanyDataService
from src.core.exceptions import CompanyNotFoundError, ValidationError, create_http_exception
from src.core.logging import get_logger
from src.core.cache import get_cache_manager

router = APIRouter()
logger = get_logger("companies_api")


@router.get("/search", response_model=CompanySearchResponse)
async def search_companies(
    keyword: Optional[str] = Query(None, max_length=50, description="搜尋關鍵字"),
    industry_code: Optional[str] = Query(None, pattern=r"^[A-Z0-9]{2,10}$", description="產業代碼"),
    market_type: Optional[str] = Query(None, description="市場類型"),
    limit: int = Query(20, ge=1, le=100, description="返回筆數限制"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """公司搜尋"""
    try:
        # 初始化服務
        cache_manager = await get_cache_manager()
        service = CompanyDataService(cache_manager)
        
        # 建立搜尋請求
        search_request = CompanySearchRequest(
            keyword=keyword,
            industry_code=industry_code,
            market_type=market_type,
            limit=limit,
            offset=offset
        )
        
        companies = await service.search_companies(search_request)
        
        return CompanySearchResponse(
            data=companies,
            search_meta={
                "keyword": keyword,
                "industry_code": industry_code,
                "market_type": market_type,
                "results_count": len(companies),
                "limit": limit,
                "offset": offset
            }
        )
        
    except (CompanyNotFoundError, ValidationError) as e:
        raise create_http_exception(e)
    except Exception as e:
        logger.error(f"公司搜尋失敗: {e}")
        raise HTTPException(status_code=500, detail="搜尋服務暫時不可用")


@router.get("/", response_model=CompanyListResponse)
async def list_companies(
    industry_code: Optional[str] = Query(None, pattern=r"^[A-Z0-9]{2,10}$"),
    market_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """取得公司列表"""
    try:
        # 初始化服務
        cache_manager = await get_cache_manager()
        service = CompanyDataService(cache_manager)
        
        # 建立列表請求
        list_request = CompanyListRequest(
            industry_code=industry_code,
            market_type=market_type,
            limit=limit,
            offset=offset
        )
        
        companies = await service.get_company_list(list_request)
        
        # 取得總數用於分頁
        filters = {}
        if industry_code:
            filters["industry_code"] = industry_code
        if market_type:
            filters["market_type"] = market_type
        
        total_count = await service.get_company_count(filters)
        
        return CompanyListResponse(
            data=companies,
            meta={
                "page": (offset // limit) + 1,
                "page_size": limit,
                "total": total_count,
                "total_pages": (total_count + limit - 1) // limit,
                "has_next": (offset + limit) < total_count,
                "has_prev": offset > 0
            }
        )
        
    except (ValidationError,) as e:
        raise create_http_exception(e)
    except Exception as e:
        logger.error(f"取得公司列表失敗: {e}")
        raise HTTPException(status_code=500, detail="公司資料服務暫時不可用")


@router.get("/{company_id}", response_model=CompanyDetailResponse)
async def get_company(company_id: str):
    """取得公司詳情"""
    try:
        # 初始化服務
        cache_manager = await get_cache_manager()
        service = CompanyDataService(cache_manager)
        
        company = await service.get_company_by_id(company_id)
        
        if not company:
            raise CompanyNotFoundError(company_id)
        
        return CompanyDetailResponse(data=company)
        
    except (CompanyNotFoundError, ValidationError) as e:
        raise create_http_exception(e)
    except Exception as e:
        logger.error(f"取得公司詳情失敗 {company_id}: {e}")
        raise HTTPException(status_code=500, detail="公司資料服務暫時不可用")