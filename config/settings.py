"""
Production configuration settings
生產環境配置設定
"""

import os
from typing import Optional

class ProductionConfig:
    """生產環境配置"""
    
    # 基本設定
    ENV: str = "production"
    DEBUG: bool = False
    
    # 資料庫設定
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    TIMESERIES_DATABASE_URL: Optional[str] = os.getenv("TIMESERIES_DATABASE_URL")
    
    # Redis設定
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # API金鑰
    ALPHA_VANTAGE_API_KEY: Optional[str] = os.getenv("ALPHA_VANTAGE_API_KEY")
    TWSE_API_KEY: Optional[str] = os.getenv("TWSE_API_KEY")
    
    # 安全設定
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    
    # 應用設定
    APP_NAME: str = os.getenv("APP_NAME", "Financial Analysis System")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # CORS設定
    ALLOWED_ORIGINS: list = [
        "https://your-domain.com",
        "https://api.your-domain.com"
    ]
    
    # 檔案上傳設定
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))  # 10MB
    UPLOAD_PATH: str = os.getenv("UPLOAD_PATH", "./uploads")

config = ProductionConfig()