"""
文件上傳與處理 API 端點
Document Upload and Processing API Endpoints
"""

import asyncio
import logging
import tempfile
import os
import time
import uuid
from collections import OrderedDict
from typing import Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from src.api.endpoints.auth import get_current_user
from src.models import User
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


# 上傳大小上限（維持既有對外公告的 50MB）與分段讀取大小
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1MB
# 整個 request body 允許比檔案上限多出的 multipart 開銷
REQUEST_BODY_SLACK = 1024 * 1024

# 結果儲存上限與保留時間
RESULT_STORE_MAX_ENTRIES = 500
RESULT_STORE_TTL_SECONDS = 3600

GENERIC_PROCESSING_ERROR = "文件處理失敗：無法解析文件內容"


def _size_limit_detail() -> str:
    return f"檔案大小超過限制（最大{MAX_FILE_SIZE // (1024*1024)}MB）"


class _BoundedResultStore(OrderedDict):
    """有筆數上限與 TTL 的處理結果儲存（實際專案中應使用Redis或資料庫）"""

    def __init__(self, max_entries: int, ttl_seconds: int):
        super().__init__()
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._timestamps: Dict[str, float] = {}

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.move_to_end(key)
        self._timestamps[key] = time.monotonic()
        self.evict()

    def __delitem__(self, key):
        super().__delitem__(key)
        self._timestamps.pop(key, None)

    def evict(self) -> None:
        now = time.monotonic()
        for key in [k for k, ts in self._timestamps.items() if now - ts > self.ttl_seconds]:
            if key in self:
                del self[key]
        while len(self) > self.max_entries:
            del self[next(iter(self))]

    def clear(self) -> None:
        super().clear()
        self._timestamps.clear()


# 暫存處理結果：document_id -> {..., 'owner_id': 使用者ID}
processing_results = _BoundedResultStore(RESULT_STORE_MAX_ENTRIES, RESULT_STORE_TTL_SECONDS)


def _owner_id(user: Any) -> str:
    return str(getattr(user, "user_id", ""))


def _get_owned_result(document_id: str, owner_id: str) -> Dict[str, Any]:
    """取得屬於該使用者的處理結果；不存在或非擁有者一律 404"""
    processing_results.evict()
    result = processing_results.get(document_id)
    if result is None or result.get("owner_id") != owner_id:
        raise HTTPException(status_code=404, detail="找不到文件處理記錄")
    return result


