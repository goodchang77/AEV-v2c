"""
TWSE 備用資料源
Backup TWSE Data Source with Alternative Endpoints
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import json
import re

from src.core.logging import get_logger
from src.schemas.market_data import StockPrice, HistoricalPrice

logger = get_logger("twse_backup")


class TWSEBackupSource:
    """TWSE備用資料源 - 使用多個端點確保可用性"""
    
    def __init__(self, cache_manager=None):
        self.cache_manager = cache_manager
        self.session = None
        
        # 多個TWSE API端點
        self.endpoints = {
            "realtime_1": "https://mis.twse.com.tw/stock/api/getStockInfo.jsp",
            "realtime_2": "https://mis.twse.com.tw/stock/api/getStockInfo.jsp", 
            "realtime_3": "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX",
            "historical": "https://www.twse.com.tw/exchangeReport/STOCK_DAY",
            # 新增其他可能的端點
            "yahoo_tw": "https://tw.stock.yahoo.com/quote/2330",
            "basic_info": "https://isin.twse.com.tw/isin/C_public.jsp"
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Accept": "application/json, text/html, application/xhtml+xml, application/xml;q=0.9, image/webp, */*;q=0.8",
                "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "DNT": "1"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_stock_info_method1(self, symbol: str) -> Optional[Dict]:
        """方法1: 使用標準API"""
        try:
            url = self.endpoints["realtime_1"] 
            params = {
                "ex_ch": f"tse_{symbol}.tw",
                "json": "1",
                "delay": "0"
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                        if data.get("rtcode") == "0000" and data.get("msgArray"):
                            return data["msgArray"][0]
                    except:
                        # 如果JSON解析失敗，嘗試解析HTML
                        text = await response.text()
                        logger.warning(f"API回傳HTML而非JSON，可能被重定向")
                        return None
            
            return None
            
        except Exception as e:
            logger.error(f"方法1取得股價失敗 {symbol}: {e}")
            return None
    
    async def get_stock_info_method2(self, symbol: str) -> Optional[Dict]:
        """方法2: 使用盤後資訊"""
        try:
            url = self.endpoints["realtime_2"]
            params = {
                "response": "json",
                "date": datetime.now().strftime("%Y%m%d")
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # 在盤後資訊中查找特定股票
                    if data.get("stat") == "OK":
                        for item in data.get("data5", []):  # data5包含個股資訊
                            if len(item) > 0 and item[0] == symbol:
                                return {
                                    "c": symbol,  # 代碼
                                    "z": item[2],  # 收盤價
                                    "o": item[5],  # 開盤價
                                    "h": item[6],  # 最高價
                                    "l": item[7],  # 最低價
                                    "y": item[1],  # 前收價
                                    "v": item[3]   # 成交量
                                }
            
            return None
            
        except Exception as e:
            logger.error(f"方法2取得股價失敗 {symbol}: {e}")
            return None
    
    async def get_stock_info_method3(self, symbol: str) -> Optional[Dict]:
        """方法3: 從歷史資料取得最新價格"""
        try:
            url = self.endpoints["historical"]
            params = {
                "response": "json",
                "date": datetime.now().strftime("%Y%m%d"),
                "stockNo": symbol
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("stat") == "OK" and data.get("data"):
                        # 取最新一筆資料
                        latest = data["data"][-1]
                        if len(latest) >= 9:
                            return {
                                "c": symbol,
                                "z": latest[6],  # 收盤價
                                "o": latest[3],  # 開盤價
                                "h": latest[4],  # 最高價
                                "l": latest[5],  # 最低價
                                "y": latest[6],  # 暫用收盤價作前收價
                                "v": latest[1]   # 成交股數
                            }
            
            return None
            
        except Exception as e:
            logger.error(f"方法3取得股價失敗 {symbol}: {e}")
            return None
    
    async def get_real_time_quote(self, symbol: str) -> Optional[StockPrice]:
        """取得即時報價 - 多方法容錯"""
        try:
            # 快取檢查
            cache_key = f"twse_backup_quote:{symbol}"
            if self.cache_manager:
                cached = await self.cache_manager.get(cache_key)
                if cached:
                    logger.info(f"從快取取得 {symbol} 報價")
                    return StockPrice(**cached)
            
            # 清理股票代碼
            if symbol.endswith('.TW'):
                symbol = symbol[:-3]
            
            # 嘗試多種方法
            methods = [
                self.get_stock_info_method1,
                self.get_stock_info_method2,
                self.get_stock_info_method3
            ]
            
            stock_data = None
            method_used = None
            
            for i, method in enumerate(methods, 1):
                try:
                    stock_data = await method(symbol)
                    if stock_data:
                        method_used = f"方法{i}"
                        break
                except Exception as e:
                    logger.warning(f"方法{i}失敗: {e}")
                    continue
            
            if not stock_data:
                logger.error(f"所有方法都無法取得 {symbol} 資料")
                return None
            
            # 建構StockPrice物件
            def safe_decimal(value, default="0"):
                try:
                    if value is None:
                        return Decimal(default)
                    # 移除逗號和其他格式字符
                    clean_value = str(value).replace(",", "").replace("--", "0")
                    return Decimal(clean_value) if clean_value else Decimal(default)
                except:
                    return Decimal(default)
            
            def safe_int(value, default=0):
                try:
                    if value is None:
                        return default
                    clean_value = str(value).replace(",", "")
                    return int(float(clean_value))
                except:
                    return default
            
            quote = StockPrice(
                symbol=symbol,
                current_price=safe_decimal(stock_data.get("z")),
                open_price=safe_decimal(stock_data.get("o")),
                high_price=safe_decimal(stock_data.get("h")),
                low_price=safe_decimal(stock_data.get("l")),
                previous_close=safe_decimal(stock_data.get("y")),
                volume=safe_int(stock_data.get("v")),
                timestamp=datetime.now(),
                currency="TWD"
            )
            
            # 驗證資料合理性
            if quote.current_price <= 0:
                logger.warning(f"{symbol} 價格資料異常: {quote.current_price}")
                return None
            
            # 快取資料
            if self.cache_manager:
                await self.cache_manager.set(
                    cache_key,
                    quote.dict(),
                    expire=60  # 1分鐘快取
                )
            
            logger.info(f"成功使用{method_used}取得 {symbol} 報價: ${quote.current_price}")
            return quote
            
        except Exception as e:
            logger.error(f"TWSE備用資料源取得報價失敗 {symbol}: {e}")
            return None
    
    async def get_historical_data(self, symbol: str, days: int = 30) -> List[HistoricalPrice]:
        """取得歷史資料"""
        try:
            if symbol.endswith('.TW'):
                symbol = symbol[:-3]
            
            # 當月歷史資料
            url = self.endpoints["historical"]
            params = {
                "response": "json",
                "date": datetime.now().strftime("%Y%m%d"),
                "stockNo": symbol
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("stat") == "OK":
                        historical_data = []
                        
                        for row in data.get("data", [])[:days]:  # 限制筆數
                            try:
                                # 解析民國年日期
                                date_str = row[0].replace("/", "-")
                                date_parts = date_str.split("-")
                                year = int(date_parts[0]) + 1911  # 民國年轉西元年
                                month = int(date_parts[1])
                                day = int(date_parts[2])
                                
                                hist_price = HistoricalPrice(
                                    symbol=symbol,
                                    date=datetime(year, month, day),
                                    open_price=Decimal(str(row[3]).replace(",", "")),
                                    high_price=Decimal(str(row[4]).replace(",", "")),
                                    low_price=Decimal(str(row[5]).replace(",", "")),
                                    close_price=Decimal(str(row[6]).replace(",", "")),
                                    volume=int(str(row[1]).replace(",", ""))
                                )
                                historical_data.append(hist_price)
                                
                            except (IndexError, ValueError, TypeError) as e:
                                logger.warning(f"解析歷史資料錯誤: {e}, row: {row}")
                                continue
                        
                        logger.info(f"TWSE備用取得 {symbol} 歷史資料 {len(historical_data)} 筆")
                        return historical_data
                
                return []
                
        except Exception as e:
            logger.error(f"TWSE備用取得歷史資料失敗 {symbol}: {e}")
            return []
    
    async def validate_connection(self) -> bool:
        """驗證連線"""
        try:
            # 嘗試取得台積電資料測試連線
            quote = await self.get_real_time_quote("2330")
            return quote is not None and quote.current_price > 0
        except Exception:
            return False