"""
資料庫模型定義
Database Models

定義所有資料表的 SQLAlchemy 模型
"""

from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, Text, ForeignKey, Index, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

# SQLAlchemy 2.x 未在頂層提供 Decimal 型別；DECIMAL 欄位以 Numeric 表示。
# 保留 Decimal 別名以最小化對既有 Column(Decimal(...)) 宣告的改動。
Decimal = Numeric

Base = declarative_base()


class Company(Base):
    """公司基本資料表"""
    __tablename__ = "companies"
    
    company_id = Column(String(10), primary_key=True)
    company_name = Column(String(100), nullable=False)
    company_name_en = Column(String(200))
    industry_code = Column(String(10), nullable=False, index=True)
    industry_name = Column(String(100))
    market_type = Column(String(20), nullable=False, index=True)
    listing_date = Column(Date)
    capital_amount = Column(Decimal(15, 2))
    outstanding_shares = Column(Integer)
    par_value = Column(Decimal(8, 2))
    address = Column(Text)
    website = Column(String(200))
    chairman = Column(String(50))
    ceo = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 關聯
    financial_statements = relationship("FinancialStatement", back_populates="company")
    financial_ratios = relationship("FinancialRatio", back_populates="company")


class FinancialStatement(Base):
    """財務報表資料表"""
    __tablename__ = "financial_statements"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(String(10), ForeignKey("companies.company_id"), nullable=False, index=True)
    report_type = Column(String(20), nullable=False)  # annual/quarterly
    year_quarter = Column(String(10), nullable=False, index=True)
    statement_type = Column(String(20), nullable=False)  # BS/IS/CF/SE
    report_date = Column(Date, nullable=False)
    
    # 資產負債表項目
    current_assets = Column(Decimal(15, 2))
    non_current_assets = Column(Decimal(15, 2))
    total_assets = Column(Decimal(15, 2))
    current_liabilities = Column(Decimal(15, 2))
    non_current_liabilities = Column(Decimal(15, 2))
    total_liabilities = Column(Decimal(15, 2))
    shareholders_equity = Column(Decimal(15, 2))
    cash_and_equivalents = Column(Decimal(15, 2))
    accounts_receivable = Column(Decimal(15, 2))
    inventory = Column(Decimal(15, 2))
    ppe_net = Column(Decimal(15, 2))  # 不動產、廠房及設備淨額
    accounts_payable = Column(Decimal(15, 2))
    short_term_debt = Column(Decimal(15, 2))
    long_term_debt = Column(Decimal(15, 2))
    
    # 損益表項目
    revenue = Column(Decimal(15, 2))
    cost_of_revenue = Column(Decimal(15, 2))
    gross_profit = Column(Decimal(15, 2))
    operating_expenses = Column(Decimal(15, 2))
    operating_income = Column(Decimal(15, 2))
    ebitda = Column(Decimal(15, 2))
    depreciation_amortization = Column(Decimal(15, 2))
    interest_expense = Column(Decimal(15, 2))
    interest_income = Column(Decimal(15, 2))
    pretax_income = Column(Decimal(15, 2))
    tax_expense = Column(Decimal(15, 2))
    net_income = Column(Decimal(15, 2))
    eps = Column(Decimal(8, 4))
    eps_diluted = Column(Decimal(8, 4))
    
    # 現金流量表項目
    operating_cash_flow = Column(Decimal(15, 2))
    investing_cash_flow = Column(Decimal(15, 2))
    financing_cash_flow = Column(Decimal(15, 2))
    free_cash_flow = Column(Decimal(15, 2))
    capex = Column(Decimal(15, 2))
    
    # 其他項目
    retained_earnings = Column(Decimal(15, 2))
    dividends_paid = Column(Decimal(15, 2))
    
    # 資料品質欄位
    data_source = Column(String(50))
    data_quality_score = Column(Decimal(3, 2))
    is_audited = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 關聯
    company = relationship("Company", back_populates="financial_statements")
    
    # 複合索引
    __table_args__ = (
        Index('idx_financial_statements_company_period', 'company_id', 'year_quarter'),
    )


