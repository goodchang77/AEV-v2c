# 財務分析與企業評價系統開發指南

## 專案概述
基於IFRS 13公允價值衡量原則和台灣市場實務的企業級財務分析與評價系統，提供完整的財務報表分析、企業評價、風險評估和投資決策支援功能。

## 系統架構設計

### 整體架構
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端層 (UI)    │    │   API Gateway   │    │   外部資料源     │
│                 │    │                 │    │                 │
│ • React/Vue.js  │◄──►│ • 路由管理       │◄──►│ • 公開資訊觀測站 │
│ • 圖表視覺化     │    │ • 身份驗證       │    │ • 證交所API      │
│ • 響應式設計     │    │ • 限流控制       │    │ • 財經資料庫     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   應用服務層     │    │   業務邏輯層     │    │   資料處理層     │
│                 │    │                 │    │                 │
│ • 用戶管理       │◄──►│ • 財務分析引擎   │◄──►│ • 資料爬蟲       │
│ • 報告生成       │    │ • 評價模型計算   │    │ • 資料清理       │
│ • 通知系統       │    │ • 風險評估       │    │ • 資料同步       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   資料訪問層     │    │   快取層         │    │   資料庫層       │
│                 │    │                 │    │                 │
│ • ORM映射       │◄──►│ • Redis快取     │◄──►│ • PostgreSQL    │
│ • 資料驗證       │    │ • 計算結果快取   │    │ • 時序資料庫     │
│ • 連接池管理     │    │ • 會話管理       │    │ • 檔案儲存       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 微服務架構
```
財務分析系統
├── 用戶服務 (User Service)
├── 資料服務 (Data Service)
├── 分析服務 (Analytics Service)
├── 評價服務 (Valuation Service)
├── 報告服務 (Report Service)
├── 通知服務 (Notification Service)
└── 監控服務 (Monitoring Service)
```

## 技術棧選擇

### 前端技術棧
- **框架**: React 18+ with TypeScript
- **UI組件**: Ant Design / Material-UI
- **圖表庫**: ECharts / D3.js / Chart.js
- **狀態管理**: Redux Toolkit / Zustand
- **建構工具**: Vite / Webpack
- **樣式**: Tailwind CSS / Styled-Components

### 後端技術棧
- **主框架**: FastAPI (Python) / Spring Boot (Java) / Express.js (Node.js)
- **資料庫**: PostgreSQL (主要) + TimescaleDB (時序資料)
- **快取**: Redis + Redis Cluster
- **訊息佇列**: RabbitMQ / Apache Kafka
- **搜尋引擎**: Elasticsearch
- **任務調度**: Celery / Airflow

### DevOps與部署
- **容器化**: Docker + Docker Compose
- **編排**: Kubernetes
- **CI/CD**: GitLab CI / GitHub Actions
- **監控**: Prometheus + Grafana
- **日誌**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **雲端平台**: AWS / Azure / GCP

## 資料庫設計

### 核心資料表結構

#### 1. 公司基本資料表 (companies)
```sql
CREATE TABLE companies (
    company_id VARCHAR(10) PRIMARY KEY,
    company_name VARCHAR(100) NOT NULL,
    industry_code VARCHAR(10),
    market_type VARCHAR(20), -- 上市/上櫃/興櫃
    listing_date DATE,
    capital_amount DECIMAL(15,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_companies_industry ON companies(industry_code);
CREATE INDEX idx_companies_market ON companies(market_type);
```

