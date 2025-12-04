"""
簡化資料服務層
Simplified Data Service Layer
"""

from typing import Dict, List, Optional
from sqlalchemy import select, text
from src.core.database import engine
from src.core.logging import get_logger

logger = get_logger("simple_data_service")


class SimpleCompanyService:
    """簡化公司資料服務"""
    
    def get_company_basic_info(self, company_id: str) -> Optional[Dict]:
        """取得公司基本資訊"""
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT company_id, company_name, company_name_en, 
                               industry_code, industry_name, market_type, 
                               listing_date, capital_amount, outstanding_shares,
                               website, is_active
                        FROM companies 
                        WHERE company_id = :company_id
                    """),
                    {"company_id": company_id}
                )
                
                row = result.fetchone()
                if not row:
                    return None
                
                return {
                    'company_id': row.company_id,
                    'company_name': row.company_name,
                    'company_name_en': row.company_name_en,
                    'industry_code': row.industry_code,
                    'industry_name': row.industry_name,
                    'market_type': row.market_type,
                    'listing_date': row.listing_date.isoformat() if row.listing_date else None,
                    'capital_amount': float(row.capital_amount) if row.capital_amount else None,
                    'outstanding_shares': row.outstanding_shares,
                    'website': row.website,
                    'is_active': row.is_active
                }
                
        except Exception as e:
            logger.error(f"取得公司資訊失敗 {company_id}: {e}")
            return None
    
    def search_companies(self, keyword: Optional[str] = None, 
                        market_type: Optional[str] = None,
                        limit: int = 20) -> List[Dict]:
        """搜尋公司"""
        try:
            conditions = []
            params = {}
            
            if keyword:
                conditions.append("(company_id ILIKE :keyword OR company_name ILIKE :keyword)")
                params['keyword'] = f'%{keyword}%'
            
            if market_type:
                conditions.append("market_type = :market_type")
                params['market_type'] = market_type
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            params['limit'] = limit
            
            query = f"""
                SELECT company_id, company_name, industry_code, market_type
                FROM companies 
                {where_clause}
                AND is_active = true
                ORDER BY company_id
                LIMIT :limit
            """
            
            with engine.connect() as conn:
                result = conn.execute(text(query), params)
                
                return [
                    {
                        'company_id': row.company_id,
                        'company_name': row.company_name,
                        'industry_code': row.industry_code,
                        'market_type': row.market_type
                    }
                    for row in result
                ]
                
        except Exception as e:
            logger.error(f"搜尋公司失敗: {e}")
            return []
    
    def get_companies_by_industry(self, industry_code: str, limit: int = 50) -> List[Dict]:
        """按產業取得公司"""
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT company_id, company_name, market_type, capital_amount
                        FROM companies 
                        WHERE industry_code = :industry_code 
                        AND is_active = true
                        ORDER BY capital_amount DESC NULLS LAST
                        LIMIT :limit
                    """),
                    {"industry_code": industry_code, "limit": limit}
                )
                
                return [
                    {
                        'company_id': row.company_id,
                        'company_name': row.company_name,
                        'market_type': row.market_type,
                        'capital_amount': float(row.capital_amount) if row.capital_amount else None
                    }
                    for row in result
                ]
                
        except Exception as e:
            logger.error(f"按產業取得公司失敗 {industry_code}: {e}")
            return []


class SimpleFinancialService:
    """簡化財務資料服務"""
    
    def get_financial_ratios(self, company_id: str, 
                           year_quarter: Optional[str] = None) -> Optional[Dict]:
        """取得財務比率"""
        try:
            conditions = ["company_id = :company_id"]
            params = {"company_id": company_id}
            
            if year_quarter:
                conditions.append("year_quarter = :year_quarter")
                params["year_quarter"] = year_quarter
            
            where_clause = "WHERE " + " AND ".join(conditions)
            
            query = f"""
                SELECT * FROM financial_ratios 
                {where_clause}
                ORDER BY year_quarter DESC
                LIMIT 1
            """
            
            with engine.connect() as conn:
                result = conn.execute(text(query), params)
                row = result.fetchone()
                
                if not row:
                    return None
                
                return {
                    'debt_to_asset_ratio': float(row.debt_to_asset_ratio) if row.debt_to_asset_ratio else None,
                    'debt_to_equity_ratio': float(row.debt_to_equity_ratio) if row.debt_to_equity_ratio else None,
                    'equity_ratio': float(row.equity_ratio) if row.equity_ratio else None,
                    'current_ratio': float(row.current_ratio) if row.current_ratio else None,
                    'quick_ratio': float(row.quick_ratio) if row.quick_ratio else None,
                    'cash_ratio': float(row.cash_ratio) if row.cash_ratio else None,
                    'interest_coverage_ratio': float(row.interest_coverage_ratio) if row.interest_coverage_ratio else None,
                    'receivables_turnover': float(row.receivables_turnover) if row.receivables_turnover else None,
                    'inventory_turnover': float(row.inventory_turnover) if row.inventory_turnover else None,
                    'total_asset_turnover': float(row.total_asset_turnover) if row.total_asset_turnover else None,
                    'roa': float(row.roa) if row.roa else None,
                    'roe': float(row.roe) if row.roe else None,
                    'roic': float(row.roic) if row.roic else None,
                    'gross_margin': float(row.gross_margin) if row.gross_margin else None,
                    'operating_margin': float(row.operating_margin) if row.operating_margin else None,
                    'net_margin': float(row.net_margin) if row.net_margin else None,
                    'ebitda_margin': float(row.ebitda_margin) if row.ebitda_margin else None,
                    'pe_ratio': float(row.pe_ratio) if row.pe_ratio else None,
                    'pb_ratio': float(row.pb_ratio) if row.pb_ratio else None,
                    'ev_ebitda': float(row.ev_ebitda) if row.ev_ebitda else None
                }
                
        except Exception as e:
            logger.error(f"取得財務比率失敗 {company_id}: {e}")
            return None