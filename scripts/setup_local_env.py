#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地測試環境快速設定腳本
Local Testing Environment Setup Script
"""

import os
import sys
import subprocess
import time
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import redis
import requests
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class LocalEnvironmentSetup:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.db_config = {
            'host': 'localhost',
            'port': 5432,
            'user': 'postgres',
            'password': 'dev_password_2024',
            'dbname': 'financial_analysis'
        }
        self.timescale_config = {
            'host': 'localhost',
            'port': 5433,
            'user': 'postgres',
            'password': 'dev_password_2024',
            'dbname': 'timeseries_financial'
        }
        self.redis_config = {
            'host': 'localhost',
            'port': 6379,
            'password': 'dev_redis_2024',
            'db': 0
        }

    def print_step(self, step_num, description):
        """打印步驟資訊"""
        print(f"\n{'='*50}")
        print(f"步驟 {step_num}: {description}")
        print('='*50)

    def check_docker_compose(self):
        """檢查 Docker Compose 是否安裝"""
        self.print_step(1, "檢查 Docker Compose")
        try:
            result = subprocess.run(['docker-compose', '--version'], 
                                  capture_output=True, text=True, check=True)
            print(f"✅ Docker Compose 版本: {result.stdout.strip()}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Docker Compose 未安裝或不可用")
            return False

    def start_services(self):
        """啟動本地服務"""
        self.print_step(2, "啟動本地服務")
        try:
            print("🚀 啟動 Docker Compose 服務...")
            cmd = ['docker-compose', '-f', 'docker-compose.local-test.yml', 'up', '-d']
            result = subprocess.run(cmd, cwd=self.project_root, check=True, 
                                  capture_output=True, text=True)
            
            print("✅ 服務啟動命令執行成功")
            print("⏳ 等待服務完全啟動（60秒）...")
            time.sleep(60)
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 服務啟動失敗: {e}")
            print(f"標準輸出: {e.stdout}")
            print(f"錯誤輸出: {e.stderr}")
            return False

    def wait_for_database(self, config, max_retries=30):
        """等待資料庫服務準備就緒"""
        print(f"⏳ 等待資料庫 {config['host']}:{config['port']} 準備就緒...")
        
        for i in range(max_retries):
            try:
                conn = psycopg2.connect(**config)
                conn.close()
                print(f"✅ 資料庫 {config['host']}:{config['port']} 已準備就緒")
                return True
            except psycopg2.OperationalError:
                if i < max_retries - 1:
                    print(f"⏳ 嘗試 {i+1}/{max_retries} - 等待資料庫...")
                    time.sleep(2)
                continue
        
        print(f"❌ 資料庫 {config['host']}:{config['port']} 連線超時")
        return False

    def wait_for_redis(self, max_retries=30):
        """等待 Redis 服務準備就緒"""
        print("⏳ 等待 Redis 服務準備就緒...")
        
        for i in range(max_retries):
            try:
                r = redis.Redis(
                    host=self.redis_config['host'],
                    port=self.redis_config['port'],
                    password=self.redis_config['password'],
                    db=self.redis_config['db'],
                    decode_responses=True
                )
                r.ping()
                print("✅ Redis 服務已準備就緒")
                return True
            except redis.ConnectionError:
                if i < max_retries - 1:
                    print(f"⏳ 嘗試 {i+1}/{max_retries} - 等待 Redis...")
                    time.sleep(2)
                continue
        
        print("❌ Redis 服務連線超時")
        return False

    def initialize_database(self):
        """初始化主資料庫"""
        self.print_step(3, "初始化主資料庫")
        
        if not self.wait_for_database(self.db_config):
            return False

        try:
            # 連接資料庫
            conn = psycopg2.connect(**self.db_config)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

            # 建立基本資料表結構
            print("📊 建立基本資料表...")
            
            # 建立公司基本資料表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS companies (
                    company_id VARCHAR(10) PRIMARY KEY,
                    company_name VARCHAR(100) NOT NULL,
                    industry_code VARCHAR(10),
                    market_type VARCHAR(20),
                    listing_date DATE,
                    capital_amount DECIMAL(15,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 建立財務報表資料表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS financial_statements (
                    id BIGSERIAL PRIMARY KEY,
                    company_id VARCHAR(10) NOT NULL,
                    report_type VARCHAR(20) NOT NULL,
                    year_quarter VARCHAR(10) NOT NULL,
                    statement_type VARCHAR(20) NOT NULL,
                    total_assets DECIMAL(15,2),
                    total_liabilities DECIMAL(15,2),
                    shareholders_equity DECIMAL(15,2),
                    revenue DECIMAL(15,2),
                    net_income DECIMAL(15,2),
                    eps DECIMAL(8,4),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies(company_id)
                );
            """)

            # 建立財務比率表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS financial_ratios (
                    id BIGSERIAL PRIMARY KEY,
                    company_id VARCHAR(10) NOT NULL,
                    year_quarter VARCHAR(10) NOT NULL,
                    roa DECIMAL(8,4),
                    roe DECIMAL(8,4),
                    debt_ratio DECIMAL(8,4),
                    current_ratio DECIMAL(8,4),
                    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies(company_id)
                );
            """)

            # 插入測試資料
            print("📝 插入測試資料...")
            cursor.execute("""
                INSERT INTO companies (company_id, company_name, industry_code, market_type) 
                VALUES 
                    ('2330', '台積電', 'SEMI', '上市'),
                    ('2317', '鴻海', 'ELEC', '上市'),
                    ('1301', '台塑', 'CHEM', '上市')
                ON CONFLICT (company_id) DO NOTHING;
            """)

            conn.commit()
            cursor.close()
            conn.close()
            
            print("✅ 主資料庫初始化完成")
            return True

        except Exception as e:
            print(f"❌ 主資料庫初始化失敗: {e}")
            return False

    def initialize_timescaledb(self):
        """初始化 TimescaleDB"""
        self.print_step(4, "初始化 TimescaleDB")
        
        if not self.wait_for_database(self.timescale_config):
            return False

        try:
            # 連接 TimescaleDB
            conn = psycopg2.connect(**self.timescale_config)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

            # 啟用 TimescaleDB 擴展
            print("🔧 啟用 TimescaleDB 擴展...")
            cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")

            # 建立股價資料表
            print("📈 建立股價時序資料表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_prices (
                    time TIMESTAMPTZ NOT NULL,
                    company_id VARCHAR(10) NOT NULL,
                    open_price DECIMAL(8,2),
                    high_price DECIMAL(8,2),
                    low_price DECIMAL(8,2),
                    close_price DECIMAL(8,2),
                    volume BIGINT,
                    adj_close DECIMAL(8,2)
                );
            """)

            # 建立 Hypertable
            try:
                cursor.execute("SELECT create_hypertable('stock_prices', 'time');")
                print("✅ Hypertable 建立成功")
            except psycopg2.Error as e:
                if "already exists" in str(e):
                    print("✅ Hypertable 已存在")
                else:
                    raise

            # 建立索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_stock_prices_company_time 
                ON stock_prices (company_id, time DESC);
            """)

            conn.commit()
            cursor.close()
            conn.close()
            
            print("✅ TimescaleDB 初始化完成")
            return True

        except Exception as e:
            print(f"❌ TimescaleDB 初始化失敗: {e}")
            return False

    def test_redis_connection(self):
        """測試 Redis 連線"""
        self.print_step(5, "測試 Redis 連線")
        
        if not self.wait_for_redis():
            return False

        try:
            r = redis.Redis(
                host=self.redis_config['host'],
                port=self.redis_config['port'],
                password=self.redis_config['password'],
                db=self.redis_config['db'],
                decode_responses=True
            )
            
            # 測試基本操作
            r.set('test_key', 'test_value')
            value = r.get('test_key')
            
            if value == 'test_value':
                print("✅ Redis 連線測試成功")
                r.delete('test_key')
                return True
            else:
                print("❌ Redis 資料測試失敗")
                return False

        except Exception as e:
            print(f"❌ Redis 連線測試失敗: {e}")
            return False

    def test_application(self):
        """測試應用程式"""
        self.print_step(6, "測試應用程式連線")
        
        print("⏳ 等待應用程式啟動...")
        time.sleep(30)
        
        try:
            # 測試健康檢查端點
            response = requests.get('http://localhost:8000/health', timeout=10)
            if response.status_code == 200:
                print("✅ 應用程式健康檢查通過")
                
                # 測試 API 文檔
                response = requests.get('http://localhost:8000/docs', timeout=10)
                if response.status_code == 200:
                    print("✅ API 文檔可訪問")
                    return True
                else:
                    print("⚠️  API 文檔無法訪問")
                    return True
            else:
                print(f"❌ 應用程式健康檢查失敗: {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"❌ 應用程式連線測試失敗: {e}")
            return False

    def print_service_info(self):
        """打印服務資訊"""
        self.print_step("完成", "本地測試環境設定完成")
        
        print("\n🎉 本地測試環境已準備就緒！")
        print("\n📋 服務訪問資訊:")
        print(f"  • 主應用程式: http://localhost:8000")
        print(f"  • API 文檔: http://localhost:8000/docs")
        print(f"  • PostgreSQL: localhost:5432")
        print(f"  • TimescaleDB: localhost:5433")
        print(f"  • Redis: localhost:6379")
        print(f"  • pgAdmin: http://localhost:5050")
        print(f"  • Redis Insight: http://localhost:8001")
        print(f"  • Adminer: http://localhost:8080")
        
        print(f"\n🔑 預設帳號密碼:")
        print(f"  • PostgreSQL: postgres / dev_password_2024")
        print(f"  • Redis: (密碼) dev_redis_2024")
        print(f"  • pgAdmin: admin@financial.local / admin123")
        
        print(f"\n📝 使用指令:")
        print(f"  • 查看日誌: docker-compose -f docker-compose.local-test.yml logs -f")
        print(f"  • 停止服務: docker-compose -f docker-compose.local-test.yml down")
        print(f"  • 重啟服務: docker-compose -f docker-compose.local-test.yml restart")

def main():
    """主要執行函式"""
    setup = LocalEnvironmentSetup()
    
    print("🚀 開始設定本地測試環境...")
    
    # 執行所有設定步驟
    steps = [
        setup.check_docker_compose,
        setup.start_services,
        setup.initialize_database,
        setup.initialize_timescaledb,
        setup.test_redis_connection,
        setup.test_application,
    ]
    
    for step in steps:
        if not step():
            print(f"\n❌ 設定失敗於步驟: {step.__name__}")
            return False
    
    setup.print_service_info()
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)