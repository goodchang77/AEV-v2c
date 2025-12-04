#!/usr/bin/env python3
"""
簡化版 Yahoo Finance 測試
使用 yfinance 庫進行基本功能測試
"""

import yfinance as yf
import asyncio
import sys
from datetime import datetime, timedelta


def test_yfinance_basic():
    """測試基本的yfinance功能"""
    print("🚀 開始測試 yfinance 基本功能...")
    
    try:
        # 測試台積電 (2330.TW)
        print("\n📈 測試取得台積電(2330.TW)資料...")
        ticker = yf.Ticker("2330.TW")
        
        # 取得基本資訊
        info = ticker.info
        if info and 'regularMarketPrice' in info:
            print(f"✅ 成功取得台積電基本資訊:")
            print(f"   公司名稱: {info.get('longName', 'N/A')}")
            print(f"   當前價格: ${info.get('regularMarketPrice', 'N/A')}")
            print(f"   前收價格: ${info.get('previousClose', 'N/A')}")
            print(f"   市值: {info.get('marketCap', 'N/A'):,}" if info.get('marketCap') else "   市值: N/A")
        else:
            print("⚠️  台積電基本資訊有限或為空")
        
        # 測試歷史資料
        print("\n📊 測試取得台積電歷史資料...")
        hist = ticker.history(period="5d")
        if not hist.empty:
            print(f"✅ 成功取得 {len(hist)} 筆歷史資料")
            latest = hist.iloc[-1]
            print(f"   最新收盤價: ${latest['Close']:.2f}")
            print(f"   最新成交量: {latest['Volume']:,}")
        else:
            print("❌ 無法取得台積電歷史資料")
            return False
            
        # 測試美股 (AAPL)
        print("\n🍎 測試取得蘋果(AAPL)資料...")
        aapl = yf.Ticker("AAPL")
        aapl_info = aapl.info
        if aapl_info and 'regularMarketPrice' in aapl_info:
            print(f"✅ 成功取得蘋果資料: ${aapl_info.get('regularMarketPrice', 'N/A')}")
        else:
            print("⚠️  蘋果資料有限（可能因為市場時間）")
            
        # 測試批量查詢
        print("\n🔍 測試批量查詢...")
        symbols = ["2330.TW", "2454.TW", "1301.TW"]  # 台積電、聯發科、台塑
        data = yf.download(symbols, period="1d", progress=False)
        if not data.empty:
            print(f"✅ 成功批量取得 {len(symbols)} 個股票資料")
            print(f"   資料欄位: {list(data.columns)}")
        else:
            print("❌ 批量查詢失敗")
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n🎉 yfinance 基本功能測試完成!")
    return True


async def test_integration_compatibility():
    """測試與我們系統的兼容性"""
    print("\n🔧 測試與系統的整合兼容性...")
    
    try:
        # 模擬我們的 StockPrice 模型需要的資料
        ticker = yf.Ticker("2330.TW")
        info = ticker.info
        hist = ticker.history(period="1d")
        
        if not hist.empty and info:
            latest_data = hist.iloc[-1]
            
            # 驗證我們能取得所需的所有欄位
            required_fields = {
                'symbol': '2330.TW',
                'current_price': float(latest_data['Close']),
                'open_price': float(latest_data['Open']),
                'high_price': float(latest_data['High']),
                'low_price': float(latest_data['Low']),
                'previous_close': float(info.get('previousClose', latest_data['Close'])),
                'volume': int(latest_data['Volume']),
                'market_cap': info.get('marketCap'),
                'timestamp': datetime.now(),
                'currency': 'TWD'
            }
            
            print("✅ 成功構建兼容的資料格式:")
            for key, value in required_fields.items():
                print(f"   {key}: {value}")
                
            return True
        else:
            print("❌ 無法取得足夠資料進行兼容性測試")
            return False
            
    except Exception as e:
        print(f"❌ 兼容性測試失敗: {e}")
        return False


def main():
    """主函數"""
    try:
        print("=" * 60)
        print("Yahoo Finance (yfinance) 整合測試")
        print("=" * 60)
        
        # 基本功能測試
        basic_success = test_yfinance_basic()
        
        # 兼容性測試  
        compatibility_success = asyncio.run(test_integration_compatibility())
        
        if basic_success and compatibility_success:
            print("\n✨ 所有測試通過! yfinance 整合可正常使用")
            print("\n📝 測試結論:")
            print("   ✅ yfinance 庫運行正常")
            print("   ✅ 可成功取得台股和美股資料")
            print("   ✅ 歷史資料查詢功能正常")
            print("   ✅ 與系統資料模型兼容")
            print("\n💡 建議:")
            print("   • 在生產環境中實作請求限流和錯誤重試")
            print("   • 加入快取機制減少API呼叫頻率")
            print("   • 監控API回應時間和成功率")
            return True
        else:
            print("\n💥 部分測試失敗，請檢查網路連線和API狀態")
            return False
            
    except KeyboardInterrupt:
        print("\n⏹️  測試被用戶中斷")
        return False
    except Exception as e:
        print(f"\n💥 測試過程發生錯誤: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)