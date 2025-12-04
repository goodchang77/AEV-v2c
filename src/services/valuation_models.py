"""
企業評價模型
Valuation Models

實現DCF、DDM、相對評價等多種企業評價方法
"""

from typing import Dict, List, Optional, Tuple, Union
from decimal import Decimal, ROUND_HALF_UP
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
import math

from src.core.logging import get_logger

logger = get_logger("valuation_models")


class ValuationMethod(Enum):
    """評價方法類型"""
    DCF = "現金流折現法"
    DDM = "股利折現法"
    PE = "本益比法"
    PB = "股價淨值比法"
    EV_EBITDA = "企業價值倍數法"
    ASSET = "資產重置法"


@dataclass
class DCFParameters:
    """DCF評價參數"""
    # 預測期參數
    forecast_years: int = 5
    revenue_growth_rates: List[float] = field(default_factory=list)
    
    # 獲利能力參數
    ebitda_margin: float = 0.15
    depreciation_rate: float = 0.05
    tax_rate: float = 0.25
    
    # 投資需求參數
    capex_rate: float = 0.04  # 資本支出佔營收比率
    working_capital_rate: float = 0.02  # 營運資金增加率
    
    # 折現參數
    discount_rate: float = 0.10
    terminal_growth_rate: float = 0.03
    
    # 風險調整參數
    country_risk_premium: float = 0.02
    company_risk_premium: float = 0.01


@dataclass
class DDMParameters:
    """DDM股利折現模型參數"""
    dividend_growth_rate: float = 0.05
    payout_ratio: float = 0.6
    discount_rate: float = 0.10
    stable_growth_rate: float = 0.03


@dataclass
class RelativeValuationParameters:
    """相對評價參數"""
    peer_companies: List[str] = field(default_factory=list)
    valuation_multiples: List[str] = field(default_factory=lambda: ['PE', 'PB', 'EV_EBITDA'])
    adjustment_factors: Dict[str, float] = field(default_factory=dict)


@dataclass
class ValuationResult:
    """評價結果"""
    valuation_method: ValuationMethod
    fair_value_per_share: float
    current_price: Optional[float] = None
    upside_downside: Optional[float] = None
    
    # 詳細結果
    enterprise_value: Optional[float] = None
    equity_value: Optional[float] = None
    shares_outstanding: Optional[int] = None
    
    # DCF特定結果
    dcf_value: Optional[float] = None
    terminal_value: Optional[float] = None
    terminal_value_percentage: Optional[float] = None
    
    # 敏感性分析
    sensitivity_analysis: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # 假設與參數
    assumptions: Dict[str, Union[float, List[float]]] = field(default_factory=dict)
    
    # 計算明細
    calculation_details: Dict[str, Union[float, List[float]]] = field(default_factory=dict)


