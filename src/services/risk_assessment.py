# src/services/risk_assessment.py
from dataclasses import dataclass
from typing import Dict, List
from enum import Enum

class RiskLevel(Enum):
    """風險等級"""
    LOW = "低風險"
    MEDIUM = "中等風險"
    HIGH = "高風險"
    CRITICAL = "極高風險"

@dataclass
class AltmanZScoreResult:
    """Altman Z-Score結果"""
    z_score: float
    risk_level: RiskLevel
    probability_of_bankruptcy: float
    components: Dict[str, float]  # X1-X5五個組成要素
    interpretation: str

class RiskAssessmentEngine:
    """
    風險評估引擎
    
    實作CLAUDE.md規格476-526行:
    - Altman Z-Score破產預測
    - 流動性風險評估
    - 獲利能力趨勢分析
    - 槓桿風險評估
    """
    
    def __init__(self, db_session):
        self.db = db_session
    
    def assess_financial_distress(self, company_id: str) -> Dict:
        """
        評估財務危機風險 (Altman Z-Score)
        
        公式: Z = 1.2X1 + 1.4X2 + 3.3X3 + 0.6X4 + 1.0X5
        
        X1 = 營運資金 / 總資產
        X2 = 保留盈餘 / 總資產
        X3 = 息前稅前盈餘 / 總資產
        X4 = 股東權益市值 / 總負債帳面價值
        X5 = 銷售額 / 總資產
        """
        # 從資料庫取得財務數據
        financials = self._get_latest_financials(company_id)
        
        # 計算五個組成要素
        X1 = (financials.current_assets - financials.current_liabilities) / financials.total_assets
        X2 = financials.retained_earnings / financials.total_assets
        X3 = financials.ebit / financials.total_assets
        X4 = financials.market_cap / financials.total_liabilities
        X5 = financials.revenue / financials.total_assets
        
        # 計算Z-Score
        z_score = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5
        
        # 評估風險等級
        if z_score > 2.99:
            risk_level = RiskLevel.LOW
            probability = 0.02  # 2%破產機率
        elif z_score > 1.81:
            risk_level = RiskLevel.MEDIUM
            probability = 0.15  # 15%破產機率
        else:
            risk_level = RiskLevel.HIGH
            probability = 0.80  # 80%破產機率
        
        return {
            "z_score": round(z_score, 2),
            "risk_level": risk_level.value,
            "probability_of_bankruptcy": probability,
            "components": {
                "X1_working_capital_ratio": round(X1, 4),
                "X2_retained_earnings_ratio": round(X2, 4),
                "X3_ebit_ratio": round(X3, 4),
                "X4_market_to_book_leverage": round(X4, 4),
                "X5_asset_turnover": round(X5, 4)
            },
            "interpretation": self._interpret_z_score(z_score)
        }
    
    def assess_liquidity_risk(self, company_id: str) -> Dict:
        """
        評估流動性風險
        
        評估指標:
        1. 流動比率 (Current Ratio) = 流動資產 / 流動負債
        2. 速動比率 (Quick Ratio) = (流動資產-存貨) / 流動負債
        3. 現金比率 (Cash Ratio) = 現金及約當現金 / 流動負債
        4. 現金轉換週期 (Cash Conversion Cycle)
        """
        financials = self._get_latest_financials(company_id)
        ratios = self._get_latest_ratios(company_id)
        
        # 計算流動性指標
        current_ratio = financials.current_assets / financials.current_liabilities
        quick_ratio = (financials.current_assets - financials.inventory) / financials.current_liabilities
        cash_ratio = financials.cash_and_equivalents / financials.current_liabilities
        
        # 現金轉換週期 = DSO + DIO - DPO
        dso = 365 / ratios.receivables_turnover  # 應收帳款週轉天數
        dio = 365 / ratios.inventory_turnover    # 存貨週轉天數
        dpo = 365 / ratios.payables_turnover     # 應付帳款週轉天數
        ccc = dso + dio - dpo
        
        # 流動性評分 (0-100)
        liquidity_score = self._calculate_liquidity_score(
            current_ratio, quick_ratio, cash_ratio, ccc
        )
        
        return {
            "current_ratio": round(current_ratio, 2),
            "quick_ratio": round(quick_ratio, 2),
            "cash_ratio": round(cash_ratio, 2),
            "cash_conversion_cycle": round(ccc, 1),
            "liquidity_score": liquidity_score,
            "liquidity_rating": self._rate_liquidity(liquidity_score),
            "warning_signals": self._detect_liquidity_warnings(current_ratio, quick_ratio, ccc)
        }
    
    def assess_overall_risk(self, company_id: str) -> Dict:
        """
        綜合風險評估
        
        整合以下風險維度:
        1. 財務危機風險 (Altman Z-Score)
        2. 流動性風險
        3. 獲利能力趨勢
        4. 槓桿風險
        5. 營運效率風險
        """
        distress_risk = self.assess_financial_distress(company_id)
        liquidity_risk = self.assess_liquidity_risk(company_id)
        profitability_risk = self.assess_profitability_trend(company_id)
        leverage_risk = self.assess_leverage_risk(company_id)
        
        # 加權綜合風險分數 (0-100, 越高越安全)
        overall_score = (
            distress_risk["score"] * 0.30 +
            liquidity_risk["liquidity_score"] * 0.25 +
            profitability_risk["score"] * 0.25 +
            leverage_risk["score"] * 0.20
        )
        
        return {
            "overall_risk_score": round(overall_score, 1),
            "risk_grade": self._assign_risk_grade(overall_score),
            "risk_breakdown": {
                "financial_distress": distress_risk,
                "liquidity": liquidity_risk,
                "profitability_trend": profitability_risk,
                "leverage": leverage_risk
            },
            "key_concerns": self._identify_key_concerns(
                distress_risk, liquidity_risk, profitability_risk, leverage_risk
            ),
            "recommendations": self._generate_risk_recommendations(overall_score)
        }