"""
財務比率計算引擎測試（純函式，不依賴 DB）
"""

from decimal import Decimal

import pytest

from src.services.financial_calculator import FinancialCalculator, FinancialStatements


@pytest.fixture
def statements() -> FinancialStatements:
    """範例財務報表"""
    return FinancialStatements(
        current_assets=Decimal("6000000"),
        non_current_assets=Decimal("10000000"),
        total_assets=Decimal("16000000"),
        current_liabilities=Decimal("3500000"),
        non_current_liabilities=Decimal("2500000"),
        total_liabilities=Decimal("6000000"),
        shareholders_equity=Decimal("10000000"),
        cash_and_equivalents=Decimal("1500000"),
        accounts_receivable=Decimal("2300000"),
        inventory=Decimal("1800000"),
        accounts_payable=Decimal("1800000"),
        short_term_debt=Decimal("1200000"),
        long_term_debt=Decimal("2000000"),
        revenue=Decimal("25000000"),
        cost_of_revenue=Decimal("18000000"),
        gross_profit=Decimal("7000000"),
        operating_expenses=Decimal("4500000"),
        operating_income=Decimal("2500000"),
        ebitda=Decimal("2600000"),
        interest_expense=Decimal("200000"),
        pretax_income=Decimal("2300000"),
        tax_expense=Decimal("460000"),
        net_income=Decimal("1840000"),
        eps=Decimal("3.68"),
        operating_cash_flow=Decimal("2440000"),
        investing_cash_flow=Decimal("-1000000"),
        financing_cash_flow=Decimal("-420000"),
        free_cash_flow=Decimal("1440000"),
        capex=Decimal("800000"),
    )


def test_calculate_all_ratios_profitability(statements):
    calc = FinancialCalculator()
    ratios = calc.calculate_all_ratios(statements)
    assert float(ratios.roe) == pytest.approx(0.184, rel=1e-2)  # 1840000/10000000
    assert float(ratios.roa) == pytest.approx(0.115, rel=1e-2)  # 1840000/16000000
    assert float(ratios.net_margin) == pytest.approx(0.0736, rel=1e-2)


def test_calculate_all_ratios_liquidity(statements):
    calc = FinancialCalculator()
    ratios = calc.calculate_all_ratios(statements)
    assert float(ratios.current_ratio) == pytest.approx(6000000 / 3500000, rel=1e-2)
    # 速動比率 = (流動資產 - 存貨) / 流動負債
    assert float(ratios.quick_ratio) == pytest.approx((6000000 - 1800000) / 3500000, rel=1e-2)


def test_evaluate_financial_health(statements):
    calc = FinancialCalculator()
    ratios = calc.calculate_all_ratios(statements)
    grade, details = calc.evaluate_financial_health(ratios)
    assert grade is not None
    assert isinstance(details, dict) and len(details) > 0
