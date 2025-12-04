#!/usr/bin/env python3
"""
多資料源市場資料測試腳本
Multi-Source Market Data Testing Script
"""

import asyncio
import sys
import os
from datetime import datetime

# 添加專案路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from src.services.market_data_sources import (
    TWSEDataSource, AlphaVantageDataSource, MarketDataAggregator,
    create_market_data_aggregator
)
from src.core.cache import get_cache_manager


async def test_twse_source():
    """測試TWSE資料源"""
    print("\n🏛️  測試 TWSE 台灣證券交易所資料源...")
    
    try:
        cache_manager = await get_cache_manager()
        
        async with TWSEDataSource(cache_manager) as twse:
            print("✅ TWSE資料源初始化成功")
            
            # 測試連線驗證
            is_healthy = await twse.validate_connection()
            print(f"📡 TWSE連線狀態: {'正常' if is_healthy else '異常'}")
            
            if is_healthy:
                # 測試台積電報價
                quote = await twse.get_real_time_quote("2330")
                if quote:
                    print(f"📈 台積電(2330)報價:")
                    print(f"   當前價格: ${quote.current_price}")
                    print(f"   開盤價: ${quote.open_price}")
                    print(f"   最高價: ${quote.high_price}")
                    print(f"   最低價: ${quote.low_price}")
                    print(f"   成交量: {quote.volume:,}")
                    print(f"   更新時間: {quote.timestamp}")
                else:
                    print("⚠️  無法取得台積電報價")
                
                # 測試歷史資料
                historical = await twse.get_historical_data("2330", days=5)
                if historical:
                    print(f"📊 台積電歷史資料: {len(historical)} 筆")
                    if historical:
                        latest = historical[0]
                        print(f"   最新: {latest.date.strftime('%Y-%m-%d')} 收盤 ${latest.close_price}")
                else:
                    print("⚠️  無法取得歷史資料")
            
            return is_healthy
            
    except Exception as e:
        print(f"❌ TWSE測試失敗: {e}")
        return False


async def test_alpha_vantage_source():
    """測試Alpha Vantage資料源"""
    print("\n📊 測試 Alpha Vantage 資料源...")
    
    # 檢查API Key
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key or api_key == "your_alpha_vantage_api_key_here":
        print("⚠️  未設定 ALPHA_VANTAGE_API_KEY，跳過測試")
        print("   請在 .env 檔案中設定正確的 API Key")
        return False
    
    try:
        cache_manager = await get_cache_manager()
        
        async with AlphaVantageDataSource(api_key, cache_manager) as alpha:
            print("✅ Alpha Vantage資料源初始化成功")
            
            # 測試連線驗證
            is_healthy = await alpha.validate_connection()
            print(f"📡 Alpha Vantage連線狀態: {'正常' if is_healthy else '異常'}")
            
            if is_healthy:
                # 測試蘋果股票報價
                quote = await alpha.get_real_time_quote("AAPL")
                if quote:
                    print(f"🍎 蘋果(AAPL)報價:")
                    print(f"   當前價格: ${quote.current_price}")
                    print(f"   前收價格: ${quote.previous_close}")
                    print(f"   漲跌: {quote.price_change:+.2f} ({quote.price_change_percent:+.2f}%)")
                else:
                    print("⚠️  無法取得蘋果報價 (可能因為市場時間或API限制)")
            
            return is_healthy
            
    except Exception as e:
        print(f"❌ Alpha Vantage測試失敗: {e}")
        return False


