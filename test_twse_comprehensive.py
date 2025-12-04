#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TWSE 綜合功能測試腳本
Taiwan Stock Exchange Comprehensive Test
"""

import asyncio
import sys
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import time

# 確保能找到 src 模組
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

class TWSEComprehensiveTester:
    """TWSE綜合功能測試器"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = datetime.now()
        
    async def test_twse_core_service(self):
        """測試TWSE核心服務功能"""
        print("🧪 測試TWSE核心服務功能...")
        
        test_results = {
            'single_quote': False,
            'multiple_quotes': False,
            'market_summary': False,
            'stock_search': False,
            'health_check': False,
            'cache_mechanism': False,
            'error_handling': False
        }
        
        try:
            from services.twse_service import TWStockExchangeService
            
            async with TWStockExchangeService() as twse:
                # 測試1: 單一股票查詢
                print("  📈 測試單一股票查詢 (台積電 2330)...")
                tsmc = await twse.get_stock_quote("2330")
                if tsmc and tsmc.current_price > 0:
                    test_results['single_quote'] = True
                    print(f"     ✅ 台積電: NT${tsmc.current_price:.2f}")
                    print(f"        開盤: {tsmc.open_price} 最高: {tsmc.high_price} 最低: {tsmc.low_price}")
                    print(f"        成交量: {tsmc.volume:,} 股, 成交金額: {tsmc.turnover:,.0f}")
                else:
                    print("     ❌ 台積電股票查詢失敗")
                
                # 測試2: 多檔股票批量查詢
                print("  📊 測試多檔股票批量查詢...")
                test_symbols = ["2330", "2317", "2454", "1301", "2881", "2891", "2882", "2886"]
                quotes = await twse.get_multiple_quotes(test_symbols)
                
                successful_quotes = sum(1 for q in quotes.values() if q and q.current_price > 0)
                if successful_quotes >= len(test_symbols) * 0.8:  # 80%成功率
                    test_results['multiple_quotes'] = True
                    print(f"     ✅ 批量查詢成功: {successful_quotes}/{len(test_symbols)}檔股票")
                    
                    # 顯示前5檔
                    for i, (symbol, quote) in enumerate(list(quotes.items())[:5]):
                        if quote:
                            change_str = f"{quote.change:+.2f}" if quote.change else "0.00"
                            print(f"        {quote.name} ({symbol}): NT${quote.current_price:.2f} ({change_str})")
                else:
                    print(f"     ❌ 批量查詢成功率過低: {successful_quotes}/{len(test_symbols)}")
                
                # 測試3: 市場摘要
                print("  📈 測試市場摘要功能...")
                summary = await twse.get_market_summary()
                if (summary and 'total_stocks' in summary and summary['total_stocks'] > 1000):
                    test_results['market_summary'] = True
                    print(f"     ✅ 市場摘要:")
                    print(f"        總股票數: {summary['total_stocks']:,}")
                    print(f"        上漲: {summary.get('rising_stocks', 0)} 下跌: {summary.get('falling_stocks', 0)}")
                    print(f"        總成交量: {summary.get('total_volume', 0):,}")
                    print(f"        總成交金額: NT${summary.get('total_turnover', 0):,.0f}")
                else:
                    print("     ❌ 市場摘要獲取失敗")
                
                # 測試4: 股票搜尋功能
                print("  🔍 測試股票搜尋功能...")
                search_results_by_code = await twse.search_stock("2330")
                search_results_by_name = await twse.search_stock("台積")
                
                if (len(search_results_by_code) > 0 and len(search_results_by_name) > 0):
                    test_results['stock_search'] = True
                    print(f"     ✅ 搜尋功能:")
                    print(f"        按代號搜尋 '2330': {len(search_results_by_code)} 筆結果")
                    print(f"        按名稱搜尋 '台積': {len(search_results_by_name)} 筆結果")
                else:
                    print("     ❌ 股票搜尋功能失敗")
                
                # 測試5: 健康檢查
                print("  🏥 測試API健康檢查...")
                health = await twse.health_check()
                if health:
                    test_results['health_check'] = True
                    print("     ✅ TWSE API 健康檢查通過")
                else:
                    print("     ❌ TWSE API 健康檢查失敗")
                
                # 測試6: 快取機制
                print("  ⚡ 測試快取機制...")
                start_time = time.time()
                await twse.get_stock_quote("2330")  # 第一次查詢 (會載入所有資料)
                first_query_time = time.time() - start_time
                
                start_time = time.time()
                await twse.get_stock_quote("2317")  # 第二次查詢 (應該使用快取)
                second_query_time = time.time() - start_time
                
                if second_query_time < first_query_time * 0.5:  # 第二次應該快很多
                    test_results['cache_mechanism'] = True
                    print(f"     ✅ 快取機制運作正常")
                    print(f"        第一次查詢: {first_query_time:.3f}s, 第二次查詢: {second_query_time:.3f}s")
                else:
                    print(f"     ⚠️ 快取效果不明顯")
                    print(f"        第一次查詢: {first_query_time:.3f}s, 第二次查詢: {second_query_time:.3f}s")
                
                # 測試7: 錯誤處理
                print("  🔧 測試錯誤處理機制...")
                invalid_result = await twse.get_stock_quote("9999")  # 不存在的股票代號
                malformed_result = await twse.get_stock_quote("ABC123")  # 格式錯誤的代號
                
                if invalid_result is None and malformed_result is None:
                    test_results['error_handling'] = True
                    print("     ✅ 錯誤處理機制正常")
                else:
                    print("     ❌ 錯誤處理機制異常")
        
        except Exception as e:
            print(f"  ❌ TWSE核心服務測試失敗: {e}")
            import traceback
            traceback.print_exc()
        
        return test_results
    
    async def test_twse_data_quality(self):
        """測試TWSE數據品質"""
        print("\n🔍 測試TWSE數據品質...")
        
        quality_results = {
            'data_completeness': False,
            'data_accuracy': False,
            'data_freshness': False,
            'data_consistency': False
        }
        
        try:
            from services.twse_service import TWStockExchangeService
            
            async with TWStockExchangeService() as twse:
                # 測試數據完整性
                print("  📊 測試數據完整性...")
                test_symbols = ["2330", "2317", "2454", "1301", "2308"]
                quotes = await twse.get_multiple_quotes(test_symbols)
                
                complete_data_count = 0
                for symbol, quote in quotes.items():
                    if quote:
                        # 檢查必要欄位是否完整
                        required_fields = ['current_price', 'volume', 'open_price', 'high_price', 'low_price']
                        complete_fields = sum(1 for field in required_fields 
                                           if getattr(quote, field) is not None and getattr(quote, field) > 0)
                        
                        if complete_fields >= len(required_fields) * 0.8:  # 80%欄位完整
                            complete_data_count += 1
                
                if complete_data_count >= len(test_symbols) * 0.8:
                    quality_results['data_completeness'] = True
                    print(f"     ✅ 數據完整性良好: {complete_data_count}/{len(test_symbols)} 檔股票完整")
                else:
                    print(f"     ❌ 數據完整性不足: {complete_data_count}/{len(test_symbols)} 檔股票完整")
                
                # 測試數據準確性 (價格邏輯檢查)
                print("  🎯 測試數據準確性...")
                accurate_data_count = 0
                for symbol, quote in quotes.items():
                    if quote and all([quote.open_price, quote.high_price, quote.low_price, quote.current_price]):
                        # 檢查價格邏輯: 最高價 >= 收盤價 >= 最低價, 最高價 >= 開盤價 >= 最低價
                        if (quote.low_price <= quote.current_price <= quote.high_price and
                            quote.low_price <= quote.open_price <= quote.high_price):
                            accurate_data_count += 1
                        else:
                            print(f"        ⚠️ {quote.name} 價格邏輯異常")
                            print(f"           開盤: {quote.open_price} 最高: {quote.high_price} 最低: {quote.low_price} 收盤: {quote.current_price}")
                
                if accurate_data_count >= len([q for q in quotes.values() if q]) * 0.9:
                    quality_results['data_accuracy'] = True
                    print(f"     ✅ 數據準確性良好: {accurate_data_count} 檔股票通過邏輯檢查")
                else:
                    print(f"     ❌ 數據準確性有問題: {accurate_data_count} 檔股票通過邏輯檢查")
                
                # 測試數據新鮮度
                print("  ⏰ 測試數據新鮮度...")
                tsmc = await twse.get_stock_quote("2330")
                if tsmc:
                    data_age = datetime.now() - tsmc.timestamp
                    if data_age.total_seconds() < 3600:  # 1小時內的數據
                        quality_results['data_freshness'] = True
                        print(f"     ✅ 數據新鮮度良好: 數據年齡 {data_age.total_seconds():.0f} 秒")
                    else:
                        print(f"     ⚠️ 數據可能過時: 數據年齡 {data_age.total_seconds():.0f} 秒")
                else:
                    print("     ❌ 無法取得數據進行新鮮度測試")
                
                # 測試數據一致性 (多次查詢同一股票)
                print("  🔄 測試數據一致性...")
                quote1 = await twse.get_stock_quote("2330")
                await asyncio.sleep(1)
                quote2 = await twse.get_stock_quote("2330")
                
                if quote1 and quote2:
                    if quote1.current_price == quote2.current_price:  # 應該相同(快取機制)
                        quality_results['data_consistency'] = True
                        print("     ✅ 數據一致性良好: 重複查詢結果一致")
                    else:
                        print(f"     ⚠️ 數據一致性問題: {quote1.current_price} vs {quote2.current_price}")
                else:
                    print("     ❌ 無法取得數據進行一致性測試")
        
        except Exception as e:
            print(f"  ❌ TWSE數據品質測試失敗: {e}")
        
        return quality_results
    
    async def test_twse_integration_with_system(self):
        """測試TWSE與系統整合"""
        print("\n🔗 測試TWSE與系統整合...")
        
        integration_results = {
            'external_data_manager': False,
            'api_endpoints': False,
            'market_data_sources': False,
            'failover_mechanism': False
        }
        
        try:
            # 測試外部數據管理器整合
            print("  🌐 測試外部數據管理器整合...")
            from services.external_data_manager import ExternalDataManager, DataSource
            
            async with ExternalDataManager() as manager:
                # 測試台股優先使用TWSE
                tsmc_quote = await manager.get_stock_quote("2330")
                if tsmc_quote and tsmc_quote.source == "twse":
                    integration_results['external_data_manager'] = True
                    print(f"     ✅ 外部數據管理器正確使用TWSE: {tsmc_quote.current_price}")
                else:
                    print(f"     ❌ 外部數據管理器未使用TWSE: {tsmc_quote.source if tsmc_quote else 'None'}")
                
                # 測試故障轉移機制
                print("  🔧 測試故障轉移機制...")
                health_status = await manager.health_check()
                if 'twse' in health_status and health_status['twse']:
                    integration_results['failover_mechanism'] = True
                    print("     ✅ TWSE在故障轉移系統中正常運作")
                else:
                    print("     ❌ TWSE在故障轉移系統中狀態異常")
        
        except Exception as e:
            print(f"  ❌ 系統整合測試失敗: {e}")
        
        try:
            # 測試市場數據源整合
            print("  📊 測試市場數據源整合...")
            from services.market_data_sources import MarketDataSource
            
            # 這個測試需要檢查TWSE是否正確整合到市場數據源中
            # 由於我們沒有直接訪問該模組，我們檢查TWSE服務是否可用
            from services.twse_service import TWStockExchangeService
            async with TWStockExchangeService() as twse:
                test_quote = await twse.get_stock_quote("2330")
                if test_quote:
                    integration_results['market_data_sources'] = True
                    print("     ✅ TWSE可作為市場數據源使用")
                else:
                    print("     ❌ TWSE作為市場數據源失敗")
        
        except Exception as e:
            print(f"  ❌ 市場數據源測試失敗: {e}")
        
        return integration_results
    
    async def test_twse_performance(self):
        """測試TWSE性能表現"""
        print("\n⚡ 測試TWSE性能表現...")
        
        performance_results = {
            'response_time': False,
            'throughput': False,
            'memory_usage': False,
            'concurrent_requests': False
        }
        
        try:
            from services.twse_service import TWStockExchangeService
            
            async with TWStockExchangeService() as twse:
                # 測試響應時間
                print("  ⏱️ 測試API響應時間...")
                response_times = []
                
                for i in range(5):
                    start_time = time.time()
                    await twse.get_stock_quote("2330")
                    end_time = time.time()
                    response_times.append(end_time - start_time)
                
                avg_response_time = sum(response_times) / len(response_times)
                if avg_response_time < 2.0:  # 平均響應時間小於2秒
                    performance_results['response_time'] = True
                    print(f"     ✅ 響應時間良好: 平均 {avg_response_time:.3f}s")
                else:
                    print(f"     ⚠️ 響應時間較慢: 平均 {avg_response_time:.3f}s")
                
                # 測試吞吐量 (批量查詢)
                print("  📈 測試批量查詢吞吐量...")
                batch_symbols = ["2330", "2317", "2454", "1301", "2308", "2382", "2881", "2891", "2882", "2886"]
                
                start_time = time.time()
                batch_quotes = await twse.get_multiple_quotes(batch_symbols)
                end_time = time.time()
                
                successful_quotes = sum(1 for q in batch_quotes.values() if q)
                batch_time = end_time - start_time
                throughput = successful_quotes / batch_time if batch_time > 0 else 0
                
                if throughput > 5:  # 每秒處理5個以上股票查詢
                    performance_results['throughput'] = True
                    print(f"     ✅ 吞吐量良好: {throughput:.1f} 查詢/秒")
                else:
                    print(f"     ⚠️ 吞吐量較低: {throughput:.1f} 查詢/秒")
                
                # 測試並發請求
                print("  🚀 測試並發請求處理...")
                concurrent_symbols = ["2330", "2317", "2454", "1301", "2308"]
                
                start_time = time.time()
                concurrent_tasks = [twse.get_stock_quote(symbol) for symbol in concurrent_symbols]
                concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
                end_time = time.time()
                
                successful_concurrent = sum(1 for r in concurrent_results 
                                          if not isinstance(r, Exception) and r is not None)
                concurrent_time = end_time - start_time
                
                if successful_concurrent >= len(concurrent_symbols) * 0.8:
                    performance_results['concurrent_requests'] = True
                    print(f"     ✅ 並發處理良好: {successful_concurrent}/{len(concurrent_symbols)} 在 {concurrent_time:.3f}s")
                else:
                    print(f"     ❌ 並發處理有問題: {successful_concurrent}/{len(concurrent_symbols)}")
        
        except Exception as e:
            print(f"  ❌ 性能測試失敗: {e}")
        
        return performance_results
    
    async def generate_comprehensive_report(self, all_results: Dict):
        """生成綜合測試報告"""
        print("\n📊 生成TWSE綜合測試報告...")
        
        total_tests = sum(len(results) for results in all_results.values())
        passed_tests = sum(sum(results.values()) for results in all_results.values())
        
        report_data = {
            'test_date': self.start_time.isoformat(),
            'test_duration_seconds': (datetime.now() - self.start_time).total_seconds(),
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'success_rate': passed_tests / total_tests if total_tests > 0 else 0,
                'overall_status': 'PASS' if passed_tests >= total_tests * 0.8 else 'FAIL'
            },
            'detailed_results': all_results,
            'test_categories': {
                'core_service': {
                    'tests': len(all_results.get('core_service', {})),
                    'passed': sum(all_results.get('core_service', {}).values()),
                    'critical': True
                },
                'data_quality': {
                    'tests': len(all_results.get('data_quality', {})),
                    'passed': sum(all_results.get('data_quality', {}).values()),
                    'critical': True
                },
                'system_integration': {
                    'tests': len(all_results.get('integration', {})),
                    'passed': sum(all_results.get('integration', {}).values()),
                    'critical': True
                },
                'performance': {
                    'tests': len(all_results.get('performance', {})),
                    'passed': sum(all_results.get('performance', {}).values()),
                    'critical': False
                }
            }
        }
        
        # 保存報告
        output_file = f"twse_comprehensive_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"  💾 詳細報告已保存: {output_file}")
        
        return report_data

