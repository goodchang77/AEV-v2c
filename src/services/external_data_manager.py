#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
外部資料源統一管理器
External Data Sources Manager

整合 Yahoo Finance (台股/美股)、Alpha Vantage (美股) 和其他資料源
提供統一的資料存取介面和容錯機制
"""

import asyncio
import aiohttp
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import json
import logging
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np

# 導入本地服務模組
from .twse_service import TWStockExchangeService, TWStockInfo

logger = logging.getLogger(__name__)

class MarketType(Enum):
    """市場類型"""
    TAIWAN = "TW"
    US = "US"
    GLOBAL = "GLOBAL"

class DataSource(Enum):
    """資料源類型"""
    YAHOO_FINANCE = "yahoo_finance"
    ALPHA_VANTAGE = "alpha_vantage"
    TWSE = "twse"

@dataclass
class StockQuote:
    """股票報價資料結構"""
    symbol: str
    current_price: float
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    previous_close: Optional[float] = None
    volume: Optional[int] = None
    price_change: Optional[float] = None
    price_change_percent: Optional[float] = None
    timestamp: Optional[datetime] = None
    source: Optional[str] = None
    market_type: Optional[str] = None

@dataclass
class HistoricalData:
    """歷史資料結構"""
    date: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    adj_close: Optional[float] = None
    volume: Optional[int] = None

class YahooFinanceService:
    """Yahoo Finance 服務"""
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self.session = session
        self.base_url = "https://query1.finance.yahoo.com/v8/finance/chart/"
        
    async def __aenter__(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _format_taiwan_symbol(self, symbol: str) -> str:
        """格式化台股代碼"""
        if symbol.isdigit() and len(symbol) == 4:
            return f"{symbol}.TW"
        return symbol
    
    def _format_us_symbol(self, symbol: str) -> str:
        """格式化美股代碼"""
        return symbol.upper()
    
    async def get_quote(self, symbol: str, market_type: MarketType = MarketType.TAIWAN) -> Optional[StockQuote]:
        """獲取股票報價"""
        try:
            if market_type == MarketType.TAIWAN:
                formatted_symbol = self._format_taiwan_symbol(symbol)
            else:
                formatted_symbol = self._format_us_symbol(symbol)
            
            # 使用同步的 yfinance 獲取資料
            ticker = yf.Ticker(formatted_symbol)
            info = ticker.info
            hist = ticker.history(period="1d")
            
            if hist.empty or not info:
                return None
            
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            if not current_price and not hist.empty:
                current_price = float(hist['Close'].iloc[-1])
            
            if not current_price:
                return None
            
            # 計算價格變化
            previous_close = info.get('previousClose') or info.get('regularMarketPreviousClose')
            price_change = None
            price_change_percent = None
            
            if previous_close:
                price_change = current_price - previous_close
                price_change_percent = (price_change / previous_close) * 100
            
            return StockQuote(
                symbol=symbol,
                current_price=current_price,
                open_price=info.get('open') or info.get('regularMarketOpen'),
                high_price=info.get('dayHigh') or info.get('regularMarketDayHigh'),
                low_price=info.get('dayLow') or info.get('regularMarketDayLow'),
                previous_close=previous_close,
                volume=info.get('volume') or info.get('regularMarketVolume'),
                price_change=price_change,
                price_change_percent=price_change_percent,
                timestamp=datetime.now(),
                source="yahoo_finance",
                market_type=market_type.value
            )
            
        except Exception as e:
            logger.error(f"Yahoo Finance 獲取報價失敗 {symbol}: {e}")
            return None
    
    async def get_historical_data(self, symbol: str, market_type: MarketType = MarketType.TAIWAN, 
                                days: int = 30) -> List[HistoricalData]:
        """獲取歷史資料"""
        try:
            if market_type == MarketType.TAIWAN:
                formatted_symbol = self._format_taiwan_symbol(symbol)
            else:
                formatted_symbol = self._format_us_symbol(symbol)
            
            ticker = yf.Ticker(formatted_symbol)
            hist = ticker.history(period=f"{days}d")
            
            if hist.empty:
                return []
            
            historical_data = []
            for date, row in hist.iterrows():
                historical_data.append(HistoricalData(
                    date=date.to_pydatetime(),
                    open_price=float(row['Open']),
                    high_price=float(row['High']),
                    low_price=float(row['Low']),
                    close_price=float(row['Close']),
                    adj_close=float(row['Close']),  # yfinance 已調整
                    volume=int(row['Volume']) if pd.notna(row['Volume']) else None
                ))
            
            return sorted(historical_data, key=lambda x: x.date, reverse=True)
            
        except Exception as e:
            logger.error(f"Yahoo Finance 獲取歷史資料失敗 {symbol}: {e}")
            return []

class AlphaVantageService:
    """Alpha Vantage 服務"""
    
    def __init__(self, api_key: str, session: Optional[aiohttp.ClientSession] = None):
        self.api_key = api_key
        self.session = session
        self.base_url = "https://www.alphavantage.co/query"
        self._request_count = 0
        self._last_request_time = datetime.now()
        
    async def __aenter__(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _rate_limit(self):
        """API 請求速率限制"""
        now = datetime.now()
        if (now - self._last_request_time).seconds < 12:  # Alpha Vantage 限制每分鐘5次
            await asyncio.sleep(12)
        self._last_request_time = datetime.now()
        self._request_count += 1
    
    async def get_quote(self, symbol: str) -> Optional[StockQuote]:
        """獲取美股報價"""
        try:
            await self._rate_limit()
            
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': symbol.upper(),
                'apikey': self.api_key
            }
            
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            async with self.session.get(self.base_url, params=params) as response:
                data = await response.json()
                
                if 'Global Quote' not in data:
                    logger.warning(f"Alpha Vantage 無資料回應: {data}")
                    return None
                
                quote_data = data['Global Quote']
                
                current_price = float(quote_data.get('05. price', 0))
                previous_close = float(quote_data.get('08. previous close', 0))
                
                if current_price == 0:
                    return None
                
                price_change = float(quote_data.get('09. change', 0))
                price_change_percent = float(quote_data.get('10. change percent', '0%').rstrip('%'))
                
                return StockQuote(
                    symbol=symbol,
                    current_price=current_price,
                    open_price=float(quote_data.get('02. open', 0)) or None,
                    high_price=float(quote_data.get('03. high', 0)) or None,
                    low_price=float(quote_data.get('04. low', 0)) or None,
                    previous_close=previous_close or None,
                    volume=int(quote_data.get('06. volume', 0)) or None,
                    price_change=price_change,
                    price_change_percent=price_change_percent,
                    timestamp=datetime.now(),
                    source="alpha_vantage",
                    market_type=MarketType.US.value
                )
                
        except Exception as e:
            logger.error(f"Alpha Vantage 獲取報價失敗 {symbol}: {e}")
            return None
    
    async def get_historical_data(self, symbol: str, days: int = 30) -> List[HistoricalData]:
        """獲取歷史資料"""
        try:
            await self._rate_limit()
            
            params = {
                'function': 'TIME_SERIES_DAILY',
                'symbol': symbol.upper(),
                'apikey': self.api_key,
                'outputsize': 'compact'  # 最近100天
            }
            
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            async with self.session.get(self.base_url, params=params) as response:
                data = await response.json()
                
                if 'Time Series (Daily)' not in data:
                    logger.warning(f"Alpha Vantage 歷史資料無回應: {data}")
                    return []
                
                time_series = data['Time Series (Daily)']
                historical_data = []
                
                # 取最近 days 天的資料
                sorted_dates = sorted(time_series.keys(), reverse=True)[:days]
                
                for date_str in sorted_dates:
                    day_data = time_series[date_str]
                    
                    historical_data.append(HistoricalData(
                        date=datetime.strptime(date_str, '%Y-%m-%d'),
                        open_price=float(day_data['1. open']),
                        high_price=float(day_data['2. high']),
                        low_price=float(day_data['3. low']),
                        close_price=float(day_data['4. close']),
                        adj_close=float(day_data['4. close']),
                        volume=int(day_data['5. volume'])
                    ))
                
                return historical_data
                
        except Exception as e:
            logger.error(f"Alpha Vantage 獲取歷史資料失敗 {symbol}: {e}")
            return []

class ExternalDataManager:
    """外部資料源統一管理器"""
    
    def __init__(self, alpha_vantage_key: Optional[str] = None, cache_manager=None):
        self.alpha_vantage_key = alpha_vantage_key
        self.cache_manager = cache_manager
        self.session = None
        
        # 初始化服務
        self.yahoo_service = None
        self.alpha_service = None
        self.twse_service = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        self.yahoo_service = YahooFinanceService(self.session)
        
        if self.alpha_vantage_key:
            self.alpha_service = AlphaVantageService(self.alpha_vantage_key, self.session)
            
        # 初始化 TWSE 服務
        self.twse_service = TWStockExchangeService()
        await self.twse_service.__aenter__()
            
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.twse_service:
            await self.twse_service.__aexit__(exc_type, exc_val, exc_tb)
        if self.session:
            await self.session.close()
    
    def _is_taiwan_stock(self, symbol: str) -> bool:
        """判斷是否為台股"""
        return symbol.isdigit() and len(symbol) == 4
    
    def _convert_twse_to_stock_quote(self, twse_quote: TWStockInfo) -> StockQuote:
        """將 TWStockInfo 轉換為標準 StockQuote 格式"""
        return StockQuote(
            symbol=twse_quote.symbol,
            current_price=twse_quote.current_price,
            open_price=twse_quote.open_price,
            high_price=twse_quote.high_price,
            low_price=twse_quote.low_price,
            previous_close=twse_quote.current_price - twse_quote.change if twse_quote.change else None,
            volume=twse_quote.volume,
            price_change=twse_quote.change,
            price_change_percent=twse_quote.change_percent,
            timestamp=twse_quote.timestamp,
            source="twse",
            market_type="TW"
        )
    
    def _get_cache_key(self, operation: str, symbol: str, **kwargs) -> str:
        """生成快取鍵"""
        key_parts = [operation, symbol]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        return ":".join(key_parts)
    
    async def _get_cached_data(self, cache_key: str, ttl_seconds: int = 300):
        """獲取快取資料"""
        if not self.cache_manager:
            return None
            
        try:
            cached = await self.cache_manager.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"快取讀取失敗: {e}")
        return None
    
    async def _set_cached_data(self, cache_key: str, data: Any, ttl_seconds: int = 300):
        """設定快取資料"""
        if not self.cache_manager:
            return
            
        try:
            await self.cache_manager.set(cache_key, json.dumps(data, default=str), ex=ttl_seconds)
        except Exception as e:
            logger.warning(f"快取寫入失敗: {e}")
    
    async def get_stock_quote(self, symbol: str, prefer_source: Optional[DataSource] = None) -> Optional[StockQuote]:
        """
        獲取股票報價
        自動判斷市場類型並選擇最佳資料源
        """
        # 檢查快取
        cache_key = self._get_cache_key("quote", symbol, prefer_source=prefer_source.value if prefer_source else None)
        cached_data = await self._get_cached_data(cache_key, ttl_seconds=60)  # 1分鐘快取
        
        if cached_data:
            return StockQuote(**cached_data)
        
        quote = None
        is_taiwan = self._is_taiwan_stock(symbol)
        
        try:
            if prefer_source == DataSource.TWSE and is_taiwan and self.twse_service:
                # 強制使用 TWSE (僅台股)
                twse_quote = await self.twse_service.get_stock_quote(symbol)
                if twse_quote:
                    quote = self._convert_twse_to_stock_quote(twse_quote)
                    
            elif prefer_source == DataSource.ALPHA_VANTAGE and self.alpha_service and not is_taiwan:
                # 強制使用 Alpha Vantage (僅美股)
                quote = await self.alpha_service.get_quote(symbol)
                
            elif prefer_source == DataSource.YAHOO_FINANCE:
                # 使用 Yahoo Finance (支援台股/美股)
                market_type = MarketType.TAIWAN if is_taiwan else MarketType.US
                quote = await self.yahoo_service.get_quote(symbol, market_type)
                
            else:
                # 預設邏輯: 台股優先使用 TWSE，美股優先使用 Alpha Vantage
                if is_taiwan and self.twse_service:
                    # 台股: 優先使用 TWSE
                    twse_quote = await self.twse_service.get_stock_quote(symbol)
                    if twse_quote:
                        quote = self._convert_twse_to_stock_quote(twse_quote)
                    
                    # TWSE 失敗時嘗試 Yahoo Finance 作為備援
                    if not quote and self.yahoo_service:
                        logger.info(f"TWSE 失敗，嘗試 Yahoo Finance: {symbol}")
                        quote = await self.yahoo_service.get_quote(symbol, MarketType.TAIWAN)
                        
                else:
                    # 美股: 優先使用 Alpha Vantage
                    if self.alpha_service:
                        quote = await self.alpha_service.get_quote(symbol)
                    
                    # Alpha Vantage 失敗時嘗試 Yahoo Finance
                    if not quote and self.yahoo_service:
                        logger.info(f"Alpha Vantage 失敗，嘗試 Yahoo Finance: {symbol}")
                        quote = await self.yahoo_service.get_quote(symbol, MarketType.US)
            
            # 快取結果
            if quote:
                await self._set_cached_data(cache_key, asdict(quote), ttl_seconds=60)
                
            return quote
            
        except Exception as e:
            logger.error(f"獲取股票報價失敗 {symbol}: {e}")
            return None
    
    async def get_historical_data(self, symbol: str, days: int = 30, 
                                prefer_source: Optional[DataSource] = None) -> List[HistoricalData]:
        """
        獲取歷史資料
        """
        # 檢查快取
        cache_key = self._get_cache_key("historical", symbol, days=days, prefer_source=prefer_source.value if prefer_source else None)
        cached_data = await self._get_cached_data(cache_key, ttl_seconds=3600)  # 1小時快取
        
        if cached_data:
            return [HistoricalData(**item) for item in cached_data]
        
        historical_data = []
        is_taiwan = self._is_taiwan_stock(symbol)
        
        try:
            if prefer_source == DataSource.ALPHA_VANTAGE and self.alpha_service and not is_taiwan:
                # 使用 Alpha Vantage
                historical_data = await self.alpha_service.get_historical_data(symbol, days)
                
            elif prefer_source == DataSource.YAHOO_FINANCE or prefer_source is None:
                # 使用 Yahoo Finance
                market_type = MarketType.TAIWAN if is_taiwan else MarketType.US
                historical_data = await self.yahoo_service.get_historical_data(symbol, market_type, days)
                
                # 如果失敗且有 Alpha Vantage，嘗試美股
                if not historical_data and not is_taiwan and self.alpha_service:
                    logger.info(f"Yahoo Finance 歷史資料失敗，嘗試 Alpha Vantage: {symbol}")
                    historical_data = await self.alpha_service.get_historical_data(symbol, days)
            
            # 快取結果
            if historical_data:
                cache_data = [asdict(item) for item in historical_data]
                await self._set_cached_data(cache_key, cache_data, ttl_seconds=3600)
                
            return historical_data
            
        except Exception as e:
            logger.error(f"獲取歷史資料失敗 {symbol}: {e}")
            return []
    
    async def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, Optional[StockQuote]]:
        """
        批量獲取多個股票報價
        """
        results = {}
        
        # 並行處理多個請求
        tasks = []
        for symbol in symbols:
            task = self.get_stock_quote(symbol)
            tasks.append((symbol, task))
        
        # 執行所有任務
        for symbol, task in tasks:
            try:
                quote = await task
                results[symbol] = quote
            except Exception as e:
                logger.error(f"批量獲取報價失敗 {symbol}: {e}")
                results[symbol] = None
                
        return results
    
    async def health_check(self) -> Dict[str, bool]:
        """
        健康檢查所有資料源
        """
        results = {}
        
        # 測試 Yahoo Finance
        try:
            # 測試台股
            tw_quote = await self.yahoo_service.get_quote("2330", MarketType.TAIWAN)
            results["yahoo_finance_tw"] = tw_quote is not None
            
            # 測試美股
            us_quote = await self.yahoo_service.get_quote("AAPL", MarketType.US)
            results["yahoo_finance_us"] = us_quote is not None
            
        except Exception as e:
            logger.error(f"Yahoo Finance 健康檢查失敗: {e}")
            results["yahoo_finance_tw"] = False
            results["yahoo_finance_us"] = False
        
        # 測試 Alpha Vantage
        if self.alpha_service:
            try:
                av_quote = await self.alpha_service.get_quote("AAPL")
                results["alpha_vantage"] = av_quote is not None
            except Exception as e:
                logger.error(f"Alpha Vantage 健康檢查失敗: {e}")
                results["alpha_vantage"] = False
        else:
            results["alpha_vantage"] = False
        
        # 測試 TWSE
        if self.twse_service:
            try:
                twse_health = await self.twse_service.health_check()
                results["twse"] = twse_health
            except Exception as e:
                logger.error(f"TWSE 健康檢查失敗: {e}")
                results["twse"] = False
        else:
            results["twse"] = False
            
        return results
    
    def get_available_sources(self) -> Dict[str, Dict[str, Any]]:
        """
        獲取可用資料源資訊
        """
        sources = {
            "yahoo_finance": {
                "name": "Yahoo Finance",
                "markets": ["TW", "US", "Global"],
                "features": ["real_time_quotes", "historical_data", "free"],
                "rate_limit": "無限制",
                "reliability": "高"
            }
        }
        
        if self.alpha_vantage_key:
            sources["alpha_vantage"] = {
                "name": "Alpha Vantage",
                "markets": ["US"],
                "features": ["real_time_quotes", "historical_data", "api_key_required"],
                "rate_limit": "5 calls/minute",
                "reliability": "高"
            }
            
        return sources

# 便利函數
async def create_data_manager(alpha_vantage_key: Optional[str] = None, 
                            cache_manager=None) -> ExternalDataManager:
    """
    創建外部資料管理器實例
    """
    manager = ExternalDataManager(
        alpha_vantage_key=alpha_vantage_key,
        cache_manager=cache_manager
    )
    return manager

# 快速測試函數
async def quick_test():
    """快速測試功能"""
    print("🧪 快速測試外部資料源...")
    
    alpha_key = "***REMOVED***"  # 從檔案中讀取的 API Key
    
    async with ExternalDataManager(alpha_vantage_key=alpha_key) as manager:
        # 測試台股
        print("📊 測試台積電報價...")
        tsmc_quote = await manager.get_stock_quote("2330")
        if tsmc_quote:
            print(f"✅ 台積電: ${tsmc_quote.current_price}")
        
        # 測試美股
        print("🍎 測試蘋果報價...")
        aapl_quote = await manager.get_stock_quote("AAPL")
        if aapl_quote:
            print(f"✅ 蘋果: ${aapl_quote.current_price}")
        
        # 健康檢查
        print("🏥 資料源健康檢查...")
        health = await manager.health_check()
        for source, status in health.items():
            print(f"   {source}: {'✅' if status else '❌'}")

if __name__ == "__main__":
    asyncio.run(quick_test())