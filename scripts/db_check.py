"""
資料庫連線檢查 (Phase 1)
=========================
使用 .env 中的連線設定測試 PostgreSQL 連線，並列出 public schema 的資料表。

用法:
    py -3.14 scripts/db_check.py
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import psycopg2
from src.core.config import get_settings


def main() -> int:
    settings = get_settings()
    url = settings.DATABASE_URL
    print(f"連線目標: {url.split('@')[-1]}")

    try:
        conn = psycopg2.connect(
            settings.DATABASE_URL,
            connect_timeout=8,
        )
        cur = conn.cursor()
        cur.execute("SELECT current_database(), version()")
        db_name, version = cur.fetchone()
        print(f"[OK] 已連線 -> database={db_name}")
        print(f"     version={version}")

        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' ORDER BY table_name"
        )
        tables = [r[0] for r in cur.fetchall()]
        print(f"[OK] public schema 資料表 ({len(tables)}): {tables}")

        # 檢查核心表的資料量
        for t in ("companies", "financial_statements", "financial_ratios"):
            if t in tables:
                cur.execute(f"SELECT count(*) FROM {t}")
                print(f"     {t}: {cur.fetchone()[0]} 筆")
        conn.close()
        return 0
    except Exception as e:
        print(f"[FAIL] 資料庫連線失敗: {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
