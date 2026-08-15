#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美國股票重點公司測試腳本
US Stock Key Companies Test Script

測試 NYSE 和 NASDAQ 的代表性公司，驗證 Alpha Vantage 整合功能
精選測試避免 API 限流問題
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json
import time

# 確保能找到 src 模組
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 精選12家代表性美國公司 (避免 API 限流)
TEST_US_COMPANIES = {
    # NASDAQ 科技龍頭 (6家)
    "AAPL": {"name": "Apple Inc.", "exchange": "NASDAQ", "sector": "Technology", "industry": "Consumer Electronics"},
    "MSFT": {"name": "Microsoft Corporation", "exchange": "NASDAQ", "sector": "Technology", "industry": "Software"},
    "GOOGL": {"name": "Alphabet Inc.", "exchange": "NASDAQ", "sector": "Communication", "industry": "Internet Content"},
    "AMZN": {"name": "Amazon.com Inc.", "exchange": "NASDAQ", "sector": "Consumer Discretionary", "industry": "E-commerce"},
    "NVDA": {"name": "NVIDIA Corporation", "exchange": "NASDAQ", "sector": "Technology", "industry": "Semiconductors"},
    "TSLA": {"name": "Tesla Inc.", "exchange": "NASDAQ", "sector": "Consumer Discretionary", "industry": "Electric Vehicles"},
    
    # NYSE 傳統巨頭 (6家)
    "JNJ": {"name": "Johnson & Johnson", "exchange": "NYSE", "sector": "Healthcare", "industry": "Pharmaceuticals"},
    "JPM": {"name": "JPMorgan Chase & Co.", "exchange": "NYSE", "sector": "Financial Services", "industry": "Banking"},
    "V": {"name": "Visa Inc.", "exchange": "NYSE", "sector": "Financial Services", "industry": "Payment Systems"},
    "PG": {"name": "Procter & Gamble Co.", "exchange": "NYSE", "sector": "Consumer Staples", "industry": "Personal Care"},
    "HD": {"name": "The Home Depot Inc.", "exchange": "NYSE", "sector": "Consumer Discretionary", "industry": "Home Improvement"},
    "KO": {"name": "The Coca-Cola Company", "exchange": "NYSE", "sector": "Consumer Staples", "industry": "Beverages"},
}

