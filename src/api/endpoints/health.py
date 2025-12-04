"""
系統健康檢查 API 端點
System Health Check API Endpoints
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any

from src.core.database import health_check
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/")
async def health_status() -> Dict[str, Any]:
    """基本健康檢查"""
    return {
        "status": "healthy",
        "service": "financial-analysis-api",
        "version": "0.1.0"
    }


@router.get("/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """詳細健康檢查"""
    
    # 檢查資料庫連線
    db_connected = await health_check.check_connection()
    
    # 檢查必要表格
    tables_exist = await health_check.check_tables_exist()
    
    # 取得資料庫資訊
    db_info = await health_check.get_database_info()
    
    overall_status = "healthy" if (db_connected and tables_exist) else "unhealthy"
    
    return {
        "status": overall_status,
        "checks": {
            "database_connection": {
                "status": "pass" if db_connected else "fail",
                "message": "Database connection successful" if db_connected else "Database connection failed"
            },
            "required_tables": {
                "status": "pass" if tables_exist else "fail", 
                "message": "All required tables exist" if tables_exist else "Some required tables missing"
            }
        },
        "info": {
            "service": "financial-analysis-api",
            "version": "0.1.0",
            "database": db_info
        }
    }