"""
資料服務層
Data Service Layer

提供統一的資料存取介面，連接資料庫與業務邏輯層
"""

from typing import Dict, List, Optional, Tuple, Union, Any
from decimal import Decimal
import asyncio
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload

from src.core.database import get_async_session
from src.core.logging import get_logger
from src.services.financial_calculator import FinancialStatements, FinancialCalculator
from src.services.peer_analysis import PeerCompanyData, IndustryBenchmark

logger = get_logger("data_service")


class CompanyDataService:
    """公司資料服務"""
    
    def __init__(self):
        self.calculator = FinancialCalculator()
    
    async def get_company_basic_info(self, company_id: str) -> Optional[Dict[str, Any]]:
        """
        取得公司基本資訊
        
        Args:
            company_id: 公司代碼
            
        Returns:
            Optional[Dict]: 公司基本資訊
        """
        try:
            async with get_async_session() as session:
                from src.models import Company
                
                stmt = select(Company).where(Company.company_id == company_id)
                result = await session.execute(stmt)
                company = result.scalar_one_or_none()
                
                if not company:
                    return None
                
                return {
                    'company_id': company.company_id,
                    'company_name': company.company_name,
                    'company_name_en': company.company_name_en,
                    'industry_code': company.industry_code,
                    'industry_name': company.industry_name,
                    'market_type': company.market_type,
                    'listing_date': company.listing_date.isoformat() if company.listing_date else None,
                    'capital_amount': float(company.capital_amount) if company.capital_amount else None,
                    'outstanding_shares': company.outstanding_shares,
                    'par_value': float(company.par_value) if company.par_value else None,
                    'address': company.address,
                    'website': company.website,
                    'chairman': company.chairman,
                    'ceo': company.ceo,
                    'is_active': company.is_active
                }
                
        except Exception as e:
            logger.error(f"取得公司基本資訊失敗: {company_id}, {e}")
            return None
    
    async def get_companies_by_industry(self, industry_code: str, 
                                       limit: int = 50) -> List[Dict[str, Any]]:
        """
        按產業取得公司列表
        
        Args:
            industry_code: 產業代碼
            limit: 限制筆數
            
        Returns:
            List[Dict]: 公司列表
        """
        try:
            async with get_async_session() as session:
                from src.models import Company
                
                stmt = (select(Company)
                       .where(Company.industry_code == industry_code)
                       .where(Company.is_active == True)
                       .limit(limit))
                
                result = await session.execute(stmt)
                companies = result.scalars().all()
                
                return [
                    {
                        'company_id': company.company_id,
                        'company_name': company.company_name,
                        'market_type': company.market_type,
                        'capital_amount': float(company.capital_amount) if company.capital_amount else None
                    }
                    for company in companies
                ]
                
        except Exception as e:
            logger.error(f"按產業取得公司列表失敗: {industry_code}, {e}")
            return []
    
    async def search_companies(self, keyword: str, 
                             market_type: Optional[str] = None,
                             limit: int = 20) -> List[Dict[str, Any]]:
        """
        搜尋公司
        
        Args:
            keyword: 搜尋關鍵字
            market_type: 市場類型篩選
            limit: 限制筆數
            
        Returns:
            List[Dict]: 搜尋結果
        """
        try:
            async with get_async_session() as session:
                from src.models import Company
                
                stmt = select(Company).where(Company.is_active == True)
                
                # 關鍵字搜尋
                if keyword:
                    stmt = stmt.where(
                        or_(
                            Company.company_id.contains(keyword),
                            Company.company_name.contains(keyword),
                            Company.company_name_en.contains(keyword)
                        )
                    )
                
                # 市場類型篩選
                if market_type:
                    stmt = stmt.where(Company.market_type == market_type)
                
                stmt = stmt.limit(limit)
                
                result = await session.execute(stmt)
                companies = result.scalars().all()
                
                return [
                    {
                        'company_id': company.company_id,
                        'company_name': company.company_name,
                        'industry_code': company.industry_code,
                        'market_type': company.market_type
                    }
                    for company in companies
                ]
                
        except Exception as e:
            logger.error(f"搜尋公司失敗: {keyword}, {e}")
            return []


