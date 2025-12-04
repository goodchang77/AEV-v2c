"""
自定義例外處理
Custom Exception Handling
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class FinancialAnalysisException(Exception):
    """財務分析系統基礎例外"""
    
    def __init__(
        self, 
        message: str,
        error_code: str = "FINANCIAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(FinancialAnalysisException):
    """輸入驗證錯誤"""
    
    def __init__(
        self, 
        message: str,
        field: Optional[str] = None,
        value: Any = None
    ):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422
        )
        self.field = field
        self.value = value


class CompanyNotFoundError(FinancialAnalysisException):
    """公司不存在錯誤"""
    
    def __init__(self, company_id: str):
        super().__init__(
            message=f"找不到公司代碼: {company_id}",
            error_code="COMPANY_NOT_FOUND",
            details={"company_id": company_id},
            status_code=404
        )
        self.company_id = company_id


class FinancialDataNotFoundError(FinancialAnalysisException):
    """財務資料不存在錯誤"""
    
    def __init__(self, company_id: str, data_type: str, period: Optional[str] = None):
        message = f"找不到公司 {company_id} 的 {data_type}"
        if period:
            message += f" ({period})"
        
        super().__init__(
            message=message,
            error_code="FINANCIAL_DATA_NOT_FOUND",
            status_code=404
        )


class ExternalAPIError(FinancialAnalysisException):
    """外部API錯誤"""
    
    def __init__(self, message: str, api_name: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="EXTERNAL_API_ERROR",
            details={"api_name": api_name} if api_name else {},
            status_code=503
        )
        self.api_name = api_name


class DatabaseError(FinancialAnalysisException):
    """資料庫錯誤"""
    
    def __init__(self, message: str, operation: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            details={"operation": operation} if operation else {},
            status_code=500
        )


def create_http_exception(exc: FinancialAnalysisException) -> HTTPException:
    """將自定義例外轉換為HTTP例外"""
    
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    if isinstance(exc, ValidationError):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif isinstance(exc, (CompanyNotFoundError, FinancialDataNotFoundError)):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, ExternalAPIError):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(exc, DatabaseError):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    detail = {
        "error_code": exc.error_code,
        "message": exc.message,
        "details": exc.details
    }
    
    return HTTPException(
        status_code=status_code,
        detail=detail
    )