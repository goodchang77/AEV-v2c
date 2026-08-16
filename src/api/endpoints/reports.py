"""
報告 API 端點
Reports API Endpoints
=====================

- POST /reports/generate      生成財務分析報告（markdown / pdf）
- POST /reports/export-excel  匯出財務比率為 Excel
"""

import base64
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.schemas.responses import StandardResponse
from src.services.report_service import ReportService

router = APIRouter()


class ReportRequest(BaseModel):
    company_id: str = Field(..., pattern=r"^\d{4}$")
    report_type: str = Field("comprehensive", description="comprehensive / summary")
    format: str = Field("markdown", description="markdown / pdf")


class ExcelExportRequest(BaseModel):
    company_id: str = Field(..., pattern=r"^\d{4}$")


@router.post("/generate", response_model=StandardResponse)
async def generate_report(request: ReportRequest):
    """生成財務分析報告"""
    service = ReportService()
    result = await service.generate_financial_report(
        request.company_id, request.report_type, request.format
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result["message"])

    if result["format"] == "pdf":
        return StandardResponse(
            success=True,
            data={
                "format": "pdf",
                "filename": result["filename"],
                "content_base64": base64.b64encode(result["content_bytes"]).decode(),
            },
            meta={"company_id": request.company_id},
        )

    return StandardResponse(
        success=True,
        data={"format": "markdown", "content": result["content"]},
        meta={"company_id": request.company_id},
    )


@router.post("/export-excel", response_model=StandardResponse)
async def export_excel(request: ExcelExportRequest):
    """匯出公司財務比率為 Excel"""
    from src.services.data_service import CompanyDataService, FinancialDataService

    company = await CompanyDataService().get_company_basic_info(request.company_id)
    if not company:
        raise HTTPException(status_code=404, detail=f"找不到公司 {request.company_id}")

    ratios = await FinancialDataService().get_financial_ratios(request.company_id)
    if not ratios:
        raise HTTPException(status_code=404, detail=f"找不到公司 {request.company_id} 的財務比率")

    service = ReportService()
    result = await service.export_to_excel(
        {"ratios": ratios}, f"financial_data_{request.company_id}.xlsx"
    )

    return StandardResponse(
        success=True,
        data={
            "format": "xlsx",
            "filename": result["filename"],
            "content_base64": base64.b64encode(result["content_bytes"]).decode(),
        },
        meta={"company_id": request.company_id},
    )
