"""
財務分析計算引擎
Financial Analysis Calculation Engine

提供完整的財務比率計算、趨勢分析和財務健康度評估功能
"""

from typing import Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
import numpy as np
from dataclasses import dataclass
from enum import Enum

from src.core.logging import get_logger

logger = get_logger("financial_calculator")


class FinancialHealth(Enum):
    """財務健康度評級"""
    EXCELLENT = "優秀"
    GOOD = "良好" 
    FAIR = "普通"
    POOR = "不佳"
    CRITICAL = "危險"


@dataclass
class FinancialStatements:
    """財務報表資料結構"""
    # 資產負債表項目
    current_assets: Decimal
    non_current_assets: Decimal
    total_assets: Decimal
    current_liabilities: Decimal
    non_current_liabilities: Decimal
    total_liabilities: Decimal
    shareholders_equity: Decimal
    cash_and_equivalents: Decimal
    accounts_receivable: Decimal
    inventory: Decimal
    accounts_payable: Decimal
    short_term_debt: Decimal
    long_term_debt: Decimal
    
    # 損益表項目
    revenue: Decimal
    cost_of_revenue: Decimal
    gross_profit: Decimal
    operating_expenses: Decimal
    operating_income: Decimal
    ebitda: Decimal
    interest_expense: Decimal
    pretax_income: Decimal
    tax_expense: Decimal
    net_income: Decimal
    eps: Decimal
    
    # 現金流量表項目
    operating_cash_flow: Decimal
    investing_cash_flow: Decimal
    financing_cash_flow: Decimal
    free_cash_flow: Decimal
    capex: Decimal


@dataclass
class FinancialRatios:
    """財務比率計算結果"""
    # 財務結構比率
    debt_to_asset_ratio: float
    debt_to_equity_ratio: float
    equity_ratio: float
    long_term_debt_to_equity: float
    
    # 償債能力比率
    current_ratio: float
    quick_ratio: float
    cash_ratio: float
    interest_coverage_ratio: float
    debt_service_coverage_ratio: float
    
    # 經營能力比率
    receivables_turnover: float
    inventory_turnover: float
    total_asset_turnover: float
    fixed_asset_turnover: float
    days_sales_outstanding: float
    days_inventory_outstanding: float
    days_payable_outstanding: float
    cash_conversion_cycle: float
    
    # 獲利能力比率
    roa: float
    roe: float
    roic: float
    gross_margin: float
    operating_margin: float
    net_margin: float
    ebitda_margin: float
    
    # 現金流量比率
    operating_cash_ratio: float
    cash_flow_to_debt_ratio: float
    free_cash_flow_yield: float
    cash_flow_adequacy_ratio: float


class FinancialCalculator:
    """財務分析計算引擎主類別"""
    
    def __init__(self):
        self.precision = 4  # 計算精度
        
    def calculate_all_ratios(self, statements: FinancialStatements, 
                           previous_statements: Optional[FinancialStatements] = None,
                           market_cap: Optional[Decimal] = None) -> FinancialRatios:
        """
        計算所有財務比率
        
        Args:
            statements: 當期財務報表
            previous_statements: 前期財務報表（用於計算周轉率）
            market_cap: 市值（用於計算市場價值比率）
        
        Returns:
            FinancialRatios: 完整的財務比率結果
        """
        logger.calculation_log(
            company_id="calculating", 
            calculation_type="all_ratios",
            duration=0,
            success=False
        )
        
        try:
            # 計算各類比率
            structure_ratios = self._calculate_structure_ratios(statements)
            liquidity_ratios = self._calculate_liquidity_ratios(statements)
            efficiency_ratios = self._calculate_efficiency_ratios(statements, previous_statements)
            profitability_ratios = self._calculate_profitability_ratios(statements)
            cash_flow_ratios = self._calculate_cash_flow_ratios(statements)
            
            # 合併所有比率結果
            ratios = FinancialRatios(
                # 財務結構比率
                debt_to_asset_ratio=structure_ratios['debt_to_asset_ratio'],
                debt_to_equity_ratio=structure_ratios['debt_to_equity_ratio'],
                equity_ratio=structure_ratios['equity_ratio'],
                long_term_debt_to_equity=structure_ratios['long_term_debt_to_equity'],
                
                # 償債能力比率
                current_ratio=liquidity_ratios['current_ratio'],
                quick_ratio=liquidity_ratios['quick_ratio'],
                cash_ratio=liquidity_ratios['cash_ratio'],
                interest_coverage_ratio=liquidity_ratios['interest_coverage_ratio'],
                debt_service_coverage_ratio=liquidity_ratios['debt_service_coverage_ratio'],
                
                # 經營能力比率
                receivables_turnover=efficiency_ratios['receivables_turnover'],
                inventory_turnover=efficiency_ratios['inventory_turnover'],
                total_asset_turnover=efficiency_ratios['total_asset_turnover'],
                fixed_asset_turnover=efficiency_ratios['fixed_asset_turnover'],
                days_sales_outstanding=efficiency_ratios['days_sales_outstanding'],
                days_inventory_outstanding=efficiency_ratios['days_inventory_outstanding'],
                days_payable_outstanding=efficiency_ratios['days_payable_outstanding'],
                cash_conversion_cycle=efficiency_ratios['cash_conversion_cycle'],
                
                # 獲利能力比率
                roa=profitability_ratios['roa'],
                roe=profitability_ratios['roe'],
                roic=profitability_ratios['roic'],
                gross_margin=profitability_ratios['gross_margin'],
                operating_margin=profitability_ratios['operating_margin'],
                net_margin=profitability_ratios['net_margin'],
                ebitda_margin=profitability_ratios['ebitda_margin'],
                
                # 現金流量比率
                operating_cash_ratio=cash_flow_ratios['operating_cash_ratio'],
                cash_flow_to_debt_ratio=cash_flow_ratios['cash_flow_to_debt_ratio'],
                free_cash_flow_yield=cash_flow_ratios['free_cash_flow_yield'],
                cash_flow_adequacy_ratio=cash_flow_ratios['cash_flow_adequacy_ratio']
            )
            
            logger.calculation_log(
                company_id="calculated",
                calculation_type="all_ratios",
                duration=0,
                success=True,
                ratios_count=len(ratios.__dict__)
            )
            
            return ratios
            
        except Exception as e:
            logger.error(f"財務比率計算失敗: {e}")
            raise
    
    def _calculate_structure_ratios(self, statements: FinancialStatements) -> Dict[str, float]:
        """計算財務結構比率"""
        try:
            total_debt = statements.short_term_debt + statements.long_term_debt
            
            return {
                'debt_to_asset_ratio': self._safe_divide(
                    statements.total_liabilities, 
                    statements.total_assets
                ),
                'debt_to_equity_ratio': self._safe_divide(
                    total_debt,
                    statements.shareholders_equity
                ),
                'equity_ratio': self._safe_divide(
                    statements.shareholders_equity,
                    statements.total_assets
                ),
                'long_term_debt_to_equity': self._safe_divide(
                    statements.long_term_debt,
                    statements.shareholders_equity
                )
            }
        except Exception as e:
            logger.warning(f"財務結構比率計算警告: {e}")
            return self._default_structure_ratios()
    
    def _calculate_liquidity_ratios(self, statements: FinancialStatements) -> Dict[str, float]:
        """計算償債能力比率"""
        try:
            quick_assets = (statements.current_assets - 
                          statements.inventory)
            
            return {
                'current_ratio': self._safe_divide(
                    statements.current_assets,
                    statements.current_liabilities
                ),
                'quick_ratio': self._safe_divide(
                    quick_assets,
                    statements.current_liabilities
                ),
                'cash_ratio': self._safe_divide(
                    statements.cash_and_equivalents,
                    statements.current_liabilities
                ),
                'interest_coverage_ratio': self._safe_divide(
                    statements.operating_income,
                    statements.interest_expense
                ),
                'debt_service_coverage_ratio': self._safe_divide(
                    statements.operating_cash_flow,
                    statements.interest_expense + statements.short_term_debt
                )
            }
        except Exception as e:
            logger.warning(f"償債能力比率計算警告: {e}")
            return self._default_liquidity_ratios()
    
    def _calculate_efficiency_ratios(self, statements: FinancialStatements,
                                   previous_statements: Optional[FinancialStatements]) -> Dict[str, float]:
        """計算經營能力比率"""
        try:
            # 計算平均值（如果有前期資料）
            if previous_statements:
                avg_receivables = (statements.accounts_receivable + 
                                 previous_statements.accounts_receivable) / 2
                avg_inventory = (statements.inventory + previous_statements.inventory) / 2
                avg_payables = (statements.accounts_payable + 
                              previous_statements.accounts_payable) / 2
                avg_total_assets = (statements.total_assets + 
                                  previous_statements.total_assets) / 2
                avg_ppe = ((statements.total_assets - statements.current_assets) +
                          (previous_statements.total_assets - previous_statements.current_assets)) / 2
            else:
                # 使用當期數據
                avg_receivables = statements.accounts_receivable
                avg_inventory = statements.inventory
                avg_payables = statements.accounts_payable
                avg_total_assets = statements.total_assets
                avg_ppe = statements.total_assets - statements.current_assets
            
            # 計算周轉率
            receivables_turnover = self._safe_divide(statements.revenue, avg_receivables)
            inventory_turnover = self._safe_divide(statements.cost_of_revenue, avg_inventory)
            payables_turnover = self._safe_divide(statements.cost_of_revenue, avg_payables)
            
            # 計算天數
            dso = 365 / receivables_turnover if receivables_turnover > 0 else 0
            dio = 365 / inventory_turnover if inventory_turnover > 0 else 0
            dpo = 365 / payables_turnover if payables_turnover > 0 else 0
            
            return {
                'receivables_turnover': receivables_turnover,
                'inventory_turnover': inventory_turnover,
                'total_asset_turnover': self._safe_divide(statements.revenue, avg_total_assets),
                'fixed_asset_turnover': self._safe_divide(statements.revenue, avg_ppe),
                'days_sales_outstanding': dso,
                'days_inventory_outstanding': dio,
                'days_payable_outstanding': dpo,
                'cash_conversion_cycle': dso + dio - dpo
            }
        except Exception as e:
            logger.warning(f"經營能力比率計算警告: {e}")
            return self._default_efficiency_ratios()
    
    def _calculate_profitability_ratios(self, statements: FinancialStatements) -> Dict[str, float]:
        """計算獲利能力比率"""
        try:
            invested_capital = statements.shareholders_equity + statements.long_term_debt
            tax_rate = self._estimate_tax_rate(statements)
            nopat = float(statements.operating_income) * (1 - tax_rate)
            
            return {
                'roa': self._safe_divide(statements.net_income, statements.total_assets),
                'roe': self._safe_divide(statements.net_income, statements.shareholders_equity),
                'roic': self._safe_divide(nopat, invested_capital),
                'gross_margin': self._safe_divide(statements.gross_profit, statements.revenue),
                'operating_margin': self._safe_divide(statements.operating_income, statements.revenue),
                'net_margin': self._safe_divide(statements.net_income, statements.revenue),
                'ebitda_margin': self._safe_divide(statements.ebitda, statements.revenue)
            }
        except Exception as e:
            logger.warning(f"獲利能力比率計算警告: {e}")
            return self._default_profitability_ratios()
    
    def _calculate_cash_flow_ratios(self, statements: FinancialStatements) -> Dict[str, float]:
        """計算現金流量比率"""
        try:
            total_debt = statements.short_term_debt + statements.long_term_debt
            
            return {
                'operating_cash_ratio': self._safe_divide(
                    statements.operating_cash_flow,
                    statements.current_liabilities
                ),
                'cash_flow_to_debt_ratio': self._safe_divide(
                    statements.operating_cash_flow,
                    total_debt
                ),
                'free_cash_flow_yield': self._safe_divide(
                    statements.free_cash_flow,
                    statements.total_assets
                ),
                'cash_flow_adequacy_ratio': self._safe_divide(
                    statements.free_cash_flow,
                    statements.capex + statements.current_liabilities
                )
            }
        except Exception as e:
            logger.warning(f"現金流量比率計算警告: {e}")
            return self._default_cash_flow_ratios()
    
    def evaluate_financial_health(self, ratios: FinancialRatios) -> Tuple[FinancialHealth, Dict[str, str]]:
        """
        評估財務健康度
        
        Args:
            ratios: 財務比率結果
            
        Returns:
            Tuple[FinancialHealth, Dict[str, str]]: 健康度等級和詳細評估
        """
        scores = []
        details = {}
        
        # 償債能力評分 (30%)
        liquidity_score = self._evaluate_liquidity(ratios)
        scores.append(liquidity_score * 0.3)
        details['償債能力'] = self._get_liquidity_assessment(ratios)
        
        # 獲利能力評分 (25%)
        profitability_score = self._evaluate_profitability(ratios)
        scores.append(profitability_score * 0.25)
        details['獲利能力'] = self._get_profitability_assessment(ratios)
        
        # 經營效率評分 (25%)
        efficiency_score = self._evaluate_efficiency(ratios)
        scores.append(efficiency_score * 0.25)
        details['經營效率'] = self._get_efficiency_assessment(ratios)
        
        # 財務結構評分 (20%)
        structure_score = self._evaluate_structure(ratios)
        scores.append(structure_score * 0.2)
        details['財務結構'] = self._get_structure_assessment(ratios)
        
        # 計算綜合評分
        total_score = sum(scores)
        
        # 決定健康度等級
        if total_score >= 80:
            health = FinancialHealth.EXCELLENT
        elif total_score >= 65:
            health = FinancialHealth.GOOD
        elif total_score >= 50:
            health = FinancialHealth.FAIR
        elif total_score >= 35:
            health = FinancialHealth.POOR
        else:
            health = FinancialHealth.CRITICAL
        
        details['綜合評分'] = f"{total_score:.1f}/100"
        
        return health, details
    
    def _safe_divide(self, numerator, denominator, default=0.0) -> float:
        """安全除法，避免除零錯誤"""
        try:
            if denominator == 0 or denominator is None:
                return default
            result = float(numerator) / float(denominator)
            return round(result, self.precision)
        except (TypeError, ValueError, ZeroDivisionError):
            return default
    
    def _estimate_tax_rate(self, statements: FinancialStatements) -> float:
        """估算稅率"""
        if statements.pretax_income > 0:
            return float(statements.tax_expense) / float(statements.pretax_income)
        return 0.25  # 預設稅率25%
    
    # 預設值方法
    def _default_structure_ratios(self) -> Dict[str, float]:
        return {
            'debt_to_asset_ratio': 0.0,
            'debt_to_equity_ratio': 0.0,
            'equity_ratio': 1.0,
            'long_term_debt_to_equity': 0.0
        }
    
    def _default_liquidity_ratios(self) -> Dict[str, float]:
        return {
            'current_ratio': 0.0,
            'quick_ratio': 0.0,
            'cash_ratio': 0.0,
            'interest_coverage_ratio': 0.0,
            'debt_service_coverage_ratio': 0.0
        }
    
    def _default_efficiency_ratios(self) -> Dict[str, float]:
        return {
            'receivables_turnover': 0.0,
            'inventory_turnover': 0.0,
            'total_asset_turnover': 0.0,
            'fixed_asset_turnover': 0.0,
            'days_sales_outstanding': 0.0,
            'days_inventory_outstanding': 0.0,
            'days_payable_outstanding': 0.0,
            'cash_conversion_cycle': 0.0
        }
    
    def _default_profitability_ratios(self) -> Dict[str, float]:
        return {
            'roa': 0.0,
            'roe': 0.0,
            'roic': 0.0,
            'gross_margin': 0.0,
            'operating_margin': 0.0,
            'net_margin': 0.0,
            'ebitda_margin': 0.0
        }
    
    def _default_cash_flow_ratios(self) -> Dict[str, float]:
        return {
            'operating_cash_ratio': 0.0,
            'cash_flow_to_debt_ratio': 0.0,
            'free_cash_flow_yield': 0.0,
            'cash_flow_adequacy_ratio': 0.0
        }
    
    # 評估方法
    def _evaluate_liquidity(self, ratios: FinancialRatios) -> float:
        """評估償債能力 (0-100分)"""
        score = 0
        
        # 流動比率評分
        if ratios.current_ratio >= 2.0:
            score += 25
        elif ratios.current_ratio >= 1.5:
            score += 20
        elif ratios.current_ratio >= 1.0:
            score += 15
        elif ratios.current_ratio >= 0.8:
            score += 10
        
        # 速動比率評分
        if ratios.quick_ratio >= 1.5:
            score += 25
        elif ratios.quick_ratio >= 1.0:
            score += 20
        elif ratios.quick_ratio >= 0.8:
            score += 15
        elif ratios.quick_ratio >= 0.6:
            score += 10
        
        # 利息保障倍數評分
        if ratios.interest_coverage_ratio >= 10:
            score += 25
        elif ratios.interest_coverage_ratio >= 5:
            score += 20
        elif ratios.interest_coverage_ratio >= 2.5:
            score += 15
        elif ratios.interest_coverage_ratio >= 1.5:
            score += 10
        
        # 現金比率評分
        if ratios.cash_ratio >= 0.3:
            score += 25
        elif ratios.cash_ratio >= 0.2:
            score += 20
        elif ratios.cash_ratio >= 0.1:
            score += 15
        elif ratios.cash_ratio >= 0.05:
            score += 10
        
        return score
    
    def _evaluate_profitability(self, ratios: FinancialRatios) -> float:
        """評估獲利能力 (0-100分)"""
        score = 0
        
        # ROE評分
        if ratios.roe >= 0.15:
            score += 30
        elif ratios.roe >= 0.12:
            score += 25
        elif ratios.roe >= 0.08:
            score += 20
        elif ratios.roe >= 0.05:
            score += 15
        elif ratios.roe >= 0:
            score += 10
        
        # ROA評分
        if ratios.roa >= 0.08:
            score += 25
        elif ratios.roa >= 0.06:
            score += 20
        elif ratios.roa >= 0.04:
            score += 15
        elif ratios.roa >= 0.02:
            score += 10
        elif ratios.roa >= 0:
            score += 5
        
        # 淨利率評分
        if ratios.net_margin >= 0.1:
            score += 25
        elif ratios.net_margin >= 0.08:
            score += 20
        elif ratios.net_margin >= 0.05:
            score += 15
        elif ratios.net_margin >= 0.03:
            score += 10
        elif ratios.net_margin >= 0:
            score += 5
        
        # 毛利率評分
        if ratios.gross_margin >= 0.4:
            score += 20
        elif ratios.gross_margin >= 0.3:
            score += 15
        elif ratios.gross_margin >= 0.2:
            score += 10
        elif ratios.gross_margin >= 0.1:
            score += 5
        
        return score
    
    def _evaluate_efficiency(self, ratios: FinancialRatios) -> float:
        """評估經營效率 (0-100分)"""
        score = 0
        
        # 總資產周轉率評分
        if ratios.total_asset_turnover >= 1.5:
            score += 30
        elif ratios.total_asset_turnover >= 1.0:
            score += 25
        elif ratios.total_asset_turnover >= 0.8:
            score += 20
        elif ratios.total_asset_turnover >= 0.6:
            score += 15
        elif ratios.total_asset_turnover >= 0.4:
            score += 10
        
        # 應收帳款周轉天數評分
        if ratios.days_sales_outstanding <= 30:
            score += 25
        elif ratios.days_sales_outstanding <= 45:
            score += 20
        elif ratios.days_sales_outstanding <= 60:
            score += 15
        elif ratios.days_sales_outstanding <= 90:
            score += 10
        elif ratios.days_sales_outstanding <= 120:
            score += 5
        
        # 存貨周轉天數評分
        if ratios.days_inventory_outstanding <= 30:
            score += 25
        elif ratios.days_inventory_outstanding <= 60:
            score += 20
        elif ratios.days_inventory_outstanding <= 90:
            score += 15
        elif ratios.days_inventory_outstanding <= 120:
            score += 10
        elif ratios.days_inventory_outstanding <= 180:
            score += 5
        
        # 現金轉換週期評分
        if ratios.cash_conversion_cycle <= 30:
            score += 20
        elif ratios.cash_conversion_cycle <= 60:
            score += 15
        elif ratios.cash_conversion_cycle <= 90:
            score += 10
        elif ratios.cash_conversion_cycle <= 120:
            score += 5
        
        return score
    
    def _evaluate_structure(self, ratios: FinancialRatios) -> float:
        """評估財務結構 (0-100分)"""
        score = 0
        
        # 負債比率評分
        if ratios.debt_to_asset_ratio <= 0.3:
            score += 40
        elif ratios.debt_to_asset_ratio <= 0.5:
            score += 30
        elif ratios.debt_to_asset_ratio <= 0.6:
            score += 20
        elif ratios.debt_to_asset_ratio <= 0.7:
            score += 10
        elif ratios.debt_to_asset_ratio <= 0.8:
            score += 5
        
        # 權益比率評分
        if ratios.equity_ratio >= 0.7:
            score += 30
        elif ratios.equity_ratio >= 0.5:
            score += 25
        elif ratios.equity_ratio >= 0.4:
            score += 20
        elif ratios.equity_ratio >= 0.3:
            score += 15
        elif ratios.equity_ratio >= 0.2:
            score += 10
        
        # 負債權益比評分
        if ratios.debt_to_equity_ratio <= 0.5:
            score += 30
        elif ratios.debt_to_equity_ratio <= 1.0:
            score += 25
        elif ratios.debt_to_equity_ratio <= 1.5:
            score += 20
        elif ratios.debt_to_equity_ratio <= 2.0:
            score += 15
        elif ratios.debt_to_equity_ratio <= 3.0:
            score += 10
        
        return score
    
    # 評估描述方法
    def _get_liquidity_assessment(self, ratios: FinancialRatios) -> str:
        if ratios.current_ratio >= 2.0 and ratios.quick_ratio >= 1.0:
            return "償債能力優秀，短期債務償還無虞"
        elif ratios.current_ratio >= 1.5 and ratios.quick_ratio >= 0.8:
            return "償債能力良好，流動性充足"
        elif ratios.current_ratio >= 1.0:
            return "償債能力普通，需注意現金流管理"
        else:
            return "償債能力不佳，存在流動性風險"
    
    def _get_profitability_assessment(self, ratios: FinancialRatios) -> str:
        if ratios.roe >= 0.15 and ratios.net_margin >= 0.08:
            return "獲利能力優秀，投資報酬率高"
        elif ratios.roe >= 0.08 and ratios.net_margin >= 0.05:
            return "獲利能力良好，營運效益佳"
        elif ratios.roe >= 0.05:
            return "獲利能力普通，仍有改善空間"
        else:
            return "獲利能力不佳，需檢討營運策略"
    
    def _get_efficiency_assessment(self, ratios: FinancialRatios) -> str:
        if ratios.total_asset_turnover >= 1.0 and ratios.cash_conversion_cycle <= 60:
            return "經營效率優秀，資產運用效果佳"
        elif ratios.total_asset_turnover >= 0.8:
            return "經營效率良好，資產周轉正常"
        elif ratios.total_asset_turnover >= 0.6:
            return "經營效率普通，可優化資產運用"
        else:
            return "經營效率不佳，資產運用效率低"
    
    def _get_structure_assessment(self, ratios: FinancialRatios) -> str:
        if ratios.debt_to_asset_ratio <= 0.3 and ratios.equity_ratio >= 0.7:
            return "財務結構優秀，財務風險低"
        elif ratios.debt_to_asset_ratio <= 0.5:
            return "財務結構良好，負債水準合理"
        elif ratios.debt_to_asset_ratio <= 0.7:
            return "財務結構普通，需控制負債成長"
        else:
            return "財務結構不佳，負債比重過高"