class DCFValuationModel:
    """現金流折現評價模型"""
    
    def __init__(self, parameters: DCFParameters):
        self.params = parameters
        
    def calculate_enterprise_value(self, base_revenue: float, 
                                 net_debt: float = 0,
                                 shares_outstanding: int = 1000000) -> ValuationResult:
        """
        計算企業價值
        
        Args:
            base_revenue: 基期營收
            net_debt: 淨負債
            shares_outstanding: 流通股數
            
        Returns:
            ValuationResult: 評價結果
        """
        logger.calculation_log(
            company_id="dcf_valuation",
            calculation_type="DCF",
            duration=0,
            success=False
        )
        
        try:
            # 1. 預測自由現金流
            projected_fcf = self._project_free_cash_flows(base_revenue)
            
            # 2. 計算現值
            pv_fcf = self._calculate_present_values(projected_fcf)
            
            # 3. 計算終值
            terminal_fcf = projected_fcf[-1] * (1 + self.params.terminal_growth_rate)
            terminal_value = terminal_fcf / (self.params.discount_rate - self.params.terminal_growth_rate)
            pv_terminal_value = terminal_value / ((1 + self.params.discount_rate) ** self.params.forecast_years)
            
            # 4. 計算企業價值
            enterprise_value = sum(pv_fcf) + pv_terminal_value
            
            # 5. 計算股權價值
            equity_value = enterprise_value - net_debt
            fair_value_per_share = equity_value / shares_outstanding
            
            # 6. 終值占比
            terminal_value_percentage = (pv_terminal_value / enterprise_value) * 100
            
            result = ValuationResult(
                valuation_method=ValuationMethod.DCF,
                fair_value_per_share=fair_value_per_share,
                enterprise_value=enterprise_value,
                equity_value=equity_value,
                shares_outstanding=shares_outstanding,
                dcf_value=sum(pv_fcf),
                terminal_value=pv_terminal_value,
                terminal_value_percentage=terminal_value_percentage,
                assumptions={
                    'discount_rate': self.params.discount_rate,
                    'terminal_growth_rate': self.params.terminal_growth_rate,
                    'revenue_growth_rates': self.params.revenue_growth_rates,
                    'ebitda_margin': self.params.ebitda_margin,
                    'tax_rate': self.params.tax_rate
                },
                calculation_details={
                    'projected_fcf': projected_fcf,
                    'pv_fcf': pv_fcf,
                    'terminal_fcf': terminal_fcf,
                    'base_revenue': base_revenue
                }
            )
            
            logger.calculation_log(
                company_id="dcf_calculated",
                calculation_type="DCF",
                duration=0,
                success=True,
                fair_value=fair_value_per_share,
                enterprise_value=enterprise_value
            )
            
            return result
            
        except Exception as e:
            logger.error(f"DCF評價計算失敗: {e}")
            raise
    
    def _project_free_cash_flows(self, base_revenue: float) -> List[float]:
        """預測自由現金流"""
        fcf_projections = []
        current_revenue = base_revenue
        
        for year in range(self.params.forecast_years):
            # 使用指定的成長率或預設值
            if year < len(self.params.revenue_growth_rates):
                growth_rate = self.params.revenue_growth_rates[year]
            else:
                # 使用遞減成長率
                growth_rate = max(0.02, 0.15 * (0.8 ** year))
            
            # 預測營收
            projected_revenue = current_revenue * (1 + growth_rate)
            
            # 計算EBITDA
            ebitda = projected_revenue * self.params.ebitda_margin
            
            # 計算折舊攤銷
            depreciation = projected_revenue * self.params.depreciation_rate
            
            # 計算EBIT
            ebit = ebitda - depreciation
            
            # 計算稅後營業利益 (NOPAT)
            nopat = ebit * (1 - self.params.tax_rate)
            
            # 計算資本支出
            capex = projected_revenue * self.params.capex_rate
            
            # 計算營運資金變動
            wc_investment = (projected_revenue - current_revenue) * self.params.working_capital_rate
            
            # 計算自由現金流
            fcf = nopat + depreciation - capex - wc_investment
            fcf_projections.append(fcf)
            
            current_revenue = projected_revenue
        
        return fcf_projections
    
    def _calculate_present_values(self, cash_flows: List[float]) -> List[float]:
        """計算現金流現值"""
        present_values = []
        
        for year, cf in enumerate(cash_flows, 1):
            pv = cf / ((1 + self.params.discount_rate) ** year)
            present_values.append(pv)
        
        return present_values
    
    def perform_sensitivity_analysis(self, base_revenue: float,
                                   net_debt: float = 0,
                                   shares_outstanding: int = 1000000) -> Dict[str, Dict[str, float]]:
        """
        敏感性分析
        
        測試關鍵參數變動對評價結果的影響
        """
        base_result = self.calculate_enterprise_value(base_revenue, net_debt, shares_outstanding)
        base_price = base_result.fair_value_per_share
        
        sensitivity_results = {}
        
        # 折現率敏感性 (-2% ~ +2%)
        discount_rates = [
            self.params.discount_rate - 0.02,
            self.params.discount_rate - 0.01,
            self.params.discount_rate,
            self.params.discount_rate + 0.01,
            self.params.discount_rate + 0.02
        ]
        
        discount_sensitivity = {}
        for rate in discount_rates:
            temp_params = self.params
            temp_params.discount_rate = rate
            temp_model = DCFValuationModel(temp_params)
            result = temp_model.calculate_enterprise_value(base_revenue, net_debt, shares_outstanding)
            change_pct = ((result.fair_value_per_share - base_price) / base_price) * 100
            discount_sensitivity[f"{rate:.1%}"] = change_pct
        
        sensitivity_results['折現率敏感性'] = discount_sensitivity
        
        # 終值成長率敏感性 (0% ~ 5%)
        terminal_rates = [0.00, 0.01, 0.02, 0.03, 0.04, 0.05]
        terminal_sensitivity = {}
        
        for rate in terminal_rates:
            temp_params = self.params
            temp_params.terminal_growth_rate = rate
            temp_model = DCFValuationModel(temp_params)
            result = temp_model.calculate_enterprise_value(base_revenue, net_debt, shares_outstanding)
            change_pct = ((result.fair_value_per_share - base_price) / base_price) * 100
            terminal_sensitivity[f"{rate:.1%}"] = change_pct
        
        sensitivity_results['終值成長率敏感性'] = terminal_sensitivity
        
        # EBITDA邊際率敏感性 (-5% ~ +5%)
        ebitda_margins = [
            self.params.ebitda_margin * 0.8,
            self.params.ebitda_margin * 0.9,
            self.params.ebitda_margin,
            self.params.ebitda_margin * 1.1,
            self.params.ebitda_margin * 1.2
        ]
        
        ebitda_sensitivity = {}
        for margin in ebitda_margins:
            temp_params = self.params
            temp_params.ebitda_margin = margin
            temp_model = DCFValuationModel(temp_params)
            result = temp_model.calculate_enterprise_value(base_revenue, net_debt, shares_outstanding)
            change_pct = ((result.fair_value_per_share - base_price) / base_price) * 100
            ebitda_sensitivity[f"{margin:.1%}"] = change_pct
        
        sensitivity_results['EBITDA邊際率敏感性'] = ebitda_sensitivity
        
        return sensitivity_results