class FinancialDataService:
    """財務資料服務"""
    
    def __init__(self):
        self.calculator = FinancialCalculator()
    
    async def get_latest_financial_statements(self, company_id: str) -> Optional[FinancialStatements]:
        """
        取得最新財務報表
        
        Args:
            company_id: 公司代碼
            
        Returns:
            Optional[FinancialStatements]: 財務報表資料
        """
        try:
            async with get_async_session() as session:
                from src.models import FinancialStatement
                
                stmt = (select(FinancialStatement)
                       .where(FinancialStatement.company_id == company_id)
                       .order_by(desc(FinancialStatement.year_quarter))
                       .limit(1))
                
                result = await session.execute(stmt)
                statement = result.scalar_one_or_none()
                
                if not statement:
                    return None
                
                return FinancialStatements(
                    current_assets=statement.current_assets or Decimal('0'),
                    non_current_assets=statement.non_current_assets or Decimal('0'),
                    total_assets=statement.total_assets or Decimal('0'),
                    current_liabilities=statement.current_liabilities or Decimal('0'),
                    non_current_liabilities=statement.non_current_liabilities or Decimal('0'),
                    total_liabilities=statement.total_liabilities or Decimal('0'),
                    shareholders_equity=statement.shareholders_equity or Decimal('0'),
                    cash_and_equivalents=statement.cash_and_equivalents or Decimal('0'),
                    accounts_receivable=statement.accounts_receivable or Decimal('0'),
                    inventory=statement.inventory or Decimal('0'),
                    accounts_payable=statement.accounts_payable or Decimal('0'),
                    short_term_debt=statement.short_term_debt or Decimal('0'),
                    long_term_debt=statement.long_term_debt or Decimal('0'),
                    revenue=statement.revenue or Decimal('0'),
                    cost_of_revenue=statement.cost_of_revenue or Decimal('0'),
                    gross_profit=statement.gross_profit or Decimal('0'),
                    operating_expenses=statement.operating_expenses or Decimal('0'),
                    operating_income=statement.operating_income or Decimal('0'),
                    ebitda=statement.ebitda or Decimal('0'),
                    interest_expense=statement.interest_expense or Decimal('0'),
                    pretax_income=statement.pretax_income or Decimal('0'),
                    tax_expense=statement.tax_expense or Decimal('0'),
                    net_income=statement.net_income or Decimal('0'),
                    eps=statement.eps or Decimal('0'),
                    operating_cash_flow=statement.operating_cash_flow or Decimal('0'),
                    investing_cash_flow=statement.investing_cash_flow or Decimal('0'),
                    financing_cash_flow=statement.financing_cash_flow or Decimal('0'),
                    free_cash_flow=statement.free_cash_flow or Decimal('0'),
                    capex=statement.capex or Decimal('0')
                )
                
        except Exception as e:
            logger.error(f"取得財務報表失敗: {company_id}, {e}")
            return None
    
    async def get_financial_ratios(self, company_id: str, 
                                 year_quarter: Optional[str] = None) -> Optional[Dict[str, float]]:
        """
        取得財務比率
        
        Args:
            company_id: 公司代碼
            year_quarter: 期別（可選，預設為最新）
            
        Returns:
            Optional[Dict]: 財務比率
        """
        try:
            async with get_async_session() as session:
                from src.models import FinancialRatio
                
                stmt = select(FinancialRatio).where(FinancialRatio.company_id == company_id)
                
                if year_quarter:
                    stmt = stmt.where(FinancialRatio.year_quarter == year_quarter)
                else:
                    stmt = stmt.order_by(desc(FinancialRatio.year_quarter))
                
                stmt = stmt.limit(1)
                
                result = await session.execute(stmt)
                ratio = result.scalar_one_or_none()
                
                if not ratio:
                    return None
                
                return {
                    'debt_to_asset_ratio': float(ratio.debt_to_asset_ratio) if ratio.debt_to_asset_ratio else None,
                    'debt_to_equity_ratio': float(ratio.debt_to_equity_ratio) if ratio.debt_to_equity_ratio else None,
                    'equity_ratio': float(ratio.equity_ratio) if ratio.equity_ratio else None,
                    'current_ratio': float(ratio.current_ratio) if ratio.current_ratio else None,
                    'quick_ratio': float(ratio.quick_ratio) if ratio.quick_ratio else None,
                    'cash_ratio': float(ratio.cash_ratio) if ratio.cash_ratio else None,
                    'interest_coverage_ratio': float(ratio.interest_coverage_ratio) if ratio.interest_coverage_ratio else None,
                    'receivables_turnover': float(ratio.receivables_turnover) if ratio.receivables_turnover else None,
                    'inventory_turnover': float(ratio.inventory_turnover) if ratio.inventory_turnover else None,
                    'total_asset_turnover': float(ratio.total_asset_turnover) if ratio.total_asset_turnover else None,
                    'roa': float(ratio.roa) if ratio.roa else None,
                    'roe': float(ratio.roe) if ratio.roe else None,
                    'roic': float(ratio.roic) if ratio.roic else None,
                    'gross_margin': float(ratio.gross_margin) if ratio.gross_margin else None,
                    'operating_margin': float(ratio.operating_margin) if ratio.operating_margin else None,
                    'net_margin': float(ratio.net_margin) if ratio.net_margin else None,
                    'ebitda_margin': float(ratio.ebitda_margin) if ratio.ebitda_margin else None,
                    'pe_ratio': float(ratio.pe_ratio) if ratio.pe_ratio else None,
                    'pb_ratio': float(ratio.pb_ratio) if ratio.pb_ratio else None,
                    'ev_ebitda': float(ratio.ev_ebitda) if ratio.ev_ebitda else None
                }
                
        except Exception as e:
            logger.error(f"取得財務比率失敗: {company_id}, {e}")
            return None
    
    async def calculate_and_store_ratios(self, company_id: str) -> bool:
        """
        計算並儲存財務比率
        
        Args:
            company_id: 公司代碼
            
        Returns:
            bool: 是否成功
        """
        try:
            # 取得財務報表資料
            current_statements = await self.get_latest_financial_statements(company_id)
            if not current_statements:
                logger.warning(f"找不到公司財務報表: {company_id}")
                return False
            
            # 計算財務比率
            ratios = self.calculator.calculate_all_ratios(current_statements)
            
            # 儲存到資料庫
            async with get_async_session() as session:
                from src.models import FinancialRatio
                
                # 檢查是否已存在
                stmt = select(FinancialRatio).where(
                    and_(
                        FinancialRatio.company_id == company_id,
                        FinancialRatio.year_quarter == "2024Q3"  # 示例期別
                    )
                )
                
                result = await session.execute(stmt)
                existing_ratio = result.scalar_one_or_none()
                
                if existing_ratio:
                    # 更新現有記錄
                    existing_ratio.debt_to_asset_ratio = ratios.debt_to_asset_ratio
                    existing_ratio.debt_to_equity_ratio = ratios.debt_to_equity_ratio
                    existing_ratio.equity_ratio = ratios.equity_ratio
                    existing_ratio.current_ratio = ratios.current_ratio
                    existing_ratio.quick_ratio = ratios.quick_ratio
                    existing_ratio.cash_ratio = ratios.cash_ratio
                    existing_ratio.interest_coverage_ratio = ratios.interest_coverage_ratio
                    existing_ratio.receivables_turnover = ratios.receivables_turnover
                    existing_ratio.inventory_turnover = ratios.inventory_turnover
                    existing_ratio.total_asset_turnover = ratios.total_asset_turnover
                    existing_ratio.roa = ratios.roa
                    existing_ratio.roe = ratios.roe
                    existing_ratio.roic = ratios.roic
                    existing_ratio.gross_margin = ratios.gross_margin
                    existing_ratio.operating_margin = ratios.operating_margin
                    existing_ratio.net_margin = ratios.net_margin
                    existing_ratio.ebitda_margin = ratios.ebitda_margin
                else:
                    # 建立新記錄
                    new_ratio = FinancialRatio(
                        company_id=company_id,
                        year_quarter="2024Q3",  # 示例期別
                        debt_to_asset_ratio=ratios.debt_to_asset_ratio,
                        debt_to_equity_ratio=ratios.debt_to_equity_ratio,
                        equity_ratio=ratios.equity_ratio,
                        current_ratio=ratios.current_ratio,
                        quick_ratio=ratios.quick_ratio,
                        cash_ratio=ratios.cash_ratio,
                        interest_coverage_ratio=ratios.interest_coverage_ratio,
                        receivables_turnover=ratios.receivables_turnover,
                        inventory_turnover=ratios.inventory_turnover,
                        total_asset_turnover=ratios.total_asset_turnover,
                        roa=ratios.roa,
                        roe=ratios.roe,
                        roic=ratios.roic,
                        gross_margin=ratios.gross_margin,
                        operating_margin=ratios.operating_margin,
                        net_margin=ratios.net_margin,
                        ebitda_margin=ratios.ebitda_margin
                    )
                    session.add(new_ratio)
                
                await session.commit()
                
                logger.calculation_log(
                    company_id=company_id,
                    calculation_type="financial_ratios",
                    duration=0,
                    success=True
                )
                
                return True
                
        except Exception as e:
            logger.error(f"計算並儲存財務比率失敗: {company_id}, {e}")
            return False
    
    async def get_financial_trend(self, company_id: str, 
                                periods: int = 8) -> Dict[str, List[Dict]]:
        """
        取得財務趨勢資料
        
        Args:
            company_id: 公司代碼
            periods: 期數
            
        Returns:
            Dict: 趨勢資料
        """
        try:
            async with get_async_session() as session:
                from src.models import FinancialRatio
                
                stmt = (select(FinancialRatio)
                       .where(FinancialRatio.company_id == company_id)
                       .order_by(desc(FinancialRatio.year_quarter))
                       .limit(periods))
                
                result = await session.execute(stmt)
                ratios = result.scalars().all()
                
                trend_data = {
                    'profitability': [],
                    'liquidity': [],
                    'efficiency': [],
                    'leverage': []
                }
                
                for ratio in reversed(ratios):  # 反轉以時間順序排列
                    trend_data['profitability'].append({
                        'period': ratio.year_quarter,
                        'roe': float(ratio.roe) if ratio.roe else 0,
                        'roa': float(ratio.roa) if ratio.roa else 0,
                        'net_margin': float(ratio.net_margin) if ratio.net_margin else 0
                    })
                    
                    trend_data['liquidity'].append({
                        'period': ratio.year_quarter,
                        'current_ratio': float(ratio.current_ratio) if ratio.current_ratio else 0,
                        'quick_ratio': float(ratio.quick_ratio) if ratio.quick_ratio else 0,
                        'cash_ratio': float(ratio.cash_ratio) if ratio.cash_ratio else 0
                    })
                    
                    trend_data['efficiency'].append({
                        'period': ratio.year_quarter,
                        'total_asset_turnover': float(ratio.total_asset_turnover) if ratio.total_asset_turnover else 0,
                        'receivables_turnover': float(ratio.receivables_turnover) if ratio.receivables_turnover else 0,
                        'inventory_turnover': float(ratio.inventory_turnover) if ratio.inventory_turnover else 0
                    })
                    
                    trend_data['leverage'].append({
                        'period': ratio.year_quarter,
                        'debt_to_asset_ratio': float(ratio.debt_to_asset_ratio) if ratio.debt_to_asset_ratio else 0,
                        'debt_to_equity_ratio': float(ratio.debt_to_equity_ratio) if ratio.debt_to_equity_ratio else 0,
                        'equity_ratio': float(ratio.equity_ratio) if ratio.equity_ratio else 0
                    })
                
                return trend_data
                
        except Exception as e:
            logger.error(f"取得財務趨勢失敗: {company_id}, {e}")
            return {'profitability': [], 'liquidity': [], 'efficiency': [], 'leverage': []}


