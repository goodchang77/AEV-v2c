"""
API 路由定義
API Routes Definition
"""

from fastapi import APIRouter
from src.api.endpoints import companies, financials, ratios, auth, health, market_data, market_data_v2, document_upload, analysis, agent, valuation

# 主要 API 路由器
api_router = APIRouter()

# 註冊各模組路由
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["認證"],
)

api_router.include_router(
    companies.router,
    prefix="/companies",
    tags=["公司資料"],
)

api_router.include_router(
    financials.router,
    prefix="/financials",
    tags=["財務報表"],
)

api_router.include_router(
    ratios.router,
    prefix="/ratios",
    tags=["財務比率"],
)

api_router.include_router(
    health.router,
    prefix="/health",
    tags=["系統監控"],
)

api_router.include_router(
    market_data.router,
    prefix="/market",
    tags=["市場資料"],
)

api_router.include_router(
    market_data_v2.router,
    prefix="/market",
    tags=["增強版市場資料"],
)

api_router.include_router(
    document_upload.router,
    prefix="/documents",
    tags=["文件上傳與處理"],
)

api_router.include_router(
    agent.router,
    prefix="/agent",
    tags=["AI Agent"],
)

api_router.include_router(
    analysis.router,
    prefix="/analysis",
    tags=["分析"],
)

api_router.include_router(
    valuation.router,
    prefix="/valuation",
    tags=["評價模型"],
)