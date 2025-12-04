"""
財務資料分析服務層
Financial Data Analysis Service Layer
"""

from typing import List, Dict, Optional, Any, Tuple
from decimal import Decimal
from datetime import datetime, date, timedelta
import asyncio
import logging
import numpy as np
from statistics import mean, median

from sqlalchemy import text, and_, or_, func, desc, asc
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.core.database import get_async_session, db_manager
from src.core.exceptions import (
    CompanyNotFoundError, 
    FinancialDataNotFoundError, 
    ValidationError, 
    FinancialAnalysisException
)
from src.core.cache import CacheManager
from src.core.logging import get_logger
from src.schemas.responses import FinancialRatios

logger = get_logger("financial_service")


class FinancialDataService:
    """財務資料分析服務"""
    
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        self.cache = cache_manager
        self.logger = logger
    
    async def get_financial_ratios(
        self, 
        company_id: str, 
        year_quarter: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        取得公司財務比率
        
        Args:
            company_id: 公司代碼
            year_quarter: 年季別 (e.g., "2024Q1")，若為None則取最新資料
            
        Returns:
            Dict[str, Any]: 財務比率資料，若不存在則返回 None
            
        Raises:
            ValidationError: 輸入參數驗證錯誤
            FinancialAnalysisException: 資料庫查詢錯誤
        """
        # 驗證輸入參數
        if not company_id or len(company_id) != 4 or not company_id.isdigit():
            raise ValidationError("公司代碼必須為4位數字", field="company_id", value=company_id)
        
        if year_quarter and not self._validate_year_quarter(year_quarter):
            raise ValidationError(
                "年季別格式錯誤，正確格式: 2024Q1", 
                field="year_quarter", 
                value=year_quarter
            )
        
        # 檢查快取
        cache_key = f"financial:ratios:{company_id}:{year_quarter or 'latest'}"
        if self.cache:
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                self.logger.debug(f"Financial ratios for {company_id} found in cache")
                return cached_data
        
        try:
            async with get_async_session() as session:
                # 建構查詢條件
                conditions = ["company_id = :company_id"]
                params = {"company_id": company_id}
                
                if year_quarter:
                    conditions.append("year_quarter = :year_quarter")
                    params["year_quarter"] = year_quarter
                
                where_clause = " AND ".join(conditions)
                order_clause = "ORDER BY year_quarter DESC LIMIT 1" if not year_quarter else ""
                
                query = text(f"""
                    SELECT 
                        company_id,
                        year_quarter,
                        -- 財務結構比率
                        debt_to_asset_ratio,
                        debt_to_equity_ratio,
                        equity_ratio,
                        -- 償債能力比率
                        current_ratio,
                        quick_ratio,
                        cash_ratio,
                        interest_coverage_ratio,
                        -- 經營效率比率
                        receivables_turnover,
                        inventory_turnover,
                        total_asset_turnover,
                        -- 獲利能力比率
                        roa,
                        roe,
                        roic,
                        gross_margin,
                        operating_margin,
                        net_margin,
                        ebitda_margin,
                        -- 市場評價比率
                        pe_ratio,
                        pb_ratio,
                        ev_ebitda,
                        -- 現金流量比率
                        operating_cash_ratio,
                        free_cash_flow_yield,
                        -- 計算時間
                        calculation_date
                    FROM financial_ratios 
                    WHERE {where_clause}
                    {order_clause}
                """)
                
                result = await session.execute(query, params)
                row = result.fetchone()
                
                if not row:
                    self.logger.info(f"Financial ratios not found for company {company_id}")
                    return None
                
                ratios_data = {
                    "company_id": row.company_id,
                    "year_quarter": row.year_quarter,
                    "debt_to_asset_ratio": float(row.debt_to_asset_ratio) if row.debt_to_asset_ratio else None,
                    "debt_to_equity_ratio": float(row.debt_to_equity_ratio) if row.debt_to_equity_ratio else None,
                    "equity_ratio": float(row.equity_ratio) if row.equity_ratio else None,
                    "current_ratio": float(row.current_ratio) if row.current_ratio else None,
                    "quick_ratio": float(row.quick_ratio) if row.quick_ratio else None,
                    "cash_ratio": float(row.cash_ratio) if row.cash_ratio else None,
                    "interest_coverage_ratio": float(row.interest_coverage_ratio) if row.interest_coverage_ratio else None,
                    "receivables_turnover": float(row.receivables_turnover) if row.receivables_turnover else None,
                    "inventory_turnover": float(row.inventory_turnover) if row.inventory_turnover else None,
                    "total_asset_turnover": float(row.total_asset_turnover) if row.total_asset_turnover else None,
                    "roa": float(row.roa) if row.roa else None,
                    "roe": float(row.roe) if row.roe else None,
                    "roic": float(row.roic) if row.roic else None,
                    "gross_margin": float(row.gross_margin) if row.gross_margin else None,
                    "operating_margin": float(row.operating_margin) if row.operating_margin else None,
                    "net_margin": float(row.net_margin) if row.net_margin else None,
                    "ebitda_margin": float(row.ebitda_margin) if row.ebitda_margin else None,
                    "pe_ratio": float(row.pe_ratio) if row.pe_ratio else None,
                    "pb_ratio": float(row.pb_ratio) if row.pb_ratio else None,
                    "ev_ebitda": float(row.ev_ebitda) if row.ev_ebitda else None,
                    "operating_cash_ratio": float(row.operating_cash_ratio) if row.operating_cash_ratio else None,
                    "free_cash_flow_yield": float(row.free_cash_flow_yield) if row.free_cash_flow_yield else None,
                    "calculation_date": row.calculation_date.isoformat() if row.calculation_date else None
                }
                
                # 儲存到快取
                if self.cache:
                    await self.cache.set(cache_key, ratios_data, expire=1800)  # 30分鐘過期
                
                self.logger.debug(f"Financial ratios for {company_id} retrieved from database")
                return ratios_data
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving financial ratios for {company_id}: {e}")
            raise FinancialAnalysisException(
                message="財務比率資料查詢失敗",
                error_code="RATIOS_QUERY_ERROR",
                details={"company_id": company_id, "year_quarter": year_quarter}
            )
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving financial ratios for {company_id}: {e}")
            raise FinancialAnalysisException(
                message="財務比率服務內部錯誤",
                error_code="RATIOS_INTERNAL_ERROR"
            )
    
    async def get_financial_statements(
        self, 
        company_id: str, 
        statement_type: str,
        periods: int = 8
    ) -> List[Dict[str, Any]]:
        """
        取得財務報表資料
        
        Args:
            company_id: 公司代碼
            statement_type: 報表類型 ('BS', 'IS', 'CF', 'SE')
            periods: 期數 (預設8期)
            
        Returns:
            List[Dict[str, Any]]: 財務報表資料列表
            
        Raises:
            ValidationError: 輸入參數驗證錯誤
            FinancialAnalysisException: 資料庫查詢錯誤
        """
        if not company_id or len(company_id) != 4 or not company_id.isdigit():
            raise ValidationError("公司代碼必須為4位數字", field="company_id", value=company_id)
        
        valid_types = ['BS', 'IS', 'CF', 'SE']
        if statement_type not in valid_types:
            raise ValidationError(
                f"報表類型錯誤，有效類型: {', '.join(valid_types)}", 
                field="statement_type", 
                value=statement_type
            )
        
        cache_key = f"financial:statements:{company_id}:{statement_type}:{periods}"
        if self.cache:
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                return cached_data
        
        try:
            async with get_async_session() as session:
                query = text("""
                    SELECT 
                        company_id,
                        year_quarter,
                        statement_type,
                        report_type,
                        -- 資產負債表
                        current_assets,
                        non_current_assets,
                        total_assets,
                        current_liabilities,
                        non_current_liabilities,
                        total_liabilities,
                        shareholders_equity,
                        -- 損益表
                        revenue,
                        gross_profit,
                        operating_income,
                        net_income,
                        eps,
                        -- 現金流量表
                        operating_cash_flow,
                        investing_cash_flow,
                        financing_cash_flow,
                        -- 其他
                        created_at
                    FROM financial_statements 
                    WHERE company_id = :company_id 
                      AND statement_type = :statement_type
                    ORDER BY year_quarter DESC
                    LIMIT :periods
                """)
                
                result = await session.execute(query, {
                    "company_id": company_id,
                    "statement_type": statement_type,
                    "periods": periods
                })
                rows = result.fetchall()
                
                statements = []
                for row in rows:
                    statement_data = {
                        "company_id": row.company_id,
                        "year_quarter": row.year_quarter,
                        "statement_type": row.statement_type,
                        "report_type": row.report_type,
                        "current_assets": float(row.current_assets) if row.current_assets else None,
                        "non_current_assets": float(row.non_current_assets) if row.non_current_assets else None,
                        "total_assets": float(row.total_assets) if row.total_assets else None,
                        "current_liabilities": float(row.current_liabilities) if row.current_liabilities else None,
                        "non_current_liabilities": float(row.non_current_liabilities) if row.non_current_liabilities else None,
                        "total_liabilities": float(row.total_liabilities) if row.total_liabilities else None,
                        "shareholders_equity": float(row.shareholders_equity) if row.shareholders_equity else None,
                        "revenue": float(row.revenue) if row.revenue else None,
                        "gross_profit": float(row.gross_profit) if row.gross_profit else None,
                        "operating_income": float(row.operating_income) if row.operating_income else None,
                        "net_income": float(row.net_income) if row.net_income else None,
                        "eps": float(row.eps) if row.eps else None,
                        "operating_cash_flow": float(row.operating_cash_flow) if row.operating_cash_flow else None,
                        "investing_cash_flow": float(row.investing_cash_flow) if row.investing_cash_flow else None,
                        "financing_cash_flow": float(row.financing_cash_flow) if row.financing_cash_flow else None,
                        "created_at": row.created_at.isoformat() if row.created_at else None
                    }
                    statements.append(statement_data)
                
                # 儲存到快取
                if self.cache:
                    await self.cache.set(cache_key, statements, expire=3600)  # 1小時過期
                
                self.logger.info(f"Retrieved {len(statements)} financial statements for {company_id}")
                return statements
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving financial statements for {company_id}: {e}")
            raise FinancialAnalysisException(
                message="財務報表資料查詢失敗",
                error_code="STATEMENTS_QUERY_ERROR",
                details={"company_id": company_id, "statement_type": statement_type}
            )
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving financial statements for {company_id}: {e}")
            raise FinancialAnalysisException(
                message="財務報表服務內部錯誤",
                error_code="STATEMENTS_INTERNAL_ERROR"
            )
    
    async def get_financial_trend(
        self, 
        company_id: str, 
        periods: int = 8
    ) -> Dict[str, Any]:
        """
        取得財務趨勢分析
        
        Args:
            company_id: 公司代碼
            periods: 分析期數
            
        Returns:
            Dict[str, Any]: 財務趨勢資料
            
        Raises:
            ValidationError: 輸入參數驗證錯誤
            FinancialAnalysisException: 資料庫查詢錯誤
        """
        if not company_id or len(company_id) != 4 or not company_id.isdigit():
            raise ValidationError("公司代碼必須為4位數字", field="company_id", value=company_id)
        
        if periods < 2 or periods > 20:
            raise ValidationError("分析期數必須在2-20之間", field="periods", value=periods)
        
        cache_key = f"financial:trend:{company_id}:{periods}"
        if self.cache:
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                return cached_data
        
        try:
            async with get_async_session() as session:
                # 取得財務比率趨勢
                ratios_query = text("""
                    SELECT 
                        year_quarter,
                        roa,
                        roe,
                        gross_margin,
                        operating_margin,
                        net_margin,
                        current_ratio,
                        debt_to_asset_ratio,
                        calculated_at
                    FROM financial_ratios 
                    WHERE company_id = :company_id
                    ORDER BY year_quarter DESC
                    LIMIT :periods
                """)
                
                # 取得營收和獲利趨勢
                statements_query = text("""
                    SELECT 
                        year_quarter,
                        revenue,
                        gross_profit,
                        operating_income,
                        net_income,
                        eps
                    FROM financial_statements 
                    WHERE company_id = :company_id 
                      AND statement_type = 'IS'
                    ORDER BY year_quarter DESC
                    LIMIT :periods
                """)
                
                params = {"company_id": company_id, "periods": periods}
                
                ratios_result = await session.execute(ratios_query, params)
                statements_result = await session.execute(statements_query, params)
                
                # 處理比率趨勢
                ratios_trend = []
                for row in ratios_result:
                    ratios_trend.append({
                        "period": row.year_quarter,
                        "roa": float(row.roa) if row.roa else None,
                        "roe": float(row.roe) if row.roe else None,
                        "gross_margin": float(row.gross_margin) if row.gross_margin else None,
                        "operating_margin": float(row.operating_margin) if row.operating_margin else None,
                        "net_margin": float(row.net_margin) if row.net_margin else None,
                        "current_ratio": float(row.current_ratio) if row.current_ratio else None,
                        "debt_to_asset_ratio": float(row.debt_to_asset_ratio) if row.debt_to_asset_ratio else None
                    })
                
                # 處理財務報表趨勢
                statements_trend = []
                for row in statements_result:
                    statements_trend.append({
                        "period": row.year_quarter,
                        "revenue": float(row.revenue) if row.revenue else None,
                        "gross_profit": float(row.gross_profit) if row.gross_profit else None,
                        "operating_income": float(row.operating_income) if row.operating_income else None,
                        "net_income": float(row.net_income) if row.net_income else None,
                        "eps": float(row.eps) if row.eps else None
                    })
                
                # 計算成長率
                growth_analysis = self._calculate_growth_rates(statements_trend)
                
                # 趨勢分析結果
                trend_data = {
                    "company_id": company_id,
                    "periods_analyzed": len(ratios_trend),
                    "ratios_trend": ratios_trend,
                    "statements_trend": statements_trend,
                    "growth_analysis": growth_analysis,
                    "trend_summary": self._generate_trend_summary(ratios_trend, statements_trend),
                    "analysis_date": datetime.now().isoformat()
                }
                
                # 儲存到快取
                if self.cache:
                    await self.cache.set(cache_key, trend_data, expire=3600)  # 1小時過期
                
                return trend_data
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving financial trend for {company_id}: {e}")
            raise FinancialAnalysisException(
                message="財務趨勢資料查詢失敗",
                error_code="TREND_QUERY_ERROR",
                details={"company_id": company_id}
            )
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving financial trend for {company_id}: {e}")
            raise FinancialAnalysisException(
                message="財務趨勢服務內部錯誤",
                error_code="TREND_INTERNAL_ERROR"
            )
    
    async def calculate_financial_health(
        self, 
        company_id: str, 
        analysis_period: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        計算財務健康度評估
        
        Args:
            company_id: 公司代碼
            analysis_period: 分析期間
            
        Returns:
            Dict[str, Any]: 財務健康度評估結果
            
        Raises:
            ValidationError: 輸入參數驗證錯誤
            FinancialAnalysisException: 計算錯誤
        """
        # 取得財務比率資料
        ratios = await self.get_financial_ratios(company_id, analysis_period)
        if not ratios:
            raise FinancialDataNotFoundError(company_id, "財務比率", analysis_period)
        
        try:
            # 健康度評分項目
            health_scores = {}
            
            # 1. 獲利能力評分 (25%)
            profitability_score = self._calculate_profitability_score(ratios)
            health_scores["profitability"] = profitability_score
            
            # 2. 流動性評分 (25%)
            liquidity_score = self._calculate_liquidity_score(ratios)
            health_scores["liquidity"] = liquidity_score
            
            # 3. 槓桿風險評分 (25%)
            leverage_score = self._calculate_leverage_score(ratios)
            health_scores["leverage"] = leverage_score
            
            # 4. 經營效率評分 (25%)
            efficiency_score = self._calculate_efficiency_score(ratios)
            health_scores["efficiency"] = efficiency_score
            
            # 計算綜合評分
            weights = {"profitability": 0.25, "liquidity": 0.25, "leverage": 0.25, "efficiency": 0.25}
            overall_score = sum(health_scores[key] * weights[key] for key in health_scores.keys())
            
            # 確定評級
            overall_grade = self._determine_health_grade(overall_score)
            
            # 生成評估詳情和建議
            assessment_details = self._generate_assessment_details(health_scores, ratios)
            recommendations = self._generate_recommendations(health_scores)
            
            health_assessment = {
                "overall_grade": overall_grade,
                "overall_score": round(overall_score, 2),
                "detailed_scores": {k: round(v, 2) for k, v in health_scores.items()},
                "assessment_details": assessment_details,
                "strengths": self._identify_strengths(health_scores),
                "weaknesses": self._identify_weaknesses(health_scores),
                "recommendations": recommendations,
                "analysis_period": analysis_period or "latest",
                "analysis_date": datetime.now().isoformat()
            }
            
            return health_assessment
            
        except Exception as e:
            self.logger.error(f"Error calculating financial health for {company_id}: {e}")
            raise FinancialAnalysisException(
                message="財務健康度計算失敗",
                error_code="HEALTH_CALCULATION_ERROR",
                details={"company_id": company_id}
            )
    
    async def get_industry_peer_comparison(
        self, 
        company_id: str, 
        industry_code: str
    ) -> Dict[str, Any]:
        """
        取得同業比較分析
        
        Args:
            company_id: 目標公司代碼
            industry_code: 產業代碼
            
        Returns:
            Dict[str, Any]: 同業比較分析結果
            
        Raises:
            FinancialAnalysisException: 分析錯誤
        """
        cache_key = f"peer:comparison:{company_id}:{industry_code}"
        if self.cache:
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                return cached_data
        
        try:
            async with get_async_session() as session:
                # 取得目標公司比率
                target_ratios = await self.get_financial_ratios(company_id)
                if not target_ratios:
                    raise FinancialDataNotFoundError(company_id, "財務比率")
                
                # 取得同業平均比率
                peer_query = text("""
                    SELECT 
                        AVG(fr.roa) as avg_roa,
                        AVG(fr.roe) as avg_roe,
                        AVG(fr.gross_margin) as avg_gross_margin,
                        AVG(fr.operating_margin) as avg_operating_margin,
                        AVG(fr.net_margin) as avg_net_margin,
                        AVG(fr.current_ratio) as avg_current_ratio,
                        AVG(fr.debt_to_asset_ratio) as avg_debt_ratio,
                        AVG(fr.pe_ratio) as avg_pe_ratio,
                        COUNT(DISTINCT fr.company_id) as peer_count
                    FROM financial_ratios fr
                    JOIN companies c ON fr.company_id = c.company_id
                    WHERE c.industry_code = :industry_code 
                      AND c.is_active = true
                      AND fr.company_id != :company_id
                      AND fr.year_quarter = (
                          SELECT MAX(year_quarter) 
                          FROM financial_ratios fr2 
                          WHERE fr2.company_id = fr.company_id
                      )
                """)
                
                result = await session.execute(peer_query, {
                    "industry_code": industry_code,
                    "company_id": company_id
                })
                peer_data = result.fetchone()
                
                if not peer_data or peer_data.peer_count == 0:
                    raise FinancialAnalysisException(
                        message="同業資料不足，無法進行比較分析",
                        error_code="INSUFFICIENT_PEER_DATA"
                    )
                
                # 比較分析
                comparison_result = {
                    "target_company": company_id,
                    "industry_code": industry_code,
                    "peer_count": peer_data.peer_count,
                    "comparison_metrics": {
                        "roa": {
                            "target": target_ratios.get("roa"),
                            "peer_average": float(peer_data.avg_roa) if peer_data.avg_roa else None,
                            "performance": self._calculate_relative_performance(
                                target_ratios.get("roa"), 
                                float(peer_data.avg_roa) if peer_data.avg_roa else None
                            )
                        },
                        "roe": {
                            "target": target_ratios.get("roe"),
                            "peer_average": float(peer_data.avg_roe) if peer_data.avg_roe else None,
                            "performance": self._calculate_relative_performance(
                                target_ratios.get("roe"), 
                                float(peer_data.avg_roe) if peer_data.avg_roe else None
                            )
                        },
                        "gross_margin": {
                            "target": target_ratios.get("gross_margin"),
                            "peer_average": float(peer_data.avg_gross_margin) if peer_data.avg_gross_margin else None,
                            "performance": self._calculate_relative_performance(
                                target_ratios.get("gross_margin"), 
                                float(peer_data.avg_gross_margin) if peer_data.avg_gross_margin else None
                            )
                        },
                        "current_ratio": {
                            "target": target_ratios.get("current_ratio"),
                            "peer_average": float(peer_data.avg_current_ratio) if peer_data.avg_current_ratio else None,
                            "performance": self._calculate_relative_performance(
                                target_ratios.get("current_ratio"), 
                                float(peer_data.avg_current_ratio) if peer_data.avg_current_ratio else None
                            )
                        }
                    },
                    "analysis_summary": self._generate_peer_comparison_summary(target_ratios, peer_data),
                    "analysis_date": datetime.now().isoformat()
                }
                
                # 儲存到快取
                if self.cache:
                    await self.cache.set(cache_key, comparison_result, expire=7200)  # 2小時過期
                
                return comparison_result
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error in peer comparison for {company_id}: {e}")
            raise FinancialAnalysisException(
                message="同業比較資料查詢失敗",
                error_code="PEER_COMPARISON_QUERY_ERROR"
            )
        except Exception as e:
            self.logger.error(f"Error in peer comparison for {company_id}: {e}")
            raise FinancialAnalysisException(
                message="同業比較分析失敗",
                error_code="PEER_COMPARISON_ERROR"
            )
    
    # 輔助方法
    def _validate_year_quarter(self, year_quarter: str) -> bool:
        """驗證年季別格式"""
        import re
        pattern = r"^20\d{2}Q[1-4]$"
        return re.match(pattern, year_quarter) is not None
    
    def _calculate_growth_rates(self, statements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """計算成長率"""
        if len(statements) < 2:
            return {"message": "資料不足，無法計算成長率"}
        
        try:
            # 按期間排序 (最新在前)
            sorted_statements = sorted(statements, key=lambda x: x["period"], reverse=True)
            
            growth_rates = {}
            metrics = ["revenue", "gross_profit", "operating_income", "net_income"]
            
            for metric in metrics:
                current = sorted_statements[0].get(metric)
                previous = sorted_statements[1].get(metric)
                
                if current and previous and previous != 0:
                    growth_rate = ((current - previous) / abs(previous)) * 100
                    growth_rates[f"{metric}_growth"] = round(growth_rate, 2)
                else:
                    growth_rates[f"{metric}_growth"] = None
            
            return growth_rates
            
        except Exception as e:
            self.logger.warning(f"Error calculating growth rates: {e}")
            return {"error": "成長率計算失敗"}
    
    def _generate_trend_summary(
        self, 
        ratios_trend: List[Dict], 
        statements_trend: List[Dict]
    ) -> Dict[str, str]:
        """產生趨勢摘要"""
        try:
            summary = {}
            
            # 獲利能力趨勢
            if len(ratios_trend) >= 2:
                latest_roe = ratios_trend[0].get("roe")
                prev_roe = ratios_trend[1].get("roe")
                
                if latest_roe and prev_roe:
                    if latest_roe > prev_roe:
                        summary["profitability_trend"] = "改善"
                    elif latest_roe < prev_roe:
                        summary["profitability_trend"] = "惡化"
                    else:
                        summary["profitability_trend"] = "持平"
            
            # 營收趨勢
            if len(statements_trend) >= 2:
                latest_revenue = statements_trend[0].get("revenue")
                prev_revenue = statements_trend[1].get("revenue")
                
                if latest_revenue and prev_revenue:
                    if latest_revenue > prev_revenue:
                        summary["revenue_trend"] = "成長"
                    elif latest_revenue < prev_revenue:
                        summary["revenue_trend"] = "衰退"
                    else:
                        summary["revenue_trend"] = "持平"
            
            return summary
            
        except Exception as e:
            self.logger.warning(f"Error generating trend summary: {e}")
            return {"error": "趨勢摘要產生失敗"}
    
    def _calculate_profitability_score(self, ratios: Dict[str, Any]) -> float:
        """計算獲利能力評分"""
        score = 0
        max_score = 100
        
        # ROE評分 (40%)
        roe = ratios.get("roe")
        if roe:
            if roe >= 0.15:  # 15%以上
                score += 40
            elif roe >= 0.10:  # 10-15%
                score += 30
            elif roe >= 0.05:  # 5-10%
                score += 20
            elif roe >= 0:  # 正數
                score += 10
        
        # 毛利率評分 (30%)
        gross_margin = ratios.get("gross_margin")
        if gross_margin:
            if gross_margin >= 0.30:  # 30%以上
                score += 30
            elif gross_margin >= 0.20:  # 20-30%
                score += 25
            elif gross_margin >= 0.10:  # 10-20%
                score += 15
            elif gross_margin >= 0:  # 正數
                score += 5
        
        # 淨利率評分 (30%)
        net_margin = ratios.get("net_margin")
        if net_margin:
            if net_margin >= 0.10:  # 10%以上
                score += 30
            elif net_margin >= 0.05:  # 5-10%
                score += 25
            elif net_margin >= 0.02:  # 2-5%
                score += 15
            elif net_margin >= 0:  # 正數
                score += 5
        
        return min(score, max_score)
    
    def _calculate_liquidity_score(self, ratios: Dict[str, Any]) -> float:
        """計算流動性評分"""
        score = 0
        max_score = 100
        
        # 流動比率評分 (60%)
        current_ratio = ratios.get("current_ratio")
        if current_ratio:
            if 1.5 <= current_ratio <= 3.0:  # 理想範圍
                score += 60
            elif 1.2 <= current_ratio < 1.5:  # 可接受
                score += 45
            elif 1.0 <= current_ratio < 1.2:  # 偏低
                score += 25
            elif current_ratio >= 1.0:  # 基本安全
                score += 15
        
        # 速動比率評分 (40%)
        quick_ratio = ratios.get("quick_ratio")
        if quick_ratio:
            if quick_ratio >= 1.0:  # 理想
                score += 40
            elif quick_ratio >= 0.8:  # 可接受
                score += 30
            elif quick_ratio >= 0.5:  # 偏低
                score += 15
            else:  # 過低
                score += 5
        
        return min(score, max_score)
    
    def _calculate_leverage_score(self, ratios: Dict[str, Any]) -> float:
        """計算槓桿風險評分"""
        score = 0
        max_score = 100
        
        # 負債對資產比率評分 (70%)
        debt_ratio = ratios.get("debt_to_asset_ratio")
        if debt_ratio:
            if debt_ratio <= 0.30:  # 30%以下 - 保守
                score += 70
            elif debt_ratio <= 0.50:  # 30-50% - 適中
                score += 55
            elif debt_ratio <= 0.70:  # 50-70% - 偏高
                score += 35
            elif debt_ratio <= 0.85:  # 70-85% - 高風險
                score += 15
            else:  # 85%以上 - 極高風險
                score += 5
        
        # 利息保障倍數評分 (30%)
        interest_coverage = ratios.get("interest_coverage_ratio")
        if interest_coverage:
            if interest_coverage >= 10:  # 10倍以上
                score += 30
            elif interest_coverage >= 5:  # 5-10倍
                score += 25
            elif interest_coverage >= 2.5:  # 2.5-5倍
                score += 15
            elif interest_coverage >= 1.5:  # 1.5-2.5倍
                score += 10
            else:  # 1.5倍以下
                score += 5
        
        return min(score, max_score)
    
    def _calculate_efficiency_score(self, ratios: Dict[str, Any]) -> float:
        """計算經營效率評分"""
        score = 0
        max_score = 100
        
        # 資產周轉率評分 (50%)
        asset_turnover = ratios.get("total_asset_turnover")
        if asset_turnover:
            if asset_turnover >= 1.0:  # 1.0以上
                score += 50
            elif asset_turnover >= 0.8:  # 0.8-1.0
                score += 40
            elif asset_turnover >= 0.5:  # 0.5-0.8
                score += 25
            elif asset_turnover >= 0.3:  # 0.3-0.5
                score += 15
            else:  # 0.3以下
                score += 5
        
        # 應收帳款周轉率評分 (25%)
        receivables_turnover = ratios.get("receivables_turnover")
        if receivables_turnover:
            if receivables_turnover >= 10:  # 10次以上
                score += 25
            elif receivables_turnover >= 6:  # 6-10次
                score += 20
            elif receivables_turnover >= 4:  # 4-6次
                score += 15
            else:  # 4次以下
                score += 10
        
        # 存貨周轉率評分 (25%)
        inventory_turnover = ratios.get("inventory_turnover")
        if inventory_turnover:
            if inventory_turnover >= 8:  # 8次以上
                score += 25
            elif inventory_turnover >= 4:  # 4-8次
                score += 20
            elif inventory_turnover >= 2:  # 2-4次
                score += 15
            else:  # 2次以下
                score += 10
        
        return min(score, max_score)
    
    def _determine_health_grade(self, overall_score: float) -> str:
        """確定健康度評級"""
        if overall_score >= 90:
            return "優秀"
        elif overall_score >= 80:
            return "良好"
        elif overall_score >= 70:
            return "普通"
        elif overall_score >= 60:
            return "不佳"
        else:
            return "危險"
    
    def _generate_assessment_details(
        self, 
        health_scores: Dict[str, float], 
        ratios: Dict[str, Any]
    ) -> List[str]:
        """產生評估詳情"""
        details = []
        
        # 獲利能力評估
        profit_score = health_scores.get("profitability", 0)
        roe = ratios.get("roe")
        if profit_score >= 80:
            details.append("獲利能力表現優異")
        elif profit_score >= 60:
            details.append("獲利能力表現良好")
        else:
            details.append("獲利能力有待改善")
        
        # 流動性評估
        liquidity_score = health_scores.get("liquidity", 0)
        if liquidity_score >= 80:
            details.append("流動性充足")
        elif liquidity_score >= 60:
            details.append("流動性適中")
        else:
            details.append("流動性風險需注意")
        
        # 槓桿評估
        leverage_score = health_scores.get("leverage", 0)
        if leverage_score >= 80:
            details.append("財務結構穩健")
        elif leverage_score >= 60:
            details.append("負債水準可控")
        else:
            details.append("槓桿風險偏高")
        
        return details
    
    def _generate_recommendations(self, health_scores: Dict[str, float]) -> List[str]:
        """產生改善建議"""
        recommendations = []
        
        if health_scores.get("profitability", 0) < 60:
            recommendations.append("建議提升營運效率以改善獲利能力")
        
        if health_scores.get("liquidity", 0) < 60:
            recommendations.append("建議改善流動資產管理")
        
        if health_scores.get("leverage", 0) < 60:
            recommendations.append("建議優化資本結構，降低財務風險")
        
        if health_scores.get("efficiency", 0) < 60:
            recommendations.append("建議提升資產使用效率")
        
        if not recommendations:
            recommendations.append("整體財務狀況良好，建議持續監控")
        
        return recommendations
    
    def _identify_strengths(self, health_scores: Dict[str, float]) -> List[str]:
        """識別優勢項目"""
        strengths = []
        for category, score in health_scores.items():
            if score >= 80:
                category_names = {
                    "profitability": "獲利能力",
                    "liquidity": "流動性",
                    "leverage": "財務結構",
                    "efficiency": "經營效率"
                }
                strengths.append(category_names.get(category, category))
        return strengths
    
    def _identify_weaknesses(self, health_scores: Dict[str, float]) -> List[str]:
        """識別劣勢項目"""
        weaknesses = []
        for category, score in health_scores.items():
            if score < 60:
                category_names = {
                    "profitability": "獲利能力",
                    "liquidity": "流動性", 
                    "leverage": "財務結構",
                    "efficiency": "經營效率"
                }
                weaknesses.append(category_names.get(category, category))
        return weaknesses
    
    def _calculate_relative_performance(
        self, 
        target_value: Optional[float], 
        peer_average: Optional[float]
    ) -> Optional[str]:
        """計算相對表現"""
        if target_value is None or peer_average is None or peer_average == 0:
            return None
        
        performance_ratio = target_value / peer_average
        
        if performance_ratio >= 1.2:
            return "顯著優於同業"
        elif performance_ratio >= 1.1:
            return "優於同業"
        elif performance_ratio >= 0.9:
            return "與同業相當"
        elif performance_ratio >= 0.8:
            return "略遜於同業"
        else:
            return "顯著遜於同業"
    
    def _generate_peer_comparison_summary(
        self, 
        target_ratios: Dict[str, Any], 
        peer_data: Any
    ) -> str:
        """產生同業比較摘要"""
        summary_parts = []
        
        # ROE比較
        target_roe = target_ratios.get("roe")
        peer_roe = float(peer_data.avg_roe) if peer_data.avg_roe else None
        
        if target_roe and peer_roe:
            if target_roe > peer_roe * 1.1:
                summary_parts.append("ROE表現優於同業")
            elif target_roe < peer_roe * 0.9:
                summary_parts.append("ROE表現遜於同業")
            else:
                summary_parts.append("ROE表現與同業相當")
        
        # 毛利率比較
        target_margin = target_ratios.get("gross_margin")
        peer_margin = float(peer_data.avg_gross_margin) if peer_data.avg_gross_margin else None
        
        if target_margin and peer_margin:
            if target_margin > peer_margin * 1.1:
                summary_parts.append("毛利率高於同業平均")
            elif target_margin < peer_margin * 0.9:
                summary_parts.append("毛利率低於同業平均")
        
        return "；".join(summary_parts) if summary_parts else "與同業表現相當"


# 預設的財務資料服務實例
financial_service = FinancialDataService()