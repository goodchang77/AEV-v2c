# tests/test_risk_assessment.py
import pytest
from src.services.risk_assessment import RiskAssessmentEngine

class TestAltmanZScore:
    """Altman Z-Score測試 - 基於CLAUDE.md規格476-526行"""
    
    def test_healthy_company_z_score(self, test_db, sample_company_data):
        """測試財務健康公司(台積電)應得到高Z-Score"""
        engine = RiskAssessmentEngine(test_db)
        result = engine.assess_financial_distress("2330")
        
        # 根據Altman Z-Score標準:
        # Z > 2.99: 安全區(綠燈)
        # 1.81 < Z < 2.99: 灰色區
        # Z < 1.81: 危險區(紅燈)
        assert result["z_score"] > 2.99
        assert result["risk_level"] == "LOW"
        assert result["probability_of_bankruptcy"] < 0.05
    
    def test_distressed_company_z_score(self, test_db):
        """測試財務困難公司應得到低Z-Score"""
        # 模擬高負債、低獲利公司
        distressed_data = {
            "company_id": "9999",
            "working_capital": -50_000_000,  # 負營運資金
            "total_assets": 100_000_000,
            "retained_earnings": -20_000_000,  # 虧損累積
            "ebit": -5_000_000,  # 營業虧損
            "market_cap": 10_000_000,
            "total_liabilities": 120_000_000
        }
        
        engine = RiskAssessmentEngine(test_db)
        result = engine.assess_financial_distress("9999")
        
        assert result["z_score"] < 1.81
        assert result["risk_level"] == "HIGH"
        assert result["probability_of_bankruptcy"] > 0.50

class TestLiquidityRisk:
    """流動性風險測試 - 基於台積電財報數據"""
    
    def test_current_ratio_assessment(self, test_db):
        """測試流動比率評估"""
        engine = RiskAssessmentEngine(test_db)
        result = engine.assess_liquidity_risk("2330")
        
        # 台積電2006年流動比率 = 451.4% (從文件中提取)
        assert result["current_ratio"] > 4.0
        assert result["liquidity_score"] > 90  # 0-100分制
        assert "EXCELLENT" in result["liquidity_rating"]
    
    def test_cash_conversion_cycle(self, test_db):
        """測試現金轉換週期"""
        engine = RiskAssessmentEngine(test_db)
        result = engine.assess_liquidity_risk("2330")
        
        # 台積電: 應收帳款週轉天數55天 + 存貨週轉天數62天 - 應付帳款天數23天 = 94天
        expected_ccc = 55 + 62 - 23
        assert abs(result["cash_conversion_cycle"] - expected_ccc) < 5  # 允許5天誤差