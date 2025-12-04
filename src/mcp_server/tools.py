"""
MCP Server 財務分析工具定義
==========================

遵循 Model Context Protocol 規範，定義8個核心工具供AI Agent使用。

工具設計原則:
1. 單一職責 (每個工具專注一個任務)
2. 輸入輸出標準化 (JSON格式)
3. 錯誤處理完整 (返回結構化錯誤)
4. 可觀測性 (日誌記錄所有調用)
"""

from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime, date
from enum import Enum
import json


# ============================================================================
# 工具輸入/輸出模型定義
# ============================================================================

class ToolResponse(BaseModel):
    """標準工具響應格式"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"result": "calculation completed"},
                "error": None,
                "metadata": {
                    "execution_time_ms": 145,
                    "tool_version": "1.0.0"
                }
            }
        }


# ============================================================================
# 工具 1: 財務比率計算器
# ============================================================================

class FinancialRatiosInput(BaseModel):
    """財務比率計算輸入"""
    company_id: str = Field(
        ..., 
        description="公司股票代號(4碼)",
        pattern=r"^\d{4}$",
        examples=["2330", "2317"]
    )
    period: Literal["latest", "annual", "quarterly"] = Field(
        default="latest",
        description="計算期間: latest(最新一期), annual(年度), quarterly(季度)"
    )
    ratio_categories: Optional[List[str]] = Field(
        default=None,
        description="指定計算類別: liquidity, profitability, efficiency, leverage, cash_flow。若為None則計算全部"
    )


class FinancialRatiosOutput(BaseModel):
    """財務比率計算輸出"""
    company_id: str
    company_name: str
    period: str
    period_date: date
    
    # 財務結構 (4個指標)
    financial_structure: Dict[str, float] = Field(
        description="負債比率、權益比率、長期資金比率等"
    )
    
    # 流動性指標 (4個指標)
    liquidity_ratios: Dict[str, float] = Field(
        description="流動比率、速動比率、現金比率、利息保障倍數"
    )
    
    # 效率指標 (6個指標)
    efficiency_ratios: Dict[str, float] = Field(
        description="總資產週轉率、應收帳款週轉率、存貨週轉率等"
    )
    
    # 獲利能力 (9個指標)
    profitability_ratios: Dict[str, float] = Field(
        description="ROA, ROE, ROE, 毛利率, 營業利益率, 淨利率等"
    )
    
    # 現金流量 (5個指標)
    cash_flow_ratios: Dict[str, float] = Field(
        description="營業現金流量比率、自由現金流量等"
    )
    
    # 綜合評分
    financial_health_score: float = Field(
        ge=0, le=100,
        description="財務健康綜合評分 (0-100分)"
    )
    
    rating: Literal["Excellent", "Good", "Average", "Below Average", "Poor"]


# ============================================================================
# 工具 2: DCF估值模型
# ============================================================================

class DCFValuationInput(BaseModel):
    """DCF估值輸入"""
    company_id: str = Field(..., pattern=r"^\d{4}$")
    
    # 預測參數
    revenue_growth_rates: List[float] = Field(
        ...,
        min_items=3,
        max_items=10,
        description="未來3-10年的收入成長率預測 (小數形式, 例如0.15代表15%)"
    )
    
    # 終值參數
    terminal_growth_rate: float = Field(
        ...,
        ge=0,
        le=0.10,
        description="永續成長率 (0-10%)"
    )
    
    # 折現率
    discount_rate: Optional[float] = Field(
        default=None,
        ge=0.01,
        le=0.30,
        description="折現率(WACC)，若為None則自動計算"
    )
    
    # 情境分析
    perform_sensitivity_analysis: bool = Field(
        default=True,
        description="是否執行敏感性分析"
    )
    
    @validator("revenue_growth_rates")
    def validate_growth_rates(cls, v):
        if any(rate < -0.50 or rate > 2.0 for rate in v):
            raise ValueError("收入成長率必須介於-50%到200%之間")
        return v


class DCFValuationOutput(BaseModel):
    """DCF估值輸出"""
    company_id: str
    company_name: str
    valuation_date: datetime
    
    # 估值結果
    enterprise_value: float = Field(description="企業價值 (億元)")
    equity_value: float = Field(description="權益價值 (億元)")
    fair_value_per_share: float = Field(description="每股公允價值 (元)")
    
    # 當前市場資訊
    current_market_price: float = Field(description="當前市價 (元)")
    current_market_cap: float = Field(description="當前市值 (億元)")
    
    # 投資建議
    upside_downside_percentage: float = Field(
        description="上漲/下跌空間 (%)"
    )
    investment_recommendation: Literal[
        "強力買入", "買入", "持有", "賣出", "強力賣出"
    ]
    
    # 估值明細
    valuation_details: Dict[str, Any] = Field(
        description="包含自由現金流量預測、終值計算、折現率細節等"
    )
    
    # 敏感性分析 (可選)
    sensitivity_analysis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="折現率和成長率的敏感性矩陣"
    )


# ============================================================================
# 工具 3: 風險評估引擎
# ============================================================================

class RiskAssessmentInput(BaseModel):
    """風險評估輸入"""
    company_id: str = Field(..., pattern=r"^\d{4}$")
    
    assessment_scope: List[str] = Field(
        default=["all"],
        description="評估範圍: all, financial_distress, liquidity, profitability, leverage, operational"
    )
    
    include_industry_comparison: bool = Field(
        default=True,
        description="是否包含產業比較"
    )


class RiskLevel(str, Enum):
    """風險等級"""
    LOW = "低風險"
    MEDIUM = "中等風險"
    HIGH = "高風險"
    CRITICAL = "極高風險"


class RiskAssessmentOutput(BaseModel):
    """風險評估輸出"""
    company_id: str
    company_name: str
    assessment_date: datetime
    
    # 綜合風險評分
    overall_risk_score: float = Field(
        ge=0, le=100,
        description="綜合風險評分 (0-100, 越高越安全)"
    )
    overall_risk_level: RiskLevel
    risk_grade: Literal["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "CC", "C", "D"]
    
    # 子風險評估
    risk_breakdown: Dict[str, Dict[str, Any]] = Field(
        description="各項風險的詳細評估"
    )
    
    # Altman Z-Score (破產預測)
    altman_z_score: float = Field(description="Altman Z-Score")
    bankruptcy_probability: float = Field(
        ge=0, le=1,
        description="破產機率 (0-1)"
    )
    
    # 關鍵風險警示
    key_concerns: List[str] = Field(
        description="需要關注的關鍵風險事項"
    )
    
    # 風險趨勢
    risk_trend: Literal["improving", "stable", "deteriorating"] = Field(
        description="風險趨勢: improving(改善中), stable(穩定), deteriorating(惡化中)"
    )
    
    # 產業比較 (可選)
    industry_comparison: Optional[Dict[str, Any]] = Field(
        default=None,
        description="與同業的風險比較"
    )
    
    # 改善建議
    recommendations: List[str] = Field(
        description="風險改善建議"
    )


# ============================================================================
# 工具 4: 同業比較分析
# ============================================================================

class PeerComparisonInput(BaseModel):
    """同業比較輸入"""
    company_id: str = Field(..., pattern=r"^\d{4}$")
    
    peer_selection_method: Literal["auto", "manual"] = Field(
        default="auto",
        description="同業選擇方式: auto(自動選取), manual(手動指定)"
    )
    
    manual_peer_ids: Optional[List[str]] = Field(
        default=None,
        description="手動指定的同業公司代號列表"
    )
    
    comparison_metrics: List[str] = Field(
        default=["valuation", "profitability", "efficiency", "growth"],
        description="比較指標類別"
    )
    
    num_peers: int = Field(
        default=5,
        ge=3,
        le=10,
        description="比較同業數量 (3-10家)"
    )


class PeerComparisonOutput(BaseModel):
    """同業比較輸出"""
    company_id: str
    company_name: str
    industry: str
    comparison_date: datetime
    
    # 同業列表
    peers: List[Dict[str, Any]] = Field(
        description="同業公司列表及其關鍵指標"
    )
    
    # 相對排名
    rankings: Dict[str, int] = Field(
        description="在各項指標中的排名 (1=最佳)"
    )
    
    # 綜合評分
    composite_score: float = Field(
        ge=0, le=100,
        description="相對同業的綜合評分 (0-100)"
    )
    
    performance_rating: Literal[
        "Excellent", "Above Average", "Average", "Below Average", "Poor"
    ]
    
    # 比較分析
    comparison_analysis: Dict[str, Any] = Field(
        description="詳細的比較分析，包含估值倍數、獲利能力等"
    )
    
    # SWOT分析
    swot_analysis: Dict[str, List[str]] = Field(
        description="基於同業比較的SWOT分析"
    )
    
    # 相對估值
    relative_valuation: Dict[str, Any] = Field(
        description="相對估值分析 (PE, PB, PS等)"
    )


# ============================================================================
# 工具 5: 資料擷取器
# ============================================================================

class DataFetcherInput(BaseModel):
    """資料擷取輸入"""
    company_id: str = Field(..., pattern=r"^\d{4}$")
    
    data_types: List[str] = Field(
        ...,
        description="需要擷取的資料類型: financials, ratios, prices, news, announcements"
    )
    
    start_date: Optional[date] = Field(
        default=None,
        description="起始日期 (用於歷史資料)"
    )
    
    end_date: Optional[date] = Field(
        default=None,
        description="結束日期"
    )
    
    include_metadata: bool = Field(
        default=True,
        description="是否包含資料來源等元數據"
    )


class DataFetcherOutput(BaseModel):
    """資料擷取輸出"""
    company_id: str
    company_name: str
    fetch_date: datetime
    
    # 擷取的資料
    fetched_data: Dict[str, Any] = Field(
        description="按data_types分類的擷取結果"
    )
    
    # 資料完整性
    data_completeness: Dict[str, float] = Field(
        description="各類資料的完整度 (0-1)"
    )
    
    # 資料來源
    data_sources: List[str] = Field(
        description="資料來源列表 (公開資訊觀測站、證交所等)"
    )
    
    # 擷取統計
    fetch_statistics: Dict[str, Any] = Field(
        description="擷取統計資訊 (成功/失敗數量、回應時間等)"
    )


# ============================================================================
# 工具 6: 報告生成器
# ============================================================================

class ReportGeneratorInput(BaseModel):
    """報告生成輸入"""
    company_id: str = Field(..., pattern=r"^\d{4}$")
    
    report_type: Literal[
        "comprehensive",  # 綜合分析報告
        "valuation",      # 估值報告
        "risk",          # 風險評估報告
        "peer_comparison" # 同業比較報告
    ]
    
    report_format: Literal["pdf", "excel", "json", "markdown"] = Field(
        default="pdf"
    )
    
    include_sections: List[str] = Field(
        default=["all"],
        description="包含的報告章節"
    )
    
    language: Literal["zh-TW", "zh-CN", "en"] = Field(
        default="zh-TW",
        description="報告語言"
    )
    
    custom_parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="自訂參數 (例如估值假設、比較同業等)"
    )


class ReportGeneratorOutput(BaseModel):
    """報告生成輸出"""
    report_id: str = Field(description="報告唯一識別碼")
    company_id: str
    company_name: str
    report_type: str
    generation_date: datetime
    
    # 報告內容
    report_content: Optional[str] = Field(
        default=None,
        description="報告內容 (若format為json/markdown則直接返回)"
    )
    
    # 報告檔案路徑 (若format為pdf/excel)
    report_file_path: Optional[str] = Field(
        default=None,
        description="報告檔案儲存路徑"
    )
    
    report_download_url: Optional[str] = Field(
        default=None,
        description="報告下載連結"
    )
    
    # 報告摘要
    executive_summary: str = Field(
        description="報告執行摘要 (200-500字)"
    )
    
    # 報告統計
    report_statistics: Dict[str, Any] = Field(
        description="報告統計資訊 (頁數、圖表數量、生成時間等)"
    )


# ============================================================================
# 工具 7: 文件處理器
# ============================================================================

class DocumentProcessorInput(BaseModel):
    """文件處理輸入"""
    document_type: Literal["pdf", "excel", "image"] = Field(
        ...,
        description="文件類型"
    )
    
    document_source: Literal["file_path", "url", "base64"] = Field(
        ...,
        description="文件來源方式"
    )
    
    document_data: str = Field(
        ...,
        description="文件資料 (檔案路徑、URL或base64編碼)"
    )
    
    extraction_targets: List[str] = Field(
        default=["financial_tables", "key_metrics", "text_content"],
        description="擷取目標"
    )
    
    ocr_enabled: bool = Field(
        default=True,
        description="是否啟用OCR (用於圖片和掃描PDF)"
    )


class DocumentProcessorOutput(BaseModel):
    """文件處理輸出"""
    document_id: str
    document_type: str
    processing_date: datetime
    
    # 擷取結果
    extracted_data: Dict[str, Any] = Field(
        description="擷取的結構化資料"
    )
    
    # 財務報表 (如果有)
    financial_statements: Optional[Dict[str, Any]] = Field(
        default=None,
        description="識別出的財務報表資料"
    )
    
    # 關鍵數字
    key_numbers: List[Dict[str, Any]] = Field(
        description="擷取的關鍵數字及其上下文"
    )
    
    # 文字內容
    text_content: Optional[str] = Field(
        default=None,
        description="完整文字內容"
    )
    
    # 處理統計
    processing_statistics: Dict[str, Any] = Field(
        description="處理統計 (頁數、擷取成功率、處理時間等)"
    )
    
    # 信心分數
    confidence_scores: Dict[str, float] = Field(
        description="各項擷取結果的信心分數 (0-1)"
    )


# ============================================================================
# 工具 8: 警報監控器
# ============================================================================

class AlertMonitorInput(BaseModel):
    """警報監控輸入"""
    company_ids: List[str] = Field(
        ...,
        description="監控的公司代號列表"
    )
    
    alert_types: List[str] = Field(
        default=["all"],
        description="警報類型: price_change, financial_anomaly, risk_increase, news_event"
    )
    
    alert_thresholds: Optional[Dict[str, float]] = Field(
        default=None,
        description="自訂警報閾值"
    )
    
    lookback_period_days: int = Field(
        default=7,
        ge=1,
        le=90,
        description="回溯期間 (天數)"
    )


class AlertSeverity(str, Enum):
    """警報嚴重程度"""
    INFO = "資訊"
    WARNING = "警告"
    CRITICAL = "嚴重"
    EMERGENCY = "緊急"


class AlertMonitorOutput(BaseModel):
    """警報監控輸出"""
    monitoring_date: datetime
    lookback_period_days: int
    
    # 警報列表
    alerts: List[Dict[str, Any]] = Field(
        description="偵測到的警報事件"
    )
    
    # 警報統計
    alert_summary: Dict[str, int] = Field(
        description="按嚴重程度統計的警報數量"
    )
    
    # 需要立即關注的公司
    companies_requiring_attention: List[str] = Field(
        description="需要立即關注的公司代號"
    )
    
    # 監控狀態
    monitoring_status: Dict[str, Any] = Field(
        description="各公司的監控狀態"
    )


# ============================================================================
# MCP Server 工具註冊表
# ============================================================================

class MCPTool(BaseModel):
    """MCP工具元數據"""
    name: str
    description: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    category: str
    version: str = "1.0.0"
    estimated_execution_time_ms: int = Field(
        description="預估執行時間(毫秒)"
    )


# 8個核心工具的註冊資訊
MCP_TOOLS_REGISTRY = [
    MCPTool(
        name="calculate_financial_ratios",
        description="計算公司的30+財務比率，包括流動性、獲利能力、效率、槓桿等指標。適用於快速財務健康度評估。",
        input_schema=FinancialRatiosInput,
        output_schema=FinancialRatiosOutput,
        category="financial_analysis",
        estimated_execution_time_ms=500
    ),
    MCPTool(
        name="perform_dcf_valuation",
        description="執行DCF現金流折現估值，計算公司內在價值和投資建議。支援敏感性分析。",
        input_schema=DCFValuationInput,
        output_schema=DCFValuationOutput,
        category="valuation",
        estimated_execution_time_ms=2000
    ),
    MCPTool(
        name="assess_company_risk",
        description="綜合評估公司風險，包括Altman Z-Score破產預測、流動性風險、槓桿風險等。提供風險等級和改善建議。",
        input_schema=RiskAssessmentInput,
        output_schema=RiskAssessmentOutput,
        category="risk_management",
        estimated_execution_time_ms=1500
    ),
    MCPTool(
        name="compare_with_peers",
        description="與同業公司進行多維度比較，包含估值倍數、獲利能力、成長性等。自動生成SWOT分析。",
        input_schema=PeerComparisonInput,
        output_schema=PeerComparisonOutput,
        category="comparative_analysis",
        estimated_execution_time_ms=3000
    ),
    MCPTool(
        name="fetch_company_data",
        description="從多個資料源擷取公司財務資料、股價、新聞、公告等。支援歷史資料查詢。",
        input_schema=DataFetcherInput,
        output_schema=DataFetcherOutput,
        category="data_acquisition",
        estimated_execution_time_ms=5000
    ),
    MCPTool(
        name="generate_analysis_report",
        description="生成專業的財務分析報告，支援PDF、Excel、Markdown等格式。包含圖表和執行摘要。",
        input_schema=ReportGeneratorInput,
        output_schema=ReportGeneratorOutput,
        category="reporting",
        estimated_execution_time_ms=10000
    ),
    MCPTool(
        name="process_financial_document",
        description="處理PDF、Excel、圖片等財務文件，自動擷取財務報表和關鍵數字。支援OCR。",
        input_schema=DocumentProcessorInput,
        output_schema=DocumentProcessorOutput,
        category="document_processing",
        estimated_execution_time_ms=8000
    ),
    MCPTool(
        name="monitor_company_alerts",
        description="監控公司財務異常、價格劇烈變動、風險上升等事件。提供即時警報和關注建議。",
        input_schema=AlertMonitorInput,
        output_schema=AlertMonitorOutput,
        category="monitoring",
        estimated_execution_time_ms=2000
    )
]


def get_tool_by_name(tool_name: str) -> Optional[MCPTool]:
    """根據名稱獲取工具定義"""
    for tool in MCP_TOOLS_REGISTRY:
        if tool.name == tool_name:
            return tool
    return None


def list_available_tools(category: Optional[str] = None) -> List[MCPTool]:
    """列出可用工具"""
    if category:
        return [tool for tool in MCP_TOOLS_REGISTRY if tool.category == category]
    return MCP_TOOLS_REGISTRY


def validate_tool_input(tool_name: str, input_data: Dict[str, Any]) -> bool:
    """驗證工具輸入"""
    tool = get_tool_by_name(tool_name)
    if not tool:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    try:
        tool.input_schema(**input_data)
        return True
    except Exception as e:
        raise ValueError(f"Invalid input for {tool_name}: {str(e)}")


# ============================================================================
# 使用範例
# ============================================================================

if __name__ == "__main__":
    # 範例 1: 列出所有工具
    print("=== 可用的MCP工具 ===")
    for tool in MCP_TOOLS_REGISTRY:
        print(f"\n工具名稱: {tool.name}")
        print(f"描述: {tool.description}")
        print(f"類別: {tool.category}")
        print(f"預估執行時間: {tool.estimated_execution_time_ms}ms")
    
    # 範例 2: 驗證工具輸入
    print("\n=== 工具輸入驗證範例 ===")
    
    # 正確的輸入
    valid_input = {
        "company_id": "2330",
        "period": "latest",
        "ratio_categories": ["liquidity", "profitability"]
    }
    
    try:
        validate_tool_input("calculate_financial_ratios", valid_input)
        print("✓ 輸入驗證通過")
    except ValueError as e:
        print(f"✗ 輸入驗證失敗: {e}")
    
    # 錯誤的輸入
    invalid_input = {
        "company_id": "123",  # 應為4碼
        "period": "invalid_period"
    }
    
    try:
        validate_tool_input("calculate_financial_ratios", invalid_input)
        print("✓ 輸入驗證通過")
    except ValueError as e:
        print(f"✗ 輸入驗證失敗: {e}")
    
    # 範例 3: 生成工具說明文件
    print("\n=== 工具說明文件 (JSON Schema) ===")
    tool = get_tool_by_name("calculate_financial_ratios")
    if tool:
        schema = tool.input_schema.schema()
        print(json.dumps(schema, indent=2, ensure_ascii=False))
