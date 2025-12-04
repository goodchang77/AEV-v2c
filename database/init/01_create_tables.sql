-- =====================================================
-- 財務分析系統核心資料表結構 
-- 基於 IFRS 13 公允價值衡量原則和台灣市場實務
-- =====================================================

-- 擴展 UUID 支援
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- 1. 公司基本資料表
-- =====================================================
CREATE TABLE companies (
    company_id VARCHAR(10) PRIMARY KEY,  -- 股票代號 (e.g., 2330)
    company_name VARCHAR(100) NOT NULL,
    company_name_en VARCHAR(100),
    industry_code VARCHAR(10) NOT NULL,
    industry_name VARCHAR(50),
    market_type VARCHAR(20) NOT NULL CHECK (market_type IN ('上市', '上櫃', '興櫃')),
    listing_date DATE,
    capital_amount DECIMAL(15,2),  -- 實收資本額
    outstanding_shares BIGINT,     -- 流通在外股數
    par_value DECIMAL(8,2) DEFAULT 10.00,  -- 面額
    
    -- 公司基本資訊
    address TEXT,
    website VARCHAR(255),
    chairman VARCHAR(50),
    ceo VARCHAR(50),
    
    -- 狀態與時間戳記
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引優化
    CONSTRAINT companies_capital_positive CHECK (capital_amount >= 0),
    CONSTRAINT companies_shares_positive CHECK (outstanding_shares >= 0)
);

-- 建立索引
CREATE INDEX idx_companies_industry ON companies(industry_code);
CREATE INDEX idx_companies_market ON companies(market_type);
CREATE INDEX idx_companies_active ON companies(is_active) WHERE is_active = true;
CREATE INDEX idx_companies_listing_date ON companies(listing_date);

-- =====================================================
-- 2. 財務報表資料表
-- =====================================================
CREATE TABLE financial_statements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id VARCHAR(10) NOT NULL,
    report_type VARCHAR(20) NOT NULL CHECK (report_type IN ('annual', 'quarterly')),
    year_quarter VARCHAR(10) NOT NULL,  -- 2024Q1, 2024 格式
    statement_type VARCHAR(20) NOT NULL CHECK (statement_type IN ('BS', 'IS', 'CF', 'SE')),
    report_date DATE NOT NULL,
    
    -- 資產負債表欄位 (Balance Sheet)
    current_assets DECIMAL(15,2),
    non_current_assets DECIMAL(15,2),
    total_assets DECIMAL(15,2),
    current_liabilities DECIMAL(15,2),
    non_current_liabilities DECIMAL(15,2),
    total_liabilities DECIMAL(15,2),
    shareholders_equity DECIMAL(15,2),
    
    -- 細項資產科目
    cash_and_equivalents DECIMAL(15,2),
    accounts_receivable DECIMAL(15,2),
    inventory DECIMAL(15,2),
    ppe_net DECIMAL(15,2),  -- 不動產廠房設備淨額
    
    -- 細項負債科目
    accounts_payable DECIMAL(15,2),
    short_term_debt DECIMAL(15,2),
    long_term_debt DECIMAL(15,2),
    
    -- 損益表欄位 (Income Statement)
    revenue DECIMAL(15,2),
    cost_of_revenue DECIMAL(15,2),
    gross_profit DECIMAL(15,2),
    operating_expenses DECIMAL(15,2),
    operating_income DECIMAL(15,2),
    ebitda DECIMAL(15,2),
    depreciation_amortization DECIMAL(15,2),
    interest_expense DECIMAL(15,2),
    interest_income DECIMAL(15,2),
    pretax_income DECIMAL(15,2),
    tax_expense DECIMAL(15,2),
    net_income DECIMAL(15,2),
    eps DECIMAL(8,4),  -- 每股盈餘
    eps_diluted DECIMAL(8,4),  -- 稀釋每股盈餘
    
    -- 現金流量表欄位 (Cash Flow)
    operating_cash_flow DECIMAL(15,2),
    investing_cash_flow DECIMAL(15,2),
    financing_cash_flow DECIMAL(15,2),
    free_cash_flow DECIMAL(15,2),  -- 自由現金流量
    capex DECIMAL(15,2),  -- 資本支出
    
    -- 股東權益變動表欄位 (Stockholders' Equity)
    retained_earnings DECIMAL(15,2),
    dividends_paid DECIMAL(15,2),
    
    -- 來源與狀態
    data_source VARCHAR(50) DEFAULT 'manual',  -- manual, api, import
    data_quality_score DECIMAL(3,2) DEFAULT 1.00,  -- 資料品質評分 0-1
    is_audited BOOLEAN DEFAULT false,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 外鍵約束
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    
    -- 檢查約束
    CONSTRAINT fs_total_assets_check CHECK (
        statement_type != 'BS' OR total_assets = current_assets + non_current_assets
    ),
    CONSTRAINT fs_gross_profit_check CHECK (
        statement_type != 'IS' OR gross_profit = revenue - cost_of_revenue
    )
);

