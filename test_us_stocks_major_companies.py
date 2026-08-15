#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美國股票主要交易所測試腳本
US Stock Major Exchanges Test Script

測試 NYSE 和 NASDAQ 兩大交易所的前20大公司
驗證 Alpha Vantage 整合功能和美股資料品質
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

# NYSE 和 NASDAQ 前20大公司 (按市值排序)
TEST_US_COMPANIES = {
    # NASDAQ 科技巨頭
    "AAPL": {"name": "Apple Inc.", "exchange": "NASDAQ", "sector": "Technology", "industry": "Consumer Electronics"},
    "MSFT": {"name": "Microsoft Corporation", "exchange": "NASDAQ", "sector": "Technology", "industry": "Software"},
    "GOOGL": {"name": "Alphabet Inc.", "exchange": "NASDAQ", "sector": "Communication", "industry": "Internet Content"},
    "AMZN": {"name": "Amazon.com Inc.", "exchange": "NASDAQ", "sector": "Consumer Discretionary", "industry": "E-commerce"},
    "NVDA": {"name": "NVIDIA Corporation", "exchange": "NASDAQ", "sector": "Technology", "industry": "Semiconductors"},
    "TSLA": {"name": "Tesla Inc.", "exchange": "NASDAQ", "sector": "Consumer Discretionary", "industry": "Electric Vehicles"},
    "META": {"name": "Meta Platforms Inc.", "exchange": "NASDAQ", "sector": "Communication", "industry": "Social Media"},
    "NFLX": {"name": "Netflix Inc.", "exchange": "NASDAQ", "sector": "Communication", "industry": "Streaming"},
    "ADBE": {"name": "Adobe Inc.", "exchange": "NASDAQ", "sector": "Technology", "industry": "Software"},
    "INTC": {"name": "Intel Corporation", "exchange": "NASDAQ", "sector": "Technology", "industry": "Semiconductors"},
    
    # NYSE 傳統巨頭
    "BRK.B": {"name": "Berkshire Hathaway Inc.", "exchange": "NYSE", "sector": "Financial Services", "industry": "Conglomerate"},
    "UNH": {"name": "UnitedHealth Group Inc.", "exchange": "NYSE", "sector": "Healthcare", "industry": "Health Insurance"},
    "JNJ": {"name": "Johnson & Johnson", "exchange": "NYSE", "sector": "Healthcare", "industry": "Pharmaceuticals"},
    "XOM": {"name": "Exxon Mobil Corporation", "exchange": "NYSE", "sector": "Energy", "industry": "Oil & Gas"},
    "JPM": {"name": "JPMorgan Chase & Co.", "exchange": "NYSE", "sector": "Financial Services", "industry": "Banking"},
    "PG": {"name": "Procter & Gamble Co.", "exchange": "NYSE", "sector": "Consumer Staples", "industry": "Personal Care"},
    "MA": {"name": "Mastercard Incorporated", "exchange": "NYSE", "sector": "Financial Services", "industry": "Payment Systems"},
    "V": {"name": "Visa Inc.", "exchange": "NYSE", "sector": "Financial Services", "industry": "Payment Systems"},
    "HD": {"name": "The Home Depot Inc.", "exchange": "NYSE", "sector": "Consumer Discretionary", "industry": "Home Improvement"},
    "CVX": {"name": "Chevron Corporation", "exchange": "NYSE", "sector": "Energy", "industry": "Oil & Gas"},
    
    # 額外重要公司
    "KO": {"name": "The Coca-Cola Company", "exchange": "NYSE", "sector": "Consumer Staples", "industry": "Beverages"},
    "PFE": {"name": "Pfizer Inc.", "exchange": "NYSE", "sector": "Healthcare", "industry": "Pharmaceuticals"},
    "DIS": {"name": "The Walt Disney Company", "exchange": "NYSE", "sector": "Communication", "industry": "Entertainment"},
    "WMT": {"name": "Walmart Inc.", "exchange": "NYSE", "sector": "Consumer Staples", "industry": "Retail"},
}

