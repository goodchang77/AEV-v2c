"""
API 請求模型
Request Models

定義所有API端點的請求資料結構和驗證規則
"""

from pydantic import BaseModel, field_validator, Field
from typing import List, Optional, Dict, Any
from decimal import Decimal
from enum import Enum
import re


class MarketType(str, Enum):
    """市場類型"""
    LISTED = "上市"
    OTC = "上櫃" 
    EMERGING = "興櫃"


class ReportType(str, Enum):
    """報告類型"""
    ANNUAL = "annual"
    QUARTERLY = "quarterly"


class ValuationMethod(str, Enum):
    """評價方法"""
    DCF = "DCF"
    DDM = "DDM"
    PE = "PE"
    PB = "PB"
    EV_EBITDA = "EV_EBITDA"


# ================== 公司相關請求模型 ==================

class CompanySearchRequest(BaseModel):
    """公司搜尋請求"""
    keyword: Optional[str] = Field(None, max_length=50, description="搜尋關鍵字")
    industry_code: Optional[str] = Field(None, pattern=r"^[A-Z0-9]{2,10}$", description="產業代碼")
    market_type: Optional[MarketType] = Field(None, description="市場類型")
    limit: int = Field(20, ge=1, le=100, description="返回筆數限制")
    offset: int = Field(0, ge=0, description="分頁偏移量")

    @field_validator("keyword")
    @classmethod
    def validate_keyword(cls, v):
        if v is not None and v.strip() == "":
            return None
        return v


class CompanyListRequest(BaseModel):
    """公司列表請求"""
    industry_code: Optional[str] = Field(None, pattern=r"^[A-Z0-9]{2,10}$", description="產業代碼")
    market_type: Optional[MarketType] = Field(None, description="市場類型")
    limit: int = Field(20, ge=1, le=100, description="返回筆數限制")
    offset: int = Field(0, ge=0, description="分頁偏移量")
    is_active: Optional[bool] = Field(True, description="是否活躍")
    page: int = Field(1, ge=1, description="頁碼")
    page_size: int = Field(20, ge=1, le=100, description="每頁筆數")
    sort_by: Optional[str] = Field("company_id", pattern=r"^[a-z_]+$")
    sort_order: str = Field("asc", pattern=r"^(asc|desc)$")


# ================== 財務分析請求模型 ==================

class FinancialRatiosRequest(BaseModel):
    """財務比率請求"""
    company_id: str = Field(..., pattern=r"^\d{4}$", description="4位數公司代碼")
    year_quarter: Optional[str] = Field(None, pattern=r"^20\d{2}Q[1-4]$", description="年季別，如2024Q1")
    include_trend: bool = Field(False, description="是否包含趨勢資料")
    periods: int = Field(8, ge=1, le=20, description="趨勢分析期數")

    @field_validator("company_id")
    @classmethod
    def validate_company_id(cls, v):
        if not v.isdigit() or len(v) != 4:
            raise ValueError("公司代碼必須為4位數字")
        return v


class FinancialHealthRequest(BaseModel):
    """財務健康度評估請求"""
    company_id: str = Field(..., pattern=r"^\d{4}$")
    analysis_period: Optional[str] = Field(None, pattern=r"^20\d{2}Q[1-4]$")
    include_details: bool = Field(True, description="是否包含詳細評估")
    benchmark_comparison: bool = Field(True, description="是否進行基準比較")


# ================== DCF評價請求模型 ==================