class USStockKeyTester:
    """美國股票重點測試器"""
    
    def __init__(self):
        self.test_results = []
        self.exchange_stats = {}
        self.sector_stats = {}
        self.api_call_count = 0
        self.api_call_times = []
        
    def log_result(self, symbol: str, company_info: dict, success: bool, 
                  stock_data: Optional[dict] = None, error_msg: str = "", 
                  response_time: float = 0.0):
        """記錄測試結果"""
        result = {
            'symbol': symbol,
            'company_name': company_info['name'],
            'exchange': company_info['exchange'],
            'sector': company_info['sector'],
            'industry': company_info['industry'],
            'success': success,
            'stock_data': stock_data,
            'error': error_msg,
            'response_time': response_time,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        # 統計交易所和部門成功率
        exchange = company_info['exchange']
        sector = company_info['sector']
        
        if exchange not in self.exchange_stats:
            self.exchange_stats[exchange] = {'total': 0, 'success': 0, 'total_time': 0.0}
        if sector not in self.sector_stats:
            self.sector_stats[sector] = {'total': 0, 'success': 0}
            
        self.exchange_stats[exchange]['total'] += 1
        self.exchange_stats[exchange]['total_time'] += response_time
        self.sector_stats[sector]['total'] += 1
        
        if success:
            self.exchange_stats[exchange]['success'] += 1
            self.sector_stats[sector]['success'] += 1

    async def test_alpha_vantage_service(self):
        """測試 Alpha Vantage 服務美股功能"""
        print("🇺🇸 測試 Alpha Vantage 服務 - 美國重點公司...")
        print("="*80)
        
        try:
            from services.external_data_manager import ExternalDataManager
            
            async with ExternalDataManager(alpha_vantage_key=os.getenv("ALPHA_VANTAGE_API_KEY", "")) as manager:
                print(f"📊 開始測試 {len(TEST_US_COMPANIES)} 家美國重點公司...")
                print()
                
                # 逐一測試，加入適當延遲避免限流
                for i, (symbol, company_info) in enumerate(TEST_US_COMPANIES.items()):
                    print(f"📈 [{i+1}/{len(TEST_US_COMPANIES)}] 測試 {symbol} - {company_info['name'][:30]}")
                    
                    start_time = time.time()
                    
                    try:
                        quote = await manager.get_stock_quote(symbol)
                        response_time = time.time() - start_time
                        self.api_call_times.append(response_time)
                        self.api_call_count += 1
                        
                        if quote:
                            stock_data = {
                                'current_price': quote.current_price,
                                'price_change': quote.price_change,
                                'price_change_percent': quote.price_change_percent,
                                'volume': quote.volume,
                                'source': quote.source
                            }
                            
                            self.log_result(symbol, company_info, True, stock_data, "", response_time)
                            
                            # 格式化輸出
                            change_str = f"{quote.price_change:+.2f}" if quote.price_change is not None else "0.00"
                            change_pct_str = f"{quote.price_change_percent:+.2f}%" if quote.price_change_percent is not None else "0.00%"
                            volume_str = f"{quote.volume:,}" if quote.volume else "N/A"
                            
                            print(f"   ✅ 成功 | ${quote.current_price:.2f} | {change_str} ({change_pct_str})")
                            print(f"   📊 成交量: {volume_str} | 來源: {quote.source} | {response_time:.2f}s")
                            
                        else:
                            response_time = time.time() - start_time
                            self.log_result(symbol, company_info, False, error_msg="無法取得股價資料", response_time=response_time)
                            print(f"   ❌ 失敗 | 無法取得股價資料 | {response_time:.2f}s")
                            
                    except Exception as e:
                        response_time = time.time() - start_time
                        self.log_result(symbol, company_info, False, error_msg=str(e), response_time=response_time)
                        print(f"   💥 錯誤 | {str(e)[:40]} | {response_time:.2f}s")
                    
                    print()
                    
                    # API 限流保護：每次調用後暫停
                    if i < len(TEST_US_COMPANIES) - 1:  # 最後一個不需要暫停
                        print("⏳ 暫停 12 秒避免 API 限流...")
                        await asyncio.sleep(12)
                        print()
                
                return True
                
        except Exception as e:
            print(f"❌ Alpha Vantage 服務測試失敗: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def test_external_data_manager_integration(self):
        """測試外部資料管理器整合"""
        print("\n🔗 測試外部資料管理器整合...")
        print("="*80)
        
        try:
            from services.external_data_manager import ExternalDataManager
            
            # 選擇代表性公司進行整合測試
            sample_companies = {
                "AAPL": TEST_US_COMPANIES["AAPL"],  # 科技
                "JPM": TEST_US_COMPANIES["JPM"],   # 金融
                "JNJ": TEST_US_COMPANIES["JNJ"],   # 醫療
            }
            
            async with ExternalDataManager(alpha_vantage_key=os.getenv("ALPHA_VANTAGE_API_KEY", "")) as manager:
                print("📊 測試統一資料管理器的美股查詢...")
                print()
                
                integration_success = 0
                
                for symbol, company_info in sample_companies.items():
                    try:
                        quote = await manager.get_stock_quote(symbol)
                        
                        if quote:
                            print(f"✅ {company_info['name'][:25]:<25} ({symbol}) - {company_info['exchange']}")
                            print(f"   💰 ${quote.current_price:.2f} (來源: {quote.source})")
                            print(f"   🎯 {'成功使用 Alpha Vantage!' if quote.source == 'alpha_vantage' else '使用備援資料源'}")
                            print()
                            integration_success += 1
                        else:
                            print(f"❌ {company_info['name'][:25]:<25} ({symbol}) - 無法取得資料")
                            print()
                            
                    except Exception as e:
                        print(f"❌ {company_info['name'][:25]:<25} ({symbol}) - 錯誤: {e}")
                        print()
                    
                    # 每次查詢後短暫暫停
                    await asyncio.sleep(5)
                
                print(f"📊 整合測試結果: {integration_success}/{len(sample_companies)} 成功")
                return integration_success == len(sample_companies)
                
        except Exception as e:
            print(f"❌ 整合測試失敗: {e}")
            import traceback
            traceback.print_exc()
            return False

    def generate_analysis_report(self):
        """產生分析報告"""
        print("\n" + "="*80)
        print("📊 美國股票重點公司測試分析")
        print("="*80)
        
        # 整體統計
        total_companies = len(self.test_results)
        successful_companies = sum(1 for result in self.test_results if result['success'])
        
        print(f"\n🎯 整體測試結果:")
        print(f"   總測試公司數: {total_companies}")
        print(f"   成功取得資料: {successful_companies}")
        print(f"   成功率: {successful_companies/total_companies*100:.1f}%")
        print(f"   總API調用次數: {self.api_call_count}")
        
        if self.api_call_times:
            avg_response_time = sum(self.api_call_times) / len(self.api_call_times)
            min_time = min(self.api_call_times)
            max_time = max(self.api_call_times)
            print(f"   平均響應時間: {avg_response_time:.2f}秒")
            print(f"   響應時間範圍: {min_time:.2f}s - {max_time:.2f}s")
        
        # 按交易所統計
        print(f"\n🏛️ 交易所別成功率:")
        for exchange, stats in sorted(self.exchange_stats.items()):
            success_rate = stats['success']/stats['total']*100
            avg_time = stats['total_time']/stats['total'] if stats['total'] > 0 else 0
            print(f"   {exchange:<8} {stats['success']}/{stats['total']} ({success_rate:.1f}%) | 平均響應: {avg_time:.2f}s")
        
        # 按部門統計  
        print(f"\n🏢 產業部門成功率:")
        for sector, stats in sorted(self.sector_stats.items()):
            success_rate = stats['success']/stats['total']*100
            print(f"   {sector:<20} {stats['success']}/{stats['total']} ({success_rate:.1f}%)")
        
        # 成功案例展示
        print(f"\n💰 成功案例詳情:")
        successful_results = [r for r in self.test_results if r['success']]
        
        if successful_results:
            for i, result in enumerate(successful_results):
                stock_data = result['stock_data']
                if stock_data:
                    change_str = f"{stock_data['price_change']:+.2f}" if stock_data['price_change'] is not None else "0.00"
                    change_pct_str = f"{stock_data['price_change_percent']:+.2f}%" if stock_data['price_change_percent'] is not None else "0.00%"
                    print(f"   {i+1:2d}. {result['company_name'][:30]:<30} ({result['symbol']}) - {result['exchange']}")
                    print(f"       💰 ${stock_data['current_price']:>8.2f} | {change_str} ({change_pct_str}) | {result['sector']}")
        
        # 失敗案例
        failed_results = [r for r in self.test_results if not r['success']]
        if failed_results:
            print(f"\n❌ 失敗案例:")
            for result in failed_results:
                print(f"   • {result['company_name']} ({result['symbol']}) - {result['exchange']}")
                print(f"     錯誤: {result['error']}")

    def save_test_results(self):
        """儲存測試結果到檔案"""
        filename = f"us_key_stocks_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report_data = {
            'test_info': {
                'test_date': datetime.now().isoformat(),
                'total_companies': len(self.test_results),
                'api_calls': self.api_call_count,
                'test_companies': TEST_US_COMPANIES
            },
            'results': self.test_results,
            'statistics': {
                'exchange_stats': self.exchange_stats,
                'sector_stats': self.sector_stats
            },
            'performance': {
                'api_call_times': self.api_call_times,
                'avg_response_time': sum(self.api_call_times) / len(self.api_call_times) if self.api_call_times else 0
            }
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 測試結果已儲存至: {filename}")

async def main():
    """主測試函數"""
    print("🚀 美國股票重點公司測試開始...")
    print(f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 顯示測試公司清單
    print("📋 測試公司清單:")
    print("-" * 80)
    
    nasdaq_companies = {k: v for k, v in TEST_US_COMPANIES.items() if v['exchange'] == 'NASDAQ'}
    nyse_companies = {k: v for k, v in TEST_US_COMPANIES.items() if v['exchange'] == 'NYSE'}
    
    print(f"🔵 NASDAQ ({len(nasdaq_companies)} 家):")
    for symbol, info in nasdaq_companies.items():
        print(f"   {symbol:<6} - {info['name'][:40]:<40} | {info['sector']}")
    
    print(f"\n🔴 NYSE ({len(nyse_companies)} 家):")
    for symbol, info in nyse_companies.items():
        print(f"   {symbol:<6} - {info['name'][:40]:<40} | {info['sector']}")
    print()
    
    tester = USStockKeyTester()
    
    # 測試 1: Alpha Vantage 服務
    alpha_vantage_success = await tester.test_alpha_vantage_service()
    
    # 測試 2: 外部資料管理器整合
    integration_success = await tester.test_external_data_manager_integration()
    
    # 產生分析報告
    tester.generate_analysis_report()
    
    # 儲存結果
    tester.save_test_results()
    
    # 最終結果
    print("\n" + "="*80)
    print("🏁 測試完成摘要")
    print("="*80)
    
    total_tests = 2
    passed_tests = sum([alpha_vantage_success, integration_success])
    
    print(f"📊 測試項目: {passed_tests}/{total_tests} 通過")
    print(f"   Alpha Vantage 服務測試: {'✅ PASS' if alpha_vantage_success else '❌ FAIL'}")
    print(f"   資料管理器整合測試: {'✅ PASS' if integration_success else '❌ FAIL'}")
    
    if passed_tests == total_tests:
        print(f"\n🎉 所有測試通過！Alpha Vantage 整合支援美國重點股票查詢！")
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