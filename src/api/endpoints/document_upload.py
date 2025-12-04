"""
文件上傳與處理 API 端點
Document Upload and Processing API Endpoints
"""

import logging
import tempfile
import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.services.pdf_processor import FinancialPDFProcessor
from src.core.exceptions import FinancialAnalysisException
from src.schemas.responses import BaseResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# PDF處理器實例
from src.services.excel_processor import FinancialExcelProcessor

# PDF處理器實例
pdf_processor = FinancialPDFProcessor()
# Excel處理器實例
excel_processor = FinancialExcelProcessor()


class DocumentUploadResponse(BaseModel):
    """文件上傳響應模型"""
    success: bool
    message: str
    document_id: Optional[str] = None
    financial_data: Optional[Dict[str, Any]] = None
    validation_results: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class DocumentProcessingStatus(BaseModel):
    """文件處理狀態模型"""
    document_id: str
    status: str  # "processing", "completed", "failed"
    progress: int  # 0-100
    message: Optional[str] = None
    results: Optional[Dict[str, Any]] = None


# 暫存處理結果的字典（實際專案中應使用Redis或資料庫）
processing_results = {}


@router.post(
    "/upload/financial-statement",
    response_model=DocumentUploadResponse,
    summary="上傳財務報表文件 (PDF/Excel)",
    description="上傳並處理財務報表文件，自動提取財務數字。支援 PDF, XLSX, XLS 格式。"
)
async def upload_financial_statement(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="財務報表文件 (PDF/Excel)"),
    company_id: Optional[str] = Form(None, description="公司代碼（可選）"),
    report_period: Optional[str] = Form(None, description="報告期間（如2024Q1）"),
    async_processing: bool = Form(False, description="是否異步處理")
):
    """
    上傳財務報表文件並提取財務數字
    
    支持的文件格式：
    - PDF (.pdf)
    - Excel (.xlsx, .xls)
    
    提取的財務指標包括：
    - 資產負債表：總資產、流動資產、總負債、流動負債、股東權益
    - 損益表：營收、毛利、營業利益、淨利、EPS
    - 現金流量表：營業活動現金流、投資活動現金流、融資活動現金流
    """
    
    # 檔案驗證
    if not file.filename:
        raise HTTPException(status_code=400, detail="請提供有效的檔案名稱")
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.pdf', '.xlsx', '.xls']:
        raise HTTPException(
            status_code=400, 
            detail="僅支援 PDF 或 Excel (.xlsx, .xls) 格式文件"
        )
    
    # 檢查檔案大小（限制為50MB）
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    try:
        # 讀取檔案內容
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="上傳的文件為空")
        
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"檔案大小超過限制（最大{MAX_FILE_SIZE // (1024*1024)}MB）"
            )
        
        # 生成文件ID
        import uuid
        document_id = str(uuid.uuid4())
        
        # 如果是異步處理
        if async_processing:
            # 啟動背景任務
            background_tasks.add_task(
                process_document_background,
                document_id=document_id,
                content=content,
                filename=file.filename,
                company_id=company_id,
                report_period=report_period
            )
            
            # 立即返回處理中狀態
            processing_results[document_id] = {
                'status': 'processing',
                'progress': 0,
                'message': '文件上傳成功，開始處理...'
            }
            
            return DocumentUploadResponse(
                success=True,
                message="文件上傳成功，正在背景處理中",
                document_id=document_id,
                metadata={
                    'filename': file.filename,
                    'file_size': len(content),
                    'processing_mode': 'async'
                }
            )
        
        # 同步處理
        logger.info(f"開始處理文件: {file.filename} (大小: {len(content)} bytes)")
        
        # 根據檔案類型選擇處理器
        if ext == '.pdf':
            processing_result = await pdf_processor.process_pdf(content, file.filename)
            validator = pdf_processor
        else:
            processing_result = await excel_processor.process_excel(content, file.filename)
            validator = excel_processor
        
        if processing_result['status'] != 'success':
            raise FinancialAnalysisException(
                message=f"文件處理失敗: {processing_result.get('error_message', '未知錯誤')}",
                error_code="DOCUMENT_PROCESSING_FAILED"
            )
        
        # 驗證提取的財務數據
        validation_results = await validator.validate_financial_data(
            processing_result['financial_data']
        )
        
        logger.info(f"成功處理文件: {file.filename}，提取到 {len(processing_result['financial_data'])} 個財務指標")
        
        return DocumentUploadResponse(
            success=True,
            message="文件處理完成",
            document_id=document_id,
            financial_data=processing_result['financial_data'],
            validation_results=validation_results,
            metadata={
                'filename': file.filename,
                'file_size': len(content),
                'extraction_methods': processing_result['extraction_methods'],
                'company_id': company_id,
                'report_period': report_period,
                'processing_mode': 'sync'
            }
        )
        
    except HTTPException:
        raise
    except FinancialAnalysisException:
        raise
    except Exception as e:
        logger.error(f"處理文件時發生未預期的錯誤: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"文件處理失敗: {str(e)}"
        )