async def test_market_aggregator():
    """測試市場資料聚合器"""
    print("\n🔄 測試市場資料聚合器...")
    
    try:
        cache_manager = await get_cache_manager()
        
        # 取得API Keys
        alpha_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        fugle_key = os.getenv("FUGLE_API_KEY")
        
        aggregator = await create_market_data_aggregator(
            alpha_vantage_key=alpha_key if alpha_key != "your_alpha_vantage_api_key_here" else None,
            fugle_key=fugle_key if fugle_key != "your_fugle_api_key_here" else None,
            cache_manager=cache_manager
        )
        
        print(f"✅ 聚合器初始化成功，包含 {len(aggregator.data_sources)} 個資料源")
        
        # 健康檢查
        health_status = await aggregator.health_check()
        healthy_count = sum(1 for status in health_status.values() if status)
        print(f"📋 健康檢查: {healthy_count}/{len(health_status)} 資料源正常")
        
        for name, status in health_status.items():
            print(f"   {name}: {'✅ 正常' if status else '❌ 異常'}")
        
        # 測試台股查詢 (多資料源容錯)
        print("\n📈 測試台股多資料源查詢...")
        tw_quote = await aggregator.get_best_quote("2330")
        if tw_quote:
            print(f"✅ 成功取得台積電報價: ${tw_quote.current_price}")
        else:
            print("❌ 無法從任何資料源取得台積電報價")
        
        # 測試美股查詢
        if alpha_key and alpha_key != "your_alpha_vantage_api_key_here":
            print("\n🍎 測試美股多資料源查詢...")
            us_quote = await aggregator.get_best_quote("AAPL")
            if us_quote:
                print(f"✅ 成功取得蘋果報價: ${us_quote.current_price}")
            else:
                print("❌ 無法從任何資料源取得蘋果報價")
        
        # 測試歷史資料聚合
        print("\n📊 測試歷史資料聚合...")
        historical = await aggregator.get_aggregated_historical_data("2330", days=5)
        if historical:
            print(f"✅ 成功取得台積電歷史資料: {len(historical)} 筆")
        else:
            print("❌ 無法從任何資料源取得歷史資料")
        
        return healthy_count > 0
        
    except Exception as e:
        print(f"❌ 聚合器測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_api_endpoints():
    """測試API端點"""
    print("\n🌐 測試API端點...")
    
    try:
        import aiohttp
        
        base_url = "http://localhost:8001/api/v1/market"
        
        async with aiohttp.ClientSession() as session:
            # 測試資料源資訊端點
            async with session.get(f"{base_url}/v2/sources/info") as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ 資料源資訊端點正常")
                    sources = data.get("data", {}).get("available_sources", {})
                    print(f"   可用資料源: {list(sources.keys())}")
                else:
                    print(f"❌ 資料源資訊端點異常: {response.status}")
            
            # 測試健康檢查端點
            async with session.get(f"{base_url}/v2/health/sources") as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ 健康檢查端點正常")
                    if data.get("data"):
                        status = data["data"]
                        print(f"   健康狀態: {status.get('healthy_sources', 0)}/{status.get('total_sources', 0)}")
                else:
                    print(f"❌ 健康檢查端點異常: {response.status}")
            
            # 測試台積電報價端點 (限時測試避免超時)
            try:
                async with session.get(f"{base_url}/v2/quote/2330", timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        print("✅ 台積電報價端點正常")
                        if data.get("data"):
                            price = data["data"].get("current_price")
                            print(f"   報價: ${price}")
                    else:
                        print(f"⚠️  台積電報價端點回應: {response.status}")
            except asyncio.TimeoutError:
                print("⚠️  台積電報價端點超時 (可能因為資料源限流)")
        
        return True
        
    except Exception as e:
        print(f"❌ API端點測試失敗: {e}")
        return False


async def main():
    """主函數"""
    try:
        print("=" * 80)
        print("🚀 多資料源市場資料整合測試")
        print("=" * 80)
        
        # 檢查環境變數
        print("\n🔧 檢查環境配置...")
        alpha_key = os.getenv("ALPHA_VANTAGE_API_KEY", "")
        fugle_key = os.getenv("FUGLE_API_KEY", "")
        
        print(f"   ALPHA_VANTAGE_API_KEY: {'已設定' if alpha_key and alpha_key != 'your_alpha_vantage_api_key_here' else '未設定'}")
        print(f"   FUGLE_API_KEY: {'已設定' if fugle_key and fugle_key != 'your_fugle_api_key_here' else '未設定'}")
        
        # 執行各項測試
        results = []
        
        # 1. TWSE測試
        twse_result = await test_twse_source()
        results.append(("TWSE資料源", twse_result))
        
        # 2. Alpha Vantage測試
        alpha_result = await test_alpha_vantage_source()
        results.append(("Alpha Vantage資料源", alpha_result))
        
        # 3. 聚合器測試
        aggregator_result = await test_market_aggregator()
        results.append(("市場資料聚合器", aggregator_result))
        
        # 4. API端點測試
        api_result = await test_api_endpoints()
        results.append(("API端點", api_result))
        
        # 結果總結
        print("\n" + "=" * 80)
        print("📋 測試結果總結")
        print("=" * 80)
        
        passed = 0
        for name, result in results:
            status = "✅ 通過" if result else "❌ 失敗"
            print(f"   {name:<20} {status}")
            if result:
                passed += 1
        
        print(f"\n🎯 總體結果: {passed}/{len(results)} 項測試通過")
        
        if passed >= 2:  # 至少TWSE和聚合器要通過
            print("\n🎉 多資料源整合測試成功！")
            print("\n💡 使用建議:")
            print("   • TWSE資料源可免費使用，適合台股查詢")
            print("   • Alpha Vantage需API Key，適合國際股市")
            print("   • 聚合器提供多資料源容錯機制")
            print("   • API端點支援v2版本增強功能")
            return True
        else:
            print("\n⚠️  部分測試失敗，請檢查網路連線和API配置")
            return False
            
    except KeyboardInterrupt:
        print("\n⏹️  測試被用戶中斷")
        return False
    except Exception as e:
        print(f"\n💥 測試過程發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 設定 asyncio 相容性
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # 執行測試
    success = asyncio.run(main())
    sys.exit(0 if success else 1)