class DCFValuationRequest(BaseModel):
    """DCF評價請求"""
    company_id: str = Field(..., pattern=r"^\d{4}$", description="公司代碼")
    
    # 基本參數
    base_revenue: Optional[Decimal] = Field(None, gt=0, description="基期營收")
    forecast_years: int = Field(5, ge=3, le=10, description="預測年數")
    
    # 成長率參數
    revenue_growth_rates: List[float] = Field(
        default_factory=lambda: [0.10, 0.08, 0.06, 0.05, 0.04],
        min_length=3,
        max_length=10,
        description="各年營收成長率"
    )
    
    # 獲利能力參數
    ebitda_margin: float = Field(0.15, ge=0.0, le=1.0, description="EBITDA邊際率")
    tax_rate: float = Field(0.25, ge=0.0, le=0.6, description="稅率")
    
    # 投資參數
    capex_rate: float = Field(0.04, ge=0.0, le=0.2, description="資本支出率")
    working_capital_rate: float = Field(0.02, ge=0.0, le=0.1, description="營運資金率")
    
    # 折現參數
    discount_rate: float = Field(0.10, ge=0.01, le=0.3, description="折現率")
    terminal_growth_rate: float = Field(0.03, ge=0.0, le=0.1, description="終值成長率")
    
    # 其他參數
    net_debt: Optional[Decimal] = Field(0, description="淨負債")
    shares_outstanding: Optional[int] = Field(None, gt=0, description="流通股數")
    
    # 分析選項
    sensitivity_analysis: bool = Field(True, description="是否進行敏感性分析")
    include_assumptions: bool = Field(True, description="是否包含假設條件")

    @field_validator("revenue_growth_rates")
    @classmethod
    def validate_growth_rates(cls, v):
        for rate in v:
            if not -0.5 <= rate <= 1.0:
                raise ValueError("營收成長率必須在-50%到100%之間")
        return v

    @field_validator("discount_rate", "terminal_growth_rate")
    @classmethod
    def validate_rates_relationship(cls, v, info):
        # 這裡需要在模型驗證後檢查折現率大於終值成長率
        return v


class DDMValuationRequest(BaseModel):
    """DDM股利折現評價請求"""
    company_id: str = Field(..., pattern=r"^\d{4}$")
    current_dividend: Decimal = Field(..., gt=0, description="當前每股股利")
    dividend_growth_rate: float = Field(0.05, ge=0.0, le=0.3, description="股利成長率")
    discount_rate: float = Field(0.10, ge=0.01, le=0.3, description="折現率")
    stable_growth_rate: float = Field(0.03, ge=0.0, le=0.1, description="穩定成長率")
    shares_outstanding: Optional[int] = Field(None, gt=0, description="流通股數")


class RelativeValuationRequest(BaseModel):
    """相對評價請求"""
    company_id: str = Field(..., pattern=r"^\d{4}$")
    valuation_method: ValuationMethod = Field(..., description="評價方法")
    peer_companies: Optional[List[str]] = Field(None, max_length=20, description="指定同業公司")
    adjustment_factors: Optional[Dict[str, float]] = Field(None, description="調整因子")
    include_industry_benchmark: bool = Field(True, description="是否包含產業基準")


# ================== 同業比較請求模型 ==================

class PeerComparisonRequest(BaseModel):
    """同業比較分析請求"""
    company_id: str = Field(..., pattern=r"^\d{4}$")
    industry_code: Optional[str] = Field(None, pattern=r"^[A-Z0-9]{2,10}$")
    peer_count: int = Field(10, ge=5, le=20, description="同業公司數量")
    analysis_period: Optional[str] = Field(None, pattern=r"^20\d{2}Q[1-4]$")
    
    # 分析選項
    include_rankings: bool = Field(True, description="是否包含排名分析")
    include_recommendations: bool = Field(True, description="是否包含改善建議")
    custom_weights: Optional[Dict[str, float]] = Field(None, description="自定義權重")

    @field_validator("custom_weights")
    @classmethod
    def validate_weights(cls, v):
        if v is not None:
            total_weight = sum(v.values())
            if not 0.9 <= total_weight <= 1.1:  # 允許小幅誤差
                raise ValueError("權重總和必須接近1.0")
        return v


# ================== 產業分析請求模型 ==================

class IndustryAnalysisRequest(BaseModel):
    """產業分析請求"""
    industry_code: str = Field(..., pattern=r"^[A-Z0-9]{2,10}$")
    analysis_period: Optional[str] = Field(None, pattern=r"^20\d{2}Q[1-4]$")
    include_benchmarks: bool = Field(True, description="是否包含產業基準")
    include_trends: bool = Field(False, description="是否包含趨勢分析")
    top_companies_count: int = Field(10, ge=5, le=50, description="頂級公司數量")


# ================== 綜合分析請求模型 ==================

