"""
財務比率 API 端點  
Financial Ratios API Endpoints
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def list_ratios():
    """取得財務比率列表"""
    return {"status": "ratios_service_available", "message": "財務比率服務運行中"}

@router.get("/{company_id}")
async def get_company_ratios(company_id: str):
    """取得公司財務比率"""
    return {"company_id": company_id, "status": "ratios_data_available"}