-- 唯一索引 - 確保同一公司同一期間同一報表類型只有一筆記錄
CREATE UNIQUE INDEX idx_financial_statements_unique 
ON financial_statements(company_id, year_quarter, statement_type);

-- 查詢優化索引
CREATE INDEX idx_fs_company_period ON financial_statements(company_id, year_quarter DESC);
CREATE INDEX idx_fs_report_date ON financial_statements(report_date DESC);
CREATE INDEX idx_fs_statement_type ON financial_statements(statement_type);

-- =====================================================
-- 3. 財務比率計算表
-- =====================================================
CREATE TABLE financial_ratios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id VARCHAR(10) NOT NULL,
    year_quarter VARCHAR(10) NOT NULL,
    calculation_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 財務結構比率 (Financial Structure)
    debt_to_asset_ratio DECIMAL(8,4),        -- 負債比率
    debt_to_equity_ratio DECIMAL(8,4),       -- 負債權益比
    equity_ratio DECIMAL(8,4),               -- 權益比率
    long_term_debt_to_equity DECIMAL(8,4),   -- 長期負債權益比
    
    -- 償債能力比率 (Solvency)
    current_ratio DECIMAL(8,4),              -- 流動比率
    quick_ratio DECIMAL(8,4),                -- 速動比率
    cash_ratio DECIMAL(8,4),                 -- 現金比率
    interest_coverage_ratio DECIMAL(8,4),    -- 利息保障倍數
    debt_service_coverage_ratio DECIMAL(8,4), -- 償債覆蓋率
    
    -- 經營能力比率 (Activity/Efficiency)
    receivables_turnover DECIMAL(8,4),       -- 應收帳款週轉率
    inventory_turnover DECIMAL(8,4),         -- 存貨週轉率
    total_asset_turnover DECIMAL(8,4),       -- 總資產週轉率
    fixed_asset_turnover DECIMAL(8,4),       -- 固定資產週轉率
    working_capital_turnover DECIMAL(8,4),   -- 營運資金週轉率
    
    -- 週轉天數
    days_sales_outstanding DECIMAL(8,2),     -- 應收帳款收現天數
    days_inventory_outstanding DECIMAL(8,2), -- 存貨週轉天數
    days_payable_outstanding DECIMAL(8,2),   -- 應付帳款付現天數
    cash_conversion_cycle DECIMAL(8,2),      -- 現金轉換循環
    
    -- 獲利能力比率 (Profitability)
    roa DECIMAL(8,4),                        -- 資產報酬率
    roe DECIMAL(8,4),                        -- 股東權益報酬率
    roic DECIMAL(8,4),                       -- 投入資本報酬率
    gross_margin DECIMAL(8,4),               -- 毛利率
    operating_margin DECIMAL(8,4),           -- 營業利益率
    net_margin DECIMAL(8,4),                 -- 淨利率
    ebitda_margin DECIMAL(8,4),              -- EBITDA利潤率
    
    -- 現金流量比率 (Cash Flow)
    operating_cash_ratio DECIMAL(8,4),           -- 營運現金流量比率
    cash_flow_to_debt_ratio DECIMAL(8,4),        -- 現金流量負債比
    free_cash_flow_yield DECIMAL(8,4),           -- 自由現金流量收益率
    cash_flow_adequacy_ratio DECIMAL(8,4),       -- 現金流量充足率
    
    -- 市場價值比率 (Market Value) - 需要股價資料
    pe_ratio DECIMAL(8,4),                    -- 本益比
    pb_ratio DECIMAL(8,4),                    -- 股價淨值比
    ps_ratio DECIMAL(8,4),                    -- 股價營收比
    ev_ebitda DECIMAL(8,4),                   -- 企業價值/EBITDA
    dividend_yield DECIMAL(8,4),              -- 股利殖利率
    
    -- 成長率 (Growth Rates - YoY)
    revenue_growth DECIMAL(8,4),              -- 營收成長率
    net_income_growth DECIMAL(8,4),           -- 淨利成長率
    eps_growth DECIMAL(8,4),                  -- 每股盈餘成長率
    asset_growth DECIMAL(8,4),                -- 資產成長率
    
    -- 品質指標
    calculation_method VARCHAR(50) DEFAULT 'standard',
    data_completeness DECIMAL(3,2) DEFAULT 1.00,
    outlier_flag BOOLEAN DEFAULT false,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 外鍵約束
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

-- 索引優化
CREATE INDEX idx_ratios_company_period ON financial_ratios(company_id, year_quarter DESC);
CREATE INDEX idx_ratios_calculation_date ON financial_ratios(calculation_date DESC);

