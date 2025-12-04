#!/usr/bin/env python3
"""
數據庫連接和查詢測試腳本
Test Database Connection and Queries
"""
import sys
from pathlib import Path
import asyncio
from sqlalchemy import text

# 添加項目根目錄到Python路徑
sys.path.insert(0, str(Path(__file__).parent))

from src.core.database import get_db_session, engine

async def test_database_connection():
    """測試數據庫連接和基本查詢"""
    print("🗄️  開始數據庫連接測試...")
    
    try:
        # 測試基本連接
        print("📡 測試數據庫連接...")
        async with get_db_session() as session:
            # 執行簡單查詢
            result = await session.execute(text("SELECT 1 as test_value"))
            row = result.fetchone()
            if row and row[0] == 1:
                print("   ✅ 數據庫連接成功")
            else:
                print("   ❌ 數據庫查詢結果異常")
                return False
        
        # 測試數據庫版本
        print("\n🔍 查詢數據庫資訊...")
        async with get_db_session() as session:
            result = await session.execute(text("SELECT version()"))
            version_info = result.fetchone()[0]
            print(f"   數據庫版本: {version_info.split(',')[0]}")
            
            # 檢查當前schema
            result = await session.execute(text("SELECT current_schema()"))
            schema = result.fetchone()[0]
            print(f"   當前schema: {schema}")
        
        # 測試表結構
        print("\n📋 檢查表結構...")
        async with get_db_session() as session:
            # 查詢所有表
            result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            
            if tables:
                print(f"   找到 {len(tables)} 個表:")
                for table in tables[:10]:  # 只顯示前10個表
                    print(f"      - {table}")
                if len(tables) > 10:
                    print(f"      ... 還有 {len(tables) - 10} 個表")
            else:
                print("   ⚠️  未找到任何表")
        
        # 測試創建測試表
        print("\n🔧 測試表操作...")
        test_table_name = "test_financial_system"
        
        async with get_db_session() as session:
            # 創建測試表
            await session.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {test_table_name} (
                    id SERIAL PRIMARY KEY,
                    test_data VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # 插入測試資料
            await session.execute(text(f"""
                INSERT INTO {test_table_name} (test_data)
                VALUES ('Anthropic Financial Service Test')
            """))
            
            await session.commit()
            print(f"   ✅ 測試表 '{test_table_name}' 創建成功")
        
        # 測試查詢測試資料
        async with get_db_session() as session:
            result = await session.execute(text(f"""
                SELECT id, test_data, created_at 
                FROM {test_table_name} 
                ORDER BY created_at DESC 
                LIMIT 5
            """))
            rows = result.fetchall()
            
            print(f"   📊 查詢到 {len(rows)} 條測試記錄:")
            for row in rows:
                print(f"      ID: {row[0]}, 數據: {row[1]}, 時間: {row[2]}")
        
        # 清理測試表
        async with get_db_session() as session:
            await session.execute(text(f"DROP TABLE IF EXISTS {test_table_name}"))
            await session.commit()
            print(f"   🧹 測試表 '{test_table_name}' 已清理")
        
        # 測試連接池
        print("\n🏊 測試連接池...")
        try:
            # 並發連接測試
            tasks = []
            for i in range(5):
                tasks.append(test_concurrent_connection(i))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful = sum(1 for r in results if r is True)
            print(f"   並發連接測試: {successful}/5 成功")
            
        except Exception as e:
            print(f"   ⚠️  連接池測試遇到問題: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 數據庫測試失敗: {e}")
        return False

async def test_concurrent_connection(connection_id: int) -> bool:
    """測試並發連接"""
    try:
        async with get_db_session() as session:
            result = await session.execute(text(f"SELECT {connection_id} as connection_id, pg_backend_pid() as pid"))
            row = result.fetchone()
            print(f"      連接 {connection_id}: PID {row[1]}")
            return True
    except Exception as e:
        print(f"      連接 {connection_id} 失敗: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_database_connection())
    if success:
        print("\n✅ 數據庫連接和查詢測試完成")
    else:
        print("\n❌ 數據庫測試失敗")
        sys.exit(1)