#### 2. 財務報表資料表 (financial_statements)
```sql
CREATE TABLE financial_statements (
    id BIGSERIAL PRIMARY KEY,
    company_id VARCHAR(10) NOT NULL,
    report_type VARCHAR(20) NOT NULL, -- annual/quarterly
    year_quarter VARCHAR(10) NOT NULL, -- 2024Q1, 2024
    statement_type VARCHAR(20) NOT NULL, -- BS/IS/CF/SE
    
    -- 資產負債表欄位
    current_assets DECIMAL(15,2),
    non_current_assets DECIMAL(15,2),
    total_assets DECIMAL(15,2),
    current_liabilities DECIMAL(15,2),
    non_current_liabilities DECIMAL(15,2),
    total_liabilities DECIMAL(15,2),
    shareholders_equity DECIMAL(15,2),
    
    -- 損益表欄位
    revenue DECIMAL(15,2),
    gross_profit DECIMAL(15,2),
    operating_income DECIMAL(15,2),
    net_income DECIMAL(15,2),
    eps DECIMAL(8,4),
    
    -- 現金流量表欄位
    operating_cash_flow DECIMAL(15,2),
    investing_cash_flow DECIMAL(15,2),
    financing_cash_flow DECIMAL(15,2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE UNIQUE INDEX idx_financial_statements_unique 
ON financial_statements(company_id, year_quarter, statement_type);
```

#### 3. 財務比率計算表 (financial_ratios)
```sql
CREATE TABLE financial_ratios (
    id BIGSERIAL PRIMARY KEY,
    company_id VARCHAR(10) NOT NULL,
    year_quarter VARCHAR(10) NOT NULL,
    
    -- 財務結構比率
    debt_to_asset_ratio DECIMAL(8,4),
    equity_ratio DECIMAL(8,4),
    
    -- 償債能力比率
    current_ratio DECIMAL(8,4),
    quick_ratio DECIMAL(8,4),
    interest_coverage_ratio DECIMAL(8,4),
    
    -- 經營能力比率
    receivables_turnover DECIMAL(8,4),
    inventory_turnover DECIMAL(8,4),
    total_asset_turnover DECIMAL(8,4),
    
    -- 獲利能力比率
    roa DECIMAL(8,4),
    roe DECIMAL(8,4),
    gross_margin DECIMAL(8,4),
    operating_margin DECIMAL(8,4),
    net_margin DECIMAL(8,4),
    
    -- 現金流量比率
    operating_cash_ratio DECIMAL(8,4),
    cash_flow_adequacy_ratio DECIMAL(8,4),
    
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE INDEX idx_ratios_company_period ON financial_ratios(company_id, year_quarter);
```

#### 4. 評價模型結果表 (valuation_results)
```sql
CREATE TABLE valuation_results (
    id BIGSERIAL PRIMARY KEY,
    company_id VARCHAR(10) NOT NULL,
    valuation_date DATE NOT NULL,
    model_type VARCHAR(50) NOT NULL, -- DCF/DDM/PE/PB/EV_EBITDA
    
    -- 評價參數
    discount_rate DECIMAL(8,4),
    growth_rate DECIMAL(8,4),
    terminal_value DECIMAL(15,2),
    
    -- 評價結果
    fair_value DECIMAL(12,2),
    current_price DECIMAL(8,2),
    upside_downside DECIMAL(8,4),
    
    -- 敏感性分析
    sensitivity_analysis JSONB,
    assumptions JSONB,
    
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);
```

#### 5. 股價資料表 (stock_prices) - 時序資料
```sql
-- 使用TimescaleDB擴展
CREATE TABLE stock_prices (
    time TIMESTAMPTZ NOT NULL,
    company_id VARCHAR(10) NOT NULL,
    open_price DECIMAL(8,2),
    high_price DECIMAL(8,2),
    low_price DECIMAL(8,2),
    close_price DECIMAL(8,2),
    volume BIGINT,
    adj_close DECIMAL(8,2)
);

-- 創建TimescaleDB hypertable
SELECT create_hypertable('stock_prices', 'time');
CREATE INDEX ON stock_prices (company_id, time DESC);
```

