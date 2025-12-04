
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