async def read_upload_limited(file: UploadFile, limit: int) -> bytes:
    """分段讀取上傳檔案，一旦超過 limit 立即回 413，不把整個檔案讀進記憶體"""
    declared = getattr(file, "size", None)
    if isinstance(declared, int) and declared > limit:
        raise HTTPException(status_code=413, detail=_size_limit_detail())
    chunks = []
    total = 0
    while True:
        chunk = await file.read(UPLOAD_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(status_code=413, detail=_size_limit_detail())
        chunks.append(chunk)
    return b"".join(chunks)


def _run_coroutine_sync(func, *args):
    return asyncio.run(func(*args))


async def _run_processor(func, *args):
    """在執行緒池中執行 CPU 密集的解析（處理器為 async 介面但內部為同步運算）"""
    return await run_in_threadpool(_run_coroutine_sync, func, *args)


class DocumentBodySizeLimitMiddleware:
    """
    ASGI 中介層：限制文件上傳路徑的 request body 大小。
    - 有 Content-Length 且超過上限 → 直接 413，不讀 body
    - 無 Content-Length（chunked）→ 邊收邊計算，超過即中止並回 413
    """

    def __init__(self, app, path_prefix: str):
        self.app = app
        self.path_prefix = path_prefix

    @staticmethod
    def _limit() -> int:
        return MAX_FILE_SIZE + REQUEST_BODY_SLACK

    async def _reject(self, scope, receive, send):
        response = JSONResponse(status_code=413, content={"detail": _size_limit_detail()})
        await response(scope, receive, send)

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or not scope.get("path", "").startswith(self.path_prefix):
            await self.app(scope, receive, send)
            return

        limit = self._limit()
        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    declared = int(value)
                except ValueError:
                    await self._reject(scope, receive, send)
                    return
                if declared > limit:
                    await self._reject(scope, receive, send)
                    return

        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message.get("type") == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise HTTPException(status_code=413, detail=_size_limit_detail())
            return message

        await self.app(scope, limited_receive, send)


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
    async_processing: bool = Form(False, description="是否異步處理"),
    current_user: User = Depends(get_current_user),
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
    
    owner_id = _owner_id(current_user)

    try:
        # 分段讀取檔案內容（超過上限立即 413）
        content = await read_upload_limited(file, MAX_FILE_SIZE)
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="上傳的文件為空")
        
        # 生成文件ID
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
                report_period=report_period,
                owner_id=owner_id
            )
            
            # 立即返回處理中狀態
            processing_results[document_id] = {
                'status': 'processing',
                'progress': 0,
                'message': '文件上傳成功，開始處理...',
                'owner_id': owner_id
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
        logger.info(f"開始處理文件: document_id={document_id} (大小: {len(content)} bytes)")
        
        # 根據檔案類型選擇處理器（在執行緒池中解析，避免阻塞事件迴圈）
        if ext == '.pdf':
            processing_result = await _run_processor(pdf_processor.process_pdf, content, file.filename)
            validator = pdf_processor
        else:
            processing_result = await _run_processor(excel_processor.process_excel, content, file.filename)
            validator = excel_processor
        
        if processing_result['status'] != 'success':
            logger.warning(
                f"文件處理失敗 document_id={document_id}: {processing_result.get('error_message', '未知錯誤')}"
            )
            raise FinancialAnalysisException(
                message=GENERIC_PROCESSING_ERROR,
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
    except Exception:
        error_id = uuid.uuid4().hex[:12]
        logger.error(f"處理文件時發生未預期的錯誤 (error_id={error_id})", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"文件處理失敗，請稍後再試（error_id: {error_id}）"
        )


async def process_document_background(
    document_id: str,
    content: bytes,
    filename: str,
    company_id: Optional[str] = None,
    report_period: Optional[str] = None,
    owner_id: str = ""
):
    """背景處理文件任務 (PDF/Excel)"""
    try:
        # 更新狀態為處理中
        processing_results[document_id] = {
            'status': 'processing',
            'progress': 25,
            'message': '文件解析中...',
            'owner_id': owner_id
        }
        
        ext = os.path.splitext(filename)[1].lower()
        
        # 選擇處理器
        if ext == '.pdf':
            processing_result = await _run_processor(pdf_processor.process_pdf, content, filename)
            validator = pdf_processor
        else:
            processing_result = await _run_processor(excel_processor.process_excel, content, filename)
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
                'owner_id': owner_id,
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
            logger.warning(
                f"背景處理失敗 {document_id}: {processing_result.get('error_message', '未知錯誤')}"
            )
            processing_results[document_id] = {
                'status': 'failed',
                'progress': 100,
                'message': GENERIC_PROCESSING_ERROR,
                'owner_id': owner_id,
                'results': None
            }
            
        logger.info(f"背景任務完成: {document_id}, 狀態: {processing_results[document_id]['status']}")
        
    except Exception as e:
        logger.error(f"背景處理任務失敗 {document_id}: {e}", exc_info=True)
        processing_results[document_id] = {
            'status': 'failed',
            'progress': 100,
            'message': GENERIC_PROCESSING_ERROR,
            'owner_id': owner_id,
            'results': None
        }


@router.get(
    "/processing-status/{document_id}",
    response_model=DocumentProcessingStatus,
    summary="查詢文件處理狀態",
    description="查詢異步處理中的文件狀態和結果"
)
async def get_processing_status(
    document_id: str,
    current_user: User = Depends(get_current_user),
):
    """查詢文件處理狀態（僅限上傳者）"""
    result = _get_owned_result(document_id, _owner_id(current_user))
    
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
async def delete_processing_result(
    document_id: str,
    current_user: User = Depends(get_current_user),
):
    """刪除處理結果以釋放記憶體（僅限上傳者）"""
    _get_owned_result(document_id, _owner_id(current_user))
    processing_results.pop(document_id, None)
    
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
            "pypdf - 備用解析方法"
        ]
    }


@router.post(
    "/test-extraction",
    summary="測試數據提取",
    description="測試PDF文件的數據提取能力（不保存結果）"
)
async def test_extraction(
    file: UploadFile = File(..., description="測試用PDF文件"),
    current_user: User = Depends(get_current_user),
):
    """測試PDF數據提取功能（需登入，套用相同大小限制）"""
    
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="僅支援PDF格式文件")
    
    content = await read_upload_limited(file, MAX_FILE_SIZE)
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="上傳的文件為空")

    try:
        # 簡化的處理，只提取文字內容預覽
        result = await _run_processor(pdf_processor.process_pdf, content, file.filename)
        
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
        
    except Exception:
        error_id = uuid.uuid4().hex[:12]
        logger.error(f"測試提取失敗 (error_id={error_id})", exc_info=True)
        return {
            "success": False,
            "message": f"測試失敗：無法解析文件（error_id: {error_id}）",
            "preview": None
        }