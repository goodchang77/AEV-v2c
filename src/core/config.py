"""
應用程式設定管理
Configuration Management
"""

from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator
import os


class Settings(BaseSettings):
    """應用程式設定"""
    
    # 基本應用資訊
    APP_NAME: str = "Financial Analysis System"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_VERSION: str = "v1"
    
    # 資料庫設定
    DATABASE_URL: str = "postgresql://postgres:dev_password_2024@localhost:5432/financial_analysis"
    TIMESERIES_DATABASE_URL: str = "postgresql://postgres:dev_password_2024@localhost:5433/timeseries_financial"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Redis 設定
    REDIS_URL: str = "redis://:dev_redis_2024@localhost:6379"
    REDIS_POOL_SIZE: int = 10
    REDIS_DECODE_RESPONSES: bool = True
    
    # 安全性設定
    SECRET_KEY: str = "dev_secret_key_2024_financial_analysis_system"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ALGORITHM: str = "HS256"
    
    # CORS 設定
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000"
    ]
    ALLOWED_HOSTS: Optional[List[str]] = None
    
    # 外部 API 設定
    TWSE_API_KEY: Optional[str] = None
    TWSE_BASE_URL: str = "https://openapi.twse.com.tw"
    ALPHA_VANTAGE_API_KEY: Optional[str] = None
    ALPHA_VANTAGE_BASE_URL: str = "https://www.alphavantage.co"
    
    # 快取設定
    CACHE_TTL_COMPANIES: int = 3600  # 1小時
    CACHE_TTL_FINANCIALS: int = 1800  # 30分鐘
    CACHE_TTL_RATIOS: int = 900  # 15分鐘
    CACHE_TTL_PRICES: int = 60  # 1分鐘
    
    # 檔案上傳設定
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    UPLOAD_PATH: str = "./uploads"
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = [".xlsx", ".xls", ".csv", ".json"]
    
    # 日誌設定
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: Optional[str] = None
    
    # 監控設定
    ENABLE_METRICS: bool = True
    METRICS_PATH: str = "/metrics"
    
    # 分頁設定
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # 任務調度設定
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    
    # 郵件設定
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True

    # AI Agent 設定
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"

    # MCP Server 設定
    MCP_MAX_CONCURRENT_TOOLS: int = 5
    MCP_CACHE_ENABLED: bool = True
    MCP_CACHE_TTL_SECONDS: int = 3600
    
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        """處理 CORS origins 設定"""
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError("ALLOWED_ORIGINS must be a comma-separated string or list")
    
    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def assemble_allowed_hosts(cls, v):
        """處理 allowed hosts 設定"""
        if v is None:
            return None
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError("ALLOWED_HOSTS must be a comma-separated string or list")
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v):
        """驗證資料庫 URL"""
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL")
        return v
    
    @field_validator("REDIS_URL")
    @classmethod
    def validate_redis_url(cls, v):
        """驗證 Redis URL"""
        if not v.startswith("redis://"):
            raise ValueError("REDIS_URL must be a Redis URL")
        return v
    
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v):
        """驗證密鑰長度"""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    @field_validator("UPLOAD_PATH")
    @classmethod
    def validate_upload_path(cls, v):
        """確保上傳路徑存在 - GCP App Engine only allows /tmp"""
        # 在GCP App Engine環境中，使用/tmp目錄
        if os.environ.get("GAE_ENV", "").startswith("standard"):
            v = "/tmp/uploads"
        
        if not os.path.exists(v):
            try:
                os.makedirs(v, exist_ok=True)
            except OSError:
                # 如果無法創建目錄，使用/tmp作為fallback
                v = "/tmp"
        return v
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "env_parse_none_str": "None",
        "validate_default": True
    }


class DevelopmentSettings(Settings):
    """開發環境設定"""
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"


class ProductionSettings(Settings):
    """生產環境設定"""
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"
    
    # 生產環境安全設定
    ALLOWED_HOSTS: List[str] = ["api.financial-analysis.com"]
    ALLOWED_ORIGINS: List[str] = ["https://financial-analysis.com"]


class TestingSettings(Settings):
    """測試環境設定"""
    DEBUG: bool = True
    DATABASE_URL: str = "postgresql://postgres:test_password@localhost:5432/test_financial_analysis"
    TIMESERIES_DATABASE_URL: str = "postgresql://postgres:test_password@localhost:5433/test_timeseries_financial"
    REDIS_URL: str = "redis://:test_redis@localhost:6379/1"
    SECRET_KEY: str = "test_secret_key_for_testing_only"


@lru_cache()
def get_settings() -> Settings:
    """取得應用程式設定單例"""
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        return ProductionSettings()
    elif environment == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()


# 匯出設定實例
settings = get_settings()