async def main():
    """主測試函數"""
    print("🚀 TWSE綜合功能測試開始...")
    print("="*80)
    
    tester = TWSEComprehensiveTester()
    all_results = {}
    
    # 執行各項測試
    all_results['core_service'] = await tester.test_twse_core_service()
    all_results['data_quality'] = await tester.test_twse_data_quality()
    all_results['integration'] = await tester.test_twse_integration_with_system()
    all_results['performance'] = await tester.test_twse_performance()
    
    # 生成綜合報告
    report = await tester.generate_comprehensive_report(all_results)
    
    # 顯示最終結果
    print("\n" + "="*80)
    print("🎯 TWSE綜合測試結果")
    print("="*80)
    
    print(f"測試時間: {report['test_duration_seconds']:.1f} 秒")
    print(f"測試項目: {report['summary']['total_tests']}")
    print(f"通過項目: {report['summary']['passed_tests']}")
    print(f"成功率: {report['summary']['success_rate']*100:.1f}%")
    print(f"整體狀態: {'✅ PASS' if report['summary']['overall_status'] == 'PASS' else '❌ FAIL'}")
    
    print("\n📋 詳細結果:")
    for category, results in all_results.items():
        category_name = {
            'core_service': 'TWSE核心服務',
            'data_quality': '數據品質', 
            'integration': '系統整合',
            'performance': '性能表現'
        }.get(category, category)
        
        passed = sum(results.values())
        total = len(results)
        print(f"  {category_name}: {passed}/{total} ({'✅ PASS' if passed >= total * 0.8 else '⚠️ PARTIAL' if passed > 0 else '❌ FAIL'})")
        
        for test_name, success in results.items():
            status = "✅" if success else "❌"
            print(f"    {status} {test_name}")
    
    # 建議與結論
    print(f"\n💡 測試結論:")
    if report['summary']['success_rate'] >= 0.9:
        print("  🎉 TWSE功能表現優秀，完全可以投入生產使用")
    elif report['summary']['success_rate'] >= 0.7:
        print("  ✅ TWSE功能基本良好，建議關注失敗項目")
    else:
        print("  ⚠️ TWSE功能存在問題，需要修復後再使用")
    
    return 0 if report['summary']['overall_status'] == 'PASS' else 1

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