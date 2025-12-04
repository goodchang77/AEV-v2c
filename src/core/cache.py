"""
快取管理系統
Cache Management System
"""

import json
import pickle
from typing import Any, Optional, Union, Dict
from datetime import datetime, timedelta
import asyncio
import logging

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger("cache")
settings = get_settings()


class MemoryCache:
    """記憶體快取實現"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._logger = logger
    
    async def get(self, key: str) -> Optional[Any]:
        """取得快取資料"""
        try:
            if key in self._cache:
                item = self._cache[key]
                if item['expires_at'] and datetime.now() > item['expires_at']:
                    # 已過期，刪除
                    del self._cache[key]
                    return None
                return item['value']
            return None
        except Exception as e:
            self._logger.error(f"Error getting cache key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """設定快取資料"""
        try:
            expires_at = None
            if expire:
                expires_at = datetime.now() + timedelta(seconds=expire)
            
            self._cache[key] = {
                'value': value,
                'expires_at': expires_at,
                'created_at': datetime.now()
            }
            return True
        except Exception as e:
            self._logger.error(f"Error setting cache key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """刪除快取資料"""
        try:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
        except Exception as e:
            self._logger.error(f"Error deleting cache key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """檢查快取是否存在"""
        return key in self._cache
    
    async def clear(self) -> bool:
        """清空所有快取"""
        try:
            self._cache.clear()
            return True
        except Exception as e:
            self._logger.error(f"Error clearing cache: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """取得快取統計資訊"""
        try:
            total_keys = len(self._cache)
            expired_keys = 0
            total_memory = 0
            
            current_time = datetime.now()
            for key, item in self._cache.items():
                if item['expires_at'] and current_time > item['expires_at']:
                    expired_keys += 1
                # 簡單估算記憶體使用量
                total_memory += len(str(item))
            
            return {
                "total_keys": total_keys,
                "expired_keys": expired_keys,
                "estimated_memory_bytes": total_memory,
                "cache_type": "memory"
            }
        except Exception as e:
            self._logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)}


class RedisCache:
    """Redis快取實現"""
    
    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._redis: Optional[redis.Redis] = None
        self._logger = logger
    
    async def connect(self):
        """連接到Redis"""
        try:
            self._redis = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                max_connections=20
            )
            # 測試連接
            await self._redis.ping()
            self._logger.info("Redis cache connected successfully")
        except Exception as e:
            self._logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """斷開Redis連接"""
        try:
            if self._redis:
                await self._redis.close()
                self._logger.info("Redis cache disconnected")
        except Exception as e:
            self._logger.error(f"Error disconnecting Redis: {e}")
    
    async def get(self, key: str) -> Optional[Any]:
        """取得快取資料"""
        try:
            if not self._redis:
                await self.connect()
            
            value = await self._redis.get(key)
            if value:
                try:
                    # 嘗試JSON解析
                    return json.loads(value)
                except json.JSONDecodeError:
                    # 如果不是JSON，返回字串
                    return value
            return None
        except Exception as e:
            self._logger.error(f"Error getting Redis key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """設定快取資料"""
        try:
            if not self._redis:
                await self.connect()
            
            # 序列化值
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, ensure_ascii=False, default=str)
            else:
                serialized_value = str(value)
            
            if expire:
                result = await self._redis.setex(key, expire, serialized_value)
            else:
                result = await self._redis.set(key, serialized_value)
            
            return bool(result)
        except Exception as e:
            self._logger.error(f"Error setting Redis key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """刪除快取資料"""
        try:
            if not self._redis:
                await self.connect()
            
            result = await self._redis.delete(key)
            return result > 0
        except Exception as e:
            self._logger.error(f"Error deleting Redis key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """檢查快取是否存在"""
        try:
            if not self._redis:
                await self.connect()
            
            result = await self._redis.exists(key)
            return result > 0
        except Exception as e:
            self._logger.error(f"Error checking Redis key existence {key}: {e}")
            return False
    
    async def clear(self) -> bool:
        """清空所有快取"""
        try:
            if not self._redis:
                await self.connect()
            
            await self._redis.flushall()
            return True
        except Exception as e:
            self._logger.error(f"Error clearing Redis cache: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """取得Redis統計資訊"""
        try:
            if not self._redis:
                await self.connect()
            
            info = await self._redis.info()
            return {
                "redis_version": info.get("redis_version"),
                "total_keys": info.get("db0", {}).get("keys", 0) if "db0" in info else 0,
                "memory_used_bytes": info.get("used_memory"),
                "memory_used_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "cache_type": "redis"
            }
        except Exception as e:
            self._logger.error(f"Error getting Redis stats: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> bool:
        """Redis健康檢查"""
        try:
            if not self._redis:
                await self.connect()
            
            response = await self._redis.ping()
            return response is True
        except Exception as e:
            self._logger.error(f"Redis health check failed: {e}")
            return False


class CacheManager:
    """快取管理器"""
    
    def __init__(self, use_redis: bool = True, redis_url: Optional[str] = None):
        self._logger = logger
        
        if use_redis and REDIS_AVAILABLE and redis_url:
            try:
                self._cache = RedisCache(redis_url)
                self._cache_type = "redis"
                self._logger.info("Using Redis cache")
            except Exception as e:
                self._logger.warning(f"Failed to initialize Redis cache, falling back to memory: {e}")
                self._cache = MemoryCache()
                self._cache_type = "memory"
        else:
            self._cache = MemoryCache()
            self._cache_type = "memory"
            self._logger.info("Using memory cache")
    
    async def get(self, key: str) -> Optional[Any]:
        """取得快取資料"""
        return await self._cache.get(key)
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """設定快取資料"""
        return await self._cache.set(key, value, expire)
    
    async def delete(self, key: str) -> bool:
        """刪除快取資料"""
        return await self._cache.delete(key)
    
    async def exists(self, key: str) -> bool:
        """檢查快取是否存在"""
        return await self._cache.exists(key)
    
    async def clear(self) -> bool:
        """清空所有快取"""
        return await self._cache.clear()
    
    async def get_stats(self) -> Dict[str, Any]:
        """取得快取統計資訊"""
        stats = await self._cache.get_stats()
        stats["cache_manager_type"] = self._cache_type
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """快取健康檢查"""
        try:
            # 測試基本操作
            test_key = "health_check_test"
            test_value = {"test": True, "timestamp": datetime.now().isoformat()}
            
            # 寫入測試
            set_result = await self.set(test_key, test_value, expire=60)
            if not set_result:
                return {"status": "unhealthy", "error": "Failed to set test key"}
            
            # 讀取測試
            get_result = await self.get(test_key)
            if not get_result:
                return {"status": "unhealthy", "error": "Failed to get test key"}
            
            # 刪除測試
            delete_result = await self.delete(test_key)
            if not delete_result:
                return {"status": "unhealthy", "error": "Failed to delete test key"}
            
            # Redis特定檢查
            if self._cache_type == "redis" and hasattr(self._cache, 'health_check'):
                redis_healthy = await self._cache.health_check()
                if not redis_healthy:
                    return {"status": "unhealthy", "error": "Redis health check failed"}
            
            stats = await self.get_stats()
            return {
                "status": "healthy",
                "cache_type": self._cache_type,
                "stats": stats
            }
            
        except Exception as e:
            self._logger.error(f"Cache health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def warm_up_cache(self, warm_up_data: Optional[Dict[str, Any]] = None):
        """預熱快取"""
        try:
            if warm_up_data:
                for key, value in warm_up_data.items():
                    await self.set(key, value, expire=3600)  # 1小時過期
                self._logger.info(f"Cache warmed up with {len(warm_up_data)} items")
            else:
                # 預設預熱資料
                default_warm_up = {
                    "system:startup_time": datetime.now().isoformat(),
                    "system:cache_initialized": True
                }
                for key, value in default_warm_up.items():
                    await self.set(key, value, expire=86400)  # 24小時過期
                self._logger.info("Cache warmed up with default data")
        except Exception as e:
            self._logger.error(f"Cache warm up failed: {e}")
    
    @property
    def cache_type(self) -> str:
        """取得快取類型"""
        return self._cache_type
    
    async def __aenter__(self):
        """異步上下文管理器進入"""
        if hasattr(self._cache, 'connect'):
            await self._cache.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """異步上下文管理器退出"""
        if hasattr(self._cache, 'disconnect'):
            await self._cache.disconnect()


# 快取裝飾器
def cache_result(expire: int = 3600, key_prefix: str = ""):
    """快取結果裝飾器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 生成快取鍵
            cache_key = f"{key_prefix}{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # 嘗試從快取取得
            if hasattr(wrapper, '_cache_manager'):
                cached_result = await wrapper._cache_manager.get(cache_key)
                if cached_result is not None:
                    return cached_result
            
            # 執行原函數
            result = await func(*args, **kwargs)
            
            # 儲存到快取
            if hasattr(wrapper, '_cache_manager'):
                await wrapper._cache_manager.set(cache_key, result, expire)
            
            return result
        
        return wrapper
    return decorator


# 全域快取管理器實例
_cache_manager: Optional[CacheManager] = None


async def get_cache_manager() -> CacheManager:
    """取得全域快取管理器"""
    global _cache_manager
    
    if _cache_manager is None:
        redis_url = getattr(settings, 'REDIS_URL', None)
        use_redis = bool(redis_url and REDIS_AVAILABLE)
        
        _cache_manager = CacheManager(use_redis=use_redis, redis_url=redis_url)
        
        # 預熱快取
        await _cache_manager.warm_up_cache()
    
    return _cache_manager


async def init_cache() -> CacheManager:
    """初始化快取系統"""
    cache_manager = await get_cache_manager()
    logger.info(f"Cache system initialized with {cache_manager.cache_type} backend")
    return cache_manager


async def cleanup_cache():
    """清理快取資源"""
    global _cache_manager
    
    if _cache_manager:
        if hasattr(_cache_manager._cache, 'disconnect'):
            await _cache_manager._cache.disconnect()
        _cache_manager = None
        logger.info("Cache system cleaned up")