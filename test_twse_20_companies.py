#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TWSE 20家不同產業公司測試腳本
Test TWSE Integration with 20 Companies from Different Industries

測試橫跨台灣主要產業的20家代表性公司
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional
import json

# 確保能找到 src 模組
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 20家不同產業的代表性公司
TEST_COMPANIES = {
    # 半導體產業
    "2330": {"name": "台積電", "industry": "半導體", "sector": "科技"},
    "2454": {"name": "聯發科", "industry": "半導體", "sector": "科技"},
    "3034": {"name": "聯詠", "industry": "半導體", "sector": "科技"},
    
    # 電子製造
    "2317": {"name": "鴻海", "industry": "電子製造", "sector": "科技"},
    "2382": {"name": "廣達", "industry": "電子製造", "sector": "科技"},
    
    # 金融保險
    "2882": {"name": "國泰金", "industry": "金融保險", "sector": "金融"},
    "2891": {"name": "中信金", "industry": "金融保險", "sector": "金融"},
    "2892": {"name": "第一金", "industry": "金融保險", "sector": "金融"},
    
    # 傳統製造
    "1301": {"name": "台塑", "industry": "石化工業", "sector": "傳統製造"},
    "1303": {"name": "南亞", "industry": "石化工業", "sector": "傳統製造"},
    "2002": {"name": "中鋼", "industry": "鋼鐵工業", "sector": "傳統製造"},
    
    # 食品餐飲
    "1216": {"name": "統一", "industry": "食品工業", "sector": "民生消費"},
    "1227": {"name": "佳格", "industry": "食品工業", "sector": "民生消費"},
    
    # 零售通路
    "2912": {"name": "統一超", "industry": "零售業", "sector": "民生消費"},
    "2915": {"name": "潤泰全", "industry": "零售業", "sector": "民生消費"},
    
    # 電信通訊
    "3045": {"name": "台灣大", "industry": "電信業", "sector": "電信"},
    "4904": {"name": "遠傳", "industry": "電信業", "sector": "電信"},
    
    # 營建房地產
    "5880": {"name": "合庫金", "industry": "金融業", "sector": "金融"},
    "2886": {"name": "兆豐金", "industry": "金融業", "sector": "金融"},
    
    # 航運物流
    "2603": {"name": "長榮", "industry": "海運業", "sector": "航運"}
}