#### 6. 產業同業比較表 (industry_benchmarks)
```sql
CREATE TABLE industry_benchmarks (
    id BIGSERIAL PRIMARY KEY,
    industry_code VARCHAR(10) NOT NULL,
    year_quarter VARCHAR(10) NOT NULL,
    
    -- 產業平均比率
    avg_roe DECIMAL(8,4),
    avg_roa DECIMAL(8,4),
    avg_current_ratio DECIMAL(8,4),
    avg_debt_ratio DECIMAL(8,4),
    avg_pe_ratio DECIMAL(8,4),
    avg_pb_ratio DECIMAL(8,4),
    
    -- 產業分位數
    pe_25_percentile DECIMAL(8,4),
    pe_75_percentile DECIMAL(8,4),
    roe_25_percentile DECIMAL(8,4),
    roe_75_percentile DECIMAL(8,4),
    
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 7. 用戶與權限管理
```sql
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user', -- admin/analyst/user
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_watchlists (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    company_id VARCHAR(10) NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (company_id) REFERENCES companies(company_id),
    UNIQUE(user_id, company_id)
);
```

### 資料庫最佳化策略

#### 索引設計
```sql
-- 複合索引for查詢最佳化
CREATE INDEX idx_financial_statements_company_time 
ON financial_statements(company_id, year_quarter DESC);

-- 部分索引for活躍公司
CREATE INDEX idx_active_companies 
ON companies(company_id) WHERE market_type IN ('上市', '上櫃');

-- 表達式索引for計算欄位
CREATE INDEX idx_market_cap 
ON stock_prices((close_price * volume));
```

#### 分區策略
```sql
-- 依年份分區financial_statements表
CREATE TABLE financial_statements_2024 PARTITION OF financial_statements
    FOR VALUES FROM ('2024') TO ('2025');
```

## API設計規範

### RESTful API結構
```
財務分析API v1.0
├── /api/v1/companies
│   ├── GET /                     # 取得公司列表
│   ├── GET /{company_id}         # 取得公司詳情
│   ├── GET /{company_id}/financials # 財務報表
│   └── GET /{company_id}/ratios     # 財務比率
├── /api/v1/analysis
│   ├── POST /dcf                 # DCF評價計算
│   ├── POST /peer-comparison     # 同業比較分析
│   └── POST /risk-assessment     # 風險評估
├── /api/v1/reports
│   ├── POST /generate            # 生成分析報告
│   └── GET /{report_id}          # 下載報告
└── /api/v1/data
    ├── POST /sync                # 資料同步
    └── GET /market-data          # 市場資料
```

### API響應格式標準
```json
{
  "success": true,
  "data": {
    "company": {
      "company_id": "2330",
      "name": "台積電",
      "industry": "半導體"
    }
  },
  "meta": {
    "timestamp": "2024-01-01T00:00:00Z",
    "version": "1.0",
    "total": 100,
    "page": 1,
    "limit": 20
  },
  "errors": []
}
```

## 核心業務邏輯實現

### 1. 財務比率計算引擎
```python
# financial_calculator.py
class FinancialRatioCalculator:
    def __init__(self, financial_data: Dict):
        self.data = financial_data
    
    def calculate_liquidity_ratios(self) -> Dict[str, float]:
        """計算流動性比率"""
        return {
            'current_ratio': self.data['current_assets'] / self.data['current_liabilities'],
            'quick_ratio': (self.data['current_assets'] - self.data['inventory']) / self.data['current_liabilities'],
            'cash_ratio': self.data['cash'] / self.data['current_liabilities']
        }
    
    def calculate_profitability_ratios(self) -> Dict[str, float]:
        """計算獲利能力比率"""
        return {
            'roa': self.data['net_income'] / self.data['total_assets'],
            'roe': self.data['net_income'] / self.data['shareholders_equity'],
            'gross_margin': self.data['gross_profit'] / self.data['revenue'],
            'net_margin': self.data['net_income'] / self.data['revenue']
        }
    
    def calculate_efficiency_ratios(self) -> Dict[str, float]:
        """計算經營效率比率"""
        return {
            'asset_turnover': self.data['revenue'] / self.data['total_assets'],
            'receivables_turnover': self.data['revenue'] / self.data['avg_receivables'],
            'inventory_turnover': self.data['cogs'] / self.data['avg_inventory']
        }