async def process_document_background(
    document_id: str,
    content: bytes,
    filename: str,
    company_id: Optional[str] = None,
    report_period: Optional[str] = None
):
    """背景處理文件任務 (PDF/Excel)"""
    try:
        # 更新狀態為處理中
        processing_results[document_id] = {
            'status': 'processing',
            'progress': 25,
            'message': '文件解析中...'
        }
        
        ext = os.path.splitext(filename)[1].lower()
        
        # 選擇處理器
        if ext == '.pdf':
            processing_result = await pdf_processor.process_pdf(content, filename)
            validator = pdf_processor
        else:
            processing_result = await excel_processor.process_excel(content, filename)
            validator = excel_processor
        
        # 更新進度
        processing_results[document_id]['progress'] = 75
        processing_results[document_id]['message'] = '財務數據驗證中...'
        
        if processing_result['status'] == 'success':
            # 驗證財務數據
            validation_results = await validator.validate_financial_data(
                processing_result['financial_data']
            )
            
            # 處理完成
            processing_results[document_id] = {
                'status': 'completed',
                'progress': 100,
                'message': '處理完成',
                'results': {
                    'financial_data': processing_result['financial_data'],
                    'validation_results': validation_results,
                    'metadata': {
                        'filename': filename,
                        'extraction_methods': processing_result['extraction_methods'],
                        'company_id': company_id,
                        'report_period': report_period
                    }
                }
            }
        else:
            # 處理失敗
            processing_results[document_id] = {
                'status': 'failed',
                'progress': 100,
                'message': f"處理失敗: {processing_result.get('error_message', '未知錯誤')}",
                'results': None
            }
            
        logger.info(f"背景任務完成: {document_id}, 狀態: {processing_results[document_id]['status']}")
        
    except Exception as e:
        logger.error(f"背景處理任務失敗 {document_id}: {e}", exc_info=True)
        processing_results[document_id] = {
            'status': 'failed',
            'progress': 100,
            'message': f"處理失敗: {str(e)}",
            'results': None
        }


@router.get(
    "/processing-status/{document_id}",
    response_model=DocumentProcessingStatus,
    summary="查詢文件處理狀態",
    description="查詢異步處理中的文件狀態和結果"
)
async def get_processing_status(document_id: str):
    """查詢文件處理狀態"""
    
    if document_id not in processing_results:
        raise HTTPException(
            status_code=404,
            detail=f"找不到文件處理記錄: {document_id}"
        )
    
    result = processing_results[document_id]
    
    return DocumentProcessingStatus(
        document_id=document_id,
        status=result['status'],
        progress=result['progress'],
        message=result.get('message'),
        results=result.get('results')
    )


@router.delete(
    "/processing-result/{document_id}",
    summary="刪除處理結果",
    description="刪除已完成或失敗的文件處理結果"
)
async def delete_processing_result(document_id: str):
    """刪除處理結果以釋放記憶體"""
    
    if document_id not in processing_results:
        raise HTTPException(
            status_code=404,
            detail=f"找不到文件處理記錄: {document_id}"
        )
    
    del processing_results[document_id]
    
    return {"success": True, "message": "處理結果已刪除"}


@router.get(
    "/supported-formats",
    summary="獲取支援的文件格式",
    description="獲取系統支援的文件格式清單"
)
async def get_supported_formats():
    """獲取支援的文件格式"""
    return {
        "supported_formats": [
            {
                "format": "PDF",
                "extensions": [".pdf"],
                "description": "便攜式文件格式，支援表格和文字提取",
                "max_file_size": "50MB",
                "recommended": True
            }
        ],
        "extraction_capabilities": {
            "financial_statements": [
                "資產負債表 (Balance Sheet)",
                "損益表 (Income Statement)", 
                "現金流量表 (Cash Flow Statement)"
            ],
            "financial_metrics": [
                "總資產", "流動資產", "總負債", "流動負債", "股東權益",
                "營收", "毛利", "營業利益", "淨利", "每股盈餘",
                "營業活動現金流", "投資活動現金流", "融資活動現金流"
            ]
        },
        "processing_methods": [
            "pdfplumber - 優化表格提取",
            "PyMuPDF - 高效文字提取",
            "PyPDF2 - 備用解析方法"
        ]
    }


@router.post(
    "/test-extraction",
    summary="測試數據提取",
    description="測試PDF文件的數據提取能力（不保存結果）"
)
async def test_extraction(
    file: UploadFile = File(..., description="測試用PDF文件")
):
    """測試PDF數據提取功能"""
    
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="僅支援PDF格式文件")
    
    try:
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="上傳的文件為空")
        
        # 簡化的處理，只提取文字內容預覽
        result = await pdf_processor.process_pdf(content, file.filename)
        
        return {
            "success": True,
            "message": "測試提取完成",
            "preview": {
                "filename": file.filename,
                "file_size": len(content),
                "status": result['status'],
                "financial_metrics_found": len(result.get('financial_data', {})),
                "extraction_methods": result.get('extraction_methods', []),
                "sample_data": dict(list(result.get('financial_data', {}).items())[:5])  # 只返回前5個指標
            }
        }
        
    except Exception as e:
        logger.error(f"測試提取失敗: {e}")
        return {
            "success": False,
            "message": f"測試失敗: {str(e)}",
            "preview": None
        }