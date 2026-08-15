#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
外部資料源簡化測試腳本
External Data Sources Simple Test

專注測試核心功能，避免過度請求導致限流
"""

import asyncio
import sys
import os
from datetime import datetime
import yfinance as yf
import aiohttp
import json
from dotenv import load_dotenv

# 載入環境變數
load_dotenv('.env.local')

class SimpleExternalDataTest:
    def __init__(self):
        self.alpha_key = os.getenv("ALPHA_VANTAGE_API_KEY", "")
        self.test_results = []

    def log_test(self, name: str, success: bool, message: str = ""):
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {name}: {message}")
        self.test_results.append((name, success, message))

    async def test_yahoo_finance_basic(self):
        """測試基本 Yahoo Finance 功能"""
        print("\n📊 測試 Yahoo Finance 基本功能...")
        
        try:
            # 使用較少請求的方式測試台股
            ticker = yf.Ticker("2330.TW")
            hist = ticker.history(period="1d")
            
            if not hist.empty:
                current_price = float(hist['Close'].iloc[-1])
                self.log_test(
                    "Yahoo Finance 台股", 
                    True, 
                    f"台積電: ${current_price:.2f}"
                )
            else:
                self.log_test("Yahoo Finance 台股", False, "無法取得台積電資料")
                
            # 延遲避免過度請求
            await asyncio.sleep(2)
            
            # 測試美股
            us_ticker = yf.Ticker("AAPL")
            us_hist = us_ticker.history(period="1d")
            
            if not us_hist.empty:
                us_price = float(us_hist['Close'].iloc[-1])
                self.log_test(
                    "Yahoo Finance 美股", 
                    True, 
                    f"蘋果: ${us_price:.2f}"
                )
            else:
                self.log_test("Yahoo Finance 美股", False, "無法取得蘋果資料")
                
        except Exception as e:
            self.log_test("Yahoo Finance 測試", False, str(e))

    async def test_alpha_vantage_basic(self):
        """測試基本 Alpha Vantage 功能"""
        print("\n🔥 測試 Alpha Vantage 基本功能...")
        
        if not self.alpha_key or self.alpha_key == "your_key_here":
            self.log_test("Alpha Vantage", False, "未設定 API Key")
            return
            
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': 'AAPL',
                'apikey': self.alpha_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    data = await response.json()
                    
                    if 'Global Quote' in data:
                        price = float(data['Global Quote']['05. price'])
                        change = float(data['Global Quote']['09. change'])
                        self.log_test(
                            "Alpha Vantage 美股", 
                            True, 
                            f"蘋果: ${price:.2f} ({change:+.2f})"
                        )
                    else:
                        self.log_test("Alpha Vantage 美股", False, f"API 回應異常: {data}")
                        
        except Exception as e:
            self.log_test("Alpha Vantage 測試", False, str(e))

    async def test_data_integration(self):
        """測試資料整合功能"""
        print("\n🔗 測試資料整合功能...")
        
        try:
            # 測試將外部資料寫入本地資料庫
            import psycopg2
            
            timescale_config = {
                'host': 'localhost',
                'port': 5433,
                'user': 'postgres',
                'password': 'dev_password_2024',
                'database': 'timeseries_financial'
            }
            
            # 模擬資料 (避免過度 API 請求)
            sample_data = {
                'time': datetime.now(),
                'company_id': 'TEST_EXT',
                'close_price': 100.50,
                'volume': 1000000,
                'source': 'external_api_test'
            }
            
            conn = psycopg2.connect(**timescale_config)
            cursor = conn.cursor()
            
            # 清理測試資料
            cursor.execute("DELETE FROM stock_prices WHERE company_id = 'TEST_EXT'")
            
            # 插入測試資料
            cursor.execute("""
                INSERT INTO stock_prices (time, company_id, close_price, volume)
                VALUES (%s, %s, %s, %s)
            """, (
                sample_data['time'],
                sample_data['company_id'],
                sample_data['close_price'],
                sample_data['volume']
            ))
            
            # 驗證插入
            cursor.execute("SELECT COUNT(*) FROM stock_prices WHERE company_id = 'TEST_EXT'")
            count = cursor.fetchone()[0]
            
            conn.commit()
            cursor.close()
            conn.close()
            
            self.log_test(
                "資料庫整合", 
                count > 0, 
                f"成功儲存外部資料到 TimescaleDB"
            )
            
        except Exception as e:
            self.log_test("資料庫整合測試", False, str(e))

    async def test_redis_cache(self):
        """測試 Redis 快取功能"""
        print("\n💾 測試 Redis 快取功能...")
        
        try:
            import redis
            
            redis_client = redis.Redis(
                host='localhost',
                port=6379,
                password='dev_redis_2024',
                db=1,
                decode_responses=True
            )
            
            # 測試快取操作
            cache_key = "external_test:stock:AAPL"
            cache_data = {
                "symbol": "AAPL",
                "price": 150.25,
                "timestamp": datetime.now().isoformat(),
                "source": "test"
            }
            
            # 設定快取
            redis_client.setex(cache_key, 300, json.dumps(cache_data))
            
            # 讀取快取
            cached = redis_client.get(cache_key)
            retrieved_data = json.loads(cached) if cached else None
            
            # 清理
            redis_client.delete(cache_key)
            
            self.log_test(
                "Redis 快取", 
                retrieved_data and retrieved_data['symbol'] == 'AAPL', 
                f"快取讀寫成功"
            )
            
        except Exception as e:
            self.log_test("Redis 快取測試", False, str(e))

    def create_integration_example(self):
        """建立整合使用範例"""
        example_code = '''
# 外部資料源使用範例
from src.services.external_data_manager import ExternalDataManager

async def get_stock_data_example():
    """獲取股票資料範例"""
    async with ExternalDataManager(alpha_vantage_key="YOUR_KEY") as manager:
        
        # 獲取台股報價 (Yahoo Finance)
        tsmc_quote = await manager.get_stock_quote("2330")
        if tsmc_quote:
            print(f"台積電: ${tsmc_quote.current_price}")
        
        # 獲取美股報價 (優先使用 Yahoo Finance，失敗時自動切換到 Alpha Vantage)
        aapl_quote = await manager.get_stock_quote("AAPL")
        if aapl_quote:
            print(f"蘋果: ${aapl_quote.current_price} (來源: {aapl_quote.source})")
        
        # 批量獲取多個股票
        symbols = ["2330", "AAPL", "MSFT", "GOOGL"]
        quotes = await manager.get_multiple_quotes(symbols)
        for symbol, quote in quotes.items():
            if quote:
                print(f"{symbol}: ${quote.current_price}")
        
        # 獲取歷史資料
        historical = await manager.get_historical_data("AAPL", days=30)
        if historical:
            print(f"蘋果 30 天歷史資料: {len(historical)} 筆")
        
        # 健康檢查
        health = await manager.health_check()
        for source, status in health.items():
            print(f"{source}: {'✅' if status else '❌'}")

# 使用方法
asyncio.run(get_stock_data_example())
'''
        
        with open("external_data_usage_example.py", "w", encoding="utf-8") as f:
            f.write(example_code)
        
        print("\n📝 已建立使用範例檔案: external_data_usage_example.py")

    async def run_all_tests(self):
        """執行所有測試"""
        print("🧪 外部資料源簡化測試開始...")
        print(f"Alpha Vantage API Key: {'已設定' if self.alpha_key else '未設定'}")
        
        # 執行測試
        await self.test_yahoo_finance_basic()
        await asyncio.sleep(1)
        
        await self.test_alpha_vantage_basic()
        await asyncio.sleep(1)
        
        await self.test_data_integration()
        await self.test_redis_cache()
        
        # 建立使用範例
        self.create_integration_example()
        
        # 結果摘要
        print("\n" + "="*60)
        print("📊 外部資料源測試摘要")
        print("="*60)
        
        passed = sum(1 for _, success, _ in self.test_results if success)
        total = len(self.test_results)
        
        print(f"總測試: {total}")
        print(f"通過: {passed} ✅")
        print(f"失敗: {total - passed} ❌")
        print(f"成功率: {passed/total*100:.1f}%")
        
        if total - passed > 0:
            print("\n❌ 失敗項目:")
            for name, success, message in self.test_results:
                if not success:
                    print(f"   • {name}: {message}")
        
        print(f"\n🎯 建議:")
        print(f"   • Yahoo Finance: 免費使用，適合基本需求")
        print(f"   • Alpha Vantage: 需 API Key，適合專業應用")
        print(f"   • 組合使用: 提供最佳的資料覆蓋和可靠性")
        
        return passed == total

async def main():
    tester = SimpleExternalDataTest()
    success = await tester.run_all_tests()
    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        print(f"\n{'🎉 所有測試通過！' if success else '⚠️  部分測試失敗'}")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  測試被中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 測試錯誤: {e}")
        sys.exit(1)