```

### 2. DCF評價模型
```python
# valuation_models.py
import numpy as np
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class DCFParameters:
    revenue_growth_rates: List[float]
    terminal_growth_rate: float
    discount_rate: float
    tax_rate: float
    capex_rate: float
    working_capital_rate: float

class DCFValuationModel:
    def __init__(self, params: DCFParameters):
        self.params = params
    
    def calculate_free_cash_flow(self, revenue: float, year: int) -> float:
        """計算自由現金流量"""
        projected_revenue = revenue * (1 + self.params.revenue_growth_rates[year-1])
        ebitda = projected_revenue * 0.20  # 假設EBITDA margin
        ebit = ebitda - (projected_revenue * 0.05)  # 假設折舊攤銷
        tax = ebit * self.params.tax_rate
        nopat = ebit - tax
        
        capex = projected_revenue * self.params.capex_rate
        wc_investment = projected_revenue * self.params.working_capital_rate
        
        fcf = nopat - capex - wc_investment
        return fcf
    
    def calculate_terminal_value(self, final_fcf: float) -> float:
        """計算終值"""
        terminal_fcf = final_fcf * (1 + self.params.terminal_growth_rate)
        return terminal_fcf / (self.params.discount_rate - self.params.terminal_growth_rate)
    
    def calculate_enterprise_value(self, base_revenue: float) -> Dict[str, float]:
        """計算企業價值"""
        dcf_years = len(self.params.revenue_growth_rates)
        cash_flows = []
        
        for year in range(1, dcf_years + 1):
            fcf = self.calculate_free_cash_flow(base_revenue, year)
            pv_fcf = fcf / ((1 + self.params.discount_rate) ** year)
            cash_flows.append(pv_fcf)
        
        final_fcf = self.calculate_free_cash_flow(base_revenue, dcf_years)
        terminal_value = self.calculate_terminal_value(final_fcf)
        pv_terminal = terminal_value / ((1 + self.params.discount_rate) ** dcf_years)
        
        enterprise_value = sum(cash_flows) + pv_terminal
        
        return {
            'enterprise_value': enterprise_value,
            'dcf_value': sum(cash_flows),
            'terminal_value': pv_terminal,
            'cash_flows': cash_flows
        }
```

### 3. 同業比較分析
```python
# peer_analysis.py
class PeerComparisonAnalyzer:
    def __init__(self, db_connection):
        self.db = db_connection
    
    def get_industry_peers(self, company_id: str, industry_code: str) -> List[str]:
        """取得同業公司列表"""
        query = """
        SELECT company_id, company_name, market_cap
        FROM companies c
        LEFT JOIN stock_prices sp ON c.company_id = sp.company_id
        WHERE industry_code = %s 
        AND company_id != %s
        AND market_cap > 1000000000  -- 市值大於10億
        ORDER BY market_cap DESC
        LIMIT 10
        """
        return self.db.execute(query, (industry_code, company_id))
    
    def calculate_relative_valuation(self, target_company: str, peer_companies: List[str]) -> Dict:
        """計算相對評價"""
        ratios = ['pe_ratio', 'pb_ratio', 'ev_ebitda', 'roe', 'roa']
        results = {}
        
        for ratio in ratios:
            peer_values = self.get_peer_ratio_values(peer_companies, ratio)
            target_value = self.get_company_ratio_value(target_company, ratio)
            
            results[ratio] = {
                'target': target_value,
                'peer_median': np.median(peer_values),
                'peer_mean': np.mean(peer_values),
                'percentile': self.calculate_percentile(target_value, peer_values),
                'peer_range': (min(peer_values), max(peer_values))
            }
        
        return results
