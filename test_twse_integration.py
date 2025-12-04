#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TWSE 整合測試腳本
測試台灣證交所 API 整合功能
"""

import asyncio
import sys
import os
from datetime import datetime

# 確保能找到 src 模組
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_twse_service():
    """測試 TWSE 服務"""
    print("🧪 測試 TWSE 服務...")
    
    try:
        from services.twse_service import TWStockExchangeService
        
        async with TWStockExchangeService() as twse:
            print("\n1️⃣ 測試台積電 (2330) 股價...")
            tsmc = await twse.get_stock_quote("2330")
            if tsmc:
                print(f"✅ 台積電: NT${tsmc.current_price:.2f}")
                print(f"   - 開盤: NT${tsmc.open_price:.2f}")
                print(f"   - 最高: NT${tsmc.high_price:.2f}")
                print(f"   - 最低: NT${tsmc.low_price:.2f}")
                change_str = f"{tsmc.change:+.2f}" if tsmc.change is not None else "0.00"
                change_pct_str = f"{tsmc.change_percent:+.2f}%" if tsmc.change_percent is not None else "0.00%"
                print(f"   - 漲跌: {change_str} ({change_pct_str})")
                print(f"   - 成交量: {tsmc.volume:,} 股")
            else:
                print("❌ 無法取得台積電股價")
            
            print("\n2️⃣ 測試多檔股票查詢...")
            symbols = ["2330", "2317", "1301", "2454"]  # 台積電、鴻海、台塑、聯發科
            quotes = await twse.get_multiple_quotes(symbols)
            
            for symbol, quote in quotes.items():
                if quote:
                    print(f"✅ {quote.name} ({symbol}): NT${quote.current_price:.2f} ({quote.change:+.2f})")
                else:
                    print(f"❌ 無法取得 {symbol} 股價")
            
            print("\n3️⃣ 測試市場摘要...")
            summary = await twse.get_market_summary()
            if summary:
                print(f"✅ 市場摘要:")
                print(f"   - 總股票數: {summary.get('total_stocks', 0)}")
                print(f"   - 上漲股數: {summary.get('rising_stocks', 0)}")
                print(f"   - 下跌股數: {summary.get('falling_stocks', 0)}")
                print(f"   - 總成交量: {summary.get('total_volume', 0):,}")
                print(f"   - 總成交金額: {summary.get('total_turnover', 0):,.0f}")
            else:
                print("❌ 無法取得市場摘要")
            
            print("\n4️⃣ 測試健康檢查...")
            health = await twse.health_check()
            print(f"✅ TWSE API 健康狀態: {'正常' if health else '異常'}")
            
            return True
            
    except Exception as e:
        print(f"❌ TWSE 服務測試失敗: {e}")
        return False

async def test_external_data_manager_with_twse():
    """測試外部資料管理器的 TWSE 整合"""
    print("\n🔗 測試外部資料管理器 TWSE 整合...")
    
    try:
        from services.external_data_manager import ExternalDataManager, DataSource
        
        async with ExternalDataManager(alpha_vantage_key="***REMOVED***") as manager:
            print("\n1️⃣ 測試台股資料 (應優先使用 TWSE)...")
            tsmc_quote = await manager.get_stock_quote("2330")
            if tsmc_quote:
                print(f"✅ 台積電: NT${tsmc_quote.current_price:.2f} (來源: {tsmc_quote.source})")
                if tsmc_quote.source == "twse":
                    print("   🎯 成功使用 TWSE 作為台股資料源!")
                else:
                    print(f"   ⚠️ 使用了備用資料源: {tsmc_quote.source}")
            else:
                print("❌ 無法取得台積電股價")
            
            print("\n2️⃣ 測試美股資料 (應使用 Alpha Vantage)...")
            aapl_quote = await manager.get_stock_quote("AAPL")
            if aapl_quote:
                print(f"✅ 蘋果: ${aapl_quote.current_price:.2f} (來源: {aapl_quote.source})")
            else:
                print("❌ 無法取得蘋果股價")
            
            print("\n3️⃣ 測試強制指定 TWSE 資料源...")
            twse_quote = await manager.get_stock_quote("2317", prefer_source=DataSource.TWSE)
            if twse_quote:
                print(f"✅ 鴻海 (TWSE): NT${twse_quote.current_price:.2f}")
            else:
                print("❌ 無法使用 TWSE 取得鴻海股價")
            
            print("\n4️⃣ 測試健康檢查...")
            health = await manager.health_check()
            print("健康檢查結果:")
            for source, status in health.items():
                status_text = "✅ 正常" if status else "❌ 異常"
                print(f"   - {source}: {status_text}")
            
            return True
            
    except Exception as e:
        print(f"❌ 外部資料管理器測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主測試函數"""
    print("🚀 TWSE 整合測試開始...")
    print(f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # 測試 1: TWSE 服務
    result1 = await test_twse_service()
    results.append(("TWSE 服務測試", result1))
    
    # 測試 2: 外部資料管理器整合
    result2 = await test_external_data_manager_with_twse()
    results.append(("外部資料管理器整合", result2))
    
    # 結果摘要
    print("\n" + "="*60)
    print("📊 TWSE 整合測試摘要")
    print("="*60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 測試結果: {passed}/{total} 通過")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 所有測試通過！TWSE 整合成功!")
        return 0
    else:
        print("\n⚠️ 部分測試失敗，請檢查配置")
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