class ComprehensiveAnalysisRequest(BaseModel):
    """綜合分析請求"""
    company_id: str = Field(..., pattern=r"^\d{4}$")
    analysis_types: List[str] = Field(
        default=["financial_ratios", "dcf_valuation", "peer_comparison"],
        description="分析類型列表"
    )
    
    # DCF參數（可選）
    dcf_params: Optional[Dict[str, Any]] = None
    
    # 同業比較參數（可選）
    peer_params: Optional[Dict[str, Any]] = None
    
    # 輸出選項
    include_charts: bool = Field(False, description="是否包含圖表資料")
    include_raw_data: bool = Field(False, description="是否包含原始資料")
    report_format: str = Field("json", pattern=r"^(json|pdf|excel)$", description="報告格式")

    @field_validator("analysis_types")
    @classmethod
    def validate_analysis_types(cls, v):
        valid_types = [
            "financial_ratios", "financial_health", "dcf_valuation", 
            "ddm_valuation", "relative_valuation", "peer_comparison",
            "industry_analysis", "trend_analysis"
        ]
        for analysis_type in v:
            if analysis_type not in valid_types:
                raise ValueError(f"無效的分析類型: {analysis_type}")
        return v


# ================== 批量處理請求模型 ==================

class BatchAnalysisRequest(BaseModel):
    """批量分析請求"""
    company_ids: List[str] = Field(..., min_length=1, max_length=50)
    analysis_type: str = Field(..., description="分析類型")
    parameters: Optional[Dict[str, Any]] = Field(None, description="分析參數")
    callback_url: Optional[str] = Field(None, description="回調URL")
    priority: int = Field(1, ge=1, le=5, description="處理優先級")

    @field_validator("company_ids")
    @classmethod
    def validate_company_ids(cls, v):
        for company_id in v:
            if not re.match(r"^\d{4}$", company_id):
                raise ValueError(f"無效的公司代碼: {company_id}")
        return v


# ================== 資料匯出請求模型 ==================

class DataExportRequest(BaseModel):
    """資料匯出請求"""
    export_type: str = Field(..., pattern=r"^(financial_statements|financial_ratios|analysis_results)$")
    company_ids: Optional[List[str]] = Field(None, max_length=100)
    date_range: Optional[Dict[str, str]] = Field(None, description="日期範圍")
    file_format: str = Field("csv", pattern=r"^(csv|excel|json)$")
    include_metadata: bool = Field(True, description="是否包含後設資料")
    compression: bool = Field(False, description="是否壓縮檔案")


# ================== 文件上傳請求模型 ==================

class DocumentUploadRequest(BaseModel):
    """文件上傳請求"""
    company_id: Optional[str] = Field(None, pattern=r"^\d{4}$", description="公司代碼")
    report_period: Optional[str] = Field(None, pattern=r"^20\d{2}Q[1-4]$", description="報告期間")
    document_type: str = Field("financial_statement", description="文件類型")
    async_processing: bool = Field(False, description="是否異步處理")
    extract_tables: bool = Field(True, description="是否提取表格")
    validate_data: bool = Field(True, description="是否驗證數據")


class DocumentProcessingConfig(BaseModel):
    """文件處理配置"""
    extraction_methods: List[str] = Field(
        default=["pdfplumber", "pymupdf"],
        description="使用的提取方法"
    )
    confidence_threshold: float = Field(0.5, ge=0.0, le=1.0, description="置信度閾值")
    unit_detection: bool = Field(True, description="是否自動檢測金額單位")
    data_validation: bool = Field(True, description="是否進行數據驗證")
    
    @field_validator("extraction_methods")
    @classmethod
    def validate_extraction_methods(cls, v):
        valid_methods = ["pdfplumber", "pymupdf", "pypdf2"]
        for method in v:
            if method not in valid_methods:
                raise ValueError(f"無效的提取方法: {method}")
        return v


# ================== AI Agent 請求模型 ==================

class AgentAnalysisRequest(BaseModel):
    """AI Agent分析請求"""
    user_query: str = Field(..., min_length=1, max_length=2000, description="使用者查詢問題")
    company_id: Optional[str] = Field(None, pattern=r"^\d{4}$", description="公司代碼(可選)")
    context: Optional[Dict[str, Any]] = Field(None, description="額外上下文資訊")
    analysis_depth: str = Field("standard", pattern=r"^(quick|standard|deep)$", description="分析深度")
    include_recommendations: bool = Field(True, description="是否包含建議")
    language: str = Field("zh-TW", pattern=r"^(zh-TW|zh-CN|en)$", description="回應語言")

    @field_validator("user_query")
    @classmethod
    def validate_user_query(cls, v):
        """驗證使用者查詢"""
        if v.strip() == "":
            raise ValueError("查詢內容不能為空")
        return v.strip()


class AgentConversationRequest(BaseModel):
    """AI Agent對話請求"""
    conversation_id: str = Field(..., description="對話ID")
    message: str = Field(..., min_length=1, max_length=2000)
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="附件資訊")