```

### 4. 風險評估系統
```python
# risk_assessment.py
class RiskAssessmentEngine:
    def __init__(self):
        self.risk_indicators = {
            'financial_distress': self.assess_financial_distress,
            'liquidity_risk': self.assess_liquidity_risk,
            'profitability_trend': self.assess_profitability_trend,
            'leverage_risk': self.assess_leverage_risk
        }
    
    def assess_overall_risk(self, company_id: str) -> Dict[str, Any]:
        """綜合風險評估"""
        risk_scores = {}
        
        for risk_type, assessment_func in self.risk_indicators.items():
            risk_scores[risk_type] = assessment_func(company_id)
        
        # 計算綜合風險評級
        overall_score = self.calculate_composite_score(risk_scores)
        risk_grade = self.determine_risk_grade(overall_score)
        
        return {
            'overall_grade': risk_grade,
            'overall_score': overall_score,
            'detailed_scores': risk_scores,
            'recommendations': self.generate_recommendations(risk_scores)
        }
    
    def assess_financial_distress(self, company_id: str) -> float:
        """財務危機評估 - 基於Altman Z-Score"""
        ratios = self.get_latest_ratios(company_id)
        
        # Altman Z-Score計算
        z_score = (
            1.2 * ratios['working_capital_to_assets'] +
            1.4 * ratios['retained_earnings_to_assets'] +
            3.3 * ratios['ebit_to_assets'] +
            0.6 * ratios['market_cap_to_liabilities'] +
            1.0 * ratios['sales_to_assets']
        )
        
        # 將Z-Score轉換為0-100的風險分數
        if z_score > 2.99:
            return 10  # 低風險
        elif z_score > 1.81:
            return 50  # 中等風險
        else:
            return 90  # 高風險
```

## 測試環境建立

### 1. 單元測試框架
```python
# tests/test_financial_calculator.py
import pytest
from src.financial_calculator import FinancialRatioCalculator

class TestFinancialRatioCalculator:
    @pytest.fixture
    def sample_financial_data(self):
        return {
            'current_assets': 1000000,
            'current_liabilities': 500000,
            'inventory': 200000,
            'cash': 100000,
            'net_income': 150000,
            'total_assets': 2000000,
            'shareholders_equity': 1200000,
            'revenue': 800000,
            'gross_profit': 300000
        }
    
    def test_current_ratio_calculation(self, sample_financial_data):
        calculator = FinancialRatioCalculator(sample_financial_data)
        ratios = calculator.calculate_liquidity_ratios()
        
        expected_current_ratio = 1000000 / 500000  # 2.0
        assert ratios['current_ratio'] == expected_current_ratio
    
    def test_roe_calculation(self, sample_financial_data):
        calculator = FinancialRatioCalculator(sample_financial_data)
        ratios = calculator.calculate_profitability_ratios()
        
        expected_roe = 150000 / 1200000  # 0.125
        assert abs(ratios['roe'] - expected_roe) < 0.001

# tests/test_dcf_model.py
class TestDCFValuationModel:
    @pytest.fixture
    def dcf_parameters(self):
        return DCFParameters(
            revenue_growth_rates=[0.15, 0.12, 0.10, 0.08, 0.05],
            terminal_growth_rate=0.03,
            discount_rate=0.10,
            tax_rate=0.25,
            capex_rate=0.05,
            working_capital_rate=0.02
        )
    
    def test_enterprise_value_calculation(self, dcf_parameters):
        model = DCFValuationModel(dcf_parameters)
        result = model.calculate_enterprise_value(base_revenue=1000000)
        
        assert result['enterprise_value'] > 0
        assert 'terminal_value' in result
        assert len(result['cash_flows']) == 5
```

### 2. 整合測試
```python
# tests/test_integration.py
class TestIntegrationAPI:
    @pytest.fixture(scope="session")
    def test_client(self):
        from src.main import app
        with TestClient(app) as client:
            yield client
    
    def test_financial_analysis_workflow(self, test_client):
        # 1. 取得公司資料
        response = test_client.get("/api/v1/companies/2330")
        assert response.status_code == 200
        
        # 2. 計算財務比率
        response = test_client.get("/api/v1/companies/2330/ratios")
        assert response.status_code == 200
        ratios = response.json()['data']
        assert 'roe' in ratios
        
        # 3. 執行DCF評價
        dcf_params = {
            "revenue_growth_rates": [0.15, 0.12, 0.10, 0.08, 0.05],
            "terminal_growth_rate": 0.03,
            "discount_rate": 0.10
        }
        response = test_client.post("/api/v1/analysis/dcf", json=dcf_params)
        assert response.status_code == 200