class IndustryDiversityTester:
    """產業多元化測試器"""
    
    def __init__(self):
        self.test_results = []
        self.industry_stats = {}
        self.sector_stats = {}
        
    def log_result(self, symbol: str, company_info: dict, success: bool, 
                  stock_data: Optional[dict] = None, error_msg: str = ""):
        """記錄測試結果"""
        result = {
            'symbol': symbol,
            'company_name': company_info['name'],
            'industry': company_info['industry'],
            'sector': company_info['sector'],
            'success': success,
            'stock_data': stock_data,
            'error': error_msg,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        # 統計產業和部門成功率
        industry = company_info['industry']
        sector = company_info['sector']
        
        if industry not in self.industry_stats:
            self.industry_stats[industry] = {'total': 0, 'success': 0}
        if sector not in self.sector_stats:
            self.sector_stats[sector] = {'total': 0, 'success': 0}
            
        self.industry_stats[industry]['total'] += 1
        self.sector_stats[sector]['total'] += 1
        
        if success:
            self.industry_stats[industry]['success'] += 1
            self.sector_stats[sector]['success'] += 1

    async def test_twse_service_companies(self):
        """測試 TWSE 服務的20家公司"""
        print("🧪 測試 TWSE 服務 - 20家不同產業公司...")
        print("="*80)
        
        try:
            from services.twse_service import TWStockExchangeService
            
            async with TWStockExchangeService() as twse:
                print(f"📊 開始測試 {len(TEST_COMPANIES)} 家公司...")
                print()
                
                # 批量獲取所有公司資料
                symbols = list(TEST_COMPANIES.keys())
                quotes = await twse.get_multiple_quotes(symbols)
                
                # 逐一處理結果
                for symbol, company_info in TEST_COMPANIES.items():
                    quote = quotes.get(symbol)
                    
                    if quote:
                        stock_data = {
                            'current_price': quote.current_price,
                            'change': quote.change,
                            'change_percent': quote.change_percent,
                            'volume': quote.volume,
                            'turnover': quote.turnover
                        }
                        
                        self.log_result(symbol, company_info, True, stock_data)
                        
                        # 格式化輸出
                        change_str = f"{quote.change:+.2f}" if quote.change is not None else "0.00"
                        change_pct_str = f"{quote.change_percent:+.2f}%" if quote.change_percent is not None else "0.00%"
                        volume_str = f"{quote.volume:,}" if quote.volume else "N/A"
                        
                        print(f"✅ {company_info['name']} ({symbol}) - {company_info['industry']}")
                        print(f"   💰 股價: NT${quote.current_price:.2f} | 漲跌: {change_str} ({change_pct_str})")
                        print(f"   📊 成交量: {volume_str} 股 | 成交值: {quote.turnover:,.0f}" if quote.turnover else "")
                        print()
                        
                    else:
                        self.log_result(symbol, company_info, False, error_msg="無法取得股價資料")
                        print(f"❌ {company_info['name']} ({symbol}) - {company_info['industry']}")
                        print(f"   ⚠️ 無法取得股價資料")
                        print()
                
                return True
                
        except Exception as e:
            print(f"❌ TWSE 服務測試失敗: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def test_external_data_manager_companies(self):
        """測試外部資料管理器的20家公司"""
        print("\n🔗 測試外部資料管理器整合...")
        print("="*80)
        
        try:
            from services.external_data_manager import ExternalDataManager
            
            async with ExternalDataManager(alpha_vantage_key=os.getenv("ALPHA_VANTAGE_API_KEY", "")) as manager:
                print("📊 測試統一資料管理器的公司查詢...")
                print()
                
                # 選擇5家代表性公司進行詳細測試
                sample_companies = {
                    "2330": TEST_COMPANIES["2330"],  # 半導體
                    "2882": TEST_COMPANIES["2882"],  # 金融
                    "1301": TEST_COMPANIES["1301"],  # 石化
                    "1216": TEST_COMPANIES["1216"],  # 食品
                    "2603": TEST_COMPANIES["2603"]   # 航運
                }
                
                manager_success = 0
                
                for symbol, company_info in sample_companies.items():
                    try:
                        quote = await manager.get_stock_quote(symbol)
                        
                        if quote:
                            print(f"✅ {company_info['name']} ({symbol}) - {company_info['industry']}")
                            print(f"   💰 股價: NT${quote.current_price:.2f} (來源: {quote.source})")
                            print(f"   🎯 {'成功使用 TWSE!' if quote.source == 'twse' else '使用備援資料源'}")
                            print()
                            manager_success += 1
                        else:
                            print(f"❌ {company_info['name']} ({symbol}) - 無法取得資料")
                            print()
                            
                    except Exception as e:
                        print(f"❌ {company_info['name']} ({symbol}) - 錯誤: {e}")
                        print()
                
                print(f"📊 外部資料管理器測試結果: {manager_success}/{len(sample_companies)} 成功")
                return manager_success == len(sample_companies)
                
        except Exception as e:
            print(f"❌ 外部資料管理器測試失敗: {e}")
            import traceback
            traceback.print_exc()
            return False

    def generate_industry_analysis(self):
        """產生產業分析報告"""
        print("\n" + "="*80)
        print("📊 產業多元化分析報告")
        print("="*80)
        
        # 整體統計
        total_companies = len(self.test_results)
        successful_companies = sum(1 for result in self.test_results if result['success'])
        
        print(f"\n🎯 整體測試結果:")
        print(f"   總測試公司數: {total_companies}")
        print(f"   成功取得資料: {successful_companies}")
        print(f"   成功率: {successful_companies/total_companies*100:.1f}%")
        
        # 按產業統計
        print(f"\n🏭 產業別成功率:")
        for industry, stats in sorted(self.industry_stats.items()):
            success_rate = stats['success']/stats['total']*100
            print(f"   {industry:<12} {stats['success']}/{stats['total']} ({success_rate:.1f}%)")
        
        # 按部門統計  
        print(f"\n🏢 部門別成功率:")
        for sector, stats in sorted(self.sector_stats.items()):
            success_rate = stats['success']/stats['total']*100
            print(f"   {sector:<12} {stats['success']}/{stats['total']} ({success_rate:.1f}%)")
        
        # 成功案例展示
        print(f"\n💰 成功案例 (依股價排序):")
        successful_results = [r for r in self.test_results if r['success']]
        successful_results.sort(key=lambda x: x['stock_data']['current_price'], reverse=True)
        
        for i, result in enumerate(successful_results[:10]):  # 顯示前10名
            stock_data = result['stock_data']
            change_str = f"{stock_data['change']:+.2f}" if stock_data['change'] is not None else "0.00"
            print(f"   {i+1:2d}. {result['company_name']:<8} ({result['symbol']}) "
                  f"NT${stock_data['current_price']:>8.2f} ({change_str}) - {result['industry']}")
        
        # 失敗案例
        failed_results = [r for r in self.test_results if not r['success']]
        if failed_results:
            print(f"\n❌ 失敗案例:")
            for result in failed_results:
                print(f"   • {result['company_name']} ({result['symbol']}) - {result['industry']}")
                print(f"     錯誤: {result['error']}")

    def save_test_results(self):
        """儲存測試結果到檔案"""
        filename = f"twse_20_companies_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report_data = {
            'test_info': {
                'test_date': datetime.now().isoformat(),
                'total_companies': len(self.test_results),
                'test_companies': TEST_COMPANIES
            },
            'results': self.test_results,
            'statistics': {
                'industry_stats': self.industry_stats,
                'sector_stats': self.sector_stats
            }
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 測試結果已儲存至: {filename}")

async def main():
    """主測試函數"""
    print("🚀 TWSE 20家不同產業公司測試開始...")
    print(f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 顯示測試公司清單
    print("📋 測試公司清單:")
    print("-" * 80)
    for symbol, info in TEST_COMPANIES.items():
        print(f"   {symbol} - {info['name']:<10} | {info['industry']:<12} | {info['sector']}")
    print()
    
    tester = IndustryDiversityTester()
    
    # 測試 1: TWSE 服務
    twse_success = await tester.test_twse_service_companies()
    
    # 測試 2: 外部資料管理器
    manager_success = await tester.test_external_data_manager_companies()
    
    # 產生分析報告
    tester.generate_industry_analysis()
    
    # 儲存結果
    tester.save_test_results()
    
    # 最終結果
    print("\n" + "="*80)
    print("🏁 測試完成摘要")
    print("="*80)
    
    total_tests = 2
    passed_tests = sum([twse_success, manager_success])
    
    print(f"📊 測試項目: {passed_tests}/{total_tests} 通過")
    print(f"   TWSE 服務測試: {'✅ PASS' if twse_success else '❌ FAIL'}")
    print(f"   資料管理器測試: {'✅ PASS' if manager_success else '❌ FAIL'}")
    
    if passed_tests == total_tests:
        print(f"\n🎉 所有測試通過！TWSE 整合可支援多元化產業股票查詢！")
        return 0
    else:
        print(f"\n⚠️ 部分測試失敗，請檢查相關配置")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️ 測試被中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 測試執行失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)