class AgentTaskRequest(BaseModel):
    """AI Agent任務請求"""
    task_type: str = Field(..., pattern=r"^(analysis|valuation|comparison|monitoring)$")
    parameters: Dict[str, Any] = Field(..., description="任務參數")
    priority: int = Field(1, ge=1, le=5, description="優先級")
    async_execution: bool = Field(False, description="是否異步執行")


# ================== 系統管理請求模型 ==================

class CacheManagementRequest(BaseModel):
    """快取管理請求"""
    action: str = Field(..., pattern=r"^(clear|refresh|status)$")
    cache_type: Optional[str] = Field(None, pattern=r"^(company|financial|analysis|all)$")
    company_ids: Optional[List[str]] = None
    force: bool = Field(False, description="強制執行")


class SystemHealthRequest(BaseModel):
    """系統健康檢查請求"""
    check_types: List[str] = Field(
        default=["database", "cache", "external_apis"],
        description="檢查類型"
    )
    detailed: bool = Field(False, description="詳細檢查")
    timeout: int = Field(30, ge=5, le=300, description="超時時間(秒)")

    @field_validator("check_types")
    @classmethod
    def validate_check_types(cls, v):
        valid_types = ["database", "cache", "external_apis", "disk_space", "memory", "cpu"]
        for check_type in v:
            if check_type not in valid_types:
                raise ValueError(f"無效的檢查類型: {check_type}")
        return v


# ================== 風險評估請求模型 ==================

class RiskAssessmentRequest(BaseModel):
    """綜合風險評估請求"""
    company_id: str = Field(..., pattern=r"^\d{4}$", description="公司代碼")
    assessment_scope: Optional[List[str]] = Field(
        None,
        description="評估範圍，例如 ['financial_distress', 'liquidity', 'profitability', 'leverage']",
    )


# ================== 同業比較（顯式資料）請求模型 ==================

class PeerCompanyDataInput(BaseModel):
    """同業公司資料輸入（用於顯式同業比較）"""
    company_id: str = Field(..., description="公司代碼")
    company_name: str = Field(..., description="公司名稱")
    market_cap: float = Field(..., description="市值")
    revenue: float = Field(..., description="營收")
    net_income: float = Field(..., description="淨利")
    total_assets: float = Field(..., description="總資產")
    shareholders_equity: float = Field(..., description="股東權益")
    roe: float = Field(..., description="ROE")
    roa: float = Field(..., description="ROA")
    current_ratio: float = Field(..., description="流動比率")
    debt_ratio: float = Field(..., description="負債比率")
    net_margin: float = Field(..., description="淨利率")
    pe_ratio: Optional[float] = Field(None, description="本益比")
    pb_ratio: Optional[float] = Field(None, description="股價淨值比")
    ev_ebitda: Optional[float] = Field(None, description="EV/EBITDA")


class IndustryBenchmarkInput(BaseModel):
    """產業基準資料輸入"""
    industry_code: str = Field(..., description="產業代碼")
    industry_name: str = Field(..., description="產業名稱")
    company_count: int = Field(..., description="產業內公司數量")
    avg_roe: float
    avg_roa: float
    avg_current_ratio: float
    avg_debt_ratio: float
    avg_gross_margin: float
    avg_net_margin: float
    avg_pe_ratio: float
    avg_pb_ratio: float
    median_roe: float
    median_roa: float
    median_current_ratio: float
    median_debt_ratio: float
    roe_25_percentile: float
    roe_75_percentile: float
    pe_25_percentile: float
    pe_75_percentile: float
    debt_25_percentile: float
    debt_75_percentile: float
    roe_std_dev: float
    roa_std_dev: float


class PeerComparisonDataRequest(BaseModel):
    """同業比較分析請求（顯式提供目標公司、同業與產業基準資料）"""
    target: PeerCompanyDataInput = Field(..., description="目標公司資料")
    peers: List[PeerCompanyDataInput] = Field(..., min_length=1, description="同業公司列表")
    industry_benchmark: IndustryBenchmarkInput = Field(..., description="產業基準")


class AutoPeerComparisonRequest(BaseModel):
    """同業比較分析請求（自動由 DB 抓取資料）"""
    target_company_id: str = Field(..., pattern=r"^\d{4}$", description="目標公司代碼")
    peer_company_ids: List[str] = Field(..., min_length=1, description="同業公司代碼列表")