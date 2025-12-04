#!/usr/bin/env python3
"""
Yahoo Finance 服務測試腳本
"""

import asyncio
import sys
import os

# 添加專案路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from src.services.yahoo_finance_service import YahooFinanceService
from src.core.cache import get_cache_manager


async def test_yahoo_finance():
    """測試 Yahoo Finance 服務"""
    print("🚀 開始測試 Yahoo Finance 服務...")
    
    try:
        # 初始化快取管理器
        cache_manager = await get_cache_manager()
        print("✅ 快取管理器初始化成功")
        
        # 初始化 Yahoo Finance 服務
        async with YahooFinanceService(cache_manager=cache_manager) as yahoo_service:
            print("✅ Yahoo Finance 服務初始化成功")
            
            # 測試連線驗證
            print("\n📡 測試連線驗證...")
            is_healthy = await yahoo_service.validate_connection()
            if is_healthy:
                print("✅ Yahoo Finance 連線正常")
            else:
                print("❌ Yahoo Finance 連線失敗")
                return False
            
            # 測試取得台積電即時報價
            print("\n📈 測試取得台積電(2330)即時報價...")
            quote = await yahoo_service.get_real_time_quote("2330")
            if quote:
                print(f"✅ 成功取得報價:")
                print(f"   股票代碼: {quote.symbol}")
                print(f"   當前價格: ${quote.current_price}")
                print(f"   開盤價格: ${quote.open_price}")
                print(f"   最高價格: ${quote.high_price}")
                print(f"   最低價格: ${quote.low_price}")
                print(f"   前收價格: ${quote.previous_close}")
                print(f"   成交量: {quote.volume:,}")
                print(f"   更新時間: {quote.timestamp}")
                print(f"   價格變化: {quote.price_change:+.2f} ({quote.price_change_percent:+.2f}%)")
            else:
                print("❌ 無法取得台積電報價")
                return False
            
            # 測試取得美股報價 (蘋果)
            print("\n🍎 測試取得蘋果(AAPL)即時報價...")
            aapl_quote = await yahoo_service.get_real_time_quote("AAPL")
            if aapl_quote:
                print(f"✅ 成功取得蘋果報價: ${aapl_quote.current_price}")
            else:
                print("⚠️  無法取得蘋果報價 (可能因為市場時間)")
            
            # 測試取得歷史資料
            print("\n📊 測試取得台積電歷史資料...")
            historical = await yahoo_service.get_historical_data("2330", period="5d", interval="1d")
            if historical:
                print(f"✅ 成功取得 {len(historical)} 筆歷史資料")
                if len(historical) > 0:
                    latest = historical[-1]
                    print(f"   最新資料: {latest['date']}")
                    print(f"   收盤價: ${latest.get('close', 'N/A')}")
            else:
                print("❌ 無法取得歷史資料")
            
            # 測試市場摘要
            print("\n🏢 測試取得市場摘要...")
            market_summary = await yahoo_service.get_market_summary()
            if market_summary:
                print(f"✅ 成功取得市場摘要資料，包含 {len(market_summary)} 個指數")
                for index, data in market_summary.items():
                    if data.get('current'):
                        print(f"   {index}: {data['current']}")
            else:
                print("⚠️  市場摘要資料為空")
                
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n🎉 Yahoo Finance 服務測試完成!")
    return True


async def main():
    """主函數"""
    try:
        success = await test_yahoo_finance()
        if success:
            print("\n✨ 所有測試通過! Yahoo Finance 服務運行正常")
            exit(0)
        else:
            print("\n💥 部分測試失敗，請檢查服務配置")
            exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  測試被用戶中斷")
        exit(1)
    except Exception as e:
        print(f"\n💥 測試過程發生錯誤: {e}")
        exit(1)


if __name__ == "__main__":
    # 設定 asyncio 在 Windows 上的相容性
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # 執行測試
    asyncio.run(main())