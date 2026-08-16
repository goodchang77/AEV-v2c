-- =====================================================
-- 投資組合部位表
-- （對齊 src/models.py 的 PortfolioPosition）
-- 冪等：可重複執行
-- =====================================================

CREATE TABLE IF NOT EXISTS portfolio_positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    company_id VARCHAR(10) NOT NULL,
    shares DECIMAL(15,2) NOT NULL DEFAULT 0,
    cost_basis DECIMAL(15,4) NOT NULL DEFAULT 0,   -- 每股成本
    current_price DECIMAL(15,4),                   -- 最新股價（可由外部同步）
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    UNIQUE(user_id, company_id)
);

CREATE INDEX IF NOT EXISTS idx_portfolio_user ON portfolio_positions(user_id);
