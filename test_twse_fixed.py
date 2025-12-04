#!/usr/bin/env python3
"""
測試修復後的TWSE資料源
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from src.services.market_data_sources import TWSEDataSource
from src.services.twse_backup import TWSEBackupSource
from src.core.cache import get_cache_manager


async def test_twse_sources():
    """測試TWSE資料源"""
    print("🧪 測試修復後的TWSE資料源...")
    
    cache_manager = await get_cache_manager()
    
    # 測試主要TWSE資料源
    print("\n1️⃣ 測試主要TWSE資料源...")
    async with TWSEDataSource(cache_manager) as twse:
        quote = await twse.get_real_time_quote("2330")
        if quote:
            print(f"✅ 主要資料源成功: 台積電 ${quote.current_price}")
        else:
            print("⚠️  主要資料源失敗")
    
    # 測試備用TWSE資料源
    print("\n2️⃣ 測試備用TWSE資料源...")
    async with TWSEBackupSource(cache_manager) as backup:
        quote = await backup.get_real_time_quote("2330")
        if quote:
            print(f"✅ 備用資料源成功: 台積電 ${quote.current_price}")
            print(f"   開盤: ${quote.open_price}")
            print(f"   最高: ${quote.high_price}")
            print(f"   最低: ${quote.low_price}")
            print(f"   成交量: {quote.volume:,}")
        else:
            print("⚠️  備用資料源失敗")
        
        # 測試歷史資料
        historical = await backup.get_historical_data("2330", days=5)
        if historical:
            print(f"✅ 歷史資料: {len(historical)} 筆")
            latest = historical[0]
            print(f"   最新: {latest.date.strftime('%Y-%m-%d')} 收盤 ${latest.close_price}")
        else:
            print("⚠️  歷史資料失敗")
    
    # 測試其他股票
    print("\n3️⃣ 測試其他熱門股票...")
    test_stocks = ["2454", "1301", "2317"]  # 聯發科、台塑、鴻海
    
    async with TWSEDataSource(cache_manager) as twse:
        for stock in test_stocks:
            try:
                quote = await twse.get_real_time_quote(stock)
                if quote:
                    print(f"✅ {stock}: ${quote.current_price}")
                else:
                    print(f"❌ {stock}: 無法取得")
            except Exception as e:
                print(f"❌ {stock}: 錯誤 - {e}")


if __name__ == "__main__":
    asyncio.run(test_twse_sources())