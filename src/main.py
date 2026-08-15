"""
財務分析與企業評價系統 - 主要應用程式入口
Financial Analysis & Valuation System - Main Application
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import logging
import time
import uvicorn

from src.core.config import get_settings
from src.core.database import engine, create_tables
from src.core.logging import setup_logging
from src.api.routes import api_router
from src.core.exceptions import FinancialAnalysisException


# 設定日誌
setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    # 啟動時執行
    logger.info("Financial Analysis System starting up...")
    
    # 創建資料庫表格
    await create_tables()
    logger.info("Database tables created/verified")
    
    yield
    
    # 關閉時執行
    logger.info("Financial Analysis System shutting down...")


# 創建 FastAPI 應用實例
app = FastAPI(
    title="財務分析與企業評價系統",
    description="""
    基於 IFRS 13 公允價值衡量原則的企業級財務分析系統
    
    ## 主要功能
    
    * **財務報表分析** - 完整的三大報表分析
    * **財務比率計算** - 流動性、獲利能力、效率比率
    * **企業評價** - DCF、DDM、相對評價法
    * **同業比較** - 產業基準分析
    * **風險評估** - 多維度風險指標
    """,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan
)

# CORS 中介軟體
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# 信任主機中介軟體
if settings.ALLOWED_HOSTS:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """添加請求處理時間標頭"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time, 4))
    return response


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """請求日誌中介軟體"""
    start_time = time.time()
    
    # 記錄請求
    logger.info(
        f"Request started",
        extra={
            "method": request.method,
            "url": str(request.url),
            "user_agent": request.headers.get("user-agent", ""),
            "client_ip": request.client.host if request.client else ""
        }
    )
    
    response = await call_next(request)
    
    # 記錄回應
    process_time = time.time() - start_time
    logger.info(
        f"Request completed",
        extra={
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "process_time": round(process_time, 4)
        }
    )
    
    return response


# 全域異常處理器
@app.exception_handler(FinancialAnalysisException)
async def financial_analysis_exception_handler(request: Request, exc: FinancialAnalysisException):
    """財務分析系統自定義異常處理"""
    logger.error(
        f"Financial Analysis Exception: {exc.message}",
        extra={
            "error_code": exc.error_code,
            "url": str(request.url),
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "type": "FinancialAnalysisError"
            },
            "data": None,
            "meta": {
                "timestamp": time.time(),
                "path": str(request.url.path)
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """一般異常處理器"""
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "url": str(request.url),
            "method": request.method,
            "exception_type": type(exc).__name__
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred" if not settings.DEBUG else str(exc),
                "type": "InternalError"
            },
            "data": None,
            "meta": {
                "timestamp": time.time(),
                "path": str(request.url.path)
            }
        }
    )


# 健康檢查端點
@app.get("/health")
async def health_check():
    """系統健康檢查"""
    return {
        "status": "healthy",
        "service": "financial-analysis-api",
        "version": settings.APP_VERSION,
        "timestamp": time.time()
    }


@app.get("/")
async def root():
    """根路徑"""
    return {
        "message": "財務分析與企業評價系統 API",
        "version": settings.APP_VERSION,
        "docs": "/docs" if settings.DEBUG else "Contact admin for API documentation",
        "health": "/health"
    }


# 註冊靜態文件服務
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# 註冊 API 路由
app.include_router(api_router, prefix=f"/api/{settings.API_VERSION}")

# 開發模式啟動
if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )