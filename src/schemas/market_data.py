"""
市場資料模型
Market Data Models for Yahoo Finance Integration
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum


class Currency(str, Enum):
    """貨幣類型"""
    TWD = "TWD"  # 台幣
    USD = "USD"  # 美元
    HKD = "HKD"  # 港幣
    JPY = "JPY"  # 日圓


class MarketStatus(str, Enum):
    """市場狀態"""
    OPEN = "OPEN"           # 開盤中
    CLOSED = "CLOSED"       # 收盤
    PRE_MARKET = "PRE_MARKET"   # 盤前
    AFTER_HOURS = "AFTER_HOURS"  # 盤後


class StockPrice(BaseModel):
    """股價資料模型"""
    symbol: str = Field(..., description="股票代碼")
    current_price: Decimal = Field(..., description="當前價格")
    open_price: Decimal = Field(..., description="開盤價")
    high_price: Decimal = Field(..., description="最高價")
    low_price: Decimal = Field(..., description="最低價")
    previous_close: Decimal = Field(..., description="前收盤價")
    volume: int = Field(0, description="成交量")
    market_cap: Optional[int] = Field(None, description="市值")
    timestamp: datetime = Field(..., description="更新時間")
    currency: Currency = Field(Currency.TWD, description="貨幣類型")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("股票代碼不能為空")
        return v.strip()
    
    @validator('current_price', 'open_price', 'high_price', 'low_price', 'previous_close')
    def validate_positive_price(cls, v):
        if v <= 0:
            raise ValueError("價格必須大於0")
        return v
    
    @validator('volume')
    def validate_volume(cls, v):
        if v < 0:
            raise ValueError("成交量不能為負數")
        return v
    
    @property
    def price_change(self) -> Decimal:
        """價格變化"""
        return self.current_price - self.previous_close
    
    @property
    def price_change_percent(self) -> Decimal:
        """價格變化百分比"""
        if self.previous_close == 0:
            return Decimal('0')
        return (self.price_change / self.previous_close) * 100


class HistoricalPrice(BaseModel):
    """歷史股價資料模型"""
    symbol: str = Field(..., description="股票代碼")
    date: datetime = Field(..., description="日期")
    open_price: Decimal = Field(..., description="開盤價")
    high_price: Decimal = Field(..., description="最高價")
    low_price: Decimal = Field(..., description="最低價")
    close_price: Decimal = Field(..., description="收盤價")
    adjusted_close: Optional[Decimal] = Field(None, description="調整後收盤價")
    volume: int = Field(0, description="成交量")
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


class MarketData(BaseModel):
    """綜合市場資料模型"""
    market_name: str = Field(..., description="市場名稱")
    market_status: MarketStatus = Field(..., description="市場狀態")
    indices: List[Dict[str, Any]] = Field(default_factory=list, description="指數資料")
    active_stocks: List[StockPrice] = Field(default_factory=list, description="活躍股票")
    market_summary: Dict[str, Any] = Field(default_factory=dict, description="市場摘要")
    last_updated: datetime = Field(..., description="最後更新時間")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class QuoteRequest(BaseModel):
    """即時報價請求模型"""
    symbol: str = Field(..., pattern=r"^[A-Z0-9]{1,10}(\.[A-Z]{1,3})?$", description="股票代碼")
    include_extended_hours: bool = Field(False, description="是否包含延長交易時間")
    
    @validator('symbol')
    def normalize_symbol(cls, v):
        # 台灣股票代碼標準化
        if v.isdigit() and len(v) == 4:
            return f"{v}.TW"
        return v.upper()


class HistoricalDataRequest(BaseModel):
    """歷史資料請求模型"""
    symbol: str = Field(..., description="股票代碼")
    period: str = Field("1y", pattern=r"^(1d|5d|1mo|3mo|6mo|1y|2y|5y|10y|ytd|max)$", description="時間區間")
    interval: str = Field("1d", pattern=r"^(1m|2m|5m|15m|30m|60m|90m|1h|1d|5d|1wk|1mo|3mo)$", description="資料間隔")
    start_date: Optional[datetime] = Field(None, description="開始日期")
    end_date: Optional[datetime] = Field(None, description="結束日期")
    
    @validator('symbol')
    def normalize_symbol(cls, v):
        if v.isdigit() and len(v) == 4:
            return f"{v}.TW"
        return v.upper()
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        if v and values.get('start_date'):
            if v <= values['start_date']:
                raise ValueError("結束日期必須晚於開始日期")
        return v


class MarketSyncRequest(BaseModel):
    """市場資料同步請求模型"""
    company_ids: List[str] = Field(..., min_items=1, max_items=100, description="公司代碼列表")
    sync_type: str = Field("realtime", pattern=r"^(realtime|historical|both)$", description="同步類型")
    force_update: bool = Field(False, description="強制更新")
    notification_url: Optional[str] = Field(None, description="完成通知URL")
    
    @validator('company_ids')
    def validate_company_ids(cls, v):
        for company_id in v:
            if not company_id.isdigit() or len(company_id) != 4:
                raise ValueError(f"無效的公司代碼: {company_id}")
        return v


class MarketSyncResponse(BaseModel):
    """市場資料同步響應模型"""
    sync_id: str = Field(..., description="同步任務ID")
    status: str = Field(..., description="同步狀態")
    total_companies: int = Field(..., description="總公司數")
    success_count: int = Field(0, description="成功數量")
    failed_count: int = Field(0, description="失敗數量")
    errors: List[str] = Field(default_factory=list, description="錯誤訊息")
    start_time: datetime = Field(..., description="開始時間")
    end_time: Optional[datetime] = Field(None, description="結束時間")
    estimated_completion: Optional[datetime] = Field(None, description="預計完成時間")
    
    @property
    def completion_rate(self) -> float:
        """完成率"""
        if self.total_companies == 0:
            return 0.0
        return (self.success_count + self.failed_count) / self.total_companies * 100
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TechnicalIndicators(BaseModel):
    """技術指標模型"""
    symbol: str = Field(..., description="股票代碼")
    calculation_date: datetime = Field(..., description="計算日期")
    
    # 移動平均
    ma_5: Optional[Decimal] = Field(None, description="5日移動平均")
    ma_10: Optional[Decimal] = Field(None, description="10日移動平均")
    ma_20: Optional[Decimal] = Field(None, description="20日移動平均")
    ma_50: Optional[Decimal] = Field(None, description="50日移動平均")
    ma_200: Optional[Decimal] = Field(None, description="200日移動平均")
    
    # RSI指標
    rsi_14: Optional[Decimal] = Field(None, ge=0, le=100, description="14日RSI")
    
    # MACD指標
    macd_line: Optional[Decimal] = Field(None, description="MACD線")
    macd_signal: Optional[Decimal] = Field(None, description="訊號線")
    macd_histogram: Optional[Decimal] = Field(None, description="MACD柱狀圖")
    
    # 布林通道
    bollinger_upper: Optional[Decimal] = Field(None, description="布林通道上軌")
    bollinger_middle: Optional[Decimal] = Field(None, description="布林通道中軌")
    bollinger_lower: Optional[Decimal] = Field(None, description="布林通道下軌")
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


class MarketAlert(BaseModel):
    """市場警示模型"""
    alert_id: str = Field(..., description="警示ID")
    symbol: str = Field(..., description="股票代碼")
    alert_type: str = Field(..., description="警示類型")
    condition: str = Field(..., description="觸發條件")
    current_value: Decimal = Field(..., description="當前值")
    threshold_value: Decimal = Field(..., description="閾值")
    severity: str = Field(..., pattern=r"^(LOW|MEDIUM|HIGH|CRITICAL)$", description="嚴重程度")
    created_at: datetime = Field(..., description="創建時間")
    triggered_at: Optional[datetime] = Field(None, description="觸發時間")
    acknowledged: bool = Field(False, description="已確認")
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }