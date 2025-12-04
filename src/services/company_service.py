"""
公司資料服務層
Company Data Service Layer
"""

from typing import List, Dict, Optional, Any
from decimal import Decimal
from datetime import datetime, date
import asyncio
import logging

from sqlalchemy import text, and_, or_, func, desc, asc
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload

from src.core.database import get_async_session, db_manager
from src.core.exceptions import CompanyNotFoundError, ValidationError, FinancialAnalysisException
from src.core.cache import CacheManager
from src.core.logging import get_logger
from src.schemas.requests import CompanySearchRequest, CompanyListRequest
from src.schemas.responses import CompanyBasicInfo

logger = get_logger("company_service")


class CompanyDataService:
    """公司資料服務"""
    
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        self.cache = cache_manager
        self.logger = logger
    
    async def get_company_by_id(self, company_id: str) -> Optional[CompanyBasicInfo]:
        """
        根據公司代碼取得公司基本資訊
        
        Args:
            company_id: 公司代碼 (4位數字)
            
        Returns:
            CompanyBasicInfo: 公司基本資訊，若不存在則返回 None
            
        Raises:
            ValidationError: 輸入參數驗證錯誤
            FinancialAnalysisException: 資料庫查詢錯誤
        """
        if not company_id or not company_id.isdigit() or len(company_id) != 4:
            raise ValidationError("公司代碼必須為4位數字", field="company_id", value=company_id)
        
        # 檢查快取
        cache_key = f"company:basic:{company_id}"
        if self.cache:
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                self.logger.debug(f"Company {company_id} found in cache")
                return CompanyBasicInfo(**cached_data)
        
        try:
            async with get_async_session() as session:
                query = text("""
                    SELECT 
                        company_id,
                        company_name,
                        company_name_en,
                        industry_code,
                        industry_name,
                        market_type,
                        listing_date,
                        capital_amount,
                        outstanding_shares,
                        website,
                        is_active,
                        created_at,
                        updated_at
                    FROM companies 
                    WHERE company_id = :company_id AND is_active = true
                """)
                
                result = await session.execute(query, {"company_id": company_id})
                row = result.fetchone()
                
                if not row:
                    self.logger.info(f"Company {company_id} not found")
                    return None
                
                company_data = {
                    "company_id": row.company_id,
                    "company_name": row.company_name,
                    "company_name_en": row.company_name_en,
                    "industry_code": row.industry_code,
                    "industry_name": row.industry_name,
                    "market_type": row.market_type,
                    "listing_date": row.listing_date.isoformat() if row.listing_date else None,
                    "capital_amount": str(row.capital_amount) if row.capital_amount else None,
                    "outstanding_shares": row.outstanding_shares,
                    "website": row.website,
                    "is_active": row.is_active
                }
                
                company_info = CompanyBasicInfo(**company_data)
                
                # 儲存到快取
                if self.cache:
                    await self.cache.set(cache_key, company_data, expire=3600)  # 1小時過期
                
                self.logger.debug(f"Company {company_id} retrieved from database")
                return company_info
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving company {company_id}: {e}")
            raise FinancialAnalysisException(
                message=f"資料庫查詢失敗: {str(e)}",
                error_code="DATABASE_ERROR",
                details={"company_id": company_id}
            )
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving company {company_id}: {e}")
            raise FinancialAnalysisException(
                message="系統內部錯誤",
                error_code="INTERNAL_ERROR"
            )
    
    async def search_companies(self, request: CompanySearchRequest) -> List[CompanyBasicInfo]:
        """
        搜尋公司
        
        Args:
            request: 公司搜尋請求參數
            
        Returns:
            List[CompanyBasicInfo]: 符合條件的公司列表
            
        Raises:
            ValidationError: 搜尋參數驗證錯誤
            FinancialAnalysisException: 資料庫查詢錯誤
        """
        try:
            # 建構查詢條件
            conditions = ["is_active = true"]
            params = {"limit": request.limit, "offset": request.offset}
            
            if request.keyword:
                conditions.append(
                    "(company_id ILIKE :keyword OR company_name ILIKE :keyword OR company_name_en ILIKE :keyword)"
                )
                params["keyword"] = f"%{request.keyword}%"
            
            if request.industry_code:
                conditions.append("industry_code = :industry_code")
                params["industry_code"] = request.industry_code
            
            if request.market_type:
                conditions.append("market_type = :market_type")
                params["market_type"] = request.market_type
            
            where_clause = " AND ".join(conditions)
            
            async with get_async_session() as session:
                # 主查詢
                query = text(f"""
                    SELECT 
                        company_id,
                        company_name,
                        company_name_en,
                        industry_code,
                        industry_name,
                        market_type,
                        listing_date,
                        capital_amount,
                        outstanding_shares,
                        website,
                        is_active
                    FROM companies 
                    WHERE {where_clause}
                    ORDER BY 
                        CASE 
                            WHEN market_type = '上市' THEN 1
                            WHEN market_type = '上櫃' THEN 2  
                            WHEN market_type = '興櫃' THEN 3
                            ELSE 4 
                        END,
                        company_id ASC
                    LIMIT :limit OFFSET :offset
                """)
                
                result = await session.execute(query, params)
                rows = result.fetchall()
                
                companies = []
                for row in rows:
                    company_data = {
                        "company_id": row.company_id,
                        "company_name": row.company_name,
                        "company_name_en": row.company_name_en,
                        "industry_code": row.industry_code,
                        "industry_name": row.industry_name,
                        "market_type": row.market_type,
                        "listing_date": row.listing_date.isoformat() if row.listing_date else None,
                        "capital_amount": str(row.capital_amount) if row.capital_amount else None,
                        "outstanding_shares": row.outstanding_shares,
                        "website": row.website,
                        "is_active": row.is_active
                    }
                    companies.append(CompanyBasicInfo(**company_data))
                
                self.logger.info(f"Found {len(companies)} companies matching search criteria")
                return companies
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error in company search: {e}")
            raise FinancialAnalysisException(
                message="公司搜尋查詢失敗",
                error_code="SEARCH_ERROR",
                details={"search_params": request.dict()}
            )
        except Exception as e:
            self.logger.error(f"Unexpected error in company search: {e}")
            raise FinancialAnalysisException(
                message="搜尋服務內部錯誤",
                error_code="SEARCH_INTERNAL_ERROR"
            )
    
    async def get_company_list(self, request: CompanyListRequest) -> List[CompanyBasicInfo]:
        """
        取得公司列表 (分頁)
        
        Args:
            request: 公司列表請求參數
            
        Returns:
            List[CompanyBasicInfo]: 公司列表
            
        Raises:
            FinancialAnalysisException: 資料庫查詢錯誤
        """
        try:
            conditions = ["is_active = true"]
            params = {"limit": request.limit, "offset": request.offset}
            
            if request.industry_code:
                conditions.append("industry_code = :industry_code")
                params["industry_code"] = request.industry_code
            
            if request.market_type:
                conditions.append("market_type = :market_type")  
                params["market_type"] = request.market_type
            
            where_clause = " AND ".join(conditions)
            
            async with get_async_session() as session:
                query = text(f"""
                    SELECT 
                        company_id,
                        company_name,
                        company_name_en,
                        industry_code,
                        industry_name,
                        market_type,
                        capital_amount,
                        outstanding_shares,
                        is_active
                    FROM companies 
                    WHERE {where_clause}
                    ORDER BY capital_amount DESC NULLS LAST, company_id ASC
                    LIMIT :limit OFFSET :offset
                """)
                
                result = await session.execute(query, params)
                rows = result.fetchall()
                
                companies = []
                for row in rows:
                    company_data = {
                        "company_id": row.company_id,
                        "company_name": row.company_name,
                        "company_name_en": row.company_name_en,
                        "industry_code": row.industry_code,
                        "industry_name": row.industry_name,
                        "market_type": row.market_type,
                        "capital_amount": str(row.capital_amount) if row.capital_amount else None,
                        "outstanding_shares": row.outstanding_shares,
                        "is_active": row.is_active
                    }
                    companies.append(CompanyBasicInfo(**company_data))
                
                return companies
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error in company list: {e}")
            raise FinancialAnalysisException(
                message="公司列表查詢失敗", 
                error_code="LIST_ERROR"
            )
        except Exception as e:
            self.logger.error(f"Unexpected error in company list: {e}")
            raise FinancialAnalysisException(
                message="列表服務內部錯誤",
                error_code="LIST_INTERNAL_ERROR" 
            )
    
    async def get_companies_by_industry(self, industry_code: str, limit: int = 50) -> List[CompanyBasicInfo]:
        """
        根據產業代碼取得公司列表
        
        Args:
            industry_code: 產業代碼
            limit: 限制返回數量
            
        Returns:
            List[CompanyBasicInfo]: 該產業的公司列表
            
        Raises:
            ValidationError: 產業代碼驗證錯誤  
            FinancialAnalysisException: 資料庫查詢錯誤
        """
        if not industry_code or len(industry_code) < 2:
            raise ValidationError("產業代碼格式錯誤", field="industry_code", value=industry_code)
        
        # 檢查快取
        cache_key = f"companies:industry:{industry_code}:{limit}"
        if self.cache:
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                return [CompanyBasicInfo(**item) for item in cached_data]
        
        try:
            async with get_async_session() as session:
                query = text("""
                    SELECT 
                        company_id,
                        company_name,
                        company_name_en, 
                        industry_code,
                        industry_name,
                        market_type,
                        capital_amount,
                        outstanding_shares,
                        is_active
                    FROM companies 
                    WHERE industry_code = :industry_code AND is_active = true
                    ORDER BY capital_amount DESC NULLS LAST, company_id ASC
                    LIMIT :limit
                """)
                
                result = await session.execute(query, {
                    "industry_code": industry_code,
                    "limit": limit
                })
                rows = result.fetchall()
                
                companies = []
                company_data_list = []
                
                for row in rows:
                    company_data = {
                        "company_id": row.company_id,
                        "company_name": row.company_name,
                        "company_name_en": row.company_name_en,
                        "industry_code": row.industry_code,
                        "industry_name": row.industry_name,
                        "market_type": row.market_type,
                        "capital_amount": str(row.capital_amount) if row.capital_amount else None,
                        "outstanding_shares": row.outstanding_shares,
                        "is_active": row.is_active
                    }
                    companies.append(CompanyBasicInfo(**company_data))
                    company_data_list.append(company_data)
                
                # 儲存到快取
                if self.cache:
                    await self.cache.set(cache_key, company_data_list, expire=1800)  # 30分鐘過期
                
                self.logger.info(f"Retrieved {len(companies)} companies for industry {industry_code}")
                return companies
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving companies for industry {industry_code}: {e}")
            raise FinancialAnalysisException(
                message="產業公司查詢失敗",
                error_code="INDUSTRY_QUERY_ERROR",
                details={"industry_code": industry_code}
            )
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving companies for industry {industry_code}: {e}")
            raise FinancialAnalysisException(
                message="產業查詢服務內部錯誤", 
                error_code="INDUSTRY_INTERNAL_ERROR"
            )
    
    async def get_company_count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        取得符合條件的公司總數
        
        Args:
            filters: 篩選條件
            
        Returns:
            int: 公司總數
            
        Raises:
            FinancialAnalysisException: 資料庫查詢錯誤
        """
        try:
            conditions = ["is_active = true"]
            params = {}
            
            if filters:
                if filters.get("industry_code"):
                    conditions.append("industry_code = :industry_code")
                    params["industry_code"] = filters["industry_code"]
                
                if filters.get("market_type"):
                    conditions.append("market_type = :market_type")
                    params["market_type"] = filters["market_type"]
                
                if filters.get("keyword"):
                    conditions.append(
                        "(company_id ILIKE :keyword OR company_name ILIKE :keyword)"
                    )
                    params["keyword"] = f"%{filters['keyword']}%"
            
            where_clause = " AND ".join(conditions)
            
            async with get_async_session() as session:
                query = text(f"SELECT COUNT(*) FROM companies WHERE {where_clause}")
                result = await session.execute(query, params)
                count = result.scalar()
                
                return count
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting company count: {e}")
            raise FinancialAnalysisException(
                message="公司計數查詢失敗",
                error_code="COUNT_ERROR"
            )
        except Exception as e:
            self.logger.error(f"Unexpected error getting company count: {e}")
            raise FinancialAnalysisException(
                message="計數服務內部錯誤",
                error_code="COUNT_INTERNAL_ERROR"
            )
    
    async def validate_company_exists(self, company_id: str) -> bool:
        """
        驗證公司是否存在且活躍
        
        Args:
            company_id: 公司代碼
            
        Returns:
            bool: 公司是否存在且活躍
        """
        try:
            company = await self.get_company_by_id(company_id)
            return company is not None and company.is_active
        except CompanyNotFoundError:
            return False
        except Exception:
            return False
    
    async def get_market_summary(self) -> Dict[str, Any]:
        """
        取得市場摘要統計
        
        Returns:
            Dict[str, Any]: 市場統計資訊
            
        Raises:
            FinancialAnalysisException: 資料庫查詢錯誤
        """
        cache_key = "market:summary"
        if self.cache:
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                return cached_data
        
        try:
            async with get_async_session() as session:
                # 市場分類統計
                market_query = text("""
                    SELECT 
                        market_type,
                        COUNT(*) as company_count,
                        SUM(capital_amount) as total_capital
                    FROM companies 
                    WHERE is_active = true
                    GROUP BY market_type
                    ORDER BY company_count DESC
                """)
                
                # 產業統計
                industry_query = text("""
                    SELECT 
                        industry_code,
                        industry_name,
                        COUNT(*) as company_count
                    FROM companies 
                    WHERE is_active = true
                    GROUP BY industry_code, industry_name
                    ORDER BY company_count DESC
                    LIMIT 10
                """)
                
                market_result = await session.execute(market_query)
                industry_result = await session.execute(industry_query)
                
                market_stats = []
                for row in market_result:
                    market_stats.append({
                        "market_type": row.market_type,
                        "company_count": row.company_count,
                        "total_capital": float(row.total_capital) if row.total_capital else 0
                    })
                
                industry_stats = []
                for row in industry_result:
                    industry_stats.append({
                        "industry_code": row.industry_code,
                        "industry_name": row.industry_name,
                        "company_count": row.company_count
                    })
                
                summary = {
                    "market_statistics": market_stats,
                    "top_industries": industry_stats,
                    "last_updated": datetime.now().isoformat()
                }
                
                # 儲存到快取
                if self.cache:
                    await self.cache.set(cache_key, summary, expire=7200)  # 2小時過期
                
                return summary
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting market summary: {e}")
            raise FinancialAnalysisException(
                message="市場摘要查詢失敗",
                error_code="MARKET_SUMMARY_ERROR"
            )
        except Exception as e:
            self.logger.error(f"Unexpected error getting market summary: {e}")
            raise FinancialAnalysisException(
                message="市場摘要服務內部錯誤",
                error_code="MARKET_SUMMARY_INTERNAL_ERROR"
            )


# 預設的公司資料服務實例
company_service = CompanyDataService()