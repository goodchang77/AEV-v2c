"""
台股模擬資料源
Taiwan Stock Mock Data Source

當 TWSE API 無法連線時的備用方案
提供常見台股的模擬報價資料
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from decimal import Decimal

from src.schemas.market_data import StockPrice, HistoricalPrice
from src.core.logging import get_logger

logger = get_logger("taiwan_mock")


class TaiwanMockDataSource:
    """台股模擬資料源 - 提供常見台股的合理模擬價格"""
    
    def __init__(self, cache_manager=None):
        self.cache_manager = cache_manager
        self.name = "TaiwanMock"
        
        # 常見台股的基準價格和合理波動範圍
        self.stock_data = {
            "2330": {"base_price": 580.0, "name": "台積電", "range": 0.03},  # 台積電
            "2317": {"base_price": 127.0, "name": "鴻海", "range": 0.025},   # 鴻海
            "2454": {"base_price": 1050.0, "name": "聯發科", "range": 0.04}, # 聯發科
            "1301": {"base_price": 85.5, "name": "台塑", "range": 0.02},     # 台塑
            "2412": {"base_price": 65.2, "name": "中華電", "range": 0.015},  # 中華電
            "1303": {"base_price": 62.8, "name": "南亞", "range": 0.025},    # 南亞
            "2002": {"base_price": 59.1, "name": "中鋼", "range": 0.03},     # 中鋼
            "2881": {"base_price": 24.35, "name": "富邦金", "range": 0.02},  # 富邦金
            "2882": {"base_price": 22.15, "name": "國泰金", "range": 0.02},  # 國泰金
            "2884": {"base_price": 18.95, "name": "玉山金", "range": 0.025}, # 玉山金
            "1216": {"base_price": 160.5, "name": "統一", "range": 0.02},    # 統一
            "3008": {"base_price": 285.0, "name": "大立光", "range": 0.05},  # 大立光
            "2603": {"base_price": 42.6, "name": "長榮", "range": 0.06},     # 長榮
            "2609": {"base_price": 78.5, "name": "陽明", "range": 0.07},     # 陽明
            "3711": {"base_price": 415.0, "name": "日月光投控", "range": 0.03} # 日月光
        }
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def _generate_realistic_price(self, base_price: float, volatility: float) -> float:
        """生成合理的股價波動"""
        # 使用正態分布生成合理的價格波動
        change_percent = random.gauss(0, volatility)
        # 限制最大波動範圍
        change_percent = max(min(change_percent, volatility * 3), -volatility * 3)
        
        new_price = base_price * (1 + change_percent)
        return round(new_price, 2)
    
    def _generate_volume(self, base_volume: int = 10000000) -> int:
        """生成合理的成交量"""
        volume_multiplier = random.uniform(0.3, 2.5)
        return int(base_volume * volume_multiplier)
    
    async def get_real_time_quote(self, symbol: str) -> Optional[StockPrice]:
        """取得模擬即時報價"""
        try:
            # 移除 .TW 後綴
            if symbol.endswith('.TW'):
                symbol = symbol[:-3]
            
            # 檢查是否為支援的股票
            if symbol not in self.stock_data:
                logger.warning(f"模擬資料源不支援股票代碼: {symbol}")
                return None
            
            stock_info = self.stock_data[symbol]
            base_price = stock_info["base_price"]
            volatility = stock_info["range"]
            name = stock_info["name"]
            
            # 生成當日價格範圍
            open_price = self._generate_realistic_price(base_price, volatility * 0.5)
            current_price = self._generate_realistic_price(open_price, volatility)
            high_price = max(open_price, current_price) * random.uniform(1.0, 1.02)
            low_price = min(open_price, current_price) * random.uniform(0.98, 1.0)
            previous_close = self._generate_realistic_price(base_price, volatility * 0.3)
            volume = self._generate_volume()
            
            # 模擬輕微延遲
            await asyncio.sleep(0.1)
            
            quote = StockPrice(
                symbol=symbol,
                current_price=str(current_price),
                open_price=str(round(open_price, 2)),
                high_price=str(round(high_price, 2)),
                low_price=str(round(low_price, 2)),
                previous_close=str(round(previous_close, 2)),
                volume=volume,
                timestamp=datetime.now(),
                currency="TWD"
            )
            
            logger.info(f"生成 {name}({symbol}) 模擬報價: ${current_price}")
            return quote
            
        except Exception as e:
            logger.error(f"生成模擬報價失敗 {symbol}: {e}")
            return None
    
    async def get_historical_data(self, symbol: str, days: int = 30) -> List[HistoricalPrice]:
        """取得模擬歷史資料"""
        try:
            if symbol.endswith('.TW'):
                symbol = symbol[:-3]
            
            if symbol not in self.stock_data:
                return []
            
            stock_info = self.stock_data[symbol]
            base_price = stock_info["base_price"]
            volatility = stock_info["range"]
            
            historical_data = []
            current_price = base_price
            
            # 生成過去 days 天的歷史資料
            for i in range(days, 0, -1):
                date = datetime.now() - timedelta(days=i)
                
                # 生成當日的開高低收
                open_price = current_price
                close_price = self._generate_realistic_price(open_price, volatility)
                high_price = max(open_price, close_price) * random.uniform(1.0, 1.015)
                low_price = min(open_price, close_price) * random.uniform(0.985, 1.0)
                volume = self._generate_volume(base_volume=8000000)
                
                historical_data.append(HistoricalPrice(
                    date=date.date(),
                    open_price=round(open_price, 2),
                    high_price=round(high_price, 2),
                    low_price=round(low_price, 2),
                    close_price=round(close_price, 2),
                    volume=volume,
                    adj_close=round(close_price, 2)
                ))
                
                current_price = close_price
            
            logger.info(f"生成 {symbol} 模擬歷史資料: {len(historical_data)} 筆")
            return historical_data
            
        except Exception as e:
            logger.error(f"生成模擬歷史資料失敗 {symbol}: {e}")
            return []
    
    async def validate_connection(self) -> bool:
        """驗證模擬資料源連線 (總是成功)"""
        return True