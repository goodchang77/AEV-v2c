"""
風險評估引擎測試（純函式，不依賴 DB）
"""

import pytest

from src.services.risk_assessment import RiskAssessmentEngine


def test_compute_altman_z_score_known_value():
    # Z = 1.2X1 + 1.4X2 + 3.3X3 + 0.6X4 + 1.0X5
    z = RiskAssessmentEngine.compute_altman_z_score(0.1, 0.2, 0.3, 0.4, 0.5)
    assert z == pytest.approx(1.2 * 0.1 + 1.4 * 0.2 + 3.3 * 0.3 + 0.6 * 0.4 + 1.0 * 0.5)


def test_interpret_z_score_zones():
    engine = RiskAssessmentEngine()
    assert "安全區" in engine._interpret_z_score(4.0)
    assert "警戒區" in engine._interpret_z_score(2.0)
    assert "危險區" in engine._interpret_z_score(1.0)


def test_assign_risk_grade_mapping():
    engine = RiskAssessmentEngine()
    assert engine._assign_risk_grade(90) == "A"
    assert engine._assign_risk_grade(70) == "B"
    assert engine._assign_risk_grade(55) == "C"
    assert engine._assign_risk_grade(40) == "D"
    assert engine._assign_risk_grade(20) == "F"


def test_score_to_risk_level_mapping():
    engine = RiskAssessmentEngine()
    assert engine._score_to_risk_level(90) == "低風險"
    assert engine._score_to_risk_level(60) == "中等風險"
    assert engine._score_to_risk_level(40) == "高風險"
    assert engine._score_to_risk_level(10) == "極高風險"
