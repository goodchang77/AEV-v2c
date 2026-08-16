"""
技術指標 API 端點
Technical Indicators API Endpoints
"""

from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.schemas.responses import StandardResponse
from src.services.technical_indicators import compute_all

router = APIRouter()


class IndicatorsRequest(BaseModel):
    """技術指標計算請求（顯式提供收盤價序列）"""

    prices: List[float] = Field(..., min_length=14, description="收盤價序列（由舊到新）")
    sma_period: int = Field(20, ge=2, le=250)
    rsi_period: int = Field(14, ge=2, le=100)
    macd_fast: int = Field(12, ge=2, le=100)
    macd_slow: int = Field(26, ge=3, le=250)
    macd_signal: int = Field(9, ge=2, le=100)


@router.post("/calculate", response_model=StandardResponse)
def calculate_indicators(request: IndicatorsRequest):
    """計算 SMA/EMA/RSI/MACD 技術指標"""
    if request.macd_slow <= request.macd_fast:
        raise HTTPException(status_code=422, detail="macd_slow 必須大於 macd_fast")

    result = compute_all(
        request.prices,
        sma_period=request.sma_period,
        rsi_period=request.rsi_period,
        macd_fast=request.macd_fast,
        macd_slow=request.macd_slow,
        macd_signal=request.macd_signal,
    )

    return StandardResponse(
        success=True,
        data=result,
        meta={"data_points": len(request.prices)},
    )
