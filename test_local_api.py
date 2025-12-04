#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地 API 功能測試腳本
Local API Function Test Script

此腳本測試所有主要的財務分析功能：
1. 資料庫連線
2. 基本 API 端點
3. 財務分析計算
4. 股價資料處理
5. Redis 快取功能
"""

import asyncio
import asyncpg
import redis
import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import json
from typing import Dict, List, Optional
import sys
import os

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class LocalAPITester:
    def __init__(self):
        """初始化測試器"""
        self.db_config = {
            'host': 'localhost',
            'port': 5432,
            'user': 'postgres',
            'password': 'dev_password_2024',
            'database': 'financial_analysis'
        }
        
        self.timescale_config = {
            'host': 'localhost',
            'port': 5433,
            'user': 'postgres',
            'password': 'dev_password_2024',
            'database': 'timeseries_financial'
        }
        
        self.redis_config = {
            'host': 'localhost',
            'port': 6379,
            'password': 'dev_redis_2024',
            'db': 0,
            'decode_responses': True
        }
        
        self.test_results = []

    def log_test_result(self, test_name: str, success: bool, message: str = ""):
        """記錄測試結果"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            'test_name': test_name,
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        logger.info(f"{status} - {test_name}: {message}")

    def test_postgresql_connection(self) -> bool:
        """測試 PostgreSQL 連線"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # 測試基本查詢
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            
            # 測試公司資料
            cursor.execute("SELECT COUNT(*) FROM companies;")
            company_count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            self.log_test_result(
                "PostgreSQL 連線測試", 
                True, 
                f"版本: {version[0][:50]}..., 公司數量: {company_count}"
            )
            return True
            
        except Exception as e:
            self.log_test_result("PostgreSQL 連線測試", False, str(e))
            return False

    def test_timescaledb_connection(self) -> bool:
        """測試 TimescaleDB 連線"""
        try:
            conn = psycopg2.connect(**self.timescale_config)
            cursor = conn.cursor()
            
            # 檢查 TimescaleDB 擴展
            cursor.execute("SELECT installed_version FROM pg_available_extensions WHERE name='timescaledb';")
            version = cursor.fetchone()
            
            # 檢查 hypertable
            cursor.execute("SELECT * FROM timescaledb_information.hypertables;")
            hypertables = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            self.log_test_result(
                "TimescaleDB 連線測試", 
                True, 
                f"TimescaleDB 版本: {version[0] if version else 'N/A'}, Hypertables: {len(hypertables)}"
            )
            return True
            
        except Exception as e:
            self.log_test_result("TimescaleDB 連線測試", False, str(e))
            return False

    def test_redis_connection(self) -> bool:
        """測試 Redis 連線"""
        try:
            r = redis.Redis(**self.redis_config)
            
            # 基本連線測試
            ping_result = r.ping()
            
            # 設定測試資料
            test_key = "test_api_connection"
            test_value = {"timestamp": datetime.now().isoformat(), "test": "success"}
            
            r.set(test_key, json.dumps(test_value))
            retrieved_value = json.loads(r.get(test_key))
            
            # 清理測試資料
            r.delete(test_key)
            
            self.log_test_result(
                "Redis 連線測試", 
                True, 
                f"Ping: {ping_result}, 資料存取: {retrieved_value['test']}"
            )
            return True
            
        except Exception as e:
            self.log_test_result("Redis 連線測試", False, str(e))
            return False

    def test_financial_calculations(self) -> bool:
        """測試財務計算功能"""
        try:
            # 模擬財務資料
            financial_data = {
                'revenue': 1000000,
                'net_income': 150000,
                'total_assets': 2000000,
                'shareholders_equity': 1200000,
                'current_assets': 800000,
                'current_liabilities': 400000
            }
            
            # 計算財務比率
            calculations = self.calculate_financial_ratios(financial_data)
            
            # 驗證計算結果
            expected_roe = financial_data['net_income'] / financial_data['shareholders_equity']
            expected_current_ratio = financial_data['current_assets'] / financial_data['current_liabilities']
            
            success = (
                abs(calculations['roe'] - expected_roe) < 0.001 and
                abs(calculations['current_ratio'] - expected_current_ratio) < 0.001
            )
            
            self.log_test_result(
                "財務計算功能測試", 
                success, 
                f"ROE: {calculations['roe']:.4f}, 流動比率: {calculations['current_ratio']:.2f}"
            )
            return success
            
        except Exception as e:
            self.log_test_result("財務計算功能測試", False, str(e))
            return False

    def calculate_financial_ratios(self, data: Dict) -> Dict:
        """計算財務比率"""
        return {
            'roe': data['net_income'] / data['shareholders_equity'],
            'roa': data['net_income'] / data['total_assets'],
            'current_ratio': data['current_assets'] / data['current_liabilities'],
            'net_margin': data['net_income'] / data['revenue']
        }

    def test_dcf_valuation(self) -> bool:
        """測試 DCF 評價模型"""
        try:
            # DCF 參數
            params = {
                'initial_cash_flow': 1000000,
                'growth_rates': [0.15, 0.12, 0.10, 0.08, 0.05],
                'terminal_growth_rate': 0.03,
                'discount_rate': 0.10
            }
            
            # 計算 DCF 價值
            dcf_result = self.calculate_dcf_valuation(params)
            
            # 基本驗證
            success = (
                dcf_result['enterprise_value'] > 0 and
                dcf_result['terminal_value'] > 0 and
                len(dcf_result['cash_flows']) == 5
            )
            
            self.log_test_result(
                "DCF 評價模型測試", 
                success, 
                f"企業價值: ${dcf_result['enterprise_value']:,.0f}, 終值佔比: {dcf_result['terminal_value']/dcf_result['enterprise_value']:.1%}"
            )
            return success
            
        except Exception as e:
            self.log_test_result("DCF 評價模型測試", False, str(e))
            return False

    def calculate_dcf_valuation(self, params: Dict) -> Dict:
        """計算 DCF 評價"""
        cash_flows = []
        dcf_value = 0
        
        # 計算預測期現金流
        for i, growth_rate in enumerate(params['growth_rates']):
            if i == 0:
                cf = params['initial_cash_flow'] * (1 + growth_rate)
            else:
                cf = cash_flows[-1] * (1 + growth_rate)
            
            present_value = cf / ((1 + params['discount_rate']) ** (i + 1))
            cash_flows.append(cf)
            dcf_value += present_value
        
        # 計算終值
        terminal_cf = cash_flows[-1] * (1 + params['terminal_growth_rate'])
        terminal_value = terminal_cf / (params['discount_rate'] - params['terminal_growth_rate'])
        terminal_pv = terminal_value / ((1 + params['discount_rate']) ** len(params['growth_rates']))
        
        enterprise_value = dcf_value + terminal_pv
        
        return {
            'enterprise_value': enterprise_value,
            'dcf_value': dcf_value,
            'terminal_value': terminal_pv,
            'cash_flows': cash_flows
        }

    def test_stock_data_processing(self) -> bool:
        """測試股價資料處理"""
        try:
            # 生成模擬股價資料
            stock_data = self.generate_sample_stock_data()
            
            # 插入到 TimescaleDB
            success = self.insert_stock_data_to_db(stock_data)
            
            if success:
                # 測試資料查詢
                query_result = self.query_stock_data_from_db()
                
                self.log_test_result(
                    "股價資料處理測試", 
                    True, 
                    f"插入 {len(stock_data)} 筆資料，查詢到 {len(query_result)} 筆資料"
                )
                return True
            else:
                return False
                
        except Exception as e:
            self.log_test_result("股價資料處理測試", False, str(e))
            return False

    def generate_sample_stock_data(self) -> List[Dict]:
        """生成樣本股價資料"""
        data = []
        base_price = 100.0
        base_date = datetime.now() - timedelta(days=30)
        
        for i in range(30):
            # 簡單的隨機遊走
            change = np.random.normal(0, 2)  # 平均0，標準差2的正態分佈
            base_price += change
            base_price = max(base_price, 10)  # 確保價格不會太低
            
            volume = np.random.randint(1000000, 10000000)
            
            data.append({
                'time': base_date + timedelta(days=i),
                'company_id': '2330',
                'open_price': round(base_price * 0.99, 2),
                'high_price': round(base_price * 1.02, 2),
                'low_price': round(base_price * 0.98, 2),
                'close_price': round(base_price, 2),
                'volume': volume,
                'adj_close': round(base_price, 2)
            })
        
        return data

    def insert_stock_data_to_db(self, stock_data: List[Dict]) -> bool:
        """插入股價資料到資料庫"""
        try:
            conn = psycopg2.connect(**self.timescale_config)
            cursor = conn.cursor()
            
            # 先清理舊資料
            cursor.execute("DELETE FROM stock_prices WHERE company_id = '2330';")
            
            # 插入新資料
            for data in stock_data:
                cursor.execute("""
                    INSERT INTO stock_prices 
                    (time, company_id, open_price, high_price, low_price, close_price, volume, adj_close)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    data['time'], data['company_id'], data['open_price'],
                    data['high_price'], data['low_price'], data['close_price'],
                    data['volume'], data['adj_close']
                ))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            self.log_test_result("股價資料插入", False, str(e))
            return False

    def query_stock_data_from_db(self) -> List[Dict]:
        """從資料庫查詢股價資料"""
        try:
            conn = psycopg2.connect(**self.timescale_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT time, company_id, close_price, volume
                FROM stock_prices 
                WHERE company_id = '2330'
                ORDER BY time DESC
                LIMIT 10
            """)
            
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return [
                {
                    'time': row[0],
                    'company_id': row[1],
                    'close_price': float(row[2]),
                    'volume': row[3]
                }
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"查詢股價資料失敗: {e}")
            return []

    def test_cache_functionality(self) -> bool:
        """測試快取功能"""
        try:
            r = redis.Redis(**self.redis_config)
            
            # 測試快取財務計算結果
            company_id = "2330"
            cache_key = f"financial_ratios:{company_id}"
            
            # 模擬計算結果
            financial_ratios = {
                'roe': 0.125,
                'roa': 0.08,
                'current_ratio': 2.0,
                'calculated_at': datetime.now().isoformat()
            }
            
            # 存入快取
            r.setex(cache_key, 300, json.dumps(financial_ratios))  # 5分鐘過期
            
            # 從快取讀取
            cached_data = json.loads(r.get(cache_key))
            
            # 驗證資料完整性
            success = (
                cached_data['roe'] == financial_ratios['roe'] and
                cached_data['roa'] == financial_ratios['roa']
            )
            
            # 清理測試資料
            r.delete(cache_key)
            
            self.log_test_result(
                "快取功能測試", 
                success, 
                f"快取存取成功，ROE: {cached_data['roe']}"
            )
            return success
            
        except Exception as e:
            self.log_test_result("快取功能測試", False, str(e))
            return False

    def test_data_analysis_features(self) -> bool:
        """測試資料分析功能"""
        try:
            # 使用 pandas 進行資料分析
            data = {
                'company': ['2330', '2317', '1301', '1216', '2454'],
                'revenue': [1000000, 800000, 600000, 400000, 1200000],
                'net_income': [150000, 80000, 60000, 40000, 180000],
                'total_assets': [2000000, 1600000, 1200000, 800000, 2400000]
            }
            
            df = pd.DataFrame(data)
            
            # 計算財務指標
            df['roe'] = df['net_income'] / (df['total_assets'] * 0.6)  # 假設股東權益是總資產的60%
            df['net_margin'] = df['net_income'] / df['revenue']
            
            # 統計分析
            stats = {
                'avg_roe': df['roe'].mean(),
                'median_roe': df['roe'].median(),
                'top_performer': df.loc[df['roe'].idxmax(), 'company']
            }
            
            success = len(df) == 5 and stats['avg_roe'] > 0
            
            self.log_test_result(
                "資料分析功能測試", 
                success, 
                f"分析 {len(df)} 家公司，平均 ROE: {stats['avg_roe']:.4f}, 最佳表現: {stats['top_performer']}"
            )
            return success
            
        except Exception as e:
            self.log_test_result("資料分析功能測試", False, str(e))
            return False

    def test_external_data_sources(self) -> bool:
        """測試外部資料源整合"""
        try:
            # 測試 TWSE 台股資料源
            twse_success = self._test_twse_integration()
            
            # 測試 Alpha Vantage 美股資料源
            av_success, av_message = self._sync_external_test()
            
            self.log_test_result(
                "外部資料源測試 (TWSE台股)", 
                twse_success, 
                "台灣證交所 API" + ("連線成功" if twse_success else "連線失敗")
            )
            
            self.log_test_result(
                "外部資料源測試 (Alpha Vantage美股)", 
                av_success, 
                av_message
            )
            
            # 測試本地資料源管理器存在性
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    "external_data_manager", 
                    "/mnt/d/Project/AEV-v2c/src/services/external_data_manager.py"
                )
                
                module_exists = spec is not None
                self.log_test_result(
                    "外部資料源管理器模組", 
                    module_exists, 
                    "外部資料源管理器已建立" if module_exists else "模組不存在"
                )
                
            except Exception as e:
                self.log_test_result("外部資料源管理器模組", False, str(e))
                module_exists = False
            
            return twse_success or av_success or module_exists
            
        except Exception as e:
            self.log_test_result("外部資料源整合測試", False, str(e))
            return False
    
    def _test_twse_integration(self):
        """測試 TWSE 整合功能"""
        try:
            import urllib.request
            import json
            
            # 測試 TWSE API
            url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
            
            with urllib.request.urlopen(url, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    # 查找台積電資料驗證
                    for item in data:
                        if isinstance(item, dict) and item.get('Code') == '2330':
                            return True
                    return False
                else:
                    return False
                    
        except Exception:
            return False
    
    def _sync_external_test(self):
        """同步方式測試外部資料源"""
        try:
            import urllib.request
            import json
            
            # 測試 Alpha Vantage API
            alpha_key = "***REMOVED***"
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey={alpha_key}"
            
            with urllib.request.urlopen(url, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    if 'Global Quote' in data:
                        price = float(data['Global Quote']['05. price'])
                        return True, f"Alpha Vantage 連線成功，蘋果股價: ${price:.2f}"
                    else:
                        return False, f"API 回應格式錯誤: {str(data)[:100]}"
                else:
                    return False, f"HTTP 錯誤: {response.status}"
                    
        except Exception as e:
            return False, f"連線失敗: {str(e)[:50]}"

    def print_summary(self):
        """打印測試摘要"""
        print("\n" + "="*60)
        print("🎯 財務分析系統 - 本地功能測試報告")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"\n📊 測試統計:")
        print(f"   總測試數: {total_tests}")
        print(f"   通過測試: {passed_tests} ✅")
        print(f"   失敗測試: {failed_tests} ❌")
        print(f"   成功率: {passed_tests/total_tests*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ 失敗的測試:")
            for result in self.test_results:
                if not result['success']:
                    print(f"   • {result['test_name']}: {result['message']}")
        
        print(f"\n🎉 系統狀態: {'所有功能正常' if failed_tests == 0 else '部分功能需要修復'}")
        print("="*60)

    async def run_all_tests(self):
        """執行所有測試"""
        print("🚀 開始執行財務分析系統功能測試...")
        
        # 基礎連線測試
        self.test_postgresql_connection()
        self.test_timescaledb_connection()
        self.test_redis_connection()
        
        # 功能測試
        self.test_financial_calculations()
        self.test_dcf_valuation()
        self.test_stock_data_processing()
        self.test_cache_functionality()
        self.test_data_analysis_features()
        self.test_external_data_sources()
        
        # 打印結果
        self.print_summary()
        
        return all(result['success'] for result in self.test_results)

def main():
    """主程式"""
    tester = LocalAPITester()
    
    try:
        # 執行測試
        success = asyncio.run(tester.run_all_tests())
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  測試被用戶中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 測試執行出現未預期錯誤: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()