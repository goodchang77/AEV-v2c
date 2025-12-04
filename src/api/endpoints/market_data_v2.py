"""
改進版市場資料 API 端點
Enhanced Market Data API with Multiple Sources
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Path
from typing import Optional, List
from datetime import datetime
import os

from src.schemas.market_data import StockPrice, HistoricalPrice
from src.schemas.responses import BaseResponse
from src.services.market_data_sources import MarketDataAggregator, create_market_data_aggregator
from src.core.logging import get_logger
from src.core.cache import get_cache_manager

router = APIRouter()
logger = get_logger("market_data_v2_api")


async def get_market_aggregator() -> MarketDataAggregator:
    """取得市場資料聚合器"""
    try:
        cache_manager = await get_cache_manager()
        
        # 從環境變數取得API Keys
        alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        fugle_key = os.getenv("FUGLE_API_KEY")
        
        aggregator = await create_market_data_aggregator(
            alpha_vantage_key=alpha_vantage_key,
            fugle_key=fugle_key,
            cache_manager=cache_manager
        )
        
        return aggregator
        
    except Exception as e:
        logger.error(f"初始化市場資料聚合器失敗: {e}")
        raise HTTPException(status_code=500, detail="市場資料服務初始化失敗")


@router.get("/v2/quote/{symbol}", response_model=BaseResponse[StockPrice])
async def get_enhanced_quote(
    symbol: str = Path(..., description="股票代碼 (支援 2330, 2330.TW, AAPL 等)"),
    aggregator: MarketDataAggregator = Depends(get_market_aggregator)
):
    """取得增強版即時報價
    
    支援多資料源自動容錯：
    - 台股：優先使用TWSE官方API，備援Fugle API
    - 美股：使用Alpha Vantage API
    - 自動判斷股票市場並選擇最佳資料源
    """
    try:
        quote = await aggregator.get_best_quote(symbol)
        
        if not quote:
            raise HTTPException(
                status_code=404,
                detail=f"無法從任何資料源取得 {symbol} 的報價資料"
            )
        
        logger.info(f"成功取得 {symbol} 增強版報價")
        return BaseResponse(
            success=True,
            data=quote,
            message=f"成功取得 {symbol} 即時報價",
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取得增強版報價失敗 {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"取得 {symbol} 報價失敗")


@router.get("/v2/quotes/batch")
async def get_enhanced_batch_quotes(
    symbols: str = Query(..., description="股票代碼列表，以逗號分隔", example="2330,AAPL,2454"),
    aggregator: MarketDataAggregator = Depends(get_market_aggregator)
):
    """批量取得增強版即時報價
    
    支援混合市場查詢：
    - 可同時查詢台股和美股
    - 每個股票自動選擇最佳資料源
    - 失敗的股票會在errors中回報
    """
    try:
        symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
        if len(symbol_list) > 20:  # 降低批量限制
            raise HTTPException(status_code=400, detail="單次查詢股票數量不能超過20個")
        
        results = {}
        errors = []
        
        # 並發查詢多個股票
        import asyncio
        
        async def get_single_quote(symbol: str):
            try:
                quote = await aggregator.get_best_quote(symbol)
                return symbol, quote, None
            except Exception as e:
                return symbol, None, str(e)
        
        # 並發執行所有查詢
        tasks = [get_single_quote(symbol) for symbol in symbol_list]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for response in responses:
            if isinstance(response, Exception):
                errors.append(f"系統錯誤: {str(response)}")
                continue
                
            symbol, quote, error = response
            if quote:
                results[symbol] = quote
            else:
                errors.append(f"{symbol}: {error}")
        
        response_data = {
            "quotes": results,
            "success_count": len(results),
            "error_count": len(errors),
            "errors": errors,
            "data_sources_used": list(aggregator.data_sources.keys())
        }
        
        logger.info(f"批量增強查詢完成，成功: {len(results)}, 失敗: {len(errors)}")
        return BaseResponse(
            success=len(results) > 0,
            data=response_data,
            message=f"成功取得 {len(results)} 個股票報價",
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量增強查詢失敗: {e}")
        raise HTTPException(status_code=500, detail="批量查詢服務暫時不可用")


@router.get("/v2/history/{symbol}")
async def get_enhanced_historical_data(
    symbol: str = Path(..., description="股票代碼"),
    days: int = Query(30, ge=1, le=365, description="查詢天數"),
    aggregator: MarketDataAggregator = Depends(get_market_aggregator)
):
    """取得增強版歷史資料
    
    支援多資料源容錯：
    - 台股：優先TWSE，備援其他源
    - 美股：Alpha Vantage
    - 資料完整性更高
    """
    try:
        historical_data = await aggregator.get_aggregated_historical_data(symbol, days)
        
        if not historical_data:
            raise HTTPException(
                status_code=404,
                detail=f"無法從任何資料源取得 {symbol} 的歷史資料"
            )
        
        response_data = {
            "symbol": symbol,
            "requested_days": days,
            "actual_data_points": len(historical_data),
            "date_range": {
                "start": min(data.date for data in historical_data).isoformat() if historical_data else None,
                "end": max(data.date for data in historical_data).isoformat() if historical_data else None
            },
            "data": historical_data
        }
        
        logger.info(f"成功取得 {symbol} 增強版歷史資料，共 {len(historical_data)} 筆")
        return BaseResponse(
            success=True,
            data=response_data,
            message=f"成功取得 {symbol} 歷史資料",
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取得增強版歷史資料失敗 {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"取得 {symbol} 歷史資料失敗")


@router.get("/v2/health/sources")
async def check_all_sources_health(
    aggregator: MarketDataAggregator = Depends(get_market_aggregator)
):
    """檢查所有資料源健康狀態"""
    try:
        health_status = await aggregator.health_check()
        
        healthy_sources = sum(1 for status in health_status.values() if status)
        total_sources = len(health_status)
        
        overall_health = "healthy" if healthy_sources > 0 else "unhealthy"
        
        response_data = {
            "overall_status": overall_health,
            "healthy_sources": healthy_sources,
            "total_sources": total_sources,
            "sources_detail": health_status,
            "recommendations": []
        }
        
        # 生成建議
        if healthy_sources == 0:
            response_data["recommendations"].append("所有資料源都無法連接，請檢查網路和API配置")
        elif healthy_sources < total_sources:
            unhealthy = [name for name, status in health_status.items() if not status]
            response_data["recommendations"].append(f"以下資料源異常: {', '.join(unhealthy)}")
        
        if "TWSE" in health_status and not health_status["TWSE"]:
            response_data["recommendations"].append("TWSE官方API異常，台股查詢可能受影響")
        
        logger.info(f"資料源健康檢查完成: {healthy_sources}/{total_sources} 正常")
        
        return BaseResponse(
            success=healthy_sources > 0,
            data=response_data,
            message=f"資料源健康檢查完成，{healthy_sources}/{total_sources} 正常",
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"資料源健康檢查失敗: {e}")
        raise HTTPException(status_code=500, detail="健康檢查服務暫時不可用")


@router.get("/v2/sources/info")
async def get_data_sources_info():
    """取得可用資料源資訊"""
    
    sources_info = {
        "TWSE": {
            "name": "台灣證券交易所",
            "description": "官方免費台股資料",
            "markets": ["台灣股市"],
            "features": ["即時報價", "歷史資料", "完全免費"],
            "rate_limit": "較寬鬆",
            "reliability": "極高"
        },
        "AlphaVantage": {
            "name": "Alpha Vantage",
            "description": "專業國際金融資料",
            "markets": ["美股", "國際股市"],
            "features": ["即時報價", "歷史資料", "技術指標"],
            "rate_limit": "免費版: 5次/分鐘",
            "reliability": "高",
            "requires_api_key": True
        },
        "Fugle": {
            "name": "富果 Fugle",
            "description": "台股專業資料服務",
            "markets": ["台灣股市"],
            "features": ["高頻即時資料", "專業技術分析"],
            "rate_limit": "依方案而定",
            "reliability": "極高",
            "requires_api_key": True
        }
    }
    
    return BaseResponse(
        success=True,
        data={
            "available_sources": sources_info,
            "recommended_configuration": {
                "台股": "TWSE (主要) + Fugle (專業版)",
                "美股": "Alpha Vantage",
                "國際股市": "Alpha Vantage"
            },
            "setup_instructions": {
                "TWSE": "無需設定，直接使用",
                "AlphaVantage": "設定環境變數 ALPHA_VANTAGE_API_KEY",
                "Fugle": "設定環境變數 FUGLE_API_KEY"
            }
        },
        message="資料源資訊",
        timestamp=datetime.now()
    )


# 路由標籤和描述
router.tags = ["Enhanced Market Data"]