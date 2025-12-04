#!/usr/bin/env python
"""
環境變數驗證腳本
Verify Environment Variables

快速檢查所有必要的環境變數是否已正確設定
"""

import os
import sys
from pathlib import Path

# 嘗試載入 .env 檔案
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ .env 檔案已載入\n")
except ImportError:
    print("⚠ python-dotenv 未安裝，使用系統環境變數")
    print("  安裝: pip install python-dotenv\n")


def check_env_var(var_name: str, description: str, required: bool = True, hide_value: bool = False):
    """檢查單個環境變數"""
    value = os.getenv(var_name)

    if value:
        if hide_value:
            display_value = value[:10] + "..." if len(value) > 10 else "***"
        else:
            display_value = value[:60] + "..." if len(value) > 60 else value

        print(f"✓ {var_name:30} = {display_value}")
        return True
    else:
        status = "✗ 必要" if required else "○ 可選"
        print(f"{status} {var_name:30} = 未設定")
        return not required


def test_database_connection():
    """測試資料庫連線"""
    print("\n" + "="*70)
    print("測試資料庫連線...")
    print("="*70)

    try:
        from sqlalchemy import create_engine
        db_url = os.getenv("DATABASE_URL")

        if not db_url:
            print("✗ DATABASE_URL 未設定")
            return False

        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute("SELECT version();")
            version = result.fetchone()[0]
            print(f"✓ 資料庫連線成功!")
            print(f"  PostgreSQL 版本: {version.split(',')[0]}")
            return True

    except ImportError:
        print("○ sqlalchemy 未安裝，跳過資料庫測試")
        print("  安裝: pip install sqlalchemy psycopg2-binary")
        return None
    except Exception as e:
        print(f"✗ 資料庫連線失敗: {str(e)[:100]}")
        return False


def test_redis_connection():
    """測試 Redis 連線"""
    print("\n" + "="*70)
    print("測試 Redis 連線...")
    print("="*70)

    try:
        import redis
        redis_url = os.getenv("REDIS_URL")

        if not redis_url:
            print("✗ REDIS_URL 未設定")
            return False

        r = redis.from_url(redis_url)
        r.ping()
        info = r.info()
        print(f"✓ Redis 連線成功!")
        print(f"  Redis 版本: {info['redis_version']}")
        return True

    except ImportError:
        print("○ redis 未安裝，跳過 Redis 測試")
        print("  安裝: pip install redis")
        return None
    except Exception as e:
        print(f"✗ Redis 連線失敗: {str(e)[:100]}")
        return False


def test_anthropic_api():
    """測試 Claude API"""
    print("\n" + "="*70)
    print("測試 Claude API 連線...")
    print("="*70)

    try:
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

        if not api_key:
            print("✗ ANTHROPIC_API_KEY 未設定")
            return False

        client = anthropic.Anthropic(api_key=api_key)

        # 簡單測試請求
        message = client.messages.create(
            model=model,
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}]
        )

        print(f"✓ Claude API 連線成功!")
        print(f"  模型: {model}")
        print(f"  回應: {message.content[0].text}")
        return True

    except ImportError:
        print("○ anthropic 未安裝，跳過 Claude API 測試")
        print("  安裝: pip install anthropic")
        return None
    except Exception as e:
        print(f"✗ Claude API 連線失敗: {str(e)[:100]}")
        return False


def main():
    """主程式"""
    print("="*70)
    print("AEV-v2c 環境變數驗證工具")
    print("="*70)
    print()

    # 檢查必要環境變數
    print("檢查必要環境變數:")
    print("-" * 70)

    required_vars = {
        # 資料庫
        "DATABASE_URL": ("資料庫連線", True, True),
        "REDIS_URL": ("Redis 快取", True, True),

        # AI Agent
        "ANTHROPIC_API_KEY": ("Claude API 金鑰", True, True),
        "ANTHROPIC_MODEL": ("AI 模型", True, False),

        # MCP Server
        "MCP_MAX_CONCURRENT_TOOLS": ("MCP 並發數", True, False),
        "MCP_CACHE_ENABLED": ("MCP 快取啟用", True, False),
        "MCP_CACHE_TTL_SECONDS": ("MCP 快取時間", True, False),
    }

    all_ok = True
    for var_name, (desc, required, hide) in required_vars.items():
        if not check_env_var(var_name, desc, required, hide):
            all_ok = False

    print()

    # 檢查可選環境變數
    print("\n檢查可選環境變數:")
    print("-" * 70)

    optional_vars = {
        "TIMESERIES_DATABASE_URL": ("時序資料庫", False, True),
        "TWSE_API_KEY": ("證交所 API", False, True),
        "ALPHA_VANTAGE_API_KEY": ("Alpha Vantage API", False, True),
        "DEBUG": ("除錯模式", False, False),
    }

    for var_name, (desc, required, hide) in optional_vars.items():
        check_env_var(var_name, desc, required, hide)

    # 連線測試
    if all_ok:
        print("\n✓ 所有必要環境變數已設定")
        print("\n開始連線測試...\n")

        db_ok = test_database_connection()
        redis_ok = test_redis_connection()
        api_ok = test_anthropic_api()

        # 總結
        print("\n" + "="*70)
        print("驗證總結")
        print("="*70)

        tests = [
            ("環境變數", all_ok),
            ("資料庫連線", db_ok),
            ("Redis 連線", redis_ok),
            ("Claude API", api_ok),
        ]

        for name, result in tests:
            if result is True:
                print(f"✓ {name:20} 正常")
            elif result is False:
                print(f"✗ {name:20} 失敗")
            else:
                print(f"○ {name:20} 跳過")

        print()

        if all(r is not False for r in [all_ok, db_ok, redis_ok, api_ok]):
            print("🎉 所有檢查通過！系統已準備就緒。")
            print("\n啟動系統:")
            print("  uvicorn src.main:app --reload --port 8000")
            return 0
        else:
            print("⚠️ 部分檢查失敗，請修復後再啟動系統。")
            print("\n參考文件: ENV_SETUP_GUIDE.md")
            return 1
    else:
        print("\n✗ 部分必要環境變數缺失")
        print("\n請檢查 .env 檔案並設定缺失的環境變數")
        print("參考範本: .env.example")
        return 1


if __name__ == "__main__":
    sys.exit(main())
