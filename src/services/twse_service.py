#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
台灣證券交易所 (TWSE) API 服務
Taiwan Stock Exchange API Service

提供台股即時資料獲取功能，包括：
- 個股日成交資訊
- 股價資料查詢
- 證券基本資料
"""

import aiohttp
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class TWStockInfo:
    """台股資訊資料類別"""
    symbol: str                    # 證券代號
    name: str                      # 證券名稱 
    current_price: float           # 收盤價
    change: Optional[float] = None # 漲跌價差
    change_percent: Optional[float] = None  # 漲跌幅度
    volume: Optional[int] = None   # 成交股數
    turnover: Optional[float] = None  # 成交金額
    open_price: Optional[float] = None  # 開盤價
    high_price: Optional[float] = None  # 最高價
    low_price: Optional[float] = None   # 最低價
    transaction_count: Optional[int] = None  # 成交筆數
    timestamp: datetime = datetime.now()

class TWStockExchangeService:
    """台灣證券交易所 API 服務"""
    
    def __init__(self):
        self.base_url = "https://openapi.twse.com.tw/v1"
        self.backup_url = "https://www.twse.com.tw/exchangeReport"
        self.session: Optional[aiohttp.ClientSession] = None
        self._stock_data_cache: Dict[str, TWStockInfo] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_duration = timedelta(minutes=5)  # 快取 5 分鐘
    
    async def __aenter__(self):
        """異步上下文管理器進入"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'Mozilla/5.0 (compatible; TWSE-API-Client)'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """異步上下文管理器退出"""
        if self.session:
            await self.session.close()
    
    def _is_cache_valid(self) -> bool:
        """檢查快取是否有效"""
        if not self._cache_timestamp:
            return False
        return datetime.now() - self._cache_timestamp < self._cache_duration
    
    async def _fetch_all_stocks_data(self) -> Dict[str, TWStockInfo]:
        """獲取所有上市股票的當日成交資訊"""
        if self._is_cache_valid():
            logger.info("使用快取的股票資料")
            return self._stock_data_cache
        
        try:
            # 嘗試主要 API
            url = f"{self.base_url}/exchangeReport/STOCK_DAY_ALL"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    stocks = self._parse_stock_data(data)
                    
                    # 更新快取
                    self._stock_data_cache = stocks
                    self._cache_timestamp = datetime.now()
                    
                    logger.info(f"成功獲取 {len(stocks)} 檔股票資料")
                    return stocks
                else:
                    logger.warning(f"TWSE API 回應錯誤: {response.status}")
        
        except Exception as e:
            logger.error(f"獲取 TWSE 股票資料失敗: {e}")
        
        # 嘗試備用 API
        try:
            backup_url = f"{self.backup_url}/STOCK_DAY_ALL?response=open_data"
            
            async with self.session.get(backup_url) as response:
                if response.status == 200:
                    data = await response.json()
                    stocks = self._parse_stock_data(data)
                    
                    # 更新快取
                    self._stock_data_cache = stocks
                    self._cache_timestamp = datetime.now()
                    
                    logger.info(f"備用 API 成功獲取 {len(stocks)} 檔股票資料")
                    return stocks
                    
        except Exception as e:
            logger.error(f"備用 API 也失敗: {e}")
        
        # 如果都失敗，返回舊的快取資料
        if self._stock_data_cache:
            logger.warning("API 失敗，使用舊的快取資料")
            return self._stock_data_cache
        
        return {}
    
    def _parse_stock_data(self, data: List[Dict]) -> Dict[str, TWStockInfo]:
        """解析 TWSE API 回傳的股票資料"""
        stocks = {}
        
        for item in data:
            try:
                if not isinstance(item, dict):
                    continue
                
                # TWSE API 回傳格式為字典:
                # {'Date': '1140829', 'Code': '2330', 'Name': '台積電', 
                #  'TradeVolume': '21820054', 'TradeValue': '25485864558',
                #  'OpeningPrice': '1180.00', 'HighestPrice': '1185.00', 
                #  'LowestPrice': '1160.00', 'ClosingPrice': '1160.00', 
                #  'Change': '0.0000', 'Transaction': '25658'}
                
                symbol = item.get('Code', '').strip()
                name = item.get('Name', '').strip()
                
                if not symbol:
                    continue
                
                # 處理數值欄位，去除逗號並轉換
                def safe_float(value: str) -> Optional[float]:
                    try:
                        if not value or value in ['--', '-', '']:
                            return None
                        return float(str(value).replace(',', '').replace('+', ''))
                    except (ValueError, AttributeError, TypeError):
                        return None
                
                def safe_int(value: str) -> Optional[int]:
                    try:
                        if not value or value in ['--', '-', '']:
                            return None
                        return int(str(value).replace(',', ''))
                    except (ValueError, AttributeError, TypeError):
                        return None
                
                volume = safe_int(item.get('TradeVolume'))
                turnover = safe_float(item.get('TradeValue'))
                open_price = safe_float(item.get('OpeningPrice'))
                high_price = safe_float(item.get('HighestPrice'))
                low_price = safe_float(item.get('LowestPrice'))
                close_price = safe_float(item.get('ClosingPrice'))
                change = safe_float(item.get('Change'))
                transaction_count = safe_int(item.get('Transaction'))
                
                # 計算漲跌幅
                change_percent = None
                if change and close_price and close_price - change != 0:
                    change_percent = (change / (close_price - change)) * 100
                
                stock_info = TWStockInfo(
                    symbol=symbol,
                    name=name,
                    current_price=close_price if close_price else 0.0,
                    change=change,
                    change_percent=change_percent,
                    volume=volume,
                    turnover=turnover,
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    transaction_count=transaction_count,
                    timestamp=datetime.now()
                )
                
                stocks[symbol] = stock_info
                
            except Exception as e:
                logger.warning(f"解析股票資料失敗 {item}: {e}")
                continue
        
        return stocks
    
    async def get_stock_quote(self, symbol: str) -> Optional[TWStockInfo]:
        """獲取單一股票報價"""
        try:
            # 確保符號格式正確（4位數字）
            symbol = symbol.replace('.TW', '').replace('.TWO', '')
            if not symbol.isdigit() or len(symbol) != 4:
                logger.error(f"不正確的台股代號格式: {symbol}")
                return None
            
            # 獲取所有股票資料
            all_stocks = await self._fetch_all_stocks_data()
            
            if symbol in all_stocks:
                return all_stocks[symbol]
            else:
                logger.warning(f"找不到股票代號: {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"獲取股票 {symbol} 報價失敗: {e}")
            return None
    
    async def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, Optional[TWStockInfo]]:
        """批量獲取多個股票報價"""
        try:
            # 獲取所有股票資料
            all_stocks = await self._fetch_all_stocks_data()
            
            results = {}
            for symbol in symbols:
                # 清理符號格式
                clean_symbol = symbol.replace('.TW', '').replace('.TWO', '')
                if clean_symbol in all_stocks:
                    results[symbol] = all_stocks[clean_symbol]
                else:
                    results[symbol] = None
            
            return results
            
        except Exception as e:
            logger.error(f"批量獲取股票報價失敗: {e}")
            return {symbol: None for symbol in symbols}
    
    async def search_stock(self, keyword: str) -> List[TWStockInfo]:
        """搜尋股票（依名稱或代號）"""
        try:
            all_stocks = await self._fetch_all_stocks_data()
            
            results = []
            keyword = keyword.upper().strip()
            
            for stock in all_stocks.values():
                if (keyword in stock.symbol or 
                    keyword in stock.name or 
                    stock.symbol == keyword):
                    results.append(stock)
            
            return sorted(results, key=lambda x: x.symbol)
            
        except Exception as e:
            logger.error(f"搜尋股票失敗: {e}")
            return []
    
    async def get_market_summary(self) -> Dict[str, any]:
        """獲取市場摘要資訊"""
        try:
            all_stocks = await self._fetch_all_stocks_data()
            
            if not all_stocks:
                return {}
            
            # 計算市場統計
            total_stocks = len(all_stocks)
            rising_stocks = sum(1 for stock in all_stocks.values() 
                              if stock.change and stock.change > 0)
            falling_stocks = sum(1 for stock in all_stocks.values() 
                               if stock.change and stock.change < 0)
            unchanged_stocks = total_stocks - rising_stocks - falling_stocks
            
            total_volume = sum(stock.volume or 0 for stock in all_stocks.values())
            total_turnover = sum(stock.turnover or 0 for stock in all_stocks.values())
            
            return {
                'total_stocks': total_stocks,
                'rising_stocks': rising_stocks,
                'falling_stocks': falling_stocks,
                'unchanged_stocks': unchanged_stocks,
                'total_volume': total_volume,
                'total_turnover': total_turnover,
                'update_time': datetime.now().isoformat(),
                'data_source': 'TWSE'
            }
            
        except Exception as e:
            logger.error(f"獲取市場摘要失敗: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """健康檢查"""
        try:
            url = f"{self.base_url}/exchangeReport/STOCK_DAY_ALL"
            
            async with self.session.get(url) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"TWSE API 健康檢查失敗: {e}")
            return False

# 使用範例
async def main():
    """使用範例"""
    async with TWStockExchangeService() as twse:
        # 測試台積電
        tsmc = await twse.get_stock_quote("2330")
        if tsmc:
            print(f"台積電 (2330): NT${tsmc.current_price} ({tsmc.change:+.2f})")
        
        # 批量查詢
        symbols = ["2330", "2317", "1301", "2454"]
        quotes = await twse.get_multiple_quotes(symbols)
        for symbol, quote in quotes.items():
            if quote:
                print(f"{quote.name} ({symbol}): NT${quote.current_price}")
        
        # 市場摘要
        summary = await twse.get_market_summary()
        print(f"市場摘要: {summary}")

if __name__ == "__main__":
    asyncio.run(main())