class DDMValuationModel:
    """股利折現模型"""
    
    def __init__(self, parameters: DDMParameters):
        self.params = parameters
    
    def calculate_fair_value(self, current_dividend: float,
                           shares_outstanding: int = 1000000) -> ValuationResult:
        """
        計算股利折現模型公允價值
        
        Args:
            current_dividend: 當前每股股利
            shares_outstanding: 流通股數
            
        Returns:
            ValuationResult: 評價結果
        """
        try:
            if self.params.discount_rate <= self.params.dividend_growth_rate:
                raise ValueError("折現率必須大於股利成長率")
            
            # 高成長期 (假設5年)
            high_growth_years = 5
            pv_dividends = 0
            
            for year in range(1, high_growth_years + 1):
                future_dividend = current_dividend * ((1 + self.params.dividend_growth_rate) ** year)
                pv_dividend = future_dividend / ((1 + self.params.discount_rate) ** year)
                pv_dividends += pv_dividend
            
            # 穩定成長期終值
            dividend_year_6 = current_dividend * ((1 + self.params.dividend_growth_rate) ** (high_growth_years + 1))
            stable_dividend = dividend_year_6 * (1 + self.params.stable_growth_rate)
            terminal_value = stable_dividend / (self.params.discount_rate - self.params.stable_growth_rate)
            pv_terminal_value = terminal_value / ((1 + self.params.discount_rate) ** high_growth_years)
            
            # 每股公允價值
            fair_value_per_share = pv_dividends + pv_terminal_value
            
            result = ValuationResult(
                valuation_method=ValuationMethod.DDM,
                fair_value_per_share=fair_value_per_share,
                equity_value=fair_value_per_share * shares_outstanding,
                shares_outstanding=shares_outstanding,
                assumptions={
                    'current_dividend': current_dividend,
                    'dividend_growth_rate': self.params.dividend_growth_rate,
                    'discount_rate': self.params.discount_rate,
                    'stable_growth_rate': self.params.stable_growth_rate
                },
                calculation_details={
                    'pv_dividends': pv_dividends,
                    'terminal_value': pv_terminal_value,
                    'high_growth_years': high_growth_years
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"DDM評價計算失敗: {e}")
            raise


class RelativeValuationModel:
    """相對評價模型"""
    
    def __init__(self, parameters: RelativeValuationParameters):
        self.params = parameters
    
    def calculate_pe_valuation(self, target_eps: float,
                              peer_pe_ratios: List[float],
                              shares_outstanding: int = 1000000) -> ValuationResult:
        """
        本益比評價法
        
        Args:
            target_eps: 目標公司每股盈餘
            peer_pe_ratios: 同業本益比列表
            shares_outstanding: 流通股數
            
        Returns:
            ValuationResult: 評價結果
        """
        try:
            # 計算同業平均本益比
            peer_pe_ratios = [pe for pe in peer_pe_ratios if pe > 0]  # 過濾負值
            
            if not peer_pe_ratios:
                raise ValueError("無有效的同業本益比資料")
            
            average_pe = np.mean(peer_pe_ratios)
            median_pe = np.median(peer_pe_ratios)
            
            # 使用中位數較為保守
            applied_pe = median_pe
            
            # 風險調整
            if 'quality_adjustment' in self.params.adjustment_factors:
                applied_pe *= (1 + self.params.adjustment_factors['quality_adjustment'])
            
            # 計算公允價值
            fair_value_per_share = target_eps * applied_pe
            
            result = ValuationResult(
                valuation_method=ValuationMethod.PE,
                fair_value_per_share=fair_value_per_share,
                equity_value=fair_value_per_share * shares_outstanding,
                shares_outstanding=shares_outstanding,
                assumptions={
                    'target_eps': target_eps,
                    'peer_pe_average': average_pe,
                    'peer_pe_median': median_pe,
                    'applied_pe': applied_pe
                },
                calculation_details={
                    'peer_pe_ratios': peer_pe_ratios,
                    'pe_range': {'min': min(peer_pe_ratios), 'max': max(peer_pe_ratios)}
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"PE評價計算失敗: {e}")
            raise
    
    def calculate_pb_valuation(self, target_bvps: float,
                              peer_pb_ratios: List[float],
                              shares_outstanding: int = 1000000) -> ValuationResult:
        """
        股價淨值比評價法
        
        Args:
            target_bvps: 目標公司每股淨值
            peer_pb_ratios: 同業股價淨值比列表
            shares_outstanding: 流通股數
            
        Returns:
            ValuationResult: 評價結果
        """
        try:
            # 過濾異常值
            peer_pb_ratios = [pb for pb in peer_pb_ratios if 0.1 <= pb <= 10.0]
            
            if not peer_pb_ratios:
                raise ValueError("無有效的同業股價淨值比資料")
            
            average_pb = np.mean(peer_pb_ratios)
            median_pb = np.median(peer_pb_ratios)
            
            # 使用中位數
            applied_pb = median_pb
            
            # 風險調整
            if 'roe_adjustment' in self.params.adjustment_factors:
                applied_pb *= (1 + self.params.adjustment_factors['roe_adjustment'])
            
            # 計算公允價值
            fair_value_per_share = target_bvps * applied_pb
            
            result = ValuationResult(
                valuation_method=ValuationMethod.PB,
                fair_value_per_share=fair_value_per_share,
                equity_value=fair_value_per_share * shares_outstanding,
                shares_outstanding=shares_outstanding,
                assumptions={
                    'target_bvps': target_bvps,
                    'peer_pb_average': average_pb,
                    'peer_pb_median': median_pb,
                    'applied_pb': applied_pb
                },
                calculation_details={
                    'peer_pb_ratios': peer_pb_ratios,
                    'pb_range': {'min': min(peer_pb_ratios), 'max': max(peer_pb_ratios)}
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"PB評價計算失敗: {e}")
            raise


class ValuationEngine:
    """整合評價引擎"""
    
    def __init__(self):
        self.results = []
    
    def comprehensive_valuation(self, 
                              company_data: Dict,
                              peer_data: Optional[Dict] = None,
                              current_stock_price: Optional[float] = None) -> Dict[str, ValuationResult]:
        """
        綜合評價分析
        
        Args:
            company_data: 目標公司財務數據
            peer_data: 同業比較數據
            current_stock_price: 當前股價
            
        Returns:
            Dict[str, ValuationResult]: 各種評價方法的結果
        """
        results = {}
        
        try:
            # 1. DCF評價
            if all(k in company_data for k in ['revenue', 'net_debt', 'shares_outstanding']):
                dcf_params = DCFParameters(
                    revenue_growth_rates=company_data.get('revenue_growth_rates', [0.1, 0.08, 0.06, 0.05, 0.04]),
                    ebitda_margin=company_data.get('ebitda_margin', 0.15),
                    discount_rate=company_data.get('discount_rate', 0.10),
                    terminal_growth_rate=company_data.get('terminal_growth_rate', 0.03)
                )
                
                dcf_model = DCFValuationModel(dcf_params)
                dcf_result = dcf_model.calculate_enterprise_value(
                    base_revenue=company_data['revenue'],
                    net_debt=company_data.get('net_debt', 0),
                    shares_outstanding=company_data['shares_outstanding']
                )
                
                # 敏感性分析
                dcf_result.sensitivity_analysis = dcf_model.perform_sensitivity_analysis(
                    base_revenue=company_data['revenue'],
                    net_debt=company_data.get('net_debt', 0),
                    shares_outstanding=company_data['shares_outstanding']
                )
                
                results['DCF'] = dcf_result
            
            # 2. DDM評價（如果有股利數據）
            if 'dividend_per_share' in company_data:
                ddm_params = DDMParameters(
                    dividend_growth_rate=company_data.get('dividend_growth_rate', 0.05),
                    discount_rate=company_data.get('discount_rate', 0.10)
                )
                
                ddm_model = DDMValuationModel(ddm_params)
                ddm_result = ddm_model.calculate_fair_value(
                    current_dividend=company_data['dividend_per_share'],
                    shares_outstanding=company_data['shares_outstanding']
                )
                
                results['DDM'] = ddm_result
            
            # 3. 相對評價（如果有同業數據）
            if peer_data:
                rel_params = RelativeValuationParameters()
                rel_model = RelativeValuationModel(rel_params)
                
                # PE評價
                if 'eps' in company_data and 'peer_pe_ratios' in peer_data:
                    pe_result = rel_model.calculate_pe_valuation(
                        target_eps=company_data['eps'],
                        peer_pe_ratios=peer_data['peer_pe_ratios'],
                        shares_outstanding=company_data['shares_outstanding']
                    )
                    results['PE'] = pe_result
                
                # PB評價
                if 'book_value_per_share' in company_data and 'peer_pb_ratios' in peer_data:
                    pb_result = rel_model.calculate_pb_valuation(
                        target_bvps=company_data['book_value_per_share'],
                        peer_pb_ratios=peer_data['peer_pb_ratios'],
                        shares_outstanding=company_data['shares_outstanding']
                    )
                    results['PB'] = pb_result
            
            # 4. 計算上漲下跌空間
            if current_stock_price:
                for method, result in results.items():
                    result.current_price = current_stock_price
                    result.upside_downside = ((result.fair_value_per_share - current_stock_price) 
                                            / current_stock_price) * 100
            
            logger.calculation_log(
                company_id="comprehensive_valuation",
                calculation_type="COMPREHENSIVE",
                duration=0,
                success=True,
                methods_count=len(results)
            )
            
            return results
            
        except Exception as e:
            logger.error(f"綜合評價計算失敗: {e}")
            raise
    
    def calculate_weighted_fair_value(self, results: Dict[str, ValuationResult],
                                    weights: Optional[Dict[str, float]] = None) -> float:
        """
        計算加權公允價值
        
        Args:
            results: 各種評價方法結果
            weights: 各方法權重（預設相等權重）
            
        Returns:
            float: 加權公允價值
        """
        if not results:
            return 0.0
        
        if weights is None:
            # 預設相等權重
            weights = {method: 1.0/len(results) for method in results.keys()}
        
        weighted_value = 0.0
        total_weight = 0.0
        
        for method, result in results.items():
            if method in weights:
                weight = weights[method]
                weighted_value += result.fair_value_per_share * weight
                total_weight += weight
        
        return weighted_value / total_weight if total_weight > 0 else 0.0