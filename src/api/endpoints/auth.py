"""
認證 API 端點
Authentication API Endpoints
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def auth_status():
    """認證狀態檢查"""
    return {"status": "auth_service_available", "message": "認證服務運行中"}