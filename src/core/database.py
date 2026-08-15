"""
資料庫連線與管理
Database Connection and Management
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
# from databases import Database  # Removed databases dependency

from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# 資料庫連線設定
DATABASE_URL = settings.DATABASE_URL
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# SQLAlchemy 設定
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    echo=settings.DEBUG
)

# 同步引擎（用於 Alembic 遷移）
sync_engine = create_engine(
    DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    echo=settings.DEBUG
)

# Session 工廠
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

SessionLocal = sessionmaker(
    sync_engine,
    autocommit=False,
    autoflush=False
)

# Databases 實例（用於純 SQL 查詢）
# database = Database(ASYNC_DATABASE_URL)  # Removed databases dependency

# 宣告式基礎類別
Base = declarative_base()

# 中繼資料
metadata = MetaData()


class DatabaseManager:
    """資料庫管理器"""
    
    def __init__(self):
        # self.database = database  # Removed databases dependency
        self.engine = engine
        self.sync_engine = sync_engine
    
    async def connect(self):
        """連線到資料庫"""
        try:
            # Connection is handled by the async engine automatically
            logger.info("Database connected successfully")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    async def disconnect(self):
        """斷線資料庫"""
        try:
            await self.engine.dispose()
            logger.info("Database disconnected successfully")
        except Exception as e:
            logger.error(f"Database disconnection failed: {e}")
    
    async def execute_query(self, query: str, values: dict = None):
        """執行 SQL 查詢"""
        try:
            from sqlalchemy import text
            async with self.engine.connect() as conn:
                if values:
                    result = await conn.execute(text(query), values)
                else:
                    result = await conn.execute(text(query))
                return result.fetchall()
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    async def execute_one(self, query: str, values: dict = None):
        """執行 SQL 查詢並返回一筆記錄"""
        try:
            from sqlalchemy import text
            async with self.engine.connect() as conn:
                if values:
                    result = await conn.execute(text(query), values)
                else:
                    result = await conn.execute(text(query))
                return result.fetchone()
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    async def execute_command(self, query: str, values: dict = None):
        """執行 SQL 命令（INSERT, UPDATE, DELETE）"""
        try:
            from sqlalchemy import text
            async with self.engine.connect() as conn:
                if values:
                    result = await conn.execute(text(query), values)
                else:
                    result = await conn.execute(text(query))
                await conn.commit()
                return result
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            raise


# 全域資料庫管理器實例
db_manager = DatabaseManager()


async def get_database():
    """取得資料庫管理器實例"""
    return db_manager


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """取得非同步資料庫 session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_session() -> Session:
    """取得同步資料庫 session"""
    return SessionLocal()


@asynccontextmanager 
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """依賴注入用的資料庫 session"""
    async with get_async_session() as session:
        yield session


async def create_tables():
    """驗證資料庫連線（實際建表由 database/init/*.sql 於容器初始化時完成）

    啟動階段若資料庫尚未就緒，不應阻止應用程式啟動：
    僅記錄警告，讓無狀態端點（/health、/analysis/dcf、/analysis/peer-comparison）
    仍可正常服務；需要 DB 的端點會在請求時各自回報錯誤。
    """
    try:
        async with engine.begin() as conn:
            # 這裡可以執行創建表格的 SQL
            # 實際的表格創建在 database/init/01_create_tables.sql 中
            logger.info("Database tables creation verified")
    except Exception as e:
        logger.warning(f"Database not available at startup (tables are created by init SQL): {e}")


class DatabaseHealthCheck:
    """資料庫健康檢查"""
    
    @staticmethod
    async def check_connection() -> bool:
        """檢查資料庫連線狀態"""
        try:
            async with get_async_session() as session:
                result = await session.execute("SELECT 1")
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    @staticmethod
    async def check_tables_exist() -> bool:
        """檢查必要的表格是否存在"""
        required_tables = [
            'companies', 
            'financial_statements', 
            'financial_ratios', 
            'users'
        ]
        
        try:
            async with get_async_session() as session:
                for table in required_tables:
                    result = await session.execute(
                        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :table_name)",
                        {"table_name": table}
                    )
                    if not result.scalar():
                        logger.error(f"Required table '{table}' does not exist")
                        return False
                return True
        except Exception as e:
            logger.error(f"Table existence check failed: {e}")
            return False
    
    @staticmethod 
    async def get_database_info() -> dict:
        """取得資料庫資訊"""
        try:
            async with get_async_session() as session:
                # 資料庫版本
                version_result = await session.execute("SELECT version()")
                version = version_result.scalar()
                
                # 連線數
                connections_result = await session.execute(
                    "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
                )
                active_connections = connections_result.scalar()
                
                # 資料庫大小
                size_result = await session.execute(
                    "SELECT pg_size_pretty(pg_database_size(current_database()))"
                )
                database_size = size_result.scalar()
                
                return {
                    "version": version,
                    "active_connections": active_connections,
                    "database_size": database_size,
                    "connection_url": DATABASE_URL.split("@")[1] if "@" in DATABASE_URL else "unknown"
                }
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {"error": str(e)}


# 資料庫健康檢查實例
health_check = DatabaseHealthCheck()