class FinancialRatio(Base):
    """財務比率表"""
    __tablename__ = "financial_ratios"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(String(10), ForeignKey("companies.company_id"), nullable=False, index=True)
    year_quarter = Column(String(10), nullable=False, index=True)
    calculation_date = Column(DateTime, default=datetime.utcnow)
    
    # 財務結構比率
    debt_to_asset_ratio = Column(Decimal(8, 4))
    debt_to_equity_ratio = Column(Decimal(8, 4))
    equity_ratio = Column(Decimal(8, 4))
    long_term_debt_to_equity = Column(Decimal(8, 4))
    
    # 償債能力比率
    current_ratio = Column(Decimal(8, 4))
    quick_ratio = Column(Decimal(8, 4))
    cash_ratio = Column(Decimal(8, 4))
    interest_coverage_ratio = Column(Decimal(8, 4))
    debt_service_coverage_ratio = Column(Decimal(8, 4))
    
    # 經營能力比率
    receivables_turnover = Column(Decimal(8, 4))
    inventory_turnover = Column(Decimal(8, 4))
    total_asset_turnover = Column(Decimal(8, 4))
    fixed_asset_turnover = Column(Decimal(8, 4))
    working_capital_turnover = Column(Decimal(8, 4))
    days_sales_outstanding = Column(Decimal(8, 2))
    days_inventory_outstanding = Column(Decimal(8, 2))
    days_payable_outstanding = Column(Decimal(8, 2))
    cash_conversion_cycle = Column(Decimal(8, 2))
    
    # 獲利能力比率
    roa = Column(Decimal(8, 4))
    roe = Column(Decimal(8, 4))
    roic = Column(Decimal(8, 4))
    gross_margin = Column(Decimal(8, 4))
    operating_margin = Column(Decimal(8, 4))
    net_margin = Column(Decimal(8, 4))
    ebitda_margin = Column(Decimal(8, 4))
    
    # 現金流量比率
    operating_cash_ratio = Column(Decimal(8, 4))
    cash_flow_to_debt_ratio = Column(Decimal(8, 4))
    free_cash_flow_yield = Column(Decimal(8, 4))
    cash_flow_adequacy_ratio = Column(Decimal(8, 4))
    
    # 市場價值比率
    pe_ratio = Column(Decimal(8, 4))
    pb_ratio = Column(Decimal(8, 4))
    ps_ratio = Column(Decimal(8, 4))
    ev_ebitda = Column(Decimal(8, 4))
    dividend_yield = Column(Decimal(8, 4))
    
    # 成長率
    revenue_growth = Column(Decimal(8, 4))
    net_income_growth = Column(Decimal(8, 4))
    eps_growth = Column(Decimal(8, 4))
    asset_growth = Column(Decimal(8, 4))
    
    # 計算相關
    calculation_method = Column(String(50))
    data_completeness = Column(Decimal(3, 2))
    outlier_flag = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 關聯
    company = relationship("Company", back_populates="financial_ratios")
    
    # 複合索引
    __table_args__ = (
        Index('idx_financial_ratios_company_period', 'company_id', 'year_quarter'),
    )


class IndustryBenchmarks(Base):
    """產業基準表"""
    __tablename__ = "industry_benchmarks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    industry_code = Column(String(10), nullable=False, index=True)
    year_quarter = Column(String(10), nullable=False, index=True)
    company_count = Column(Integer)
    
    # 平均值
    avg_roe = Column(Decimal(8, 4))
    avg_roa = Column(Decimal(8, 4))
    avg_current_ratio = Column(Decimal(8, 4))
    avg_debt_ratio = Column(Decimal(8, 4))
    avg_gross_margin = Column(Decimal(8, 4))
    avg_operating_margin = Column(Decimal(8, 4))
    avg_net_margin = Column(Decimal(8, 4))
    avg_pe_ratio = Column(Decimal(8, 4))
    avg_pb_ratio = Column(Decimal(8, 4))
    
    # 中位數
    median_roe = Column(Decimal(8, 4))
    median_roa = Column(Decimal(8, 4))
    median_current_ratio = Column(Decimal(8, 4))
    median_debt_ratio = Column(Decimal(8, 4))
    
    # 分位數
    roe_25_percentile = Column(Decimal(8, 4))
    roe_75_percentile = Column(Decimal(8, 4))
    pe_25_percentile = Column(Decimal(8, 4))
    pe_75_percentile = Column(Decimal(8, 4))
    debt_25_percentile = Column(Decimal(8, 4))
    debt_75_percentile = Column(Decimal(8, 4))
    
    # 標準差
    roe_std_dev = Column(Decimal(8, 4))
    roa_std_dev = Column(Decimal(8, 4))
    
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    # 複合索引
    __table_args__ = (
        Index('idx_industry_benchmarks_industry_period', 'industry_code', 'year_quarter'),
    )


class User(Base):
    """用戶表"""
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default='user')  # admin/analyst/user
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 關聯
    watchlists = relationship("UserWatchlist", back_populates="user")


class UserWatchlist(Base):
    """用戶關注清單表"""
    __tablename__ = "user_watchlists"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    company_id = Column(String(10), ForeignKey("companies.company_id"), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    
    # 關聯
    user = relationship("User", back_populates="watchlists")
    company = relationship("Company")
    
    # 複合唯一索引
    __table_args__ = (
        Index('idx_user_watchlist_unique', 'user_id', 'company_id', unique=True),
    )