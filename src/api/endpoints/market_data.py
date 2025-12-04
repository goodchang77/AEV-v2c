"""
市場資料 API 端點
Market Data API Endpoints with Yahoo Finance Integration
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, Path
from typing import Optional, List
from datetime import datetime

from src.schemas.market_data import (
    StockPrice, HistoricalPrice, MarketData, QuoteRequest, 
    HistoricalDataRequest, MarketSyncRequest, MarketSyncResponse
)
from src.schemas.responses import BaseResponse
from src.services.yahoo_finance_service import YahooFinanceService, MarketDataSyncService
from src.core.exceptions import ExternalAPIError, ValidationError, create_http_exception
from src.core.logging import get_logger
from src.core.cache import get_cache_manager
# from src.core.database import get_async_db  # 暫時移除未使用的import

router = APIRouter()
logger = get_logger("market_data_api")


async def get_yahoo_service():
    """取得Yahoo Finance服務實例"""
    try:
        cache_manager = await get_cache_manager()
        service = YahooFinanceService(cache_manager=cache_manager)
        return service
    except Exception as e:
        logger.error(f"初始化Yahoo Finance服務失敗: {e}")
        raise HTTPException(status_code=500, detail="市場資料服務暫時不可用")


@router.get("/quote/{symbol}", response_model=BaseResponse[StockPrice])
async def get_real_time_quote(
    symbol: str = Path(..., pattern=r"^[A-Za-z0-9]{1,10}$", description="股票代碼"),
    yahoo_service: YahooFinanceService = Depends(get_yahoo_service)
):
    """取得即時股價報價
    
    支援台灣股票代碼（4位數字）和國際股票代碼
    範例：
    - 2330 (台積電)
    - AAPL (蘋果)
    - TSLA (特斯拉)
    """
    try:
        async with yahoo_service:
            quote = await yahoo_service.get_real_time_quote(symbol)
            
            if not quote:
                raise HTTPException(
                    status_code=404, 
                    detail=f"無法取得 {symbol} 的即時報價資料"
                )
            
            logger.info(f"成功取得 {symbol} 即時報價")
            return BaseResponse(
                success=True,
                data=quote,
                message=f"成功取得 {symbol} 即時報價",
                timestamp=datetime.now()
            )
        
    except ExternalAPIError as e:
        logger.error(f"Yahoo Finance API錯誤: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"取得即時報價失敗 {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"取得 {symbol} 報價失敗")


@router.get("/quotes/batch")
async def get_batch_quotes(
    symbols: str = Query(..., description="股票代碼列表，以逗號分隔", example="2330,2454,1301"),
    yahoo_service: YahooFinanceService = Depends(get_yahoo_service)
):
    """批量取得多個股票的即時報價"""
    try:
        symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
        if len(symbol_list) > 50:  # 限制批量查詢數量
            raise HTTPException(status_code=400, detail="單次查詢股票數量不能超過50個")
        
        results = {}
        errors = []
        
        async with yahoo_service:
            for symbol in symbol_list:
                try:
                    quote = await yahoo_service.get_real_time_quote(symbol)
                    if quote:
                        results[symbol] = quote
                    else:
                        errors.append(f"{symbol}: 無法取得報價")
                except Exception as e:
                    errors.append(f"{symbol}: {str(e)}")
                    logger.warning(f"取得 {symbol} 報價失敗: {e}")
        
        response_data = {
            "quotes": results,
            "success_count": len(results),
            "error_count": len(errors),
            "errors": errors
        }
        
        logger.info(f"批量查詢完成，成功: {len(results)}, 失敗: {len(errors)}")
        return BaseResponse(
            success=len(results) > 0,
            data=response_data,
            message=f"成功取得 {len(results)} 個股票報價",
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量查詢失敗: {e}")
        raise HTTPException(status_code=500, detail="批量查詢服務暫時不可用")


@router.get("/history/{symbol}")
async def get_historical_data(
    symbol: str = Path(..., description="股票代碼"),
    period: str = Query("1y", pattern=r"^(1d|5d|1mo|3mo|6mo|1y|2y|5y|10y|ytd|max)$", 
                       description="時間區間"),
    interval: str = Query("1d", pattern=r"^(1m|2m|5m|15m|30m|60m|90m|1h|1d|5d|1wk|1mo|3mo)$", 
                         description="資料間隔"),
    yahoo_service: YahooFinanceService = Depends(get_yahoo_service)
):
    """取得歷史股價資料
    
    時間區間選項：
    - 1d, 5d: 天數
    - 1mo, 3mo, 6mo: 月數  
    - 1y, 2y, 5y, 10y: 年數
    - ytd: 年初至今
    - max: 所有可用資料
    
    資料間隔選項：
    - 分鐘級: 1m, 2m, 5m, 15m, 30m, 60m, 90m
    - 小時級: 1h
    - 日週月: 1d, 5d, 1wk, 1mo, 3mo
    """
    try:
        async with yahoo_service:
            historical_data = await yahoo_service.get_historical_data(
                symbol=symbol, 
                period=period, 
                interval=interval
            )
            
            if not historical_data:
                raise HTTPException(
                    status_code=404, 
                    detail=f"無法取得 {symbol} 的歷史資料"
                )
            
            response_data = {
                "symbol": symbol,
                "period": period,
                "interval": interval,
                "data_points": len(historical_data),
                "data": historical_data
            }
            
            logger.info(f"成功取得 {symbol} 歷史資料，共 {len(historical_data)} 筆")
            return BaseResponse(
                success=True,
                data=response_data,
                message=f"成功取得 {symbol} 歷史資料",
                timestamp=datetime.now()
            )
        
    except ExternalAPIError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"取得歷史資料失敗 {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"取得 {symbol} 歷史資料失敗")


@router.get("/market/summary")
async def get_market_summary(
    yahoo_service: YahooFinanceService = Depends(get_yahoo_service)
):
    """取得市場摘要資料
    
    包含台灣主要指數：
    - ^TWII: 台灣加權指數
    - ^TW50: 台灣50指數
    """
    try:
        async with yahoo_service:
            market_data = await yahoo_service.get_market_summary()
            
            if not market_data:
                raise HTTPException(
                    status_code=503, 
                    detail="目前無法取得市場摘要資料"
                )
            
            logger.info("成功取得市場摘要資料")
            return BaseResponse(
                success=True,
                data={
                    "market_summary": market_data,
                    "indices_count": len(market_data),
                    "last_updated": datetime.now().isoformat()
                },
                message="成功取得市場摘要",
                timestamp=datetime.now()
            )
        
    except ExternalAPIError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"取得市場摘要失敗: {e}")
        raise HTTPException(status_code=500, detail="市場摘要服務暫時不可用")


@router.post("/sync/stocks")
async def sync_stock_data(
    request: MarketSyncRequest,
    background_tasks: BackgroundTasks,
    yahoo_service: YahooFinanceService = Depends(get_yahoo_service),
    # db = Depends(get_async_db)  # 暫時移除
):
    """同步股票市場資料
    
    支援批量同步多個股票的即時或歷史資料到資料庫
    """
    try:
        # 驗證公司代碼
        invalid_symbols = []
        for company_id in request.company_ids:
            if not company_id.isdigit() or len(company_id) != 4:
                invalid_symbols.append(company_id)
        
        if invalid_symbols:
            raise ValidationError(
                f"無效的公司代碼: {', '.join(invalid_symbols)}", 
                field="company_ids", 
                value=invalid_symbols
            )
        
        # 初始化同步服務
        sync_service = MarketDataSyncService(yahoo_service, None)  # 暫時不使用資料庫
        sync_id = f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 建立同步響應
        sync_response = MarketSyncResponse(
            sync_id=sync_id,
            status="STARTED",
            total_companies=len(request.company_ids),
            start_time=datetime.now()
        )
        
        # 背景任務同步資料
        if request.sync_type in ["realtime", "both"]:
            background_tasks.add_task(
                sync_service.sync_stock_prices,
                request.company_ids
            )
        
        logger.info(f"啟動市場資料同步任務 {sync_id}，共 {len(request.company_ids)} 個股票")
        
        return BaseResponse(
            success=True,
            data=sync_response,
            message=f"市場資料同步已啟動，任務ID: {sync_id}",
            timestamp=datetime.now()
        )
        
    except ValidationError as e:
        raise create_http_exception(e)
    except Exception as e:
        logger.error(f"啟動市場資料同步失敗: {e}")
        raise HTTPException(status_code=500, detail="市場資料同步服務暫時不可用")


@router.get("/health/yahoo-finance")
async def check_yahoo_finance_health(
    yahoo_service: YahooFinanceService = Depends(get_yahoo_service)
):
    """檢查Yahoo Finance API連線健康狀態"""
    try:
        async with yahoo_service:
            is_healthy = await yahoo_service.validate_connection()
            
            health_data = {
                "service": "Yahoo Finance API",
                "status": "healthy" if is_healthy else "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "response_time": None,  # 可以在實際實作中加入響應時間測量
                "last_test": "Connection validation test"
            }
            
            if is_healthy:
                logger.info("Yahoo Finance API連線正常")
                return BaseResponse(
                    success=True,
                    data=health_data,
                    message="Yahoo Finance API連線正常",
                    timestamp=datetime.now()
                )
            else:
                logger.warning("Yahoo Finance API連線異常")
                raise HTTPException(
                    status_code=503, 
                    detail="Yahoo Finance API連線異常"
                )
        
    except Exception as e:
        logger.error(f"Yahoo Finance健康檢查失敗: {e}")
        raise HTTPException(
            status_code=503, 
            detail=f"Yahoo Finance服務檢查失敗: {str(e)}"
        )


@router.get("/supported-markets")
async def get_supported_markets():
    """取得支援的市場列表"""
    supported_markets = {
        "taiwan": {
            "name": "台灣證券交易所",
            "symbol_suffix": ".TW",
            "currency": "TWD",
            "timezone": "Asia/Taipei",
            "trading_hours": {
                "open": "09:00",
                "close": "13:30",
                "lunch_break": "12:00-13:00"
            },
            "supported_intervals": ["1d", "1wk", "1mo"],
            "max_history": "10y"
        },
        "us": {
            "name": "美國股市",
            "symbol_suffix": "",
            "currency": "USD", 
            "timezone": "America/New_York",
            "trading_hours": {
                "open": "09:30",
                "close": "16:00"
            },
            "supported_intervals": ["1m", "2m", "5m", "15m", "30m", "60m", "1d", "1wk", "1mo"],
            "max_history": "max"
        }
    }
    
    return BaseResponse(
        success=True,
        data=supported_markets,
        message="支援的市場列表",
        timestamp=datetime.now()
    )


# 添加到主路由器的標籤和描述
router.tags = ["Market Data"]