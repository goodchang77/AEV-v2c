"""
pytest 全域測試配置與共享 fixtures
====================================

提供財務分析系統單元測試所需的資料 fixtures。
由於核心服務（financial_calculator / valuation_models / peer_analysis）皆為
「無狀態、吃記憶體 dataclass」的設計，因此本檔以純資料 fixtures 為主，
不依賴資料庫連線，讓測試可快速、可重複執行。
"""

import pytest
from decimal import Decimal

from src.services.financial_calculator import (
    FinancialStatements,
    FinancialCalculator,
)
from src.services.valuation_models import (
    DCFParameters,
    DDMParameters,
    DCFValuationModel,
    DDMValuationModel,
)
from src.services.peer_analysis import (
    PeerCompanyData,
    IndustryBenchmark,
    PeerAnalyzer,
)


@pytest.fixture
def sample_financial_statements() -> FinancialStatements:
    """以台積電規模為範本的財務報表資料（單位：新台幣千元，簡化範例）"""
    return FinancialStatements(
        # 資產負債表
        current_assets=Decimal("193676010"),
        non_current_assets=Decimal("379908894"),
        total_assets=Decimal("573584904"),
        current_liabilities=Decimal("42905154"),
        non_current_liabilities=Decimal("22658666"),
        total_liabilities=Decimal("65563820"),
        shareholders_equity=Decimal("507981284"),
        cash_and_equivalents=Decimal("120000000"),
        accounts_receivable=Decimal("30000000"),
        inventory=Decimal("25000000"),
        accounts_payable=Decimal("20000000"),
        short_term_debt=Decimal("10000000"),
        long_term_debt=Decimal("15000000"),
        # 損益表
        revenue=Decimal("573584904"),
        cost_of_revenue=Decimal("330000000"),
        gross_profit=Decimal("243584904"),
        operating_expenses=Decimal("120000000"),
        operating_income=Decimal("123584904"),
        ebitda=Decimal("150000000"),
        interest_expense=Decimal("2000000"),
        pretax_income=Decimal("121584904"),
        tax_expense=Decimal("20000000"),
        net_income=Decimal("101584904"),
        eps=Decimal("3.91"),
        # 現金流量表
        operating_cash_flow=Decimal("160000000"),
        investing_cash_flow=Decimal("-120000000"),
        financing_cash_flow=Decimal("-40000000"),
        free_cash_flow=Decimal("40000000"),
        capex=Decimal("120000000"),
    )


@pytest.fixture
def sample_dcf_parameters() -> DCFParameters:
    """DCF 評價參數範例"""
    return DCFParameters(
        forecast_years=5,
        revenue_growth_rates=[0.15, 0.12, 0.10, 0.08, 0.05],
        ebitda_margin=0.20,
        depreciation_rate=0.05,
        tax_rate=0.25,
        capex_rate=0.05,
        working_capital_rate=0.02,
        discount_rate=0.10,
        terminal_growth_rate=0.03,
    )


@pytest.fixture
def sample_dcf_model(sample_dcf_parameters) -> DCFValuationModel:
    """DCF 模型實例"""
    return DCFValuationModel(sample_dcf_parameters)


@pytest.fixture
def sample_peer_companies() -> list:
    """同業公司範例資料"""
    def _make(cid, name, roe, roa, current_ratio, debt_ratio, net_margin,
              market_cap=500_000_000_000, pe=None, pb=None):
        return PeerCompanyData(
            company_id=cid,
            company_name=name,
            market_cap=market_cap,
            revenue=300_000_000_000,
            net_income=50_000_000_000,
            total_assets=600_000_000_000,
            shareholders_equity=400_000_000_000,
            roe=roe,
            roa=roa,
            current_ratio=current_ratio,
            debt_ratio=debt_ratio,
            net_margin=net_margin,
            pe_ratio=pe,
            pb_ratio=pb,
        )

    return [
        _make("2454", "聯發科", 0.28, 0.20, 2.5, 0.30, 0.30, pe=20.0, pb=3.0),
        _make("2303", "聯電", 0.18, 0.12, 2.0, 0.40, 0.22, pe=15.0, pb=2.0),
        _make("3711", "日月光", 0.15, 0.08, 1.5, 0.50, 0.12, pe=12.0, pb=1.5),
    ]


@pytest.fixture
def sample_industry_benchmark() -> IndustryBenchmark:
    """產業基準範例資料"""
    return IndustryBenchmark(
        industry_code="SMI",
        industry_name="半導體",
        company_count=50,
        avg_roe=0.20,
        avg_roa=0.14,
        avg_current_ratio=2.0,
        avg_debt_ratio=0.40,
        avg_gross_margin=0.40,
        avg_net_margin=0.20,
        avg_pe_ratio=18.0,
        avg_pb_ratio=2.5,
        median_roe=0.18,
        median_roa=0.12,
        median_current_ratio=1.8,
        median_debt_ratio=0.42,
        roe_25_percentile=0.10,
        roe_75_percentile=0.25,
        pe_25_percentile=12.0,
        pe_75_percentile=24.0,
        debt_25_percentile=0.30,
        debt_75_percentile=0.55,
        roe_std_dev=0.06,
        roa_std_dev=0.05,
    )


@pytest.fixture
def sample_target_company() -> PeerCompanyData:
    """目標公司（台積電）範例資料"""
    return PeerCompanyData(
        company_id="2330",
        company_name="台積電",
        market_cap=15_000_000_000_000,
        revenue=573_584_904_000,
        net_income=101_584_904_000,
        total_assets=573_584_904_000,
        shareholders_equity=507_981_284_000,
        roe=0.266,
        roa=0.236,
        current_ratio=4.51,
        debt_ratio=0.11,
        net_margin=0.177,
        pe_ratio=25.0,
        pb_ratio=6.0,
    )


@pytest.fixture
def financial_calculator() -> FinancialCalculator:
    """財務比率計算器實例"""
    return FinancialCalculator()


@pytest.fixture
def peer_analyzer() -> PeerAnalyzer:
    """同業比較分析器實例"""
    return PeerAnalyzer()
