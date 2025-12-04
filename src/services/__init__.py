"""
Services Package
================

Financial Analysis System Core Services
"""

# Financial Calculation Services
from src.services.financial_calculator import (
    FinancialCalculator,
    FinancialHealth,
    FinancialStatements
)

# Valuation Model Services
from src.services.valuation_models import (
    DCFValuationModel,
    DCFParameters,
    DDMValuationModel
)

# Peer Comparison Analysis
from src.services.peer_analysis import PeerAnalyzer

# Risk Assessment Service
from src.services.risk_assessment import (
    RiskAssessmentEngine,
    RiskLevel,
    AltmanZScoreResult
)

# Report Generation Service
from src.services.report_service import ReportService

# Alert Monitor Service
from src.services.alert_monitor import (
    AlertMonitor,
    AlertLevel,
    AlertType,
    DEFAULT_ALERT_THRESHOLDS
)

# Data Services
# Data Services - using actual class names
from src.services.company_service import CompanyDataService
from src.services.financial_service import FinancialDataService

# External Data Sources
from src.services.external_data_manager import ExternalDataManager
from src.services.twse_service import TWStockExchangeService
from src.services.yahoo_finance_service import YahooFinanceService

# File Processing Services
from src.services.excel_processor import FinancialExcelProcessor
from src.services.pdf_processor import FinancialPDFProcessor


__all__ = [
    # Financial Calculation
    "FinancialCalculator",
    "FinancialHealth",
    "FinancialStatements",

    # Valuation Models
    "DCFValuationModel",
    "DCFParameters",
    "DDMValuationModel",

    # Analysis & Assessment
    "PeerAnalyzer",
    "RiskAssessmentEngine",
    "RiskLevel",
    "AltmanZScoreResult",

    # Reports & Alerts
    "ReportService",
    "AlertMonitor",
    "AlertLevel",
    "AlertType",
    "DEFAULT_ALERT_THRESHOLDS",

    # Data Services
    "CompanyDataService",
    "FinancialDataService",

    # External Data
    "ExternalDataManager",
    "TWStockExchangeService",
    "YahooFinanceService",

    # File Processing
    "FinancialExcelProcessor",
    "FinancialPDFProcessor",
]
