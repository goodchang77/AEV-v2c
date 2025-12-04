-- =====================================================
-- TimescaleDB 股價與市場資料時序表
-- =====================================================

-- 建立 TimescaleDB 擴展
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- =====================================================
-- 1. 股價資料表 (時序資料)
-- =====================================================
CREATE TABLE stock_prices (
    time TIMESTAMPTZ NOT NULL,
    company_id VARCHAR(10) NOT NULL,
    
    -- OHLCV 基本資料
    open_price DECIMAL(10,2),
    high_price DECIMAL(10,2),
    low_price DECIMAL(10,2),
    close_price DECIMAL(10,2) NOT NULL,
    volume BIGINT DEFAULT 0,
    
    -- 調整後價格
    adj_close DECIMAL(10,2),
    adj_factor DECIMAL(8,6) DEFAULT 1.000000,  -- 調整係數
    
    -- 市場資料
    market_cap DECIMAL(18,2),          -- 市值
    turnover DECIMAL(15,2),            -- 成交金額
    turnover_rate DECIMAL(6,4),        -- 週轉率
    
    -- 技術指標 (可後續計算或即時更新)
    ma5 DECIMAL(10,2),                 -- 5日移動平均
    ma10 DECIMAL(10,2),                -- 10日移動平均
    ma20 DECIMAL(10,2),                -- 20日移動平均
    ma60 DECIMAL(10,2),                -- 60日移動平均
    
    rsi_14 DECIMAL(5,2),               -- 14日RSI
    
    -- 資料品質與來源
    data_source VARCHAR(50) DEFAULT 'api',  -- api, manual, import
    is_trading_day BOOLEAN DEFAULT true,
    
    -- 約束條件
    CONSTRAINT stock_prices_positive_prices CHECK (
        open_price >= 0 AND high_price >= 0 AND 
        low_price >= 0 AND close_price >= 0
    ),
    CONSTRAINT stock_prices_ohlc_logic CHECK (
        high_price >= GREATEST(open_price, close_price) AND
        low_price <= LEAST(open_price, close_price)
    )
);

-- 建立 TimescaleDB hypertable (以時間為主要分區鍵)
SELECT create_hypertable('stock_prices', 'time', chunk_time_interval => INTERVAL '7 days');

-- 建立索引
CREATE INDEX ON stock_prices (company_id, time DESC);
CREATE INDEX ON stock_prices (time DESC, company_id);
CREATE INDEX ON stock_prices (company_id) WHERE is_trading_day = true;

-- =====================================================
-- 2. 股利資料表
-- =====================================================
CREATE TABLE dividends (
    record_date DATE NOT NULL,
    company_id VARCHAR(10) NOT NULL,
    
    -- 股利資訊
    cash_dividend DECIMAL(8,4) DEFAULT 0,     -- 現金股利
    stock_dividend DECIMAL(8,4) DEFAULT 0,    -- 股票股利
    dividend_type VARCHAR(20) NOT NULL CHECK (
        dividend_type IN ('cash', 'stock', 'mixed')
    ),
    
    -- 重要日期
    announcement_date DATE,                    -- 公告日
    ex_dividend_date DATE,                     -- 除權息日
    payment_date DATE,                         -- 發放日
    
    -- 稅務資訊
    tax_credit DECIMAL(8,4) DEFAULT 0,        -- 可扣抵稅額
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (company_id, record_date, dividend_type)
);

CREATE INDEX ON dividends (ex_dividend_date DESC);
CREATE INDEX ON dividends (company_id, record_date DESC);

-- =====================================================
-- 3. 法人買賣資料表
-- =====================================================
CREATE TABLE institutional_trading (
    trade_date DATE NOT NULL,
    company_id VARCHAR(10) NOT NULL,
    
    -- 外資
    foreign_buy_volume BIGINT DEFAULT 0,
    foreign_sell_volume BIGINT DEFAULT 0,
    foreign_net_volume BIGINT DEFAULT 0,
    foreign_buy_amount DECIMAL(15,2) DEFAULT 0,
    foreign_sell_amount DECIMAL(15,2) DEFAULT 0,
    foreign_net_amount DECIMAL(15,2) DEFAULT 0,
    
    -- 投信
    fund_buy_volume BIGINT DEFAULT 0,
    fund_sell_volume BIGINT DEFAULT 0,
    fund_net_volume BIGINT DEFAULT 0,
    fund_buy_amount DECIMAL(15,2) DEFAULT 0,
    fund_sell_amount DECIMAL(15,2) DEFAULT 0,
    fund_net_amount DECIMAL(15,2) DEFAULT 0,
    
    -- 自營商
    dealer_buy_volume BIGINT DEFAULT 0,
    dealer_sell_volume BIGINT DEFAULT 0,
    dealer_net_volume BIGINT DEFAULT 0,
    dealer_buy_amount DECIMAL(15,2) DEFAULT 0,
    dealer_sell_amount DECIMAL(15,2) DEFAULT 0,
    dealer_net_amount DECIMAL(15,2) DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (company_id, trade_date)
);

