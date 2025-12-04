"""
Yahoo Finance 資料服務
Real-time Market Data Service using Yahoo Finance API
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import json

from src.core.logging import get_logger
from src.core.cache import get_cache_manager
from src.core.exceptions import ExternalAPIError, ValidationError
from src.schemas.market_data import StockPrice, MarketData

logger = get_logger("yahoo_finance_service")


class YahooFinanceService:
    """Yahoo Finance API 整合服務"""
    
    def __init__(self, cache_manager=None, timeout: int = 30):
        self.base_url = "https://query1.finance.yahoo.com/v8/finance"
        self.cache_manager = cache_manager
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict:
        """發送HTTP請求到Yahoo Finance API"""
        try:
            url = f"{self.base_url}/{endpoint}"
            
            if not self.session:
                self.session = aiohttp.ClientSession(timeout=self.timeout)
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    error_text = await response.text()
                    logger.error(f"Yahoo Finance API錯誤: {response.status} - {error_text}")
                    raise ExternalAPIError(f"Yahoo Finance API請求失敗: {response.status}")
        
        except aiohttp.ClientError as e:
            logger.error(f"網路請求錯誤: {e}")
            raise ExternalAPIError(f"無法連接到Yahoo Finance: {str(e)}")
        except Exception as e:
            logger.error(f"Yahoo Finance服務錯誤: {e}")
            raise ExternalAPIError(f"Yahoo Finance服務異常: {str(e)}")
    
    async def get_real_time_quote(self, symbol: str) -> Optional[StockPrice]:
        """取得即時股價報價
        
        Args:
            symbol: 股票代碼 (如: "2330.TW" 對應台積電)
        
        Returns:
            StockPrice: 即時股價資料
        """
        try:
            # 檢查快取
            cache_key = f"yahoo_quote:{symbol}"
            if self.cache_manager:
                cached_data = await self.cache_manager.get(cache_key)
                if cached_data:
                    logger.info(f"從快取取得 {symbol} 即時報價")
                    return StockPrice(**cached_data)
            
            # 台灣股票需要添加 .TW 後綴
            if symbol.isdigit() and len(symbol) == 4:
                yahoo_symbol = f"{symbol}.TW"
            else:
                yahoo_symbol = symbol
            
            params = {
                "symbols": yahoo_symbol,
                "modules": "price"
            }
            
            data = await self._make_request("chart", params)
            
            if not data.get("chart", {}).get("result"):
                logger.warning(f"Yahoo Finance 無法取得 {symbol} 的資料")
                return None
            
            result = data["chart"]["result"][0]
            meta = result.get("meta", {})
            
            # 解析股價資料
            current_price = meta.get("regularMarketPrice")
            if current_price is None:
                logger.warning(f"無法取得 {symbol} 的當前價格")
                return None
            
            stock_price = StockPrice(
                symbol=symbol,
                current_price=Decimal(str(current_price)),
                open_price=Decimal(str(meta.get("regularMarketOpen", current_price))),
                high_price=Decimal(str(meta.get("regularMarketDayHigh", current_price))),
                low_price=Decimal(str(meta.get("regularMarketDayLow", current_price))),
                previous_close=Decimal(str(meta.get("previousClose", current_price))),
                volume=meta.get("regularMarketVolume", 0),
                market_cap=meta.get("marketCap"),
                timestamp=datetime.now(),
                currency=meta.get("currency", "TWD")
            )
            
            # 快取資料 (5分鐘)
            if self.cache_manager:
                await self.cache_manager.set(
                    cache_key, 
                    stock_price.dict(), 
                    expire=300
                )
            
            logger.info(f"成功取得 {symbol} 即時報價: ${current_price}")
            return stock_price
            
        except Exception as e:
            logger.error(f"取得即時報價失敗 {symbol}: {e}")
            raise ExternalAPIError(f"無法取得 {symbol} 即時報價: {str(e)}")
    
    async def get_historical_data(self, symbol: str, 
                                period: str = "1y",
                                interval: str = "1d") -> List[Dict[str, Any]]:
        """取得歷史股價資料
        
        Args:
            symbol: 股票代碼
            period: 時間區間 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: 資料間隔 (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
        
        Returns:
            List[Dict]: 歷史股價資料列表
        """
        try:
            # 快取檢查
            cache_key = f"yahoo_history:{symbol}:{period}:{interval}"
            if self.cache_manager:
                cached_data = await self.cache_manager.get(cache_key)
                if cached_data:
                    logger.info(f"從快取取得 {symbol} 歷史資料")
                    return cached_data
            
            # 台灣股票後綴處理
            if symbol.isdigit() and len(symbol) == 4:
                yahoo_symbol = f"{symbol}.TW"
            else:
                yahoo_symbol = symbol
            
            params = {
                "symbol": yahoo_symbol,
                "period1": 0,  # 將根據period動態計算
                "period2": int(datetime.now().timestamp()),
                "interval": interval,
                "includePrePost": "false",
                "events": "div,splits"
            }
            
            # 根據period計算開始時間
            if period == "1d":
                start_date = datetime.now() - timedelta(days=1)
            elif period == "1y":
                start_date = datetime.now() - timedelta(days=365)
            elif period == "2y":
                start_date = datetime.now() - timedelta(days=730)
            else:
                start_date = datetime.now() - timedelta(days=365)  # 預設1年
            
            params["period1"] = int(start_date.timestamp())
            
            data = await self._make_request("chart", params)
            
            if not data.get("chart", {}).get("result"):
                return []
            
            result = data["chart"]["result"][0]
            timestamps = result.get("timestamp", [])
            indicators = result.get("indicators", {})
            quote = indicators.get("quote", [{}])[0]
            
            historical_data = []
            for i, timestamp in enumerate(timestamps):
                try:
                    price_data = {
                        "date": datetime.fromtimestamp(timestamp).isoformat(),
                        "open": quote.get("open", [])[i] if i < len(quote.get("open", [])) else None,
                        "high": quote.get("high", [])[i] if i < len(quote.get("high", [])) else None,
                        "low": quote.get("low", [])[i] if i < len(quote.get("low", [])) else None,
                        "close": quote.get("close", [])[i] if i < len(quote.get("close", [])) else None,
                        "volume": quote.get("volume", [])[i] if i < len(quote.get("volume", [])) else None
                    }
                    
                    # 過濾掉有None值的資料
                    if price_data["close"] is not None:
                        historical_data.append(price_data)
                        
                except (IndexError, KeyError) as e:
                    logger.warning(f"解析第{i}筆歷史資料時發生錯誤: {e}")
                    continue
            
            # 快取資料 (30分鐘)
            if self.cache_manager and historical_data:
                await self.cache_manager.set(
                    cache_key, 
                    historical_data, 
                    expire=1800
                )
            
            logger.info(f"成功取得 {symbol} {len(historical_data)}筆歷史資料")
            return historical_data
            
        except Exception as e:
            logger.error(f"取得歷史資料失敗 {symbol}: {e}")
            raise ExternalAPIError(f"無法取得 {symbol} 歷史資料: {str(e)}")
    
    async def get_market_summary(self) -> Dict[str, Any]:
        """取得市場摘要資料"""
        try:
            cache_key = "yahoo_market_summary"
            if self.cache_manager:
                cached_data = await self.cache_manager.get(cache_key)
                if cached_data:
                    return cached_data
            
            # 台灣主要指數
            indices = ["^TWII", "^TW50"]  # 加權指數、台灣50
            market_data = {}
            
            for index in indices:
                try:
                    params = {"symbols": index, "modules": "price"}
                    data = await self._make_request("chart", params)
                    
                    if data.get("chart", {}).get("result"):
                        result = data["chart"]["result"][0]
                        meta = result.get("meta", {})
                        
                        market_data[index] = {
                            "current": meta.get("regularMarketPrice"),
                            "change": meta.get("regularMarketChange"),
                            "change_percent": meta.get("regularMarketChangePercent"),
                            "volume": meta.get("regularMarketVolume"),
                            "timestamp": datetime.now().isoformat()
                        }
                except Exception as e:
                    logger.warning(f"無法取得 {index} 資料: {e}")
                    continue
            
            # 快取10分鐘
            if self.cache_manager and market_data:
                await self.cache_manager.set(cache_key, market_data, expire=600)
            
            return market_data
            
        except Exception as e:
            logger.error(f"取得市場摘要失敗: {e}")
            raise ExternalAPIError(f"無法取得市場摘要: {str(e)}")
    
    async def validate_connection(self) -> bool:
        """驗證Yahoo Finance連線狀態"""
        try:
            # 測試取得台積電資料
            test_quote = await self.get_real_time_quote("2330")
            return test_quote is not None
        except Exception as e:
            logger.error(f"Yahoo Finance連線驗證失敗: {e}")
            return False


class MarketDataSyncService:
    """市場資料同步服務"""
    
    def __init__(self, yahoo_service: YahooFinanceService, db_connection):
        self.yahoo_service = yahoo_service
        self.db = db_connection
    
    async def sync_stock_prices(self, company_ids: List[str]) -> Dict[str, Any]:
        """批量同步股價資料"""
        try:
            results = {
                "success_count": 0,
                "failed_count": 0,
                "errors": []
            }
            
            for company_id in company_ids:
                try:
                    # 取得即時報價
                    quote = await self.yahoo_service.get_real_time_quote(company_id)
                    if quote:
                        # 儲存到資料庫 (這裡需要實作資料庫寫入邏輯)
                        await self._save_stock_price(quote)
                        results["success_count"] += 1
                        logger.info(f"成功同步 {company_id} 股價")
                    else:
                        results["failed_count"] += 1
                        results["errors"].append(f"{company_id}: 無法取得報價")
                        
                except Exception as e:
                    results["failed_count"] += 1
                    results["errors"].append(f"{company_id}: {str(e)}")
                    logger.error(f"同步 {company_id} 失敗: {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"批量同步失敗: {e}")
            raise ExternalAPIError(f"市場資料同步失敗: {str(e)}")
    
    async def _save_stock_price(self, stock_price: StockPrice):
        """儲存股價到資料庫"""
        # 這裡應該實作具體的資料庫寫入邏輯
        # 可能需要插入到 stock_prices 表或類似的時序資料表
        pass