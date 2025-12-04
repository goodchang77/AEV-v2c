"""
多資料源市場資料整合服務
Multi-Source Market Data Integration Service
"""

import asyncio
import aiohttp
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from decimal import Decimal
import json

from src.core.logging import get_logger
from src.core.cache import get_cache_manager
from src.core.exceptions import ExternalAPIError
from src.schemas.market_data import StockPrice, HistoricalPrice
from src.services.twse_backup import TWSEBackupSource
from src.services.yahoo_tw_source import YahooTaiwanDataSource

logger = get_logger("market_data_sources")


class DataSource(ABC):
    """資料源基礎類別"""
    
    def __init__(self, name: str, cache_manager=None):
        self.name = name
        self.cache_manager = cache_manager
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Accept": "application/json, text/html, application/xhtml+xml, application/xml;q=0.9, image/webp, */*;q=0.8",
                "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Connection": "keep-alive",
                "DNT": "1",
                "Referer": "https://mis.twse.com.tw/"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def get_real_time_quote(self, symbol: str) -> Optional[StockPrice]:
        """取得即時報價"""
        pass
    
    @abstractmethod
    async def get_historical_data(self, symbol: str, days: int = 30) -> List[HistoricalPrice]:
        """取得歷史資料"""
        pass
    
    @abstractmethod
    async def validate_connection(self) -> bool:
        """驗證連線"""
        pass


class TWSEDataSource(DataSource):
    """台灣證券交易所資料源"""
    
    def __init__(self, cache_manager=None):
        super().__init__("TWSE", cache_manager)
        self.base_url = "https://mis.twse.com.tw/stock/api"
        self.history_url = "https://www.twse.com.tw/exchangeReport"
    
    async def get_real_time_quote(self, symbol: str) -> Optional[StockPrice]:
        """取得台股即時報價 - 優先使用主要API，失敗時自動切換備用源"""
        try:
            # 先嘗試原有方法
            quote = await self._get_quote_primary(symbol)
            if quote:
                return quote
            
            # 主要方法失敗，嘗試備用TWSE資料源
            logger.warning(f"主要TWSE API失敗，切換TWSE備用資料源: {symbol}")
            async with TWSEBackupSource(self.cache_manager) as backup:
                quote = await backup.get_real_time_quote(symbol)
                if quote:
                    logger.info(f"TWSE備用資料源成功取得 {symbol} 報價")
                    return quote
            
            # TWSE備用資料源失敗，嘗試Yahoo Taiwan真實資料源
            logger.warning(f"TWSE備用資料源失敗，切換Yahoo Taiwan資料源: {symbol}")
            async with YahooTaiwanDataSource(self.cache_manager) as yahoo_tw:
                quote = await yahoo_tw.get_real_time_quote(symbol)
                if quote:
                    logger.info(f"Yahoo Taiwan資料源成功取得 {symbol} 報價")
                    return quote
            
            # 所有真實資料源都失敗
            logger.error(f"所有真實台股資料源都無法取得 {symbol} 報價")
            return None
                
        except Exception as e:
            logger.error(f"TWSE取得報價失敗 {symbol}: {e}")
            return None
    
    async def _get_quote_primary(self, symbol: str) -> Optional[StockPrice]:
        """主要TWSE API方法"""
        try:
            # 快取檢查
            cache_key = f"twse_quote:{symbol}"
            if self.cache_manager:
                cached = await self.cache_manager.get(cache_key)
                if cached:
                    return StockPrice(**cached)
            
            # 台股代碼格式化
            if symbol.endswith('.TW'):
                symbol = symbol[:-3]
            
            # 改用更穩定的TWSE API端點
            url = f"{self.base_url}/getStockInfo.jsp"
            params = {
                "ex_ch": f"tse_{symbol}.tw",
                "json": "1",
                "delay": "0"
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
                "Referer": "https://mis.twse.com.tw/stock/fibest.jsp"
            }
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("rtcode") == "0000" and data.get("msgArray"):
                        stock_data = data["msgArray"][0]
                        
                        # 建構StockPrice物件
                        quote = StockPrice(
                            symbol=symbol,
                            current_price=Decimal(stock_data.get("z", "0")),
                            open_price=Decimal(stock_data.get("o", "0")),
                            high_price=Decimal(stock_data.get("h", "0")),
                            low_price=Decimal(stock_data.get("l", "0")),
                            previous_close=Decimal(stock_data.get("y", "0")),
                            volume=int(stock_data.get("v", "0")),
                            timestamp=datetime.now(),
                            currency="TWD"
                        )
                        
                        # 快取資料
                        if self.cache_manager:
                            await self.cache_manager.set(
                                cache_key, 
                                quote.dict(), 
                                expire=60  # 1分鐘快取
                            )
                        
                        logger.info(f"成功取得TWSE {symbol} 報價: ${quote.current_price}")
                        return quote
                
                return None
                
        except Exception as e:
            logger.warning(f"TWSE主要API失敗 {symbol}: {e}")
            return None
    
    async def get_historical_data(self, symbol: str, days: int = 30) -> List[HistoricalPrice]:
        """取得台股歷史資料"""
        try:
            if symbol.endswith('.TW'):
                symbol = symbol[:-3]
            
            # 計算日期範圍
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            url = f"{self.history_url}/STOCK_DAY"
            params = {
                "response": "json",
                "date": end_date.strftime("%Y%m%d"),
                "stockNo": symbol
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("stat") == "OK":
                        historical_data = []
                        
                        for row in data.get("data", []):
                            try:
                                date_str = row[0].replace("/", "-")
                                date_parts = date_str.split("-")
                                # 民國年轉西元年
                                year = int(date_parts[0]) + 1911
                                month = int(date_parts[1])
                                day = int(date_parts[2])
                                
                                hist_price = HistoricalPrice(
                                    symbol=symbol,
                                    date=datetime(year, month, day),
                                    open_price=Decimal(row[3].replace(",", "")),
                                    high_price=Decimal(row[4].replace(",", "")),
                                    low_price=Decimal(row[5].replace(",", "")),
                                    close_price=Decimal(row[6].replace(",", "")),
                                    volume=int(row[1].replace(",", ""))
                                )
                                historical_data.append(hist_price)
                                
                            except (IndexError, ValueError) as e:
                                logger.warning(f"解析TWSE歷史資料錯誤: {e}")
                                continue
                        
                        logger.info(f"成功取得TWSE {symbol} 歷史資料 {len(historical_data)} 筆")
                        return historical_data
                
                return []
                
        except Exception as e:
            logger.error(f"TWSE取得歷史資料失敗 {symbol}: {e}")
            return []
    
    async def validate_connection(self) -> bool:
        """驗證TWSE連線"""
        try:
            # 測試取得台積電資料
            quote = await self.get_real_time_quote("2330")
            return quote is not None
        except Exception:
            return False


class AlphaVantageDataSource(DataSource):
    """Alpha Vantage資料源"""
    
    def __init__(self, api_key: str, cache_manager=None):
        super().__init__("AlphaVantage", cache_manager)
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
    
    async def get_real_time_quote(self, symbol: str) -> Optional[StockPrice]:
        """取得國際股市即時報價"""
        try:
            cache_key = f"alpha_quote:{symbol}"
            if self.cache_manager:
                cached = await self.cache_manager.get(cache_key)
                if cached:
                    return StockPrice(**cached)
            
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": self.api_key
            }
            
            async with self.session.get(self.base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    global_quote = data.get("Global Quote", {})
                    if global_quote:
                        quote = StockPrice(
                            symbol=symbol,
                            current_price=Decimal(global_quote.get("05. price", "0")),
                            open_price=Decimal(global_quote.get("02. open", "0")),
                            high_price=Decimal(global_quote.get("03. high", "0")),
                            low_price=Decimal(global_quote.get("04. low", "0")),
                            previous_close=Decimal(global_quote.get("08. previous close", "0")),
                            volume=int(global_quote.get("06. volume", "0")),
                            timestamp=datetime.now(),
                            currency="USD"  # 預設USD，需要根據市場調整
                        )
                        
                        # 快取5分鐘
                        if self.cache_manager:
                            await self.cache_manager.set(
                                cache_key, 
                                quote.dict(), 
                                expire=300
                            )
                        
                        logger.info(f"成功取得AlphaVantage {symbol} 報價: ${quote.current_price}")
                        return quote
                
                return None
                
        except Exception as e:
            logger.error(f"AlphaVantage取得報價失敗 {symbol}: {e}")
            return None
    
    async def get_historical_data(self, symbol: str, days: int = 30) -> List[HistoricalPrice]:
        """取得歷史資料"""
        try:
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "apikey": self.api_key,
                "outputsize": "compact"  # 最近100天
            }
            
            async with self.session.get(self.base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    time_series = data.get("Time Series (Daily)", {})
                    if time_series:
                        historical_data = []
                        
                        for date_str, values in list(time_series.items())[:days]:
                            try:
                                hist_price = HistoricalPrice(
                                    symbol=symbol,
                                    date=datetime.strptime(date_str, "%Y-%m-%d"),
                                    open_price=Decimal(values["1. open"]),
                                    high_price=Decimal(values["2. high"]),
                                    low_price=Decimal(values["3. low"]),
                                    close_price=Decimal(values["4. close"]),
                                    volume=int(values["5. volume"])
                                )
                                historical_data.append(hist_price)
                            except (KeyError, ValueError) as e:
                                logger.warning(f"解析AlphaVantage資料錯誤: {e}")
                                continue
                        
                        logger.info(f"成功取得AlphaVantage {symbol} 歷史資料 {len(historical_data)} 筆")
                        return historical_data
                
                return []
                
        except Exception as e:
            logger.error(f"AlphaVantage取得歷史資料失敗 {symbol}: {e}")
            return []
    
    async def validate_connection(self) -> bool:
        """驗證AlphaVantage連線"""
        try:
            # 測試取得蘋果股票資料
            quote = await self.get_real_time_quote("AAPL")
            return quote is not None
        except Exception:
            return False


class FugleDataSource(DataSource):
    """Fugle富果資料源 (範例實作)"""
    
    def __init__(self, api_key: str, cache_manager=None):
        super().__init__("Fugle", cache_manager)
        self.api_key = api_key
        self.base_url = "https://api.fugle.tw/realtime/v0.3"
        self.headers = {"X-API-KEY": api_key}
    
    async def get_real_time_quote(self, symbol: str) -> Optional[StockPrice]:
        """取得Fugle即時報價"""
        try:
            if symbol.endswith('.TW'):
                symbol = symbol[:-3]
            
            url = f"{self.base_url}/intraday/quote"
            params = {"symbolId": symbol}
            
            async with self.session.get(url, params=params, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("apiVersion") and data.get("data"):
                        quote_data = data["data"]
                        
                        quote = StockPrice(
                            symbol=symbol,
                            current_price=Decimal(str(quote_data.get("trade", {}).get("price", 0))),
                            open_price=Decimal(str(quote_data.get("priceReference", {}).get("open", 0))),
                            high_price=Decimal(str(quote_data.get("priceReference", {}).get("high", 0))),
                            low_price=Decimal(str(quote_data.get("priceReference", {}).get("low", 0))),
                            previous_close=Decimal(str(quote_data.get("priceReference", {}).get("previousClose", 0))),
                            volume=int(quote_data.get("trade", {}).get("volume", 0)),
                            timestamp=datetime.now(),
                            currency="TWD"
                        )
                        
                        logger.info(f"成功取得Fugle {symbol} 報價: ${quote.current_price}")
                        return quote
                
                return None
                
        except Exception as e:
            logger.error(f"Fugle取得報價失敗 {symbol}: {e}")
            return None
    
    async def get_historical_data(self, symbol: str, days: int = 30) -> List[HistoricalPrice]:
        """取得歷史資料"""
        # Fugle歷史資料API實作 (需要付費版本)
        return []
    
    async def validate_connection(self) -> bool:
        """驗證Fugle連線"""
        try:
            quote = await self.get_real_time_quote("2330")
            return quote is not None
        except Exception:
            return False


class MarketDataAggregator:
    """多資料源聚合器"""
    
    def __init__(self, cache_manager=None):
        self.cache_manager = cache_manager
        self.data_sources: Dict[str, DataSource] = {}
        self.taiwan_sources = []  # 台股資料源
        self.international_sources = []  # 國際股市資料源
    
    def add_data_source(self, source: DataSource, markets: List[str]):
        """添加資料源"""
        self.data_sources[source.name] = source
        
        if "TW" in markets:
            self.taiwan_sources.append(source)
        if "US" in markets:
            self.international_sources.append(source)
    
    async def get_best_quote(self, symbol: str) -> Optional[StockPrice]:
        """取得最佳報價 (多資料源容錯)"""
        # 判斷股票市場
        is_taiwan_stock = (
            symbol.endswith('.TW') or 
            (symbol.isdigit() and len(symbol) == 4)
        )
        
        sources = self.taiwan_sources if is_taiwan_stock else self.international_sources
        
        for source in sources:
            try:
                async with source:
                    quote = await source.get_real_time_quote(symbol)
                    if quote and quote.current_price > 0:
                        logger.info(f"使用 {source.name} 成功取得 {symbol} 報價")
                        return quote
            except Exception as e:
                logger.warning(f"{source.name} 取得報價失敗: {e}")
                continue
        
        logger.error(f"所有資料源都無法取得 {symbol} 報價")
        return None
    
    async def get_aggregated_historical_data(self, symbol: str, days: int = 30) -> List[HistoricalPrice]:
        """取得聚合歷史資料"""
        is_taiwan_stock = (
            symbol.endswith('.TW') or 
            (symbol.isdigit() and len(symbol) == 4)
        )
        
        sources = self.taiwan_sources if is_taiwan_stock else self.international_sources
        
        for source in sources:
            try:
                async with source:
                    historical_data = await source.get_historical_data(symbol, days)
                    if historical_data:
                        logger.info(f"使用 {source.name} 成功取得 {symbol} 歷史資料")
                        return historical_data
            except Exception as e:
                logger.warning(f"{source.name} 取得歷史資料失敗: {e}")
                continue
        
        logger.error(f"所有資料源都無法取得 {symbol} 歷史資料")
        return []
    
    async def health_check(self) -> Dict[str, bool]:
        """檢查所有資料源健康狀態"""
        health_status = {}
        
        for name, source in self.data_sources.items():
            try:
                async with source:
                    is_healthy = await source.validate_connection()
                    health_status[name] = is_healthy
                    logger.info(f"{name} 健康狀態: {'正常' if is_healthy else '異常'}")
            except Exception as e:
                health_status[name] = False
                logger.error(f"{name} 健康檢查失敗: {e}")
        
        return health_status


# 工廠函數 - 建立預設配置的聚合器
async def create_market_data_aggregator(
    alpha_vantage_key: Optional[str] = None,
    fugle_key: Optional[str] = None,
    cache_manager=None
) -> MarketDataAggregator:
    """建立市場資料聚合器"""
    
    aggregator = MarketDataAggregator(cache_manager)
    
    # 添加TWSE資料源 (台股主要來源)
    twse_source = TWSEDataSource(cache_manager)
    aggregator.add_data_source(twse_source, ["TW"])
    
    # 添加Yahoo Taiwan資料源 (台股備用來源)
    yahoo_tw_source = YahooTaiwanDataSource(cache_manager)
    aggregator.add_data_source(yahoo_tw_source, ["TW"])
    
    # 添加Alpha Vantage (國際股市)
    if alpha_vantage_key:
        alpha_source = AlphaVantageDataSource(alpha_vantage_key, cache_manager)
        aggregator.add_data_source(alpha_source, ["US", "International"])
    
    # 添加Fugle (台股專業版)
    if fugle_key:
        fugle_source = FugleDataSource(fugle_key, cache_manager)
        aggregator.add_data_source(fugle_source, ["TW"])
    
    logger.info(f"市場資料聚合器初始化完成，共 {len(aggregator.data_sources)} 個資料源")
    return aggregator