"""
API 響應模型
Response Models

定義所有API端點的響應資料結構
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union, Generic, TypeVar
from decimal import Decimal
from datetime import datetime
from enum import Enum


class ResponseStatus(str, Enum):
    """響應狀態"""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"
    PROCESSING = "processing"


class FinancialHealth(str, Enum):
    """財務健康度"""
    EXCELLENT = "優秀"
    GOOD = "良好"
    FAIR = "普通"
    POOR = "不佳"
    CRITICAL = "危險"


class PerformanceRating(str, Enum):
    """績效評等"""
    EXCELLENT = "優秀"
    ABOVE_AVERAGE = "高於平均"
    AVERAGE = "平均"
    BELOW_AVERAGE = "低於平均"
    POOR = "不佳"


# ================== 基礎響應模型 ==================

T = TypeVar('T')

class BaseResponse(BaseModel, Generic[T]):
    """基礎響應模型"""
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PaginationMeta(BaseModel):
    """分頁資訊"""
    page: int = Field(..., description="當前頁碼")
    page_size: int = Field(..., description="每頁筆數")
    total: int = Field(..., description="總筆數")
    total_pages: int = Field(..., description="總頁數")
    has_next: bool = Field(..., description="是否有下一頁")
    has_prev: bool = Field(..., description="是否有上一頁")


class ErrorDetail(BaseModel):
    """錯誤詳情"""
    code: str = Field(..., description="錯誤代碼")
    message: str = Field(..., description="錯誤訊息")
    field: Optional[str] = Field(None, description="相關欄位")
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseResponse):
    """錯誤響應"""
    status: ResponseStatus = ResponseStatus.ERROR
    errors: List[ErrorDetail] = Field(default_factory=list)


class StandardResponse(BaseModel):
    """標準API響應模型 - 用於AI Agent等通用響應"""
    success: bool = True
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    message: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ================== 公司相關響應模型 ==================

class CompanyBasicInfo(BaseModel):
    """公司基本資訊"""
    company_id: str = Field(..., description="公司代碼")
    company_name: str = Field(..., description="公司名稱")
    company_name_en: Optional[str] = Field(None, description="英文名稱")
    industry_code: str = Field(..., description="產業代碼")
    industry_name: Optional[str] = Field(None, description="產業名稱")
    market_type: str = Field(..., description="市場類型")
    listing_date: Optional[str] = Field(None, description="上市日期")
    capital_amount: Optional[Decimal] = Field(None, description="資本額")
    outstanding_shares: Optional[int] = Field(None, description="流通股數")
    website: Optional[str] = Field(None, description="官網")
    is_active: bool = Field(True, description="是否營業中")


class CompanyDetailResponse(BaseResponse):
    """公司詳情響應"""
    data: CompanyBasicInfo


class CompanyListResponse(BaseResponse):
    """公司列表響應"""
    data: List[CompanyBasicInfo]
    meta: Optional[PaginationMeta] = None


class CompanySearchResponse(BaseResponse):
    """公司搜尋響應"""
    data: List[CompanyBasicInfo]
    search_meta: Dict[str, Any] = Field(default_factory=dict)


# ================== 財務分析響應模型 ==================

class FinancialRatios(BaseModel):
    """財務比率"""
    # 財務結構比率
    debt_to_asset_ratio: Optional[float] = Field(None, description="負債對資產比率")
    debt_to_equity_ratio: Optional[float] = Field(None, description="負債對權益比率")
    equity_ratio: Optional[float] = Field(None, description="權益比率")
    
    # 償債能力比率
    current_ratio: Optional[float] = Field(None, description="流動比率")
    quick_ratio: Optional[float] = Field(None, description="速動比率")
    cash_ratio: Optional[float] = Field(None, description="現金比率")
    interest_coverage_ratio: Optional[float] = Field(None, description="利息保障倍數")
    
    # 經營能力比率
    receivables_turnover: Optional[float] = Field(None, description="應收帳款周轉率")
    inventory_turnover: Optional[float] = Field(None, description="存貨周轉率")
    total_asset_turnover: Optional[float] = Field(None, description="總資產周轉率")
    days_sales_outstanding: Optional[float] = Field(None, description="應收帳款周轉天數")
    
    # 獲利能力比率
    roa: Optional[float] = Field(None, description="資產報酬率")
    roe: Optional[float] = Field(None, description="股東權益報酬率")
    roic: Optional[float] = Field(None, description="投入資本報酬率")
    gross_margin: Optional[float] = Field(None, description="毛利率")
    operating_margin: Optional[float] = Field(None, description="營業利益率")
    net_margin: Optional[float] = Field(None, description="淨利率")
    
    # 現金流量比率
    operating_cash_ratio: Optional[float] = Field(None, description="營業現金流比率")
    free_cash_flow_yield: Optional[float] = Field(None, description="自由現金流殖利率")
    
    # 市場價值比率
    pe_ratio: Optional[float] = Field(None, description="本益比")
    pb_ratio: Optional[float] = Field(None, description="股價淨值比")
    ev_ebitda: Optional[float] = Field(None, description="企業價值倍數")


class FinancialRatiosResponse(BaseResponse):
    """財務比率響應"""
    data: FinancialRatios
    company_id: str
    year_quarter: str
    calculation_date: datetime


class FinancialHealthAssessment(BaseModel):
    """財務健康度評估"""
    overall_grade: FinancialHealth = Field(..., description="綜合評級")
    overall_score: float = Field(..., description="綜合評分")
    detailed_scores: Dict[str, float] = Field(..., description="詳細評分")
    assessment_details: Dict[str, str] = Field(..., description="評估詳情")
    strengths: List[str] = Field(default_factory=list, description="優勢項目")
    weaknesses: List[str] = Field(default_factory=list, description="劣勢項目")
    recommendations: List[str] = Field(default_factory=list, description="改善建議")


class FinancialHealthResponse(BaseResponse):
    """財務健康度響應"""
    data: FinancialHealthAssessment
    company_id: str
    analysis_period: str


class TrendData(BaseModel):
    """趨勢資料"""
    period: str = Field(..., description="期別")
    values: Dict[str, Optional[float]] = Field(..., description="指標值")


class FinancialTrendResponse(BaseResponse):
    """財務趨勢響應"""
    data: Dict[str, List[TrendData]]
    company_id: str
    periods_analyzed: int


# ================== DCF評價響應模型 ==================

class DCFAssumptions(BaseModel):
    """DCF假設條件"""
    discount_rate: float = Field(..., description="折現率")
    terminal_growth_rate: float = Field(..., description="終值成長率")
    revenue_growth_rates: List[float] = Field(..., description="營收成長率")
    ebitda_margin: float = Field(..., description="EBITDA邊際率")
    tax_rate: float = Field(..., description="稅率")
    capex_rate: float = Field(..., description="資本支出率")


class DCFCalculationDetails(BaseModel):
    """DCF計算明細"""
    projected_revenues: List[float] = Field(..., description="預測營收")
    projected_fcf: List[float] = Field(..., description="預測自由現金流")
    pv_fcf: List[float] = Field(..., description="自由現金流現值")
    terminal_fcf: float = Field(..., description="終值現金流")
    terminal_value: float = Field(..., description="終值")
    pv_terminal_value: float = Field(..., description="終值現值")


class DCFValuationResult(BaseModel):
    """DCF評價結果"""
    fair_value_per_share: float = Field(..., description="每股公允價值")
    enterprise_value: float = Field(..., description="企業價值")
    equity_value: float = Field(..., description="股權價值")
    current_price: Optional[float] = Field(None, description="當前股價")
    upside_downside: Optional[float] = Field(None, description="上漲下跌空間%")
    
    dcf_value: float = Field(..., description="DCF價值")
    terminal_value_contribution: float = Field(..., description="終值貢獻")
    terminal_value_percentage: float = Field(..., description="終值占比%")
    
    assumptions: DCFAssumptions
    calculation_details: Optional[DCFCalculationDetails] = None
    sensitivity_analysis: Optional[Dict[str, Dict[str, float]]] = None


class DCFValuationResponse(BaseResponse):
    """DCF評價響應"""
    data: DCFValuationResult
    company_id: str
    valuation_date: datetime


# ================== 同業比較響應模型 ==================

class PeerCompanyInfo(BaseModel):
    """同業公司資訊"""
    company_id: str
    company_name: str
    market_cap: float
    key_ratios: Dict[str, Optional[float]]


class RankingInfo(BaseModel):
    """排名資訊"""
    rank: int = Field(..., description="排名")
    total: int = Field(..., description="總數")
    percentile: float = Field(..., description="百分位數")
    value: float = Field(..., description="指標值")
    best_in_peer: float = Field(..., description="同業最佳值")
    worst_in_peer: float = Field(..., description="同業最差值")


class IndustryBenchmark(BaseModel):
    """產業基準"""
    industry_code: str
    industry_name: str
    company_count: int
    avg_values: Dict[str, float] = Field(..., description="平均值")
    median_values: Dict[str, float] = Field(..., description="中位數")
    percentiles: Dict[str, Dict[str, float]] = Field(..., description="分位數")


class PeerComparisonResult(BaseModel):
    """同業比較結果"""
    target_company_id: str
    industry_code: str
    peer_companies: List[PeerCompanyInfo]
    industry_benchmark: IndustryBenchmark
    
    rankings: Dict[str, RankingInfo] = Field(..., description="排名資訊")
    performance_ratings: Dict[str, PerformanceRating] = Field(..., description="績效評等")
    composite_score: float = Field(..., description="綜合評分")
    
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class PeerComparisonResponse(BaseResponse):
    """同業比較響應"""
    data: PeerComparisonResult
    analysis_date: datetime


# ================== 綜合分析響應模型 ==================

class ComprehensiveAnalysisResult(BaseModel):
    """綜合分析結果"""
    company_id: str
    company_name: str
    analysis_date: datetime
    
    # 各項分析結果
    financial_ratios: Optional[FinancialRatios] = None
    financial_health: Optional[FinancialHealthAssessment] = None
    dcf_valuation: Optional[DCFValuationResult] = None
    peer_comparison: Optional[PeerComparisonResult] = None
    
    # 綜合評估
    investment_summary: Dict[str, Any] = Field(default_factory=dict)
    key_metrics: Dict[str, float] = Field(default_factory=dict)
    investment_highlights: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    
    # 評價總結
    valuation_range: Optional[Dict[str, float]] = None
    recommendation: Optional[str] = None
    target_price: Optional[float] = None


class ComprehensiveAnalysisResponse(BaseResponse):
    """綜合分析響應"""
    data: ComprehensiveAnalysisResult


# ================== 批量處理響應模型 ==================

class BatchJobStatus(BaseModel):
    """批量作業狀態"""
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: float  # 0.0 - 1.0
    total_items: int
    processed_items: int
    failed_items: int
    created_at: datetime
    updated_at: datetime
    estimated_completion: Optional[datetime] = None


class BatchAnalysisResponse(BaseResponse):
    """批量分析響應"""
    job_status: BatchJobStatus
    results: Optional[List[Dict[str, Any]]] = None


# ================== 資料匯出響應模型 ==================

class ExportJobInfo(BaseModel):
    """匯出作業資訊"""
    export_id: str
    status: str
    file_format: str
    file_size: Optional[int] = None
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime


class DataExportResponse(BaseResponse):
    """資料匯出響應"""
    export_job: ExportJobInfo


# ================== 系統狀態響應模型 ==================

class ServiceStatus(BaseModel):
    """服務狀態"""
    name: str
    status: str  # healthy, degraded, unhealthy
    response_time: Optional[float] = None
    last_check: datetime
    details: Optional[Dict[str, Any]] = None


class SystemHealthResponse(BaseResponse):
    """系統健康狀態響應"""
    overall_status: str
    services: List[ServiceStatus]
    system_info: Dict[str, Any] = Field(default_factory=dict)


class CacheStatusInfo(BaseModel):
    """快取狀態資訊"""
    cache_type: str
    total_keys: int
    memory_usage: str
    hit_rate: float
    last_updated: datetime


class CacheManagementResponse(BaseResponse):
    """快取管理響應"""
    action: str
    affected_keys: int
    cache_status: List[CacheStatusInfo]


# ================== 市場資料響應模型 ==================

class StockPriceData(BaseModel):
    """股價資料"""
    date: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    adj_close: Optional[float] = None


class MarketDataResponse(BaseResponse):
    """市場資料響應"""
    company_id: str
    data_type: str
    date_range: Dict[str, str]
    data: List[StockPriceData]


# ================== 通用列表響應模型 ==================

class ListResponse(BaseResponse):
    """通用列表響應模型"""
    data: List[Dict[str, Any]]
    meta: Optional[PaginationMeta] = None
    filters_applied: Optional[Dict[str, Any]] = None
    sort_info: Optional[Dict[str, str]] = None


# ================== API資訊響應模型 ==================

class APIEndpointInfo(BaseModel):
    """API端點資訊"""
    path: str
    method: str
    summary: str
    tags: List[str]
    parameters: Optional[Dict[str, Any]] = None


class APIDocumentationResponse(BaseResponse):
    """API文檔響應"""
    api_version: str
    total_endpoints: int
    endpoints: List[APIEndpointInfo]
    authentication_info: Dict[str, Any]
    rate_limits: Dict[str, Any]