```

### 3. 效能測試
```python
# tests/test_performance.py
import time
import concurrent.futures

class TestPerformance:
    def test_concurrent_ratio_calculations(self):
        """測試並發財務比率計算效能"""
        companies = ['2330', '2317', '1301', '2454', '6505']
        
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(self.calculate_ratios, company) 
                      for company in companies]
            results = [future.result() for future in futures]
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        assert execution_time < 5.0  # 應在5秒內完成
        assert len(results) == 5
    
    def test_database_query_performance(self):
        """測試資料庫查詢效能"""
        start_time = time.time()
        
        # 執行複雜查詢
        result = self.db.execute("""
            SELECT c.company_id, c.company_name, 
                   AVG(fr.roe) as avg_roe,
                   COUNT(*) as data_points
            FROM companies c
            JOIN financial_ratios fr ON c.company_id = fr.company_id
            WHERE fr.year_quarter >= '2020Q1'
            GROUP BY c.company_id, c.company_name
            HAVING COUNT(*) >= 12
            ORDER BY avg_roe DESC
            LIMIT 50
        """)
        
        end_time = time.time()
        query_time = end_time - start_time
        
        assert query_time < 2.0  # 查詢應在2秒內完成
        assert len(result) > 0
```

### 4. 測試資料準備
```python
# tests/fixtures/test_data_generator.py
class TestDataGenerator:
    @staticmethod
    def create_sample_company_data():
        return {
            'company_id': '9999',
            'company_name': '測試公司',
            'industry_code': 'TEST',
            'market_type': '上市',
            'listing_date': '2020-01-01'
        }
    
    @staticmethod
    def create_sample_financial_statements(company_id: str, periods: int = 12):
        statements = []
        for i in range(periods):
            year = 2022 + (i // 4)
            quarter = (i % 4) + 1
            period = f"{year}Q{quarter}"
            
            statements.append({
                'company_id': company_id,
                'year_quarter': period,
                'revenue': 1000000 * (1 + i * 0.05),
                'net_income': 100000 * (1 + i * 0.03),
                'total_assets': 5000000 * (1 + i * 0.02),
                'shareholders_equity': 3000000 * (1 + i * 0.04)
            })
        return statements

# conftest.py - pytest設定
@pytest.fixture(scope="session")
def test_database():
    """建立測試資料庫"""
    from src.database import create_database_engine
    
    # 建立測試資料庫連線
    test_engine = create_database_engine("postgresql://test:test@localhost:5432/test_db")
    
    # 建立測試資料表
    create_test_tables(test_engine)
    
    # 插入測試資料
    load_test_data(test_engine)
    
    yield test_engine
    
    # 清理測試資料
    cleanup_test_data(test_engine)
```

## 系統監控與日誌

### 1. 應用監控
```python
# monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# 定義監控指標
REQUEST_COUNT = Counter('http_requests_total', 'HTTP requests count', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency')
ACTIVE_USERS = Gauge('active_users_total', 'Number of active users')
CALCULATION_ERRORS = Counter('calculation_errors_total', 'Calculation errors count', ['model_type'])

class MetricsMiddleware:
    def __init__(self):
        self.start_time = time.time()
    
    def __call__(self, request, response):
        REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
        
        processing_time = time.time() - self.start_time
        REQUEST_LATENCY.observe(processing_time)
        
        return response

# monitoring/health_check.py
class HealthCheckService:
    def __init__(self, db_connection, redis_connection):
        self.db = db_connection
        self.redis = redis_connection
    
    def check_database_health(self) -> bool:
        try:
            result = self.db.execute("SELECT 1")
            return result is not None
        except Exception:
            return False
    
    def check_cache_health(self) -> bool:
        try:
            self.redis.ping()
            return True
        except Exception:
            return False
    
    def get_health_status(self) -> Dict[str, Any]:
        return {
            'status': 'healthy' if self.is_healthy() else 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'database': self.check_database_health(),
                'cache': self.check_cache_health(),
                'api': True
            }
        }
```

### 2. 結構化日誌
```python
# logging/logger.py
import structlog
import logging.config

def setup_logging():
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "format": "%(message)s",
                "class": "pythonjsonlogger.jsonlogger.JsonFormatter"
            }
        },
        "handlers": {
            "default": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "json"
            }
        },
        "loggers": {
            "": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False
            }
        }
    })

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

