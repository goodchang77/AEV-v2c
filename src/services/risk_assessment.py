"""
風險評估引擎
Risk Assessment Engine
======================

實作 CLAUDE.md 規格中的風險評估系統：
- Altman Z-Score 財務危機預警
- 流動性風險評估
- 獲利能力趨勢分析
- 槓桿風險評估
- 綜合風險評等

注意：本模組使用同步 session + 原始 SQL 查詢（text()），
不依賴 src/models.py 的 ORM 模型，以避免與 database/init SQL 的欄位漂移。
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum

from sqlalchemy import text

from src.core.database import get_sync_session
from src.core.exceptions import FinancialDataNotFoundError
from src.core.logging import get_logger

logger = get_logger("risk_assessment")


class RiskLevel(Enum):
    """風險等級"""
    LOW = "低風險"
    MEDIUM = "中等風險"
    HIGH = "高風險"
    CRITICAL = "極高風險"


@dataclass
class AltmanZScoreResult:
    """Altman Z-Score 結果"""
    z_score: float
    risk_level: RiskLevel
    probability_of_bankruptcy: float
    components: Dict[str, float]  # X1-X5 五個組成要素
    interpretation: str


def _safe_div(numerator, denominator, default: float = 0.0) -> float:
    """安全除法，避免除以零"""
    try:
        if denominator is None or float(denominator) == 0:
            return default
        return float(numerator) / float(denominator)
    except (TypeError, ValueError, ZeroDivisionError):
        return default


class RiskAssessmentEngine:
    """風險評估引擎"""

    def __init__(self, db_session=None):
        # db_session 保留向後相容；實際查詢使用同步 session
        self.db = db_session

    # ------------------------------------------------------------------
    # 資料取得
    # ------------------------------------------------------------------
    def _get_latest_financials(self, company_id: str) -> Optional[Dict[str, Any]]:
        """取得最新一期損益表（statement_type = 'IS'）資料"""
        query = text("""
            SELECT * FROM financial_statements
            WHERE company_id = :cid AND statement_type = 'IS'
            ORDER BY year_quarter DESC
            LIMIT 1
        """)
        with get_sync_session() as session:
            row = session.execute(query, {"cid": company_id}).fetchone()
        return dict(row._mapping) if row else None

    def _get_financials_history(self, company_id: str, limit: int = 4) -> List[Dict[str, Any]]:
        """取得最近 N 期損益表（由近到遠）"""
        query = text("""
            SELECT * FROM financial_statements
            WHERE company_id = :cid AND statement_type = 'IS'
            ORDER BY year_quarter DESC
            LIMIT :limit
        """)
        with get_sync_session() as session:
            rows = session.execute(query, {"cid": company_id, "limit": limit}).fetchall()
        return [dict(r._mapping) for r in rows]

    def _get_latest_ratios(self, company_id: str) -> Optional[Dict[str, Any]]:
        """取得最新一期財務比率"""
        query = text("""
            SELECT * FROM financial_ratios
            WHERE company_id = :cid
            ORDER BY year_quarter DESC
            LIMIT 1
        """)
        with get_sync_session() as session:
            row = session.execute(query, {"cid": company_id}).fetchone()
        return dict(row._mapping) if row else None

    def get_company_name(self, company_id: str) -> str:
        """取得公司名稱"""
        query = text("SELECT company_name FROM companies WHERE company_id = :cid")
        with get_sync_session() as session:
            row = session.execute(query, {"cid": company_id}).fetchone()
        return row.company_name if row else company_id

    # ------------------------------------------------------------------
    # 1. 財務危機風險（Altman Z-Score）
    # ------------------------------------------------------------------
    @staticmethod
    def compute_altman_z_score(x1: float, x2: float, x3: float, x4: float, x5: float) -> float:
        """Altman Z-Score 公式：Z = 1.2X1 + 1.4X2 + 3.3X3 + 0.6X4 + 1.0X5"""
        return 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5

    def assess_financial_distress(self, company_id: str) -> Dict[str, Any]:
        """
        Altman Z-Score 財務危機評估

        公式: Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5
        - X1 = 營運資金 / 總資產
        - X2 = 保留盈餘 / 總資產
        - X3 = 息前稅前盈餘(以營業利益近似) / 總資產
        - X4 = 股東權益 / 總負債（無市值資料時以帳面值近似）
        - X5 = 營收 / 總資產
        """
        financials = self._get_latest_financials(company_id)
        if not financials:
            raise FinancialDataNotFoundError(company_id, "financial_statements")

        total_assets = financials.get("total_assets")
        total_liabilities = financials.get("total_liabilities")

        x1 = _safe_div(
            (financials.get("current_assets") or 0) - (financials.get("current_liabilities") or 0),
            total_assets,
        )
        x2 = _safe_div(financials.get("retained_earnings"), total_assets)
        x3 = _safe_div(financials.get("operating_income"), total_assets)
        x4 = _safe_div(financials.get("shareholders_equity"), total_liabilities)
        x5 = _safe_div(financials.get("revenue"), total_assets)

        z_score = self.compute_altman_z_score(x1, x2, x3, x4, x5)

        if z_score > 2.99:
            risk_level = RiskLevel.LOW
            probability = 0.02
        elif z_score > 1.81:
            risk_level = RiskLevel.MEDIUM
            probability = 0.15
        else:
            risk_level = RiskLevel.HIGH
            probability = 0.80

        # 轉換為 0-100 的「安全分數」（越高越安全）
        score = min(100.0, max(0.0, z_score * 25))

        return {
            "z_score": round(z_score, 2),
            "risk_level": risk_level.value,
            "probability_of_bankruptcy": probability,
            "score": round(score, 1),
            "components": {
                "X1_working_capital_ratio": round(x1, 4),
                "X2_retained_earnings_ratio": round(x2, 4),
                "X3_ebit_ratio": round(x3, 4),
                "X4_market_to_book_leverage": round(x4, 4),
                "X5_asset_turnover": round(x5, 4),
            },
            "interpretation": self._interpret_z_score(z_score),
        }

    # ------------------------------------------------------------------
    # 2. 流動性風險
    # ------------------------------------------------------------------
    def assess_liquidity_risk(self, company_id: str) -> Dict[str, Any]:
        """流動性風險評估（流動/速動/現金比率 + 現金轉換週期）"""
        financials = self._get_latest_financials(company_id)
        if not financials:
            raise FinancialDataNotFoundError(company_id, "financial_statements")

        ratios = self._get_latest_ratios(company_id) or {}

        current_liabilities = financials.get("current_liabilities") or 0
        current_assets = financials.get("current_assets") or 0
        inventory = financials.get("inventory") or 0
        cash = financials.get("cash_and_equivalents") or 0

        current_ratio = _safe_div(current_assets, current_liabilities)
        quick_ratio = _safe_div(current_assets - inventory, current_liabilities)
        cash_ratio = _safe_div(cash, current_liabilities)

        # 現金轉換週期：優先使用已算好的值，否則用週轉天數
        ccc = ratios.get("cash_conversion_cycle")
        if ccc is None:
            dso = ratios.get("days_sales_outstanding") or 0
            dio = ratios.get("days_inventory_outstanding") or 0
            dpo = ratios.get("days_payable_outstanding") or 0
            ccc = float(dso) + float(dio) - float(dpo)

        liquidity_score = self._calculate_liquidity_score(
            current_ratio, quick_ratio, cash_ratio, float(ccc)
        )

        return {
            "current_ratio": round(current_ratio, 2),
            "quick_ratio": round(quick_ratio, 2),
            "cash_ratio": round(cash_ratio, 2),
            "cash_conversion_cycle": round(float(ccc), 1),
            "liquidity_score": round(liquidity_score, 1),
            "liquidity_rating": self._rate_liquidity(liquidity_score),
            "warning_signals": self._detect_liquidity_warnings(
                current_ratio, quick_ratio, float(ccc)
            ),
        }

    # ------------------------------------------------------------------
    # 3. 獲利能力趨勢
    # ------------------------------------------------------------------
    def assess_profitability_trend(self, company_id: str) -> Dict[str, Any]:
        """獲利能力趨勢分析（淨利率的近期走向）"""
        history = self._get_financials_history(company_id, limit=4)
        if not history:
            raise FinancialDataNotFoundError(company_id, "financial_statements")

        margins = []
        for row in history:
            margin = _safe_div(row.get("net_income"), row.get("revenue")) * 100
            margins.append(
                {
                    "year_quarter": row.get("year_quarter"),
                    "net_margin": round(margin, 2),
                }
            )

        latest = margins[0]["net_margin"] if margins else 0.0
        if len(margins) >= 2:
            previous = margins[-1]["net_margin"]
            delta = latest - previous
        else:
            previous = latest
            delta = 0.0

        if delta > 0.5:
            trend = "改善"
            trend_score = 80
        elif delta < -0.5:
            trend = "惡化"
            trend_score = 40
        else:
            trend = "持平"
            trend_score = 60

        return {
            "latest_net_margin": round(latest, 2),
            "previous_net_margin": round(previous, 2),
            "margin_change": round(delta, 2),
            "trend": trend,
            "score": trend_score,
            "series": margins,
        }

    # ------------------------------------------------------------------
    # 4. 槓桿風險
    # ------------------------------------------------------------------
    def assess_leverage_risk(self, company_id: str) -> Dict[str, Any]:
        """槓桿風險評估（負債比率 + 利息保障倍數）"""
        financials = self._get_latest_financials(company_id)
        if not financials:
            raise FinancialDataNotFoundError(company_id, "financial_statements")

        ratios = self._get_latest_ratios(company_id) or {}

        total_assets = financials.get("total_assets")
        total_liabilities = financials.get("total_liabilities")
        equity = financials.get("shareholders_equity")

        debt_to_asset = _safe_div(total_liabilities, total_assets) * 100
        debt_to_equity = _safe_div(total_liabilities, equity) * 100
        interest_coverage = ratios.get("interest_coverage_ratio")

        # 負債比率越低越安全
        if debt_to_asset <= 30:
            score = 85
        elif debt_to_asset <= 50:
            score = 65
        elif debt_to_asset <= 70:
            score = 45
        else:
            score = 25

        # 利息保障倍數調整
        if interest_coverage is not None:
            coverage = float(interest_coverage)
            if coverage >= 5:
                score += 10
            elif coverage < 1:
                score -= 20

        score = min(100.0, max(0.0, score))

        return {
            "debt_to_asset_ratio": round(debt_to_asset, 2),
            "debt_to_equity_ratio": round(debt_to_equity, 2),
            "interest_coverage_ratio": (
                round(float(interest_coverage), 2) if interest_coverage is not None else None
            ),
            "score": round(score, 1),
            "leverage_rating": self._rate_liquidity(score),
        }

    # ------------------------------------------------------------------
    # 綜合風險
    # ------------------------------------------------------------------
    def assess_overall_risk(self, company_id: str) -> Dict[str, Any]:
        """綜合風險評估（整合財務危機、流動性、獲利趨勢、槓桿四個維度）"""
        distress_risk = self.assess_financial_distress(company_id)
        liquidity_risk = self.assess_liquidity_risk(company_id)
        profitability_risk = self.assess_profitability_trend(company_id)
        leverage_risk = self.assess_leverage_risk(company_id)

        overall_score = (
            distress_risk["score"] * 0.30
            + liquidity_risk["liquidity_score"] * 0.25
            + profitability_risk["score"] * 0.25
            + leverage_risk["score"] * 0.20
        )
        overall_score = round(min(100.0, max(0.0, overall_score)), 1)

        return {
            "overall_risk_score": overall_score,
            "risk_grade": self._assign_risk_grade(overall_score),
            "risk_level": self._score_to_risk_level(overall_score),
            "risk_trend": "持平",  # 多期比較於後續階段實作
            "risk_breakdown": {
                "financial_distress": distress_risk,
                "liquidity": liquidity_risk,
                "profitability_trend": profitability_risk,
                "leverage": leverage_risk,
            },
            "key_concerns": self._identify_key_concerns(
                distress_risk, liquidity_risk, profitability_risk, leverage_risk
            ),
            "recommendations": self._generate_risk_recommendations(overall_score),
        }

    def compare_risk_with_industry(self, company_id: str) -> Optional[Dict[str, Any]]:
        """與產業基準比較（後續階段實作）"""
        return None

    # ------------------------------------------------------------------
    # 輔助方法
    # ------------------------------------------------------------------
    def _interpret_z_score(self, z_score: float) -> str:
        if z_score > 2.99:
            return "財務結構健全，破產風險低（安全區）"
        elif z_score > 1.81:
            return "財務狀況處於灰色地帶，需持續關注（警戒區）"
        else:
            return "財務危機風險偏高，建議深入檢視償債能力（危險區）"

    def _calculate_liquidity_score(
        self, current_ratio: float, quick_ratio: float, cash_ratio: float, ccc: float
    ) -> float:
        score = 60.0
        if current_ratio >= 2.0:
            score += 15
        elif current_ratio >= 1.5:
            score += 8
        elif current_ratio < 1.0:
            score -= 20

        if quick_ratio >= 1.0:
            score += 10
        elif quick_ratio < 0.5:
            score -= 10

        if cash_ratio >= 0.5:
            score += 10
        elif cash_ratio < 0.2:
            score -= 5

        if ccc <= 0:
            score += 5
        elif ccc > 180:
            score -= 10

        return min(100.0, max(0.0, score))

    def _rate_liquidity(self, score: float) -> str:
        if score >= 80:
            return "流動性良好"
        elif score >= 60:
            return "流動性尚可"
        elif score >= 40:
            return "流動性偏緊"
        else:
            return "流動性風險高"

    def _detect_liquidity_warnings(
        self, current_ratio: float, quick_ratio: float, ccc: float
    ) -> List[str]:
        warnings = []
        if current_ratio < 1.0:
            warnings.append("流動比率低於 1，短期償債能力不足")
        if quick_ratio < 0.5:
            warnings.append("速動比率偏低，變現能力有待觀察")
        if ccc > 180:
            warnings.append("現金轉換週期過長，營運資金周轉效率偏低")
        return warnings

    def _assign_risk_grade(self, score: float) -> str:
        if score >= 80:
            return "A"
        elif score >= 65:
            return "B"
        elif score >= 50:
            return "C"
        elif score >= 35:
            return "D"
        else:
            return "F"

    def _score_to_risk_level(self, score: float) -> str:
        if score >= 80:
            return RiskLevel.LOW.value
        elif score >= 50:
            return RiskLevel.MEDIUM.value
        elif score >= 35:
            return RiskLevel.HIGH.value
        else:
            return RiskLevel.CRITICAL.value

    def _identify_key_concerns(
        self,
        distress: Dict[str, Any],
        liquidity: Dict[str, Any],
        profitability: Dict[str, Any],
        leverage: Dict[str, Any],
    ) -> List[str]:
        concerns = []
        if distress["z_score"] < 1.81:
            concerns.append(f"Altman Z-Score 為 {distress['z_score']}，落入危險區")
        if liquidity["liquidity_score"] < 60:
            concerns.append(f"流動性評分偏低（{liquidity['liquidity_score']}）")
        if profitability["trend"] == "惡化":
            concerns.append("獲利能力呈現惡化趨勢")
        if leverage["debt_to_asset_ratio"] > 70:
            concerns.append(f"負債比率偏高（{leverage['debt_to_asset_ratio']}%）")
        return concerns

    def _generate_risk_recommendations(self, overall_score: float) -> List[str]:
        if overall_score >= 80:
            return ["整體風險偏低，可維持既有投資策略，持續監控財務指標"]
        elif overall_score >= 50:
            return [
                "整體風險中等，建議定期檢視償債與流動性指標",
                "關注獲利能力與槓桿變化，避免風險進一步上升",
            ]
        else:
            return [
                "整體風險偏高，建議審慎評估投資",
                "優先檢視短期償債能力與現金流狀況",
                "考慮分散投資以降低個別標的風險",
            ]
