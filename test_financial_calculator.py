#!/usr/bin/env python3
"""
財務計算器測試腳本
Test Financial Calculator
"""
import sys
from pathlib import Path
from decimal import Decimal

# 添加項目根目錄到Python路徑
sys.path.insert(0, str(Path(__file__).parent))

from src.services.financial_calculator import FinancialCalculator, FinancialStatements

def test_financial_calculator():
    """測試財務計算器功能"""
    print("🧮 開始財務計算器功能測試...")
    
    # 創建測試數據（基於NVIDIA CFO報告數據）
    nvidia_statements = FinancialStatements(
        # 資產負債表項目 (假設數據，單位：百萬美元)
        current_assets=Decimal('45000'),
        non_current_assets=Decimal('35000'), 
        total_assets=Decimal('80000'),
        current_liabilities=Decimal('15000'),
        non_current_liabilities=Decimal('20000'),
        total_liabilities=Decimal('35000'),
        shareholders_equity=Decimal('45000'),
        cash_and_equivalents=Decimal('25000'),
        accounts_receivable=Decimal('14100'),  # 從PDF提取的數據
        inventory=Decimal('6700'),             # 從PDF提取的數據
        accounts_payable=Decimal('5000'),
        short_term_debt=Decimal('1000'),
        long_term_debt=Decimal('9000'),
        
        # 損益表項目 (從PDF提取)
        revenue=Decimal('30040'),              # 從PDF提取
        cost_of_revenue=Decimal('7311'),       # 30040 - 22729
        gross_profit=Decimal('22729'),         # 從PDF計算 (Non-GAAP)
        operating_expenses=Decimal('2792'),    # 從PDF提取 (Non-GAAP)
        operating_income=Decimal('19937'),     # 從PDF提取 (Non-GAAP)  
        ebitda=Decimal('20500'),               # 估算
        interest_expense=Decimal('100'),
        pretax_income=Decimal('20317'),        # operating_income + other income
        tax_expense=Decimal('3365'),           # 估算
        net_income=Decimal('16952'),           # 從PDF提取 (Non-GAAP)
        eps=Decimal('0.68'),                   # 從PDF提取 (Non-GAAP)
        
        # 現金流量表項目
        operating_cash_flow=Decimal('14500'),  # 估算值
        investing_cash_flow=Decimal('-1300'),
        financing_cash_flow=Decimal('-7200'),
        free_cash_flow=Decimal('13483'),       # 從PDF推算
        capex=Decimal('1017')                  # 估算
    )
    
    print("📊 使用的測試數據（基於NVIDIA Q2FY25數據）:")
    print(f"   - 總資產: ${nvidia_statements.total_assets:,}M")
    print(f"   - 營收: ${nvidia_statements.revenue:,}M") 
    print(f"   - 淨利潤: ${nvidia_statements.net_income:,}M")
    print(f"   - 股東權益: ${nvidia_statements.shareholders_equity:,}M")
    
    # 初始化計算器
    calculator = FinancialCalculator()
    
    try:
        # 計算所有財務比率
        ratios = calculator.calculate_all_ratios(nvidia_statements)
        
        print("\n📈 計算的財務比率:")
        
        # 財務結構比率
        print(f"\n🏗️  財務結構比率:")
        print(f"   - 負債資產比: {ratios.debt_to_asset_ratio:.3f} ({ratios.debt_to_asset_ratio*100:.1f}%)")
        print(f"   - 負債權益比: {ratios.debt_to_equity_ratio:.3f}")
        print(f"   - 權益比率: {ratios.equity_ratio:.3f} ({ratios.equity_ratio*100:.1f}%)")
        
        # 償債能力比率
        print(f"\n💰 償債能力比率:")
        print(f"   - 流動比率: {ratios.current_ratio:.2f}")
        print(f"   - 速動比率: {ratios.quick_ratio:.2f}")
        print(f"   - 現金比率: {ratios.cash_ratio:.2f}")
        print(f"   - 利息保障倍數: {ratios.interest_coverage_ratio:.1f}")
        
        # 獲利能力比率  
        print(f"\n📊 獲利能力比率:")
        print(f"   - ROA (資產報酬率): {ratios.roa:.3f} ({ratios.roa*100:.1f}%)")
        print(f"   - ROE (權益報酬率): {ratios.roe:.3f} ({ratios.roe*100:.1f}%)")
        print(f"   - 毛利率: {ratios.gross_margin:.3f} ({ratios.gross_margin*100:.1f}%)")
        print(f"   - 營業利益率: {ratios.operating_margin:.3f} ({ratios.operating_margin*100:.1f}%)")
        print(f"   - 淨利率: {ratios.net_margin:.3f} ({ratios.net_margin*100:.1f}%)")
        
        # 經營能力比率
        print(f"\n⚙️  經營能力比率:")
        print(f"   - 總資產周轉率: {ratios.total_asset_turnover:.2f}")
        print(f"   - 應收帳款周轉率: {ratios.receivables_turnover:.1f}")
        print(f"   - 存貨周轉率: {ratios.inventory_turnover:.1f}")
        print(f"   - 應收帳款週轉天數: {ratios.days_sales_outstanding:.0f} 天")
        
        # 現金流量比率
        print(f"\n💵 現金流量比率:")
        print(f"   - 營業現金比率: {ratios.operating_cash_ratio:.2f}")
        print(f"   - 現金流量對債務比: {ratios.cash_flow_to_debt_ratio:.2f}")
        print(f"   - 自由現金流收益率: {ratios.free_cash_flow_yield:.3f}")
        
        # 評估財務健康度
        health, details = calculator.evaluate_financial_health(ratios)
        
        print(f"\n🏥 財務健康度評估:")
        print(f"   - 綜合評級: {health.value}")
        print(f"   - 綜合評分: {details['綜合評分']}")
        
        print(f"\n📋 詳細評估:")
        for category, assessment in details.items():
            if category != '綜合評分':
                print(f"   - {category}: {assessment}")
        
        # 與行業標準比較
        print(f"\n📊 與行業標準比較 (科技業):")
        print(f"   - ROE ({ratios.roe*100:.1f}%) vs 科技業平均 (15-20%): {'✅ 優於平均' if ratios.roe > 0.15 else '⚠️  低於平均'}")
        print(f"   - 淨利率 ({ratios.net_margin*100:.1f}%) vs 科技業平均 (10-15%): {'✅ 優於平均' if ratios.net_margin > 0.1 else '⚠️  低於平均'}")
        print(f"   - 流動比率 ({ratios.current_ratio:.1f}) vs 理想範圍 (1.5-3.0): {'✅ 良好' if 1.5 <= ratios.current_ratio <= 3.0 else '⚠️  需關注'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 財務計算過程中發生錯誤: {e}")
        return False

if __name__ == "__main__":
    success = test_financial_calculator()
    if success:
        print("\n✅ 財務計算器功能測試完成")
    else:
        print("\n❌ 財務計算器功能測試失敗")
        sys.exit(1)