# 使用結構化日誌
logger = structlog.get_logger()

def log_calculation_event(company_id: str, model_type: str, result: Dict):
    logger.info(
        "valuation_calculated",
        company_id=company_id,
        model_type=model_type,
        fair_value=result.get('fair_value'),
        calculation_time=result.get('processing_time')
    )
```

## 部署與運維

### 1. Docker化部署
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 複製requirements並安裝Python依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式碼
COPY src/ ./src/
COPY config/ ./config/

# 建立非root用戶
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Docker Compose開發環境
```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/financial_db
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    volumes:
      - ./src:/app/src
      - ./config:/app/config

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: financial_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  timescaledb:
    image: timescale/timescaledb:2.11.0-pg15
    environment:
      POSTGRES_DB: timeseries_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5433:5432"
    volumes:
      - timescale_data:/var/lib/postgresql/data

volumes:
  postgres_data:
  redis_data:
  timescale_data:
```

### 3. Kubernetes部署配置
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: financial-analysis-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: financial-analysis-api
  template:
    metadata:
      labels:
        app: financial-analysis-api
    spec:
      containers:
      - name: api
        image: financial-analysis:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: database-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: financial-analysis-service
spec:
  selector:
    app: financial-analysis-api
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: LoadBalancer
```

### 4. CI/CD Pipeline
```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run tests
      run: |
        pytest tests/ --cov=src --cov-report=xml
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
        REDIS_URL: redis://localhost:6379
    
    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  build-and-deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker image
      run: |
        docker build -t financial-analysis:${{ github.sha }} .
        docker tag financial-analysis:${{ github.sha }} financial-analysis:latest
    
    - name: Deploy to staging
      run: |
        # 部署到staging環境的腳本
        echo "Deploying to staging..."
    
    - name: Run integration tests
      run: |
        # 在staging環境執行整合測試
        echo "Running integration tests..."
    
    - name: Deploy to production
      if: success()
      run: |
        # 部署到生產環境
        echo "Deploying to production..."
```

## 開發工作流程

### 1. 專案初始化
```bash
# 1. 克隆專案
git clone <repository-url>
cd financial-analysis-system

# 2. 建立虛擬環境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 3. 安裝依賴
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. 設定環境變數
cp .env.example .env
# 編輯 .env 檔案設定資料庫連線等資訊

# 5. 初始化資料庫
python scripts/init_db.py

# 6. 執行測試
pytest tests/

# 7. 啟動開發伺服器
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 開發環境設定
```python
# config/settings.py
from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # 資料庫設定
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/financial_db"
    TIMESERIES_DATABASE_URL: str = "postgresql://postgres:password@localhost:5433/timeseries_db"
    
    # Redis設定
    REDIS_URL: str = "redis://localhost:6379"
    
    # API設定
    API_VERSION: str = "v1"
    DEBUG: bool = False
    
    # 外部API設定
    TWSE_API_KEY: Optional[str] = None
    ALPHA_VANTAGE_API_KEY: Optional[str] = None
    
    # 日誌設定
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### 3. 程式碼品質控制
```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py311']
include = '\.pyi?$'

[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3

[tool.pylint.main]
max-line-length = 100
disable = [
    "missing-function-docstring",
    "missing-class-docstring",
    "too-few-public-methods"
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = "-v --tb=short --cov=src --cov-report=term-missing"
```