-- =====================================================
-- 4. 產業基準資料表
-- =====================================================
CREATE TABLE industry_benchmarks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    industry_code VARCHAR(10) NOT NULL,
    year_quarter VARCHAR(10) NOT NULL,
    
    -- 產業統計數值
    company_count INTEGER,                    -- 產業內公司數量
    
    -- 產業平均比率
    avg_roe DECIMAL(8,4),
    avg_roa DECIMAL(8,4),
    avg_current_ratio DECIMAL(8,4),
    avg_debt_ratio DECIMAL(8,4),
    avg_gross_margin DECIMAL(8,4),
    avg_operating_margin DECIMAL(8,4),
    avg_net_margin DECIMAL(8,4),
    avg_pe_ratio DECIMAL(8,4),
    avg_pb_ratio DECIMAL(8,4),
    
    -- 產業中位數
    median_roe DECIMAL(8,4),
    median_roa DECIMAL(8,4),
    median_current_ratio DECIMAL(8,4),
    median_debt_ratio DECIMAL(8,4),
    
    -- 產業分位數
    pe_25_percentile DECIMAL(8,4),
    pe_75_percentile DECIMAL(8,4),
    roe_25_percentile DECIMAL(8,4),
    roe_75_percentile DECIMAL(8,4),
    debt_25_percentile DECIMAL(8,4),
    debt_75_percentile DECIMAL(8,4),
    
    -- 產業標準差
    roe_std_dev DECIMAL(8,4),
    roa_std_dev DECIMAL(8,4),
    
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 唯一約束
    UNIQUE(industry_code, year_quarter)
);

CREATE INDEX idx_industry_benchmarks_period ON industry_benchmarks(year_quarter DESC);

-- =====================================================
-- 5. 用戶管理表
-- =====================================================
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    
    -- 權限與角色
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('admin', 'analyst', 'user', 'readonly')),
    permissions JSONB DEFAULT '{}',
    
    -- 帳戶狀態
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    last_login TIMESTAMP WITH TIME ZONE,
    login_count INTEGER DEFAULT 0,
    
    -- 個人設定
    timezone VARCHAR(50) DEFAULT 'Asia/Taipei',
    language VARCHAR(10) DEFAULT 'zh-TW',
    preferences JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active = true;

-- =====================================================
-- 6. 使用者追蹤清單
-- =====================================================
CREATE TABLE user_watchlists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    company_id VARCHAR(10) NOT NULL,
    watchlist_name VARCHAR(50) DEFAULT 'default',
    notes TEXT,
    priority INTEGER DEFAULT 0,  -- 0=normal, 1=high, -1=low
    
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    
    -- 確保同一用戶不會重複追蹤同一公司
    UNIQUE(user_id, company_id, watchlist_name)
);

CREATE INDEX idx_watchlist_user ON user_watchlists(user_id);
CREATE INDEX idx_watchlist_company ON user_watchlists(company_id);

-- =====================================================
-- 7. 觸發器：自動更新時間戳記
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 為需要的表格建立觸發器
CREATE TRIGGER update_companies_updated_at BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_financial_statements_updated_at BEFORE UPDATE ON financial_statements
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- 8. 視圖：簡化查詢
-- =====================================================

-- 公司基本財務資訊視圖
CREATE VIEW company_latest_financials AS
SELECT 
    c.company_id,
    c.company_name,
    c.industry_code,
    c.market_type,
    fs.year_quarter,
    fs.revenue,
    fs.net_income,
    fs.total_assets,
    fs.shareholders_equity,
    fs.eps,
    fr.roe,
    fr.roa,
    fr.current_ratio,
    fr.debt_to_asset_ratio
FROM companies c
LEFT JOIN financial_statements fs ON c.company_id = fs.company_id 
    AND fs.year_quarter = (
        SELECT MAX(year_quarter) 
        FROM financial_statements fs2 
        WHERE fs2.company_id = c.company_id 
        AND fs2.statement_type = 'IS'
    )
    AND fs.statement_type = 'IS'
LEFT JOIN financial_ratios fr ON c.company_id = fr.company_id 
    AND fr.year_quarter = fs.year_quarter
WHERE c.is_active = true;

-- 產業排名視圖
CREATE VIEW industry_rankings AS
SELECT 
    c.industry_code,
    c.company_id,
    c.company_name,
    fr.roe,
    fr.roa,
    RANK() OVER (PARTITION BY c.industry_code ORDER BY fr.roe DESC) as roe_rank,
    RANK() OVER (PARTITION BY c.industry_code ORDER BY fr.roa DESC) as roa_rank
FROM companies c
JOIN financial_ratios fr ON c.company_id = fr.company_id
WHERE c.is_active = true
    AND fr.year_quarter = (
        SELECT MAX(year_quarter) FROM financial_ratios 
        WHERE company_id = c.company_id
    );

-- =====================================================
-- 完成資料表建立
-- =====================================================