class IndustryDataService:
    """產業資料服務"""
    
    async def get_industry_benchmark(self, industry_code: str) -> Optional[IndustryBenchmark]:
        """
        取得產業基準
        
        Args:
            industry_code: 產業代碼
            
        Returns:
            Optional[IndustryBenchmark]: 產業基準資料
        """
        try:
            async with get_async_session() as session:
                from src.models import IndustryBenchmarks
                
                stmt = (select(IndustryBenchmarks)
                       .where(IndustryBenchmarks.industry_code == industry_code)
                       .order_by(desc(IndustryBenchmarks.year_quarter))
                       .limit(1))
                
                result = await session.execute(stmt)
                benchmark = result.scalar_one_or_none()
                
                if not benchmark:
                    return None
                
                return IndustryBenchmark(
                    industry_code=benchmark.industry_code,
                    industry_name=f"產業代碼{industry_code}",
                    company_count=benchmark.company_count or 0,
                    avg_roe=float(benchmark.avg_roe) if benchmark.avg_roe else 0,
                    avg_roa=float(benchmark.avg_roa) if benchmark.avg_roa else 0,
                    avg_current_ratio=float(benchmark.avg_current_ratio) if benchmark.avg_current_ratio else 0,
                    avg_debt_ratio=float(benchmark.avg_debt_ratio) if benchmark.avg_debt_ratio else 0,
                    avg_gross_margin=float(benchmark.avg_gross_margin) if benchmark.avg_gross_margin else 0,
                    avg_net_margin=float(benchmark.avg_net_margin) if benchmark.avg_net_margin else 0,
                    avg_pe_ratio=float(benchmark.avg_pe_ratio) if benchmark.avg_pe_ratio else 0,
                    avg_pb_ratio=float(benchmark.avg_pb_ratio) if benchmark.avg_pb_ratio else 0,
                    median_roe=float(benchmark.median_roe) if benchmark.median_roe else 0,
                    median_roa=float(benchmark.median_roa) if benchmark.median_roa else 0,
                    median_current_ratio=float(benchmark.median_current_ratio) if benchmark.median_current_ratio else 0,
                    median_debt_ratio=float(benchmark.median_debt_ratio) if benchmark.median_debt_ratio else 0,
                    roe_25_percentile=float(benchmark.roe_25_percentile) if benchmark.roe_25_percentile else 0,
                    roe_75_percentile=float(benchmark.roe_75_percentile) if benchmark.roe_75_percentile else 0,
                    pe_25_percentile=float(benchmark.pe_25_percentile) if benchmark.pe_25_percentile else 0,
                    pe_75_percentile=float(benchmark.pe_75_percentile) if benchmark.pe_75_percentile else 0,
                    debt_25_percentile=float(benchmark.debt_25_percentile) if benchmark.debt_25_percentile else 0,
                    debt_75_percentile=float(benchmark.debt_75_percentile) if benchmark.debt_75_percentile else 0,
                    roe_std_dev=float(benchmark.roe_std_dev) if benchmark.roe_std_dev else 0,
                    roa_std_dev=float(benchmark.roa_std_dev) if benchmark.roa_std_dev else 0
                )
                
        except Exception as e:
            logger.error(f"取得產業基準失敗: {industry_code}, {e}")
            return None
    
    async def get_peer_companies_data(self, industry_code: str, 
                                    exclude_company_id: str,
                                    limit: int = 10) -> List[PeerCompanyData]:
        """
        取得同業公司資料
        
        Args:
            industry_code: 產業代碼
            exclude_company_id: 排除的公司代碼
            limit: 限制筆數
            
        Returns:
            List[PeerCompanyData]: 同業公司資料列表
        """
        try:
            # 這裡應該要有更複雜的邏輯來計算市值、整合財務比率等
            # 為了示例，我們先返回空列表
            peer_companies = []
            
            async with get_async_session() as session:
                from src.models import Company
                
                # 取得同產業公司
                stmt = (select(Company)
                       .where(Company.industry_code == industry_code)
                       .where(Company.company_id != exclude_company_id)
                       .where(Company.is_active == True)
                       .limit(limit))
                
                result = await session.execute(stmt)
                companies = result.scalars().all()
                
                for company in companies:
                    # 這裡需要整合財務資料，暫時使用假資料
                    peer_data = PeerCompanyData(
                        company_id=company.company_id,
                        company_name=company.company_name,
                        market_cap=10_000_000_000,  # 假設市值
                        revenue=1_000_000_000,     # 假設營收
                        net_income=100_000_000,    # 假設淨利
                        total_assets=5_000_000_000, # 假設總資產
                        shareholders_equity=3_000_000_000, # 假設股東權益
                        roe=0.12,                   # 假設ROE
                        roa=0.08,                   # 假設ROA
                        current_ratio=1.5,          # 假設流動比率
                        debt_ratio=0.4,             # 假設負債比率
                        net_margin=0.1              # 假設淨利率
                    )
                    peer_companies.append(peer_data)
            
            return peer_companies
            
        except Exception as e:
            logger.error(f"取得同業公司資料失敗: {industry_code}, {e}")
            return []


class CacheService:
    """快取服務"""
    
    def __init__(self):
        import redis
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            password='dev_redis_2024',
            decode_responses=True
        )
        self.cache_ttl = 3600  # 1小時快取期限
    
    async def get_cached_data(self, key: str) -> Optional[Dict]:
        """取得快取資料"""
        try:
            import json
            cached_data = self.redis_client.get(key)
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.warning(f"取得快取資料失敗: {key}, {e}")
            return None
    
    async def set_cached_data(self, key: str, data: Dict, ttl: Optional[int] = None) -> bool:
        """設定快取資料"""
        try:
            import json
            ttl = ttl or self.cache_ttl
            serialized_data = json.dumps(data, default=str)
            return self.redis_client.setex(key, ttl, serialized_data)
        except Exception as e:
            logger.warning(f"設定快取資料失敗: {key}, {e}")
            return False
    
    async def invalidate_cache(self, pattern: str) -> bool:
        """清除快取"""
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys) > 0
            return True
        except Exception as e:
            logger.warning(f"清除快取失敗: {pattern}, {e}")
            return False