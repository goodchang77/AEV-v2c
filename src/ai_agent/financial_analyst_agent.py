# src/ai_agents/financial_analyst_agent.py
from typing import Dict, List
import anthropic
from src.services.risk_assessment import RiskAssessmentEngine
from src.services.valuation_models import DCFValuationModel
from src.services.peer_analysis import PeerAnalyzer

class FinancialAnalystAgent:
    """
    AI財務分析師Agent
    
    功能:
    1. 自動化財務分析
    2. 生成投資建議報告
    3. 回答財務相關問題
    4. 監控財務異常
    """
    
    def __init__(self, anthropic_api_key: str, db_session):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.db = db_session
        self.risk_engine = RiskAssessmentEngine(db_session)
        self.valuation_model = DCFValuationModel(db_session)
        self.peer_analyzer = PeerAnalyzer(db_session)
    
    async def analyze_company(self, company_id: str, user_query: str) -> Dict:
        """
        綜合公司分析
        
        使用Claude作為推理引擎，結合:
        - 風險評估結果
        - DCF估值
        - 同業比較
        - 財務比率趨勢
        """
        # 1. 收集所有分析數據
        risk_data = self.risk_engine.assess_overall_risk(company_id)
        valuation_data = self.valuation_model.calculate_enterprise_value(company_id)
        peer_data = self.peer_analyzer.analyze_peer_comparison(company_id)
        
        # 2. 構建分析提示詞
        analysis_prompt = f"""
你是一位專業的財務分析師。請基於以下數據分析公司{company_id}:

# 風險評估結果
{self._format_risk_data(risk_data)}

# DCF估值結果
{self._format_valuation_data(valuation_data)}

# 同業比較結果
{self._format_peer_data(peer_data)}

# 用戶問題
{user_query}

請提供:
1. 公司財務健康度評估(0-100分)
2. 投資建議(買入/持有/賣出)
3. 關鍵風險警示
4. 估值合理性分析
5. 與同業比較的優劣勢

請用繁體中文回答,並提供具體數據支持你的結論。
"""
        
        # 3. 調用Claude API
        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[
                {"role": "user", "content": analysis_prompt}
            ]
        )
        
        # 4. 解析AI回應並結構化輸出
        ai_analysis = message.content[0].text
        
        return {
            "company_id": company_id,
            "raw_data": {
                "risk_assessment": risk_data,
                "valuation": valuation_data,
                "peer_comparison": peer_data
            },
            "ai_analysis": ai_analysis,
            "structured_recommendation": self._parse_ai_recommendation(ai_analysis)
        }
    
    def _format_risk_data(self, data: Dict) -> str:
        """格式化風險數據為可讀文本"""
        return f"""
綜合風險分數: {data['overall_risk_score']}/100
風險等級: {data['risk_grade']}

Altman Z-Score: {data['risk_breakdown']['financial_distress']['z_score']}
流動性評分: {data['risk_breakdown']['liquidity']['liquidity_score']}/100
流動比率: {data['risk_breakdown']['liquidity']['current_ratio']}
速動比率: {data['risk_breakdown']['liquidity']['quick_ratio']}

關鍵風險:
{chr(10).join(f"- {concern}" for concern in data['key_concerns'])}
"""