class USStockExchangeTester:
    """美國股票交易所測試器"""
    
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
        print("🇺🇸 測試 Alpha Vantage 服務 - 美國主要交易所股票...")
        print("="*90)
        
        try:
            from services.external_data_manager import ExternalDataManager
            
            async with ExternalDataManager(alpha_vantage_key=os.getenv("ALPHA_VANTAGE_API_KEY", "")) as manager:
                print(f"📊 開始測試 {len(TEST_US_COMPANIES)} 家美國公司...")
                print()
                
                # 分批測試避免API限流 (Alpha Vantage 有每分鐘限制)
                symbols = list(TEST_US_COMPANIES.keys())
                batch_size = 5  # 每批5家公司
                
                for i in range(0, len(symbols), batch_size):
                    batch_symbols = symbols[i:i+batch_size]
                    print(f"📦 測試批次 {i//batch_size + 1}: {', '.join(batch_symbols)}")
                    
                    for symbol in batch_symbols:
                        company_info = TEST_US_COMPANIES[symbol]
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
                                
                                print(f"✅ {company_info['name'][:25]:<25} ({symbol}) - {company_info['exchange']}")
                                print(f"   💰 股價: ${quote.current_price:.2f} | 漲跌: {change_str} ({change_pct_str})")
                                print(f"   📊 成交量: {volume_str} | 來源: {quote.source} | 響應: {response_time:.2f}s")
                                print()
                                
                            else:
                                response_time = time.time() - start_time
                                self.log_result(symbol, company_info, False, error_msg="無法取得股價資料", response_time=response_time)
                                print(f"❌ {company_info['name'][:25]:<25} ({symbol}) - {company_info['exchange']}")
                                print(f"   ⚠️ 無法取得股價資料 | 響應: {response_time:.2f}s")
                                print()
                                
                        except Exception as e:
                            response_time = time.time() - start_time
                            self.log_result(symbol, company_info, False, error_msg=str(e), response_time=response_time)
                            print(f"❌ {company_info['name'][:25]:<25} ({symbol}) - {company_info['exchange']}")
                            print(f"   💥 錯誤: {str(e)[:50]} | 響應: {response_time:.2f}s")
                            print()
                    
                    # 批次間暫停避免API限流
                    if i + batch_size < len(symbols):
                        print(f"⏳ 暫停 15 秒避免 API 限流...")
                        await asyncio.sleep(15)
                        print()
                
                return True
                
        except Exception as e:
            print(f"❌ Alpha Vantage 服務測試失敗: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def test_external_data_manager_fallback(self):
        """測試外部資料管理器的美股備援機制"""
        print("\n🔄 測試外部資料管理器備援機制...")
        print("="*90)
        
        try:
            from services.external_data_manager import ExternalDataManager, DataSource
            
            # 測試強制指定不同資料源
            test_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
            
            async with ExternalDataManager(alpha_vantage_key=os.getenv("ALPHA_VANTAGE_API_KEY", "")) as manager:
                print("📊 測試資料源優先順序和備援機制...")
                print()
                
                fallback_success = 0
                
                for symbol in test_symbols:
                    company_info = TEST_US_COMPANIES[symbol]
                    
                    try:
                        # 測試預設 (應優先使用 Alpha Vantage)
                        quote = await manager.get_stock_quote(symbol)
                        
                        if quote:
                            print(f"✅ {company_info['name'][:20]:<20} ({symbol})")
                            print(f"   💰 ${quote.current_price:.2f} (來源: {quote.source})")
                            print(f"   🎯 {'成功使用 Alpha Vantage!' if quote.source == 'alpha_vantage' else '使用備援資料源'}")
                            print()
                            fallback_success += 1
                        else:
                            print(f"❌ {company_info['name'][:20]:<20} ({symbol}) - 無法取得資料")
                            print()
                            
                    except Exception as e:
                        print(f"❌ {company_info['name'][:20]:<20} ({symbol}) - 錯誤: {e}")
                        print()
                
                print(f"📊 備援機制測試結果: {fallback_success}/{len(test_symbols)} 成功")
                return fallback_success == len(test_symbols)
                
        except Exception as e:
            print(f"❌ 備援機制測試失敗: {e}")
            import traceback
            traceback.print_exc()
            return False

    def generate_exchange_analysis(self):
        """產生交易所分析報告"""
        print("\n" + "="*90)
        print("📊 美國股票交易所分析報告")
        print("="*90)
        
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
            print(f"   平均響應時間: {avg_response_time:.2f}秒")
        
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
        
        # 成功案例展示（按股價排序）
        print(f"\n💰 成功案例 (依股價排序):")
        successful_results = [r for r in self.test_results if r['success']]
        
        if successful_results:
            successful_results.sort(key=lambda x: x['stock_data']['current_price'] if x['stock_data'] else 0, reverse=True)
            
            for i, result in enumerate(successful_results[:15]):  # 顯示前15名
                stock_data = result['stock_data']
                if stock_data:
                    change_str = f"{stock_data['price_change']:+.2f}" if stock_data['price_change'] is not None else "0.00"
                    print(f"   {i+1:2d}. {result['company_name'][:25]:<25} ({result['symbol']}) "
                          f"${stock_data['current_price']:>8.2f} ({change_str}) - {result['exchange']}")
        
        # 失敗案例
        failed_results = [r for r in self.test_results if not r['success']]
        if failed_results:
            print(f"\n❌ 失敗案例:")
            for result in failed_results:
                print(f"   • {result['company_name']} ({result['symbol']}) - {result['exchange']}")
                print(f"     錯誤: {result['error']}")

    def generate_performance_analysis(self):
        """產生效能分析"""
        print(f"\n⚡ API 效能分析:")
        
        if self.api_call_times:
            response_times = self.api_call_times
            min_time = min(response_times)
            max_time = max(response_times)
            avg_time = sum(response_times) / len(response_times)
            
            print(f"   最快響應: {min_time:.2f}秒")
            print(f"   最慢響應: {max_time:.2f}秒") 
            print(f"   平均響應: {avg_time:.2f}秒")
            
            # 響應時間分佈
            fast_calls = sum(1 for t in response_times if t < 1.0)
            medium_calls = sum(1 for t in response_times if 1.0 <= t < 3.0)
            slow_calls = sum(1 for t in response_times if t >= 3.0)
            
            print(f"   響應時間分佈:")
            print(f"     < 1秒: {fast_calls} 次 ({fast_calls/len(response_times)*100:.1f}%)")
            print(f"     1-3秒: {medium_calls} 次 ({medium_calls/len(response_times)*100:.1f}%)")
            print(f"     > 3秒: {slow_calls} 次 ({slow_calls/len(response_times)*100:.1f}%)")

    def save_test_results(self):
        """儲存測試結果到檔案"""
        filename = f"us_stocks_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
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
    print("🚀 美國股票主要交易所測試開始...")
    print(f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 顯示測試公司清單
    print("📋 測試公司清單:")
    print("-" * 90)
    
    nasdaq_companies = {k: v for k, v in TEST_US_COMPANIES.items() if v['exchange'] == 'NASDAQ'}
    nyse_companies = {k: v for k, v in TEST_US_COMPANIES.items() if v['exchange'] == 'NYSE'}
    
    print(f"🔵 NASDAQ ({len(nasdaq_companies)} 家):")
    for symbol, info in nasdaq_companies.items():
        print(f"   {symbol:<6} - {info['name'][:30]:<30} | {info['sector']:<20}")
    
    print(f"\n🔴 NYSE ({len(nyse_companies)} 家):")
    for symbol, info in nyse_companies.items():
        print(f"   {symbol:<6} - {info['name'][:30]:<30} | {info['sector']:<20}")
    print()
    
    tester = USStockExchangeTester()
    
    # 測試 1: Alpha Vantage 服務
    alpha_vantage_success = await tester.test_alpha_vantage_service()
    
    # 測試 2: 外部資料管理器備援機制
    fallback_success = await tester.test_external_data_manager_fallback()
    
    # 產生分析報告
    tester.generate_exchange_analysis()
    tester.generate_performance_analysis()
    
    # 儲存結果
    tester.save_test_results()
    
    # 最終結果
    print("\n" + "="*90)
    print("🏁 測試完成摘要")
    print("="*90)
    
    total_tests = 2
    passed_tests = sum([alpha_vantage_success, fallback_success])
    
    print(f"📊 測試項目: {passed_tests}/{total_tests} 通過")
    print(f"   Alpha Vantage 服務測試: {'✅ PASS' if alpha_vantage_success else '❌ FAIL'}")
    print(f"   備援機制測試: {'✅ PASS' if fallback_success else '❌ FAIL'}")
    
    if passed_tests == total_tests:
        print(f"\n🎉 所有測試通過！Alpha Vantage 整合支援美國主要交易所股票查詢！")
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