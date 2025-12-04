#!/usr/bin/env python3
"""
元大0050 ETF成分股Yahoo Finance整合測試腳本
Enhanced Test Yuanta 0050 ETF Components with Yahoo Finance Real Data
"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import requests
import yfinance as yf
import pandas as pd
import numpy as np

# 添加項目根目錄到Python路徑
sys.path.insert(0, str(Path(__file__).parent))

# 元大0050前十大持股成分股清單（台股代碼）
YUANTA_0050_TOP10 = [
    {"code": "2330", "name": "台積電", "weight": 59.36, "industry": "半導體"},
    {"code": "2317", "name": "鴻海", "weight": 4.56, "industry": "電腦及週邊設備"},
    {"code": "2454", "name": "聯發科", "weight": 4.23, "industry": "半導體"},
    {"code": "2308", "name": "台達電", "weight": 2.31, "industry": "電子零組件"},
    {"code": "2382", "name": "廣達", "weight": 1.56, "industry": "電腦及週邊設備"},
    {"code": "2881", "name": "富邦金", "weight": 1.40, "industry": "金融保險"},
    {"code": "2891", "name": "中信金", "weight": 1.38, "industry": "金融保險"},
    {"code": "2882", "name": "國泰金", "weight": 1.19, "industry": "金融保險"},
    {"code": "2886", "name": "兆豐金", "weight": 1.05, "industry": "金融保險"},
    {"code": "3711", "name": "日月光投控", "weight": 1.05, "industry": "半導體"}
]

class YahooFinanceETF0050Tester:
    """Yahoo Finance整合的元大0050 ETF成分股測試器"""
    
    def __init__(self):
        self.base_url = "http://localhost:8001"
        self.test_results = {}
        self.yahoo_cache = {}
        
    async def run_comprehensive_test(self):
        """執行完整的0050成分股Yahoo Finance整合測試"""
        print("🌐 元大0050 ETF前十大持股 Yahoo Finance整合測試")
        print("="*80)
        
        print(f"\n📊 測試標的: 元大台灣卓越50證券投資信託基金 (0050)")
        print(f"📅 測試日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 測試範圍: 前十大持股成分股 (真實市場數據)")
        print(f"🔌 數據來源: Yahoo Finance API")
        
        # 顯示測試清單
        print(f"\n📋 0050前十大成分股清單:")
        total_weight = sum(stock["weight"] for stock in YUANTA_0050_TOP10)
        
        for i, stock in enumerate(YUANTA_0050_TOP10, 1):
            print(f"   {i:2d}. {stock['code']} {stock['name']:8s} - "
                  f"{stock['weight']:5.2f}% ({stock['industry']})")
        
        print(f"\n   前十大持股總權重: {total_weight:.2f}%")
        print(f"   台積電單一持股權重: {YUANTA_0050_TOP10[0]['weight']:.2f}%")
        
        # Yahoo Finance連線測試
        await self.test_yahoo_finance_connectivity()
        
        # 測試各成分股
        print(f"\n🔍 開始測試各成分股的Yahoo Finance資料整合...")
        
        for i, stock in enumerate(YUANTA_0050_TOP10, 1):
            print(f"\n[{i:2d}/10] 測試 {stock['code']} {stock['name']}")
            print("-" * 60)
            
            result = await self.test_single_stock_yahoo(stock)
            self.test_results[stock['code']] = result
            
            # 詳細結果顯示
            if result['success']:
                print(f"   ✅ {stock['name']} Yahoo Finance資料擷取成功")
                if 'yahoo_data' in result:
                    data = result['yahoo_data']
                    current_price = data.get('current_price', 0)
                    market_cap_twd = data.get('market_cap_twd', 0) / 1e8  # 轉億元
                    volume = data.get('volume', 0) / 1000  # 轉張
                    print(f"      當前股價: {current_price:>8.2f} TWD")
                    print(f"      市值: {market_cap_twd:>10.1f} 億元")
                    print(f"      成交量: {volume:>10.0f} 張")
                    print(f"      本益比: {data.get('pe_ratio', 'N/A'):>10s}")
                    print(f"      股息殖利率: {data.get('dividend_yield', 'N/A'):>6s}")
            else:
                print(f"   ❌ {stock['name']} 資料擷取失敗: {result.get('error', '未知錯誤')}")
        
        # 生成Yahoo Finance整合分析報告
        await self.generate_yahoo_analysis_report()
        
        return self.test_results
    
    async def test_yahoo_finance_connectivity(self):
        """測試Yahoo Finance API連線狀態"""
        print(f"\n🌐 檢查Yahoo Finance API連線狀態...")
        
        try:
            # 測試擷取台積電資料
            test_ticker = yf.Ticker("2330.TW")
            test_info = test_ticker.info
            
            if test_info and 'symbol' in test_info:
                print(f"   ✅ Yahoo Finance API連線正常")
                print(f"   📡 測試股票: {test_info.get('longName', '2330.TW')}")
            else:
                print(f"   ⚠️  Yahoo Finance API回應異常")
        except Exception as e:
            print(f"   ❌ Yahoo Finance API連線失敗: {e}")
            print(f"   💡 請檢查網路連線或Yahoo Finance服務狀態")
    
    async def test_single_stock_yahoo(self, stock: Dict) -> Dict[str, Any]:
        """使用Yahoo Finance測試單一股票的真實資料"""
        result = {
            'code': stock['code'],
            'name': stock['name'],
            'weight': stock['weight'],
            'industry': stock['industry'],
            'success': False,
            'data_source': 'Yahoo Finance',
            'tests': {}
        }
        
        try:
            # Yahoo Finance股票代碼 (台股格式: XXXX.TW)
            yahoo_symbol = f"{stock['code']}.TW"
            print(f"      🔍 查詢Yahoo Finance: {yahoo_symbol}")
            
            # 擷取股票資料
            ticker = yf.Ticker(yahoo_symbol)
            
            # 測試1: 基本資料查詢
            basic_result = await self.get_yahoo_basic_info(ticker, stock['code'])
            result['tests']['basic_info'] = basic_result['success']
            if basic_result['success']:
                result['basic_info'] = basic_result['data']
            
            # 測試2: 歷史價格資料
            price_result = await self.get_yahoo_price_data(ticker, stock['code'])
            result['tests']['price_data'] = price_result['success']
            if price_result['success']:
                result['price_data'] = price_result['data']
            
            # 測試3: 財務資料查詢
            financial_result = await self.get_yahoo_financial_data(ticker, stock['code'])
            result['tests']['financial_data'] = financial_result['success']
            if financial_result['success']:
                result['financial_data'] = financial_result['data']
            
            # 整合Yahoo Finance數據
            yahoo_data = {}
            if basic_result['success']:
                yahoo_data.update(basic_result['data'])
            if price_result['success']:
                yahoo_data.update(price_result['data'])
            if financial_result['success']:
                yahoo_data.update(financial_result['data'])
            
            if yahoo_data:
                result['yahoo_data'] = yahoo_data
            
            # 整體成功判定
            successful_tests = sum(1 for test in result['tests'].values() if test)
            result['success'] = successful_tests >= 2  # 至少兩項測試成功
            result['success_rate'] = successful_tests / len(result['tests'])
            
        except Exception as e:
            result['error'] = str(e)
            print(f"      ❌ Yahoo Finance查詢失敗: {e}")
        
        return result
    
    async def get_yahoo_basic_info(self, ticker, stock_code: str) -> Dict[str, Any]:
        """取得Yahoo Finance基本資料"""
        try:
            info = ticker.info
            
            if not info or 'symbol' not in info:
                return {"success": False, "error": "無法取得基本資料"}
            
            # 提取關鍵資料
            basic_data = {
                "current_price": info.get('regularMarketPrice', info.get('currentPrice', 0)),
                "market_cap_twd": info.get('marketCap', 0),
                "pe_ratio": info.get('trailingPE', 0),
                "forward_pe": info.get('forwardPE', 0),
                "dividend_yield": f"{info.get('dividendYield', 0) * 100:.2f}%" if info.get('dividendYield') else "N/A",
                "beta": info.get('beta', 0),
                "company_name": info.get('longName', info.get('shortName', '')),
                "sector": info.get('sector', ''),
                "industry_yahoo": info.get('industry', ''),
                "employees": info.get('fullTimeEmployees', 0),
                "website": info.get('website', ''),
                "business_summary": info.get('longBusinessSummary', '')[:200] + "..." if info.get('longBusinessSummary') else ""
            }
            
            print(f"         📈 股價: {basic_data['current_price']:.2f} TWD")
            
            return {"success": True, "data": basic_data}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_yahoo_price_data(self, ticker, stock_code: str) -> Dict[str, Any]:
        """取得Yahoo Finance價格資料"""
        try:
            # 取得近30天歷史資料
            hist = ticker.history(period="1mo")
            
            if hist.empty:
                return {"success": False, "error": "無法取得價格歷史資料"}
            
            # 計算統計數據
            latest_close = hist['Close'].iloc[-1]
            volume_avg = hist['Volume'].mean()
            high_52w = hist['High'].max()
            low_52w = hist['Low'].min()
            
            # 計算波動率 (30天)
            returns = hist['Close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252)  # 年化波動率
            
            price_data = {
                "latest_close": latest_close,
                "volume": hist['Volume'].iloc[-1],
                "volume_avg_30d": volume_avg,
                "high_30d": hist['High'].max(),
                "low_30d": hist['Low'].min(),
                "high_52w": high_52w,
                "low_52w": low_52w,
                "volatility_30d": volatility,
                "change_30d_pct": ((latest_close - hist['Close'].iloc[0]) / hist['Close'].iloc[0] * 100) if len(hist) > 1 else 0,
                "trading_days": len(hist)
            }
            
            print(f"         📊 30天均量: {volume_avg/1000:.0f}K 張")
            
            return {"success": True, "data": price_data}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_yahoo_financial_data(self, ticker, stock_code: str) -> Dict[str, Any]:
        """取得Yahoo Finance財務資料"""
        try:
            # 取得財務報表
            financials = ticker.financials
            balance_sheet = ticker.balance_sheet
            cashflow = ticker.cashflow
            
            financial_data = {}
            
            # 損益表數據 (最新年度)
            if not financials.empty:
                latest_financials = financials.iloc[:, 0]  # 最新一期
                financial_data.update({
                    "total_revenue": latest_financials.get('Total Revenue', 0),
                    "gross_profit": latest_financials.get('Gross Profit', 0),
                    "operating_income": latest_financials.get('Operating Income', 0),
                    "net_income": latest_financials.get('Net Income', 0),
                    "ebitda": latest_financials.get('EBITDA', 0)
                })
            
            # 資產負債表數據
            if not balance_sheet.empty:
                latest_balance = balance_sheet.iloc[:, 0]
                financial_data.update({
                    "total_assets": latest_balance.get('Total Assets', 0),
                    "total_liabilities": latest_balance.get('Total Liab', 0),
                    "stockholder_equity": latest_balance.get('Stockholders Equity', 0),
                    "cash_and_equivalents": latest_balance.get('Cash And Cash Equivalents', 0)
                })
            
            # 現金流量表數據
            if not cashflow.empty:
                latest_cashflow = cashflow.iloc[:, 0]
                financial_data.update({
                    "operating_cash_flow": latest_cashflow.get('Operating Cash Flow', 0),
                    "free_cash_flow": latest_cashflow.get('Free Cash Flow', 0),
                    "capital_expenditures": latest_cashflow.get('Capital Expenditures', 0)
                })
            
            # 計算財務比率
            if financial_data.get('total_assets', 0) > 0 and financial_data.get('stockholder_equity', 0) > 0:
                financial_data['roe'] = (financial_data.get('net_income', 0) / financial_data.get('stockholder_equity', 1)) * 100
                financial_data['roa'] = (financial_data.get('net_income', 0) / financial_data.get('total_assets', 1)) * 100
                financial_data['debt_ratio'] = (financial_data.get('total_liabilities', 0) / financial_data.get('total_assets', 1)) * 100
            
            if financial_data.get('total_revenue', 0) > 0:
                financial_data['net_margin'] = (financial_data.get('net_income', 0) / financial_data.get('total_revenue', 1)) * 100
                financial_data['gross_margin'] = (financial_data.get('gross_profit', 0) / financial_data.get('total_revenue', 1)) * 100
            
            print(f"         💰 營收: {financial_data.get('total_revenue', 0)/1e9:.1f}B")
            
            return {"success": True, "data": financial_data}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def generate_yahoo_analysis_report(self):
        """生成Yahoo Finance整合分析報告"""
        print(f"\n📊 生成0050成分股Yahoo Finance整合分析報告...")
        
        # 統計測試結果
        total_stocks = len(self.test_results)
        successful_stocks = sum(1 for result in self.test_results.values() if result['success'])
        
        print(f"\n📈 Yahoo Finance整合測試結果統計:")
        print(f"   - 測試股票數量: {total_stocks}")
        print(f"   - 成功取得資料: {successful_stocks}")
        print(f"   - 整體成功率: {successful_stocks/total_stocks*100:.1f}%")
        
        # 市值分析
        market_caps = []
        for result in self.test_results.values():
            if result['success'] and 'yahoo_data' in result:
                market_cap = result['yahoo_data'].get('market_cap_twd', 0)
                if market_cap > 0:
                    market_caps.append(market_cap / 1e8)  # 轉億元
        
        if market_caps:
            print(f"\n💰 市值分析 (依Yahoo Finance數據):")
            print(f"   - 平均市值: {np.mean(market_caps):.0f} 億元")
            print(f"   - 總市值: {sum(market_caps):.0f} 億元")
            print(f"   - 市值中位數: {np.median(market_caps):.0f} 億元")
            print(f"   - 最大市值: {max(market_caps):.0f} 億元")
            print(f"   - 最小市值: {min(market_caps):.0f} 億元")
        
        # 產業別統計
        industry_stats = {}
        industry_performance = {}
        
        for result in self.test_results.values():
            industry = result['industry']
            if industry not in industry_stats:
                industry_stats[industry] = {'count': 0, 'success': 0}
                industry_performance[industry] = {'market_caps': [], 'pe_ratios': []}
            
            industry_stats[industry]['count'] += 1
            if result['success']:
                industry_stats[industry]['success'] += 1
                
                # 收集產業績效數據
                if 'yahoo_data' in result:
                    data = result['yahoo_data']
                    if data.get('market_cap_twd', 0) > 0:
                        industry_performance[industry]['market_caps'].append(data['market_cap_twd'] / 1e8)
                    if data.get('pe_ratio', 0) > 0:
                        industry_performance[industry]['pe_ratios'].append(data['pe_ratio'])
        
        print(f"\n🏭 產業別Yahoo Finance資料取得結果:")
        for industry, stats in industry_stats.items():
            success_rate = stats['success'] / stats['count'] * 100
            avg_market_cap = np.mean(industry_performance[industry]['market_caps']) if industry_performance[industry]['market_caps'] else 0
            avg_pe = np.mean(industry_performance[industry]['pe_ratios']) if industry_performance[industry]['pe_ratios'] else 0
            
            print(f"   - {industry:10s}: {stats['success']}/{stats['count']} ({success_rate:.1f}%) "
                  f"| 平均市值: {avg_market_cap:.0f}億 | 平均PE: {avg_pe:.1f}")
        
        # 權重與市值相關性分析
        weight_market_cap_data = []
        for result in self.test_results.values():
            if result['success'] and 'yahoo_data' in result:
                weight = result['weight']
                market_cap = result['yahoo_data'].get('market_cap_twd', 0) / 1e8
                if market_cap > 0:
                    weight_market_cap_data.append((weight, market_cap))
        
        if len(weight_market_cap_data) > 2:
            weights, caps = zip(*weight_market_cap_data)
            correlation = np.corrcoef(weights, caps)[0, 1]
            print(f"\n📊 權重與市值相關性分析:")
            print(f"   - 相關係數: {correlation:.3f}")
            print(f"   - 相關性解釋: {'強正相關' if correlation > 0.7 else '中等相關' if correlation > 0.3 else '弱相關'}")
        
        # 儲存詳細結果
        report_data = {
            'test_date': datetime.now().isoformat(),
            'data_source': 'Yahoo Finance API',
            'etf_info': {
                'name': '元大台灣卓越50證券投資信託基金',
                'code': '0050',
                'test_scope': '前十大持股成分股 (真實市場數據)'
            },
            'summary': {
                'total_stocks': total_stocks,
                'successful_stocks': successful_stocks,
                'success_rate': successful_stocks/total_stocks,
                'avg_market_cap_billion': np.mean(market_caps) if market_caps else 0,
                'total_market_cap_billion': sum(market_caps) if market_caps else 0,
                'weight_market_cap_correlation': correlation if 'correlation' in locals() else None
            },
            'detailed_results': self.test_results,
            'industry_analysis': industry_stats,
            'industry_performance': {
                industry: {
                    'avg_market_cap_billion': np.mean(perf['market_caps']) if perf['market_caps'] else 0,
                    'avg_pe_ratio': np.mean(perf['pe_ratios']) if perf['pe_ratios'] else 0,
                    'count': len(perf['market_caps'])
                } for industry, perf in industry_performance.items()
            }
        }
        
        # 保存結果
        output_file = f"yuanta_0050_yahoo_finance_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n💾 Yahoo Finance整合測試結果已保存: {output_file}")
        
        # 評估與建議
        print(f"\n🎯 Yahoo Finance整合測試結論:")
        if successful_stocks >= total_stocks * 0.8:
            print(f"   ✅ Yahoo Finance整合優秀，成功取得{successful_stocks}/{total_stocks}檔股票真實數據")
        elif successful_stocks >= total_stocks * 0.6:
            print(f"   ⚠️  Yahoo Finance整合良好，建議優化{total_stocks-successful_stocks}檔股票資料取得")
        else:
            print(f"   ❌ Yahoo Finance整合需要改進，多檔股票資料取得失敗")
        
        print(f"\n💡 Yahoo Finance整合建議:")
        print(f"   - 台積電(權重59%)資料: {'✅ 成功' if self.test_results.get('2330', {}).get('success') else '❌ 需修復'}")
        print(f"   - 數據品質: 取得真實市場價格、市值、財務比率")
        print(f"   - 更新頻率: Yahoo Finance即時更新，適合動態分析")
        print(f"   - 建議加強: API錯誤處理、資料備份機制")

async def main():
    """主要執行函數"""
    tester = YahooFinanceETF0050Tester()
    
    try:
        results = await tester.run_comprehensive_test()
        return results
    except KeyboardInterrupt:
        print(f"\n⚠️  測試被用戶中斷")
        return None
    except Exception as e:
        print(f"\n❌ 測試過程發生錯誤: {e}")
        return None

if __name__ == "__main__":
    print("🚀 啟動元大0050 ETF成分股Yahoo Finance整合測試...")
    
    results = asyncio.run(main())
    
    if results:
        successful_stocks = sum(1 for result in results.values() if result['success'])
        total_stocks = len(results)
        print(f"\n🎉 Yahoo Finance整合測試完成！成功率: {successful_stocks}/{total_stocks} ({successful_stocks/total_stocks*100:.1f}%)")
    else:
        print(f"\n💥 Yahoo Finance整合測試未能完成")
        sys.exit(1)