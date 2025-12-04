"""
日誌設定與管理
Logging Configuration and Management
"""

import logging
import logging.config
import structlog
import sys
from datetime import datetime
from typing import Any, Dict

from src.core.config import get_settings

settings = get_settings()


def setup_logging():
    """設定結構化日誌"""

    # 處理LOG_FORMAT設定
    log_format = settings.LOG_FORMAT
    if log_format == "json":
        # 如果是json格式，使用標準格式並在後面配置JSON renderer
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # 基本日誌設定
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 如果指定了日誌檔案
    if settings.LOG_FILE:
        file_handler = logging.FileHandler(settings.LOG_FILE)
        file_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
        file_handler.setFormatter(logging.Formatter(settings.LOG_FORMAT))
        logging.getLogger().addHandler(file_handler)
    
    # 結構化日誌處理器
    processors = [
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
    ]
    
    if settings.DEBUG:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        processors.append(structlog.processors.JSONRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


class FinancialAnalysisLogger:
    """財務分析系統專用日誌器"""
    
    def __init__(self, name: str):
        self.logger = structlog.get_logger(name)
    
    def info(self, message: str, **kwargs):
        """記錄資訊日誌"""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """記錄警告日誌"""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """記錄錯誤日誌"""
        self.logger.error(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """記錄偵錯日誌"""
        if settings.DEBUG:
            self.logger.debug(message, **kwargs)
    
    def calculation_log(self, company_id: str, calculation_type: str, 
                       duration: float, success: bool, **kwargs):
        """記錄計算相關日誌"""
        self.logger.info(
            f"Calculation {calculation_type} {'completed' if success else 'failed'}",
            company_id=company_id,
            calculation_type=calculation_type,
            duration_seconds=duration,
            success=success,
            **kwargs
        )
    
    def api_request_log(self, method: str, path: str, status_code: int, 
                       duration: float, user_id: str = None, **kwargs):
        """記錄 API 請求日誌"""
        self.logger.info(
            "API request processed",
            method=method,
            path=path,
            status_code=status_code,
            duration_seconds=duration,
            user_id=user_id,
            **kwargs
        )
    
    def data_quality_log(self, data_source: str, data_type: str, 
                        quality_score: float, issues: list = None, **kwargs):
        """記錄資料品質日誌"""
        self.logger.info(
            "Data quality assessment",
            data_source=data_source,
            data_type=data_type,
            quality_score=quality_score,
            issues=issues or [],
            **kwargs
        )
    
    def security_log(self, event_type: str, user_id: str = None, 
                    ip_address: str = None, success: bool = True, **kwargs):
        """記錄安全相關日誌"""
        self.logger.info(
            f"Security event: {event_type}",
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            success=success,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )


def get_logger(name: str) -> FinancialAnalysisLogger:
    """取得專用日誌器實例"""
    return FinancialAnalysisLogger(name)


# 預設日誌器
logger = get_logger("financial_analysis")