#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
外部資料源整合測試腳本
External Data Sources Integration Test Script

測試 Yahoo Finance (台股/美股) 和 Alpha Vantage (美股) 整合功能
"""

import asyncio
import sys
import os
import json
from datetime import datetime, timedelta
import logging
from typing import Dict, List
import redis
import psycopg2
from dotenv import load_dotenv

# 載入環境變數
load_dotenv('.env.local')

# 添加專案路徑
project_root = os.path.dirname(__file__)
sys.path.insert(0, project_root)

# 導入外部資料源管理器
try:
    from src.services.external_data_manager import (
        ExternalDataManager, DataSource, MarketType, 
        StockQuote, HistoricalData
    )
except ImportError as e:
    print(f"❌ 無法導入外部資料源管理器: {e}")
    print("請確認 src/services/external_data_manager.py 檔案存在")
    sys.exit(1)

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

class ExternalDataSourceTester:
    def __init__(self):
        """初始化測試器"""
        # 從環境變數讀取 API Keys
        self.alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        
        # Redis 連線配置 (作為快取)
        self.redis_config = {
            'host': 'localhost',
            'port': 6379,
            'password': 'dev_redis_2024',
            'db': 1,  # 使用 db 1 避免與主測試衝突
            'decode_responses': True
        }
        
        self.test_results = []
        self.cache_manager = None

    def log_test_result(self, test_name: str, success: bool, message: str = ""):
        """記錄測試結果"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            'test_name': test_name,
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        logger.info(f"{status} - {test_name}: {message}")

    def setup_cache_manager(self):
        """設定快取管理器 (簡單的 Redis 封裝)"""
        try:
            redis_client = redis.Redis(**self.redis_config)
            redis_client.ping()
            
            # 簡單的快取管理器
            class SimpleCacheManager:
                def __init__(self, redis_client):
                    self.redis = redis_client
                
                async def get(self, key):
                    return self.redis.get(key)
                
                async def set(self, key, value, ex=300):
                    return self.redis.setex(key, ex, value)
            
            self.cache_manager = SimpleCacheManager(redis_client)
            return True
            
        except Exception as e:
            logger.warning(f"快取管理器設定失敗，將使用無快取模式: {e}")
            return False

    async def test_yahoo_finance_taiwan(self) -> bool:
        """測試 Yahoo Finance 台股功能"""
        try:
            async with ExternalDataManager(
                alpha_vantage_key=self.alpha_vantage_key,
                cache_manager=self.cache_manager
            ) as manager:
                
                # 測試台積電報價
                print("📊 測試台積電(2330)即時報價...")
                tsmc_quote = await manager.get_stock_quote("2330")
                
                if tsmc_quote:
                    self.log_test_result(
                        "Yahoo Finance 台股即時報價", 
                        True, 
                        f"台積電: ${tsmc_quote.current_price}, 來源: {tsmc_quote.source}"
                    )
                    
                    # 顯示詳細資料
                    print(f"   當前價格: ${tsmc_quote.current_price}")
                    print(f"   開盤價: ${tsmc_quote.open_price}")
                    print(f"   最高價: ${tsmc_quote.high_price}")
                    print(f"   最低價: ${tsmc_quote.low_price}")
                    print(f"   成交量: {tsmc_quote.volume:,}" if tsmc_quote.volume else "   成交量: N/A")
                    print(f"   價格變化: {tsmc_quote.price_change:+.2f}" if tsmc_quote.price_change else "   價格變化: N/A")
                    print(f"   變化百分比: {tsmc_quote.price_change_percent:+.2f}%" if tsmc_quote.price_change_percent else "   變化百分比: N/A")
                    
                    # 測試歷史資料
                    print("\n📈 測試台積電歷史資料...")
                    historical = await manager.get_historical_data("2330", days=5)
                    
                    if historical:
                        self.log_test_result(
                            "Yahoo Finance 台股歷史資料", 
                            True, 
                            f"取得 {len(historical)} 筆歷史資料"
                        )
                        
                        print(f"   歷史資料筆數: {len(historical)}")
                        if len(historical) > 0:
                            latest = historical[0]
                            print(f"   最新資料: {latest.date.strftime('%Y-%m-%d')} 收盤價 ${latest.close_price}")
                        
                    else:
                        self.log_test_result("Yahoo Finance 台股歷史資料", False, "無法取得歷史資料")
                        return False
                    
                    return True
                else:
                    self.log_test_result("Yahoo Finance 台股即時報價", False, "無法取得台積電報價")
                    return False
                    
        except Exception as e:
            self.log_test_result("Yahoo Finance 台股測試", False, str(e))
            return False

    async def test_yahoo_finance_us(self) -> bool:
        """測試 Yahoo Finance 美股功能"""
        try:
            async with ExternalDataManager(
                alpha_vantage_key=self.alpha_vantage_key,
                cache_manager=self.cache_manager
            ) as manager:
                
                # 測試蘋果報價
                print("\n🍎 測試蘋果(AAPL)即時報價...")
                aapl_quote = await manager.get_stock_quote("AAPL")
                
                if aapl_quote:
                    self.log_test_result(
                        "Yahoo Finance 美股即時報價", 
                        True, 
                        f"蘋果: ${aapl_quote.current_price}, 來源: {aapl_quote.source}"
                    )
                    
                    print(f"   當前價格: ${aapl_quote.current_price}")
                    print(f"   前收價格: ${aapl_quote.previous_close}" if aapl_quote.previous_close else "   前收價格: N/A")
                    print(f"   價格變化: {aapl_quote.price_change:+.2f}" if aapl_quote.price_change else "   價格變化: N/A")
                    
                    # 測試歷史資料
                    print("📊 測試蘋果歷史資料...")
                    historical = await manager.get_historical_data("AAPL", days=5)
                    
                    if historical:
                        self.log_test_result(
                            "Yahoo Finance 美股歷史資料", 
                            True, 
                            f"取得 {len(historical)} 筆歷史資料"
                        )
                    else:
                        self.log_test_result("Yahoo Finance 美股歷史資料", False, "無法取得歷史資料")
                        
                    return True
                else:
                    self.log_test_result("Yahoo Finance 美股即時報價", False, "無法取得蘋果報價 (可能因市場時間)")
                    return False
                    
        except Exception as e:
            self.log_test_result("Yahoo Finance 美股測試", False, str(e))
            return False

    async def test_alpha_vantage_us(self) -> bool:
        """測試 Alpha Vantage 美股功能"""
        if not self.alpha_vantage_key or self.alpha_vantage_key == "your_alpha_vantage_api_key_here":
            self.log_test_result("Alpha Vantage 美股測試", False, "未設定 ALPHA_VANTAGE_API_KEY")
            return False
            
        try:
            async with ExternalDataManager(
                alpha_vantage_key=self.alpha_vantage_key,
                cache_manager=self.cache_manager
            ) as manager:
                
                print("\n🔥 測試 Alpha Vantage 蘋果(AAPL)報價...")
                # 強制使用 Alpha Vantage
                aapl_quote = await manager.get_stock_quote("AAPL", prefer_source=DataSource.ALPHA_VANTAGE)
                
                if aapl_quote:
                    self.log_test_result(
                        "Alpha Vantage 美股即時報價", 
                        True, 
                        f"蘋果: ${aapl_quote.current_price}, 來源: {aapl_quote.source}"
                    )
                    
                    print(f"   當前價格: ${aapl_quote.current_price}")
                    print(f"   前收價格: ${aapl_quote.previous_close}" if aapl_quote.previous_close else "   前收價格: N/A")
                    print(f"   價格變化: {aapl_quote.price_change:+.2f}" if aapl_quote.price_change else "   價格變化: N/A")
                    
                    return True
                else:
                    self.log_test_result("Alpha Vantage 美股即時報價", False, "無法取得蘋果報價 (可能API限制)")
                    return False
                    
        except Exception as e:
            self.log_test_result("Alpha Vantage 美股測試", False, str(e))
            return False

    async def test_multiple_quotes(self) -> bool:
        """測試批量獲取報價功能"""
        try:
            async with ExternalDataManager(
                alpha_vantage_key=self.alpha_vantage_key,
                cache_manager=self.cache_manager
            ) as manager:
                
                print("\n📋 測試批量獲取多股票報價...")
                symbols = ["2330", "2317", "AAPL", "MSFT"]  # 台股 + 美股
                
                quotes = await manager.get_multiple_quotes(symbols)
                
                successful_quotes = sum(1 for quote in quotes.values() if quote is not None)
                
                self.log_test_result(
                    "批量獲取股票報價", 
                    successful_quotes > 0, 
                    f"成功獲取 {successful_quotes}/{len(symbols)} 個報價"
                )
                
                for symbol, quote in quotes.items():
                    if quote:
                        print(f"   {symbol}: ${quote.current_price} ({quote.source})")
                    else:
                        print(f"   {symbol}: 無法取得報價")
                
                return successful_quotes > 0
                
        except Exception as e:
            self.log_test_result("批量獲取股票報價", False, str(e))
            return False

    async def test_health_check(self) -> bool:
        """測試資料源健康檢查"""
        try:
            async with ExternalDataManager(
                alpha_vantage_key=self.alpha_vantage_key,
                cache_manager=self.cache_manager
            ) as manager:
                
                print("\n🏥 測試資料源健康檢查...")
                health_status = await manager.health_check()
                
                healthy_sources = sum(1 for status in health_status.values() if status)
                total_sources = len(health_status)
                
                self.log_test_result(
                    "資料源健康檢查", 
                    healthy_sources > 0, 
                    f"{healthy_sources}/{total_sources} 資料源正常"
                )
                
                for source, status in health_status.items():
                    status_icon = "✅" if status else "❌"
                    print(f"   {source}: {status_icon}")
                
                return healthy_sources > 0
                
        except Exception as e:
            self.log_test_result("資料源健康檢查", False, str(e))
            return False

    async def test_cache_functionality(self) -> bool:
        """測試快取功能"""
        if not self.cache_manager:
            self.log_test_result("快取功能測試", False, "快取管理器未啟用")
            return False
            
        try:
            async with ExternalDataManager(
                alpha_vantage_key=self.alpha_vantage_key,
                cache_manager=self.cache_manager
            ) as manager:
                
                print("\n💾 測試快取功能...")
                
                # 第一次獲取 (應該從 API)
                start_time = datetime.now()
                quote1 = await manager.get_stock_quote("2330")
                first_duration = (datetime.now() - start_time).total_seconds()
                
                # 第二次獲取 (應該從快取)
                start_time = datetime.now()
                quote2 = await manager.get_stock_quote("2330")
                second_duration = (datetime.now() - start_time).total_seconds()
                
                if quote1 and quote2 and quote1.current_price == quote2.current_price:
                    self.log_test_result(
                        "快取功能測試", 
                        True, 
                        f"第一次: {first_duration:.2f}s, 第二次: {second_duration:.2f}s (從快取)"
                    )
                    return True
                else:
                    self.log_test_result("快取功能測試", False, "快取資料不一致")
                    return False
                    
        except Exception as e:
            self.log_test_result("快取功能測試", False, str(e))
            return False

    async def test_data_storage_integration(self) -> bool:
        """測試資料儲存整合"""
        try:
            print("\n🗄️ 測試資料儲存整合...")
            
            # 連接到 TimescaleDB
            timescale_config = {
                'host': 'localhost',
                'port': 5433,
                'user': 'postgres',
                'password': 'dev_password_2024',
                'database': 'timeseries_financial'
            }
            
            # 獲取即時資料並儲存
            async with ExternalDataManager(
                alpha_vantage_key=self.alpha_vantage_key,
                cache_manager=self.cache_manager
            ) as manager:
                
                # 獲取台積電報價
                quote = await manager.get_stock_quote("2330")
                if not quote:
                    self.log_test_result("資料儲存整合測試", False, "無法獲取股票報價")
                    return False
                
                # 儲存到資料庫
                conn = psycopg2.connect(**timescale_config)
                cursor = conn.cursor()
                
                # 插入即時報價資料
                cursor.execute("""
                    INSERT INTO stock_prices 
                    (time, company_id, open_price, high_price, low_price, close_price, volume, adj_close)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    datetime.now(),
                    quote.symbol,
                    quote.open_price,
                    quote.high_price,
                    quote.low_price,
                    quote.current_price,
                    quote.volume,
                    quote.current_price
                ))
                
                conn.commit()
                cursor.close()
                conn.close()
                
                self.log_test_result(
                    "資料儲存整合測試", 
                    True, 
                    f"成功儲存 {quote.symbol} 報價到 TimescaleDB"
                )
                return True
                
        except Exception as e:
            self.log_test_result("資料儲存整合測試", False, str(e))
            return False

    def print_summary(self):
        """打印測試摘要"""
        print("\n" + "="*70)
        print("🎯 外部資料源整合測試報告")
        print("="*70)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"\n📊 測試統計:")
        print(f"   總測試數: {total_tests}")
        print(f"   通過測試: {passed_tests} ✅")
        print(f"   失敗測試: {failed_tests} ❌")
        print(f"   成功率: {passed_tests/total_tests*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ 失敗的測試:")
            for result in self.test_results:
                if not result['success']:
                    print(f"   • {result['test_name']}: {result['message']}")
        
        print(f"\n📋 資料源支援:")
        print(f"   • Yahoo Finance (台股): 免費，無限制")
        print(f"   • Yahoo Finance (美股): 免費，無限制")
        if self.alpha_vantage_key:
            print(f"   • Alpha Vantage (美股): 有 API Key，每分鐘 5 次")
        else:
            print(f"   • Alpha Vantage (美股): 未設定 API Key")
        
        print(f"\n🎉 系統狀態: {'所有外部資料源功能正常' if failed_tests == 0 else '部分功能需要修復'}")
        print("="*70)

    async def run_all_tests(self):
        """執行所有測試"""
        print("🚀 開始執行外部資料源整合測試...")
        print(f"Alpha Vantage API Key: {'已設定' if self.alpha_vantage_key else '未設定'}")
        
        # 設定快取管理器
        cache_setup = self.setup_cache_manager()
        print(f"快取管理器: {'已啟用' if cache_setup else '未啟用'}")
        
        # 執行所有測試
        test_functions = [
            self.test_yahoo_finance_taiwan,
            self.test_yahoo_finance_us,
            self.test_alpha_vantage_us,
            self.test_multiple_quotes,
            self.test_health_check,
            self.test_cache_functionality,
            self.test_data_storage_integration
        ]
        
        for test_func in test_functions:
            try:
                await test_func()
                await asyncio.sleep(1)  # 避免過於頻繁的 API 請求
            except Exception as e:
                logger.error(f"測試 {test_func.__name__} 時出現錯誤: {e}")
        
        # 打印結果
        self.print_summary()
        
        return all(result['success'] for result in self.test_results)

def main():
    """主程式"""
    tester = ExternalDataSourceTester()
    
    try:
        # 執行測試
        success = asyncio.run(tester.run_all_tests())
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  測試被用戶中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 測試執行出現未預期錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()