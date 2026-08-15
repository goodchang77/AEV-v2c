-- =====================================================
-- 評價模型結果表 與 股價資料表
-- （對齊 src/models.py 的 ValuationResult / StockPrice）
-- 冪等：可重複執行
-- =====================================================

-- =====================================================
-- 8. 評價模型結果表
-- =====================================================
CREATE TABLE IF NOT EXISTS valuation_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id VARCHAR(10) NOT NULL,
    valuation_date DATE NOT NULL,
    model_type VARCHAR(50) NOT NULL,  -- DCF/DDM/PE/PB/EV_EBITDA

    -- 評價參數
    discount_rate DECIMAL(8,4),
    growth_rate DECIMAL(8,4),
    terminal_value DECIMAL(15,2),

    -- 評價結果
    fair_value DECIMAL(12,2),
    current_price DECIMAL(8,2),
    upside_downside DECIMAL(8,4),

    -- 敏感性分析與假設
    sensitivity_analysis JSONB,
    assumptions JSONB,

    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_valuation_company_date
    ON valuation_results(company_id, valuation_date DESC);

-- =====================================================
-- 9. 股價資料表
-- =====================================================
CREATE TABLE IF NOT EXISTS stock_prices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    open_price DECIMAL(8,2),
    high_price DECIMAL(8,2),
    low_price DECIMAL(8,2),
    close_price DECIMAL(8,2),
    volume BIGINT,
    adj_close DECIMAL(8,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    UNIQUE(company_id, trade_date)
);

CREATE INDEX IF NOT EXISTS idx_stock_prices_company_date
    ON stock_prices(company_id, trade_date DESC);