### 4. Git工作流程
```bash
# 1. 功能開發分支
git checkout -b feature/dcf-model-enhancement

# 2. 開發過程中定期提交
git add .
git commit -m "feat: enhance DCF model with sensitivity analysis"

# 3. 推送並建立Pull Request
git push origin feature/dcf-model-enhancement

# 4. 程式碼審查後合併到develop分支
git checkout develop
git merge feature/dcf-model-enhancement

# 5. 發布到main分支
git checkout main
git merge develop
git tag v1.2.0
git push origin main --tags
```

## 安全性考量

### 1. API安全
```python
# security/auth.py
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta

security = HTTPBearer()

class AuthenticationService:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.algorithm = "HS256"
    
    def create_access_token(self, user_id: int, expires_delta: timedelta = None):
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        
        to_encode = {"sub": str(user_id), "exp": expire}
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, credentials: HTTPAuthorizationCredentials = Depends(security)):
        try:
            payload = jwt.decode(credentials.credentials, self.secret_key, algorithms=[self.algorithm])
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=401, detail="Invalid token")
            return user_id
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

# 使用認證裝飾器
@app.get("/api/v1/protected-endpoint")
async def protected_endpoint(current_user: str = Depends(auth_service.verify_token)):
    return {"message": f"Hello, user {current_user}"}
```

### 2. 資料庫安全
```python
# security/database.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import ssl

class SecureDatabaseConnection:
    def __init__(self, database_url: str):
        # 使用SSL連線
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        
        engine = create_engine(
            database_url,
            connect_args={
                "sslmode": "require",
                "sslcert": "client-cert.pem",
                "sslkey": "client-key.pem",
                "sslrootcert": "ca-cert.pem",
            },
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False
        )
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    def execute_secure_query(self, query: str, params: dict = None):
        """防SQL注入的查詢執行"""
        with self.SessionLocal() as session:
            result = session.execute(text(query), params or {})
            return result.fetchall()
```

### 3. 輸入驗證
```python
# validation/schemas.py
from pydantic import BaseModel, validator, Field
from typing import List, Optional
from decimal import Decimal

class DCFRequest(BaseModel):
    company_id: str = Field(..., regex=r"^\d{4}$", description="4位數股票代碼")
    revenue_growth_rates: List[float] = Field(..., min_items=3, max_items=10)
    terminal_growth_rate: float = Field(..., ge=0, le=0.1, description="終值成長率0-10%")
    discount_rate: float = Field(..., ge=0.01, le=0.3, description="折現率1-30%")
    
    @validator('revenue_growth_rates')
    def validate_growth_rates(cls, v):
        for rate in v:
            if not -0.5 <= rate <= 1.0:  # -50% to 100%
                raise ValueError("成長率必須在-50%到100%之間")
        return v

class CompanySearchRequest(BaseModel):
    keyword: Optional[str] = Field(None, max_length=50)
    industry_code: Optional[str] = Field(None, regex=r"^[A-Z0-9]{2,10}$")
    market_type: Optional[str] = Field(None, regex=r"^(上市|上櫃|興櫃)$")
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)
```

---

## 專案檢查清單

### 開發階段 ✓
- [ ] 環境設定與依賴安裝
- [ ] 資料庫架構建立
- [ ] 核心業務邏輯實作
- [ ] API端點開發
- [ ] 單元測試撰寫
- [ ] 整合測試實作
- [ ] 前端介面開發
- [ ] 文檔撰寫

### 測試階段 ✓
- [ ] 功能測試完成
- [ ] 效能測試通過
- [ ] 安全性測試驗證
- [ ] 使用者驗收測試
- [ ] 壓力測試執行
- [ ] 資料一致性檢查

### 部署階段 ✓
- [ ] CI/CD pipeline建立
- [ ] 監控系統配置
- [ ] 日誌收集設定
- [ ] 備份策略實施
- [ ] 災難復原計畫
- [ ] 生產環境部署

*本系統開發指南涵蓋財務分析與企業評價的完整技術實現，基於現代軟體工程最佳實務與IFRS 13準則。*