"""
資料庫初始化腳本 (Phase 1)
===========================
1. 套用 database/init/01_create_tables.sql（若資料表不存在）
2. 套用 database/init/02_sample_data.sql（若 companies 為空）
3. 插入 2330 台積電的範例財務報表（4 季 IS/BS + 1 季 CF）與財務比率
   種子檔原本缺少財務資料，導致 /financials、/ratios、/analysis/risk-assessment 無資料可用。

冪等設計：可重複執行，不會產生重複資料。

用法:
    py -3.14 scripts/init_db.py
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import psycopg2
from psycopg2 import sql

from src.core.config import get_settings

# ---------------------------------------------------------------------------
# 2330 台積電範例財務資料（單位：千元 NTD，數值為示範用途）
# ---------------------------------------------------------------------------
QUARTERS = [
    # year_quarter, report_date, revenue, cost_of_revenue, operating_expenses,
    # current_assets, non_current_assets, current_liabilities, non_current_liabilities,
    # net_income, eps
    ("2024Q1", "2024-03-31", 573_584_904, 330_000_000, 120_000_000,
     2_000_000_000, 3_735_849_040, 429_051_540, 226_586_660,
     101_584_904, 3.91),
    ("2024Q2", "2024-06-30", 602_264_149, 346_500_000, 120_000_000,
     2_100_000_000, 3_782_000_000, 450_000_000, 235_000_000,
     112_000_000, 4.31),
    ("2024Q3", "2024-09-30", 632_377_357, 363_825_000, 120_000_000,
     2_200_000_000, 3_830_000_000, 470_000_000, 245_000_000,
     122_000_000, 4.69),
    ("2024Q4", "2024-12-31", 663_996_225, 382_016_250, 120_000_000,
     2_310_000_000, 3_880_000_000, 495_000_000, 255_000_000,
     132_000_000, 5.08),
]

DEPRECIATION = 26_415_096
INTEREST_EXPENSE = 2_000_000
INTEREST_INCOME = 10_000_000


def _apply_sql_file(cur, path: Path) -> None:
    """執行一個 SQL 檔（支援多敘述）"""
    text = path.read_text(encoding="utf-8")
    cur.execute(text)
    print(f"    已套用 {path.name} ({len(text)} bytes)")


def _insert_financial_statements(cur) -> None:
    """插入 2330 的 IS/BS/CF 報表（ON CONFLICT 冪等）"""
    for (yq, rdate, revenue, cost, opex,
         ca, nca, cl, ncl, net_income, eps) in QUARTERS:
        gross = revenue - cost
        operating_income = gross - opex
        ebitda = operating_income + DEPRECIATION
        pretax = operating_income + INTEREST_INCOME - INTEREST_EXPENSE
        tax = pretax - net_income
        total_assets = ca + nca
        total_liabilities = cl + ncl
        equity = total_assets - total_liabilities

        common = dict(
            company_id="2330", report_type="quarterly", year_quarter=yq,
            report_date=rdate, data_source="sample", data_quality_score=1.00,
            is_audited=True,
            # 資產負債表
            current_assets=ca, non_current_assets=nca, total_assets=total_assets,
            current_liabilities=cl, non_current_liabilities=ncl,
            total_liabilities=total_liabilities, shareholders_equity=equity,
            cash_and_equivalents=1_200_000_000, accounts_receivable=300_000_000,
            inventory=250_000_000, ppe_net=3_000_000_000,
            accounts_payable=200_000_000, short_term_debt=100_000_000,
            long_term_debt=150_000_000,
            retained_earnings=3_000_000_000, dividends_paid=50_000_000,
        )

        # 損益表 (IS) — 附帶完整資產負債表欄位，供風險評估使用
        is_row = dict(
            **common, statement_type="IS",
            revenue=revenue, cost_of_revenue=cost, gross_profit=gross,
            operating_expenses=opex, operating_income=operating_income,
            ebitda=ebitda, depreciation_amortization=DEPRECIATION,
            interest_expense=INTEREST_EXPENSE, interest_income=INTEREST_INCOME,
            pretax_income=pretax, tax_expense=tax, net_income=net_income,
            eps=eps, eps_diluted=round(eps - 0.01, 2),
            operating_cash_flow=160_000_000, investing_cash_flow=-120_000_000,
            financing_cash_flow=-40_000_000, free_cash_flow=40_000_000,
            capex=120_000_000,
        )

        # 資產負債表 (BS) — 滿足 total_assets = current + non-current 檢查
        bs_row = dict(**common, statement_type="BS")

        # IS 插入（含 BS 欄位）
        cur.execute(
            """
            INSERT INTO financial_statements (
                company_id, report_type, year_quarter, statement_type, report_date,
                current_assets, non_current_assets, total_assets,
                current_liabilities, non_current_liabilities, total_liabilities,
                shareholders_equity, cash_and_equivalents, accounts_receivable,
                inventory, ppe_net, accounts_payable, short_term_debt, long_term_debt,
                retained_earnings, dividends_paid,
                revenue, cost_of_revenue, gross_profit, operating_expenses,
                operating_income, ebitda, depreciation_amortization,
                interest_expense, interest_income, pretax_income, tax_expense,
                net_income, eps, eps_diluted,
                operating_cash_flow, investing_cash_flow, financing_cash_flow,
                free_cash_flow, capex, data_source, data_quality_score, is_audited
            ) VALUES (
                %(company_id)s, %(report_type)s, %(year_quarter)s, %(statement_type)s, %(report_date)s,
                %(current_assets)s, %(non_current_assets)s, %(total_assets)s,
                %(current_liabilities)s, %(non_current_liabilities)s, %(total_liabilities)s,
                %(shareholders_equity)s, %(cash_and_equivalents)s, %(accounts_receivable)s,
                %(inventory)s, %(ppe_net)s, %(accounts_payable)s, %(short_term_debt)s, %(long_term_debt)s,
                %(retained_earnings)s, %(dividends_paid)s,
                %(revenue)s, %(cost_of_revenue)s, %(gross_profit)s, %(operating_expenses)s,
                %(operating_income)s, %(ebitda)s, %(depreciation_amortization)s,
                %(interest_expense)s, %(interest_income)s, %(pretax_income)s, %(tax_expense)s,
                %(net_income)s, %(eps)s, %(eps_diluted)s,
                %(operating_cash_flow)s, %(investing_cash_flow)s, %(financing_cash_flow)s,
                %(free_cash_flow)s, %(capex)s, %(data_source)s, %(data_quality_score)s, %(is_audited)s
            )
            ON CONFLICT (company_id, year_quarter, statement_type) DO NOTHING
            """,
            is_row,
        )

        # BS 插入（僅資產負債表欄位）
        cur.execute(
            """
            INSERT INTO financial_statements (
                company_id, report_type, year_quarter, statement_type, report_date,
                current_assets, non_current_assets, total_assets,
                current_liabilities, non_current_liabilities, total_liabilities,
                shareholders_equity, cash_and_equivalents, accounts_receivable,
                inventory, ppe_net, accounts_payable, short_term_debt, long_term_debt,
                retained_earnings, dividends_paid,
                data_source, data_quality_score, is_audited
            ) VALUES (
                %(company_id)s, %(report_type)s, %(year_quarter)s, %(statement_type)s, %(report_date)s,
                %(current_assets)s, %(non_current_assets)s, %(total_assets)s,
                %(current_liabilities)s, %(non_current_liabilities)s, %(total_liabilities)s,
                %(shareholders_equity)s, %(cash_and_equivalents)s, %(accounts_receivable)s,
                %(inventory)s, %(ppe_net)s, %(accounts_payable)s, %(short_term_debt)s, %(long_term_debt)s,
                %(retained_earnings)s, %(dividends_paid)s,
                %(data_source)s, %(data_quality_score)s, %(is_audited)s
            )
            ON CONFLICT (company_id, year_quarter, statement_type) DO NOTHING
            """,
            bs_row,
        )

    # 現金流量表 (CF) — 最新一季
    yq, rdate = QUARTERS[-1][0], QUARTERS[-1][1]
    cur.execute(
        """
        INSERT INTO financial_statements (
            company_id, report_type, year_quarter, statement_type, report_date,
            operating_cash_flow, investing_cash_flow, financing_cash_flow,
            free_cash_flow, capex, data_source, data_quality_score, is_audited
        ) VALUES ('2330', 'quarterly', %s, 'CF', %s,
                  160000000, -120000000, -40000000, 40000000, 120000000,
                  'sample', 1.00, true)
        ON CONFLICT (company_id, year_quarter, statement_type) DO NOTHING
        """,
        (yq, rdate),
    )
    print("    已插入 2330 財務報表（4 季 IS/BS + 1 季 CF）")


def _insert_financial_ratios(cur) -> None:
    """插入 2330 最新一季的財務比率（無唯一約束，先清再插以達冪等）"""
    cur.execute("SELECT count(*) FROM financial_ratios WHERE company_id = '2330'")
    if cur.fetchone()[0] > 0:
        print("    2330 財務比率已存在，略過")
        return

    cur.execute(
        """
        INSERT INTO financial_ratios (
            company_id, year_quarter, calculation_method, data_completeness,
            debt_to_asset_ratio, debt_to_equity_ratio, equity_ratio, long_term_debt_to_equity,
            current_ratio, quick_ratio, cash_ratio, interest_coverage_ratio, debt_service_coverage_ratio,
            receivables_turnover, inventory_turnover, total_asset_turnover,
            fixed_asset_turnover, working_capital_turnover,
            days_sales_outstanding, days_inventory_outstanding, days_payable_outstanding,
            cash_conversion_cycle,
            roa, roe, roic, gross_margin, operating_margin, net_margin, ebitda_margin,
            operating_cash_ratio, cash_flow_to_debt_ratio, free_cash_flow_yield,
            cash_flow_adequacy_ratio,
            pe_ratio, pb_ratio, ps_ratio, ev_ebitda, dividend_yield,
            revenue_growth, net_income_growth, eps_growth, asset_growth
        ) VALUES (
            '2330', '2024Q4', 'sample', 1.00,
            0.1212, 0.1379, 0.8788, 0.0469,
            4.67, 4.16, 2.42, 75.00, 20.00,
            6.64, 5.89, 0.46, 0.88, 1.50,
            55, 62, 23, 94,
            0.236, 0.266, 0.25, 0.4247, 0.2155, 0.1771, 0.2616,
            3.73, 2.44, 0.02, 1.50,
            25.0, 6.0, 5.0, 15.0, 0.015,
            0.05, 0.06, 0.05, 0.04
        )
        """,
    )
    print("    已插入 2330 財務比率（2024Q4）")


def main() -> int:
    settings = get_settings()
    print(f"連線目標: {settings.DATABASE_URL.split('@')[-1]}")

    conn = psycopg2.connect(settings.DATABASE_URL, connect_timeout=8)
    conn.autocommit = True
    cur = conn.cursor()

    # 1. 建表（若不存在）
    cur.execute("SELECT to_regclass('public.companies')")
    if cur.fetchone()[0] is None:
        print("[1/3] 建立資料表...")
        _apply_sql_file(cur, PROJECT_ROOT / "database" / "init" / "01_create_tables.sql")
    else:
        print("[1/3] 資料表已存在，略過建表")

    # 2. 種子資料（若 companies 為空）
    cur.execute("SELECT count(*) FROM companies")
    company_count = cur.fetchone()[0]
    if company_count == 0:
        print("[2/3] 載入種子資料...")
        _apply_sql_file(cur, PROJECT_ROOT / "database" / "init" / "02_sample_data.sql")
    else:
        print(f"[2/3] companies 已有 {company_count} 筆，略過種子資料")

    # 3. 財務報表 + 比率
    print("[3/3] 插入範例財務資料...")
    _insert_financial_statements(cur)
    _insert_financial_ratios(cur)

    # 4. 彙總
    print("-" * 60)
    for t in ("companies", "financial_statements", "financial_ratios",
              "industry_benchmarks", "users", "user_watchlists"):
        cur.execute(f"SELECT count(*) FROM {t}")
        print(f"    {t}: {cur.fetchone()[0]} 筆")

    cur.close()
    conn.close()
    print("✅ 資料庫初始化完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
