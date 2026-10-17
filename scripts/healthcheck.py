#!/usr/bin/env python3
"""
Production Health Check Script
生產環境健康檢查腳本（供 Dockerfile HEALTHCHECK / docker compose healthcheck 使用）

結束碼：
  0 = 所有「有執行」的檢查都通過
  1 = 任一檢查失敗

檢查項目：
  - api:      GET http://127.0.0.1:8000/health 必須回 200（可用 HEALTHCHECK_URL 覆寫）
  - database: 若有 DATABASE_URL 且可匯入 asyncpg，實際連線並執行 SELECT 1
  - cache:    若有 REDIS_URL 且可匯入 redis，實際 PING

未設定連線字串或缺少驅動時，該項目回報為「not checked」（不會假裝通過，也不計為失敗）。
設定 HEALTHCHECK_SKIP_DEPS=1 可只檢查 API。
輸出只包含檢查名稱與錯誤類型，不會印出連線字串或密碼。
"""

import asyncio
import os
import sys
from typing import Optional, Tuple

TIMEOUT_SECONDS = float(os.getenv("HEALTHCHECK_TIMEOUT", "3"))
API_URL = os.getenv("HEALTHCHECK_URL", "http://127.0.0.1:8000/health")

# (status, detail)；status ∈ {"ok", "fail", "not checked"}
Result = Tuple[str, str]


def _err(e: BaseException) -> str:
    # 只回報錯誤類型，避免把含密碼的連線字串印到 docker inspect / logs
    return type(e).__name__


async def check_api_health() -> Result:
    """檢查 API 健康狀態"""
    try:
        import aiohttp
    except ImportError:
        # 退回標準函式庫，避免因缺少套件而誤判
        import urllib.request

        def _get() -> int:
            with urllib.request.urlopen(API_URL, timeout=TIMEOUT_SECONDS) as resp:  # noqa: S310
                return resp.status

        try:
            status = await asyncio.get_running_loop().run_in_executor(None, _get)
            return ("ok", "") if status == 200 else ("fail", f"HTTP {status}")
        except Exception as e:  # noqa: BLE001
            return ("fail", _err(e))

    try:
        timeout = aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(API_URL) as response:
                if response.status == 200:
                    return ("ok", "")
                return ("fail", f"HTTP {response.status}")
    except Exception as e:  # noqa: BLE001
        return ("fail", _err(e))


def _normalize_pg_dsn(url: str) -> str:
    # asyncpg 不接受 SQLAlchemy 的 driver 後綴（postgresql+asyncpg:// 等）
    scheme, sep, rest = url.partition("://")
    if not sep:
        return url
    return scheme.split("+", 1)[0] + "://" + rest


async def check_database_health() -> Result:
    """檢查資料庫連線（SELECT 1）"""
    url: Optional[str] = os.getenv("DATABASE_URL")
    if not url or not url.startswith("postgres"):
        return ("not checked", "DATABASE_URL not set or not PostgreSQL")
    try:
        import asyncpg
    except ImportError:
        return ("not checked", "asyncpg not installed")
    try:
        conn = await asyncio.wait_for(
            asyncpg.connect(_normalize_pg_dsn(url), timeout=TIMEOUT_SECONDS),
            timeout=TIMEOUT_SECONDS + 1,
        )
        try:
            value = await asyncio.wait_for(conn.fetchval("SELECT 1"), timeout=TIMEOUT_SECONDS)
        finally:
            await conn.close()
        return ("ok", "") if value == 1 else ("fail", "unexpected result")
    except Exception as e:  # noqa: BLE001
        return ("fail", _err(e))


async def check_cache_health() -> Result:
    """檢查 Redis 連線（PING）"""
    url: Optional[str] = os.getenv("REDIS_URL")
    if not url:
        return ("not checked", "REDIS_URL not set")
    try:
        import redis.asyncio as aioredis
    except ImportError:
        return ("not checked", "redis package not installed")
    client = None
    try:
        client = aioredis.from_url(
            url,
            socket_timeout=TIMEOUT_SECONDS,
            socket_connect_timeout=TIMEOUT_SECONDS,
        )
        pong = await asyncio.wait_for(client.ping(), timeout=TIMEOUT_SECONDS + 1)
        return ("ok", "") if pong else ("fail", "no PONG")
    except Exception as e:  # noqa: BLE001
        return ("fail", _err(e))
    finally:
        if client is not None:
            closer = getattr(client, "aclose", None) or getattr(client, "close", None)
            try:
                if closer is not None:
                    await closer()
            except Exception:  # noqa: BLE001
                pass


async def main() -> int:
    """主要健康檢查函數"""
    checks = {"api": check_api_health()}
    if os.getenv("HEALTHCHECK_SKIP_DEPS", "").lower() not in ("1", "true", "yes"):
        checks["database"] = check_database_health()
        checks["cache"] = check_cache_health()

    results = await asyncio.gather(*checks.values(), return_exceptions=True)

    status = {}
    for name, result in zip(checks.keys(), results):
        if isinstance(result, BaseException):
            status[name] = ("fail", _err(result))
        else:
            status[name] = result

    healthy = all(s != "fail" for s, _ in status.values())
    icon = {"ok": "✅", "fail": "❌", "not checked": "➖"}
    print("✅ Healthy" if healthy else "❌ Health check failed")
    for name, (s, detail) in status.items():
        suffix = f" ({detail})" if detail else ""
        print(f"  {name}: {icon[s]} {s}{suffix}")
    return 0 if healthy else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
