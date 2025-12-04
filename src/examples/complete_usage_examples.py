"""
AI Agent + MCP Server 完整使用範例
===================================

展示如何使用 AI Agent 系統進行財務分析的完整工作流程。

包含:
1. 單一公司深度分析
2. 多公司比較分析
3. 投資組合檢視
4. 文件處理和分析
5. 市場監控和警報
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

from sqlalchemy.orm import Session

# 假設這些模組已經實作
from mcp_server_core import MCPServer
from ai_agent_coordinator import FinancialAnalystAgent, AgentRole
from src.core.database import get_db


# ============================================================================
# 場景 1: 深度分析單一公司 (台積電)
# ============================================================================

async def scenario_1_deep_dive_analysis():
    """
    場景: 投資者想深入了解台積電(2330)
    
    工作流程:
    1. 計算財務比率 (30+指標)
    2. 評估風險等級 (Altman Z-Score)
    3. DCF估值
    4. 同業比較
    5. 生成綜合報告
    """
    
    print("=" * 80)
    print("場景 1: 台積電深度分析")
    print("=" * 80)
    
    # 初始化
    db = next(get_db())
    mcp_server = MCPServer(db_session=db)
    agent = FinancialAnalystAgent(
        anthropic_api_key="your-api-key",
        mcp_server=mcp_server,
        role=AgentRole.FINANCIAL_ANALYST
    )
    
    # 使用者查詢
    user_query = """
    我正在考慮投資台積電(2330)，請幫我做一份完整的投資分析報告，包括:
    1. 公司財務健康度評估
    2. 風險分析 (特別關注財務風險和營運風險)
    3. 內在價值估算 (使用DCF模型)
    4. 與聯發科、聯電的比較
    5. 明確的買入/持有/賣出建議
    
    我的風險承受度為中等，投資期限為3-5年。
    """
    
    # 執行分析
    result = await agent.analyze(
        user_query=user_query,
        company_id="2330",
        context={
            "risk_tolerance": "medium",
            "investment_horizon_years": 3
        }
    )
    
    # 顯示結果
    print(f"\n任務ID: {result['task_id']}")
    print(f"執行時間: {result['metadata']['timestamp']}")
    print(f"\n執行的工具 ({len(result['metadata']['tools_executed'])} 個):")
    for tool in result['metadata']['tools_executed']:
        print(f"  ✓ {tool}")
    
    print(f"\n\n{'=' * 80}")
    print("AI 分析報告")
    print("=" * 80)
    print(result['final_answer'])
    
    # 儲存報告
    with open(f"/tmp/tsmc_analysis_{result['task_id']}.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n完整報告已儲存至: /tmp/tsmc_analysis_{result['task_id']}.json")


# ============================================================================
# 場景 2: 多公司比較 (半導體三雄)
# ============================================================================

async def scenario_2_multi_company_comparison():
    """
    場景: 比較台積電、聯發科、聯電三家半導體公司
    
    工作流程:
    1. 批次擷取三家公司的財務數據
    2. 並行計算財務比率
    3. 生成比較矩陣
    4. AI 提供投資排序建議
    """
    
    print("\n" + "=" * 80)
    print("場景 2: 半導體三雄比較分析")
    print("=" * 80)
    
    db = next(get_db())
    mcp_server = MCPServer(db_session=db, max_concurrent_tools=10)
    agent = FinancialAnalystAgent(
        anthropic_api_key="your-api-key",
        mcp_server=mcp_server
    )
    
    companies = [
        {"id": "2330", "name": "台積電"},
        {"id": "2454", "name": "聯發科"},
        {"id": "2303", "name": "聯電"}
    ]
    
    user_query = f"""
    請比較以下三家半導體公司:
    - 台積電 (2330)
    - 聯發科 (2454)
    - 聯電 (2303)
    
    比較維度:
    1. 獲利能力 (ROE, ROA, 淨利率)
    2. 成長性 (營收成長率, EPS成長率)
    3. 估值水準 (PE, PB, EV/EBITDA)
    4. 財務穩健度 (負債比率, 流動比率)
    5. 風險等級 (Altman Z-Score)
    
    最後請給出投資排序建議 (1st, 2nd, 3rd)。
    """
    
    # 並行分析三家公司
    print("\n正在並行分析三家公司...")
    
    # 方法1: 使用 Agent 自動規劃
    result = await agent.analyze(
        user_query=user_query,
        context={"companies": companies}
    )
    
    print(f"\n\n{'=' * 80}")
    print("比較分析報告")
    print("=" * 80)
    print(result['final_answer'])


# ============================================================================
# 場景 3: 投資組合健康檢查
# ============================================================================

async def scenario_3_portfolio_health_check():
    """
    場景: 檢視現有投資組合的健康度
    
    投資組合:
    - 台積電 (2330): 40%
    - 聯發科 (2454): 30%
    - 鴻海 (2317): 20%
    - 現金: 10%
    
    工作流程:
    1. 批次風險評估
    2. 檢查是否有高風險公司
    3. 計算組合整體風險
    4. 提供再平衡建議
    """
    
    print("\n" + "=" * 80)
    print("場景 3: 投資組合健康檢查")
    print("=" * 80)
    
    db = next(get_db())
    mcp_server = MCPServer(db_session=db)
    agent = FinancialAnalystAgent(
        anthropic_api_key="your-api-key",
        mcp_server=mcp_server,
        role=AgentRole.PORTFOLIO_ADVISOR
    )
    
    portfolio = [
        {"company_id": "2330", "name": "台積電", "weight": 0.40, "shares": 100},
        {"company_id": "2454", "name": "聯發科", "weight": 0.30, "shares": 50},
        {"company_id": "2317", "name": "鴻海", "weight": 0.20, "shares": 200},
        {"asset": "cash", "weight": 0.10, "amount": 100000}
    ]
    
    user_query = f"""
    請檢查我的投資組合健康度:
    
    {json.dumps(portfolio, indent=2, ensure_ascii=False)}
    
    請評估:
    1. 每家公司的當前風險等級
    2. 組合整體風險是否過高
    3. 是否有公司出現財務惡化跡象
    4. 資產配置是否需要調整
    5. 具體的再平衡建議
    
    我的風險承受度為中等偏保守。
    """
    
    result = await agent.analyze(
        user_query=user_query,
        context={"portfolio": portfolio, "risk_tolerance": "medium_conservative"}
    )
    
    print(f"\n\n{'=' * 80}")
    print("投資組合健康檢查報告")
    print("=" * 80)
    print(result['final_answer'])


# ============================================================================
# 場景 4: 文件分析 (財報PDF)
# ============================================================================

async def scenario_4_document_analysis():
    """
    場景: 上傳台積電2023年年報PDF，提取關鍵數據並分析
    
    工作流程:
    1. 使用 document_processor 工具處理PDF
    2. 提取財務報表和關鍵數字
    3. 與資料庫中的數據比對
    4. 分析差異和趨勢
    5. 生成文件分析報告
    """
    
    print("\n" + "=" * 80)
    print("場景 4: 財報文件分析")
    print("=" * 80)
    
    db = next(get_db())
    mcp_server = MCPServer(db_session=db)
    agent = FinancialAnalystAgent(
        anthropic_api_key="your-api-key",
        mcp_server=mcp_server,
        role=AgentRole.FINANCIAL_ANALYST
    )
    
    user_query = """
    我上傳了台積電2023年度的年報PDF檔案，請幫我:
    
    1. 提取主要財務數據:
       - 資產負債表
       - 綜合損益表
       - 現金流量表
    
    2. 分析關鍵指標變化:
       - 營收成長率
       - 毛利率變化
       - 淨利率變化
       - ROE變化
    
    3. 識別重大事項:
       - 重大投資計畫
       - 風險因素揭露
       - 管理層展望
    
    4. 與前一年度比較，指出需要關注的項目
    """
    
    # 模擬PDF檔案路徑
    pdf_file_path = "/tmp/TSMC_2023_Annual_Report.pdf"
    
    result = await agent.analyze(
        user_query=user_query,
        company_id="2330",
        context={
            "document_type": "pdf",
            "document_path": pdf_file_path,
            "fiscal_year": 2023
        }
    )
    
    print(f"\n\n{'=' * 80}")
    print("文件分析報告")
    print("=" * 80)
    print(result['final_answer'])


# ============================================================================
# 場景 5: 市場監控和警報
# ============================================================================

async def scenario_5_market_monitoring():
    """
    場景: 監控關注清單中的公司，偵測異常事件
    
    關注清單:
    - 台積電 (2330)
    - 聯發科 (2454)
    - 鴻海 (2317)
    - 大立光 (3008)
    - 台達電 (2308)
    
    監控項目:
    - 股價異常波動 (±10%)
    - 財務指標惡化
    - 重大新聞事件
    - 風險等級變化
    """
    
    print("\n" + "=" * 80)
    print("場景 5: 市場監控與警報")
    print("=" * 80)
    
    db = next(get_db())
    mcp_server = MCPServer(db_session=db)
    agent = FinancialAnalystAgent(
        anthropic_api_key="your-api-key",
        mcp_server=mcp_server,
        role=AgentRole.RISK_MANAGER
    )
    
    watchlist = ["2330", "2454", "2317", "3008", "2308"]
    
    user_query = f"""
    請監控以下公司在過去7天的異常狀況:
    
    關注清單: {', '.join(watchlist)}
    
    監控項目:
    1. 股價異常波動 (單日漲跌幅 > 5%)
    2. 財務比率惡化 (流動比率下降 > 10%)
    3. 風險等級上升
    4. 重大新聞事件 (財報公告、法說會、重大交易等)
    
    請按嚴重程度排序，並對需要立即關注的公司標記 🚨。
    """
    
    result = await agent.analyze(
        user_query=user_query,
        context={
            "watchlist": watchlist,
            "lookback_days": 7,
            "alert_thresholds": {
                "price_change_pct": 5.0,
                "liquidity_ratio_decline_pct": 10.0
            }
        }
    )
    
    print(f"\n\n{'=' * 80}")
    print("市場監控報告")
    print("=" * 80)
    print(result['final_answer'])


# ============================================================================
# 場景 6: 對話式互動 (多輪問答)
# ============================================================================

async def scenario_6_conversational_analysis():
    """
    場景: 與AI進行多輪對話式分析
    
    模擬投資者與AI財務分析師的對話過程
    """
    
    print("\n" + "=" * 80)
    print("場景 6: 對話式互動分析")
    print("=" * 80)
    
    db = next(get_db())
    mcp_server = MCPServer(db_session=db)
    agent = FinancialAnalystAgent(
        anthropic_api_key="your-api-key",
        mcp_server=mcp_server
    )
    
    conversation = [
        "台積電的股價最近下跌了10%，這是買入機會嗎?",
        "它的主要風險是什麼?",
        "跟三星相比，台積電的技術領先優勢有多大?",
        "如果我現在買入100股，持有5年，預期報酬率是多少?",
        "有其他更好的投資標的嗎?"
    ]
    
    for i, query in enumerate(conversation, 1):
        print(f"\n{'─' * 80}")
        print(f"第 {i} 輪對話")
        print(f"{'─' * 80}")
        print(f"👤 使用者: {query}")
        
        result = await agent.analyze(
            user_query=query,
            company_id="2330"
        )
        
        print(f"\n🤖 AI 分析師:\n{result['final_answer']}")
        
        # 模擬思考時間
        await asyncio.sleep(1)


# ============================================================================
# 效能測試
# ============================================================================

async def performance_benchmark():
    """
    效能基準測試
    
    測試項目:
    1. 單一工具執行時間
    2. 多工具並行執行時間
    3. 完整分析流程端到端時間
    """
    
    print("\n" + "=" * 80)
    print("效能基準測試")
    print("=" * 80)
    
    db = next(get_db())
    mcp_server = MCPServer(db_session=db)
    
    # 測試1: 單一工具執行時間
    print("\n測試 1: 單一工具執行時間")
    print("-" * 80)
    
    test_cases = [
        ("calculate_financial_ratios", {"company_id": "2330", "period": "latest"}),
        ("assess_company_risk", {"company_id": "2330"}),
        ("perform_dcf_valuation", {
            "company_id": "2330",
            "revenue_growth_rates": [0.10, 0.10, 0.08],
            "terminal_growth_rate": 0.03
        })
    ]
    
    for tool_name, input_data in test_cases:
        start = datetime.now()
        response = await mcp_server.execute_tool(tool_name, input_data)
        elapsed = (datetime.now() - start).total_seconds() * 1000
        
        status = "✓" if response.success else "✗"
        print(f"{status} {tool_name}: {elapsed:.2f}ms")
    
    # 測試2: 並行執行
    print("\n測試 2: 並行執行 (3個工具)")
    print("-" * 80)
    
    start = datetime.now()
    responses = await mcp_server.execute_multiple_tools([
        {"tool_name": name, "input_data": data}
        for name, data in test_cases
    ])
    elapsed = (datetime.now() - start).total_seconds() * 1000
    
    successful = sum(1 for r in responses if r.success)
    print(f"成功執行: {successful}/{len(test_cases)}")
    print(f"總耗時: {elapsed:.2f}ms")
    print(f"平均耗時: {elapsed/len(test_cases):.2f}ms")
    
    # 測試3: 完整分析流程
    print("\n測試 3: 完整分析流程 (端到端)")
    print("-" * 80)
    
    agent = FinancialAnalystAgent(
        anthropic_api_key="your-api-key",
        mcp_server=mcp_server
    )
    
    start = datetime.now()
    result = await agent.analyze(
        user_query="分析台積電的投資價值",
        company_id="2330"
    )
    elapsed = (datetime.now() - start).total_seconds()
    
    print(f"任務ID: {result['task_id']}")
    print(f"執行工具數: {len(result['metadata']['tools_executed'])}")
    print(f"總耗時: {elapsed:.2f}秒")


# ============================================================================
# 主程式
# ============================================================================

async def main():
    """執行所有場景"""
    
    print("\n" + "=" * 80)
    print("AI Agent + MCP Server 完整示範")
    print("=" * 80)
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    scenarios = [
        ("場景 1: 深度分析單一公司", scenario_1_deep_dive_analysis),
        ("場景 2: 多公司比較", scenario_2_multi_company_comparison),
        ("場景 3: 投資組合健康檢查", scenario_3_portfolio_health_check),
        ("場景 4: 文件分析", scenario_4_document_analysis),
        ("場景 5: 市場監控", scenario_5_market_monitoring),
        ("場景 6: 對話式互動", scenario_6_conversational_analysis),
        ("效能測試", performance_benchmark)
    ]
    
    print("\n可用場景:")
    for i, (name, _) in enumerate(scenarios, 1):
        print(f"{i}. {name}")
    
    print("\n選擇要執行的場景 (輸入數字，或按Enter執行全部):")
    choice = input().strip()
    
    if choice == "":
        # 執行所有場景
        for name, scenario_func in scenarios:
            try:
                await scenario_func()
                await asyncio.sleep(2)  # 場景之間暫停
            except Exception as e:
                print(f"\n❌ {name} 執行失敗: {str(e)}")
    else:
        # 執行指定場景
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(scenarios):
                name, scenario_func = scenarios[idx]
                await scenario_func()
            else:
                print("無效的選擇")
        except ValueError:
            print("請輸入有效的數字")
    
    print("\n" + "=" * 80)
    print("示範完成!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