CREATE INDEX ON institutional_trading (trade_date DESC);
CREATE INDEX ON institutional_trading (company_id, trade_date DESC);

-- =====================================================
-- 4. 市場指數資料表
-- =====================================================
CREATE TABLE market_indices (
    time TIMESTAMPTZ NOT NULL,
    index_code VARCHAR(20) NOT NULL,  -- TAIEX, OTC, etc.
    index_name VARCHAR(50),
    
    -- 指數資料
    open_value DECIMAL(10,2),
    high_value DECIMAL(10,2),
    low_value DECIMAL(10,2),
    close_value DECIMAL(10,2) NOT NULL,
    
    -- 市場統計
    total_volume BIGINT,
    total_value DECIMAL(18,2),
    up_stocks INTEGER,
    down_stocks INTEGER,
    unchanged_stocks INTEGER,
    
    PRIMARY KEY (time, index_code)
);

-- 建立 hypertable
SELECT create_hypertable('market_indices', 'time', chunk_time_interval => INTERVAL '30 days');

CREATE INDEX ON market_indices (index_code, time DESC);

-- =====================================================
-- 5. 連續合約函數：取得最新價格
-- =====================================================

-- 取得公司最新股價
CREATE OR REPLACE FUNCTION get_latest_price(p_company_id VARCHAR(10))
RETURNS TABLE(
    company_id VARCHAR(10),
    latest_time TIMESTAMPTZ,
    close_price DECIMAL(10,2),
    volume BIGINT,
    market_cap DECIMAL(18,2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        sp.company_id,
        sp.time as latest_time,
        sp.close_price,
        sp.volume,
        sp.market_cap
    FROM stock_prices sp
    WHERE sp.company_id = p_company_id
        AND sp.is_trading_day = true
    ORDER BY sp.time DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- 計算股價技術指標
CREATE OR REPLACE FUNCTION calculate_moving_average(
    p_company_id VARCHAR(10),
    p_days INTEGER,
    p_end_date TIMESTAMPTZ DEFAULT NOW()
)
RETURNS DECIMAL(10,2) AS $$
DECLARE
    result DECIMAL(10,2);
BEGIN
    SELECT AVG(close_price) INTO result
    FROM stock_prices
    WHERE company_id = p_company_id
        AND time <= p_end_date
        AND is_trading_day = true
    ORDER BY time DESC
    LIMIT p_days;
    
    RETURN COALESCE(result, 0);
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 6. 壓縮政策：自動壓縮舊資料
-- =====================================================

-- 為股價資料設定壓縮政策 (壓縮超過30天的資料)
SELECT add_compression_policy('stock_prices', INTERVAL '30 days');

-- 為市場指數設定壓縮政策
SELECT add_compression_policy('market_indices', INTERVAL '90 days');

-- =====================================================
-- 7. 資料保留政策：自動刪除過舊資料
-- =====================================================

-- 保留5年股價資料，超過的自動刪除
SELECT add_retention_policy('stock_prices', INTERVAL '5 years');

-- 保留7年市場指數資料
SELECT add_retention_policy('market_indices', INTERVAL '7 years');

-- =====================================================
-- 8. 聚合視圖：預計算常用統計
-- =====================================================

-- 每日市場摘要 (連續聚合)
CREATE MATERIALIZED VIEW daily_market_summary
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', time) AS day,
    COUNT(*) as total_stocks,
    AVG(close_price) as avg_price,
    SUM(volume) as total_volume,
    SUM(turnover) as total_turnover
FROM stock_prices
WHERE is_trading_day = true
GROUP BY day;

-- 為聚合視圖建立刷新政策
SELECT add_continuous_aggregate_policy('daily_market_summary',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

-- 週線股價資料
CREATE MATERIALIZED VIEW weekly_stock_prices
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 week', time) AS week,
    company_id,
    first(open_price, time) as open_price,
    max(high_price) as high_price,
    min(low_price) as low_price,
    last(close_price, time) as close_price,
    sum(volume) as volume
FROM stock_prices
WHERE is_trading_day = true
GROUP BY week, company_id;

-- =====================================================
-- 完成時序資料表建立
-- =====================================================