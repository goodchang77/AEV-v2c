"""
風險評估引擎測試
====================

測試 RiskAssessmentEngine 的純計算邏輯（不需資料庫）：
- Altman Z-Score 公式與等級判定
- 流動性評分與預警訊號
- 風險等級／評等對映
- 改善建議生成

DB 相關的 assess_* 整合測試將於 Phase 1（連接資料庫）時補上。
"""

import pytest

from src.services.risk_assessment import (
    RiskAssessmentEngine,
    RiskLevel,
    AltmanZScoreResult,
)


@pytest.fixture
def engine() -> RiskAssessmentEngine:
    """不需 DB 即可初始化的引擎（純計算方法不碰 DB）"""
    return RiskAssessmentEngine()


class TestAltmanZScore:
    """Altman Z-Score 公式與等級判定"""

    def test_z_score_formula(self, engine):
        """驗證 Z-Score 加權公式正確"""
        # 代入已知五個要素，手動計算期望值
        x1, x2, x3, x4, x5 = 0.5, 0.3, 0.2, 1.0, 0.8
        expected = 1.2 * 0.5 + 1.4 * 0.3 + 3.3 * 0.2 + 0.6 * 1.0 + 1.0 * 0.8
        assert engine.compute_altman_z_score(x1, x2, x3, x4, x5) == pytest.approx(expected)

    def test_healthy_company_high_z_score(self, engine):
        """財務健全公司應得到高 Z-Score（安全區）"""
        # 高營運資金、高保留盈餘、高獲利、低負債
        z = engine.compute_altman_z_score(0.40, 0.30, 0.15, 3.0, 1.0)
        assert z > 2.99

    def test_distressed_company_low_z_score(self, engine):
        """財務困難公司應得到低 Z-Score（危險區）"""
        # 負營運資金、累積虧損、營業虧損、負債大於權益
        z = engine.compute_altman_z_score(-0.50, -0.20, -0.05, 0.08, 0.3)
        assert z < 1.81

    def test_interpretation_thresholds(self, engine):
        """驗證 Z-Score 三區間的文字解讀"""
        assert "安全區" in engine._interpret_z_score(3.5)
        assert "警戒區" in engine._interpret_z_score(2.5)
        assert "危險區" in engine._interpret_z_score(1.0)


class TestLiquidityRisk:
    """流動性評分與預警訊號"""

    def test_high_liquidity_score(self, engine):
        """高流動比率／速動比率／現金比率應得高分"""
        score = engine._calculate_liquidity_score(
            current_ratio=4.5, quick_ratio=3.0, cash_ratio=1.5, ccc=50
        )
        assert score >= 90
        assert "良好" in engine._rate_liquidity(score)

    def test_low_liquidity_score(self, engine):
        """流動比率 < 1、速動比率偏低應得低分並產生預警"""
        score = engine._calculate_liquidity_score(
            current_ratio=0.6, quick_ratio=0.3, cash_ratio=0.05, ccc=200
        )
        assert score < 40
        assert "風險高" in engine._rate_liquidity(score)

    def test_liquidity_warning_signals(self, engine):
        """驗證流動性預警訊號偵測"""
        warnings = engine._detect_liquidity_warnings(
            current_ratio=0.8, quick_ratio=0.3, ccc=220
        )
        assert len(warnings) >= 2


class TestRiskGradeMapping:
    """風險等級／評等對映"""

    def test_grade_mapping(self, engine):
        assert engine._assign_risk_grade(90) == "A"
        assert engine._assign_risk_grade(70) == "B"
        assert engine._assign_risk_grade(55) == "C"
        assert engine._assign_risk_grade(40) == "D"
        assert engine._assign_risk_grade(20) == "F"

    def test_score_to_risk_level(self, engine):
        assert engine._score_to_risk_level(90) == RiskLevel.LOW.value
        assert engine._score_to_risk_level(60) == RiskLevel.MEDIUM.value
        assert engine._score_to_risk_level(40) == RiskLevel.HIGH.value
        assert engine._score_to_risk_level(10) == RiskLevel.CRITICAL.value


class TestRecommendations:
    """改善建議生成"""

    def test_low_risk_recommendation(self, engine):
        recs = engine._generate_risk_recommendations(85)
        assert len(recs) >= 1
        assert "偏低" in recs[0]

    def test_high_risk_recommendation(self, engine):
        recs = engine._generate_risk_recommendations(30)
        assert len(recs) >= 3
        assert any("審慎" in r for r in recs)


class TestAltmanZScoreResultDataclass:
    """AltmanZScoreResult 資料類結構"""

    def test_dataclass_construction(self):
        result = AltmanZScoreResult(
            z_score=4.5,
            risk_level=RiskLevel.LOW,
            probability_of_bankruptcy=0.02,
            components={"X1": 0.4, "X2": 0.3, "X3": 0.15, "X4": 3.0, "X5": 1.0},
            interpretation="安全區",
        )
        assert result.z_score == 4.5
        assert result.risk_level == RiskLevel.LOW
