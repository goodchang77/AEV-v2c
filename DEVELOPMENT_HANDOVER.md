# AEV-v2c 開發進度交接文件（2026-08-14 ~ 08-15）

> 用途：接手開發的完整上下文。可丟進 WSL 的 DSH 環境作為起始 prompt，
> 或由新接手者直接閱讀。以「可執行、可驗證」為準，不信任舊文件的完成度宣稱。

---

## 1. 兩天總覽

| 階段 | 內容 | 結果 |
|---|---|---|
| 接手評估 | 全目錄掃描 + 讀取 README/進度文件/核心程式碼 | 產出接手計畫，發現「文件宣稱 80-100% 完成，實際分層 API 不對齊」 |
| Phase 0 | 建立可運行基線 | import 45/45 ✅、app 可啟動 ✅、pytest 可收集 ✅ |
| Phase 1 | 資料庫上線 + DB 端點打通 | DB 端點 9/9 ✅、風險評估可跑出 Z-Score ✅ |
| 環境釐清 | WSL 移除烏龍 → WSL 其實還在 | 確認 PostgreSQL/Redis 都在 WSL 內運行 |

**測試結果現況**：pytest `59 passed, 2 skipped, 5 failed`（5 個失敗皆為既有 PDF 測試漂移，非本次造成）。

---

## 2. 環境現況（重要）

### 2.1 Windows
| 項目 | 值 |
|---|---|
| 主開發 Python | **3.14.0**（`C:\Python314`，`py -3.14`）→ 已裝齊 runtime 依賴 + pytest 9.1.1 |
| 次要 Python | 3.13.2（`D:\Python\Python313`）→ 有 pytest 與符合 requirements pin 的 fastapi 0.104.1，但缺 anthropic/pydantic-settings/redis/asyncpg 等 runtime 套件，**不建議當主環境** |
| Python 3.12 | 幾乎未使用 |
| `venv/` | **已刪除**（原本是 Linux venv，gitignored；當時誤以為 WSL 已移除）。如需要可重建（見 §7.2） |
| Docker CLI | 未安裝（不需要，DB 已直接在 WSL 原生跑） |

### 2.2 WSL Ubuntu（仍然存在！）
| 服務 | 位置 | 備註 |
|---|---|---|
| PostgreSQL 16.14 | `localhost:5432`（經 `wslrelay.exe` 轉送） | 資料庫 `financial_analysis`，使用者 `postgres`／密碼 `dev_password_2024` |
| Redis | `localhost:6379` | **無密碼**（`.env` 已配合修正） |
| 5432 監聽程序 | PID 為 `wslrelay.exe`（`C:\Program Files\WSL\wslrelay.exe`） | 證明 DB 在 WSL 內 |

### 2.3 DeepSeek Harness（dsh）— 開發用的 AI 環境
| 項目 | 值 |
|---|---|
| Checkout | `D:\Project\deepseek-harness-master` |
| Web GUI | `http://127.0.0.1:3080`（僅綁 127.0.0.1，官方刻意禁止 0.0.0.0） |
| 模型設定 | `provider: deepseek-official`、`model: deepseek-v4-pro`、`reasoningEffort: max`（見 `C:\Users\Good Chang\.dsh\settings.yaml`） |
| API key | `C:\Users\Good Chang\.dsh\.credentials.yaml` 內 `DEEPSEEK_API_KEY`（請自行複製，勿印出） |
| Node 需求 | `^22.19.0 \|\| >=24.0.0` |
| API 相容性 | DeepSeek 官方 API 為 **OpenAI 相容**：`https://api.deepseek.com/chat/completions`；模型名 `deepseek-v4-pro`／`deepseek-v4-flash`（1M token 上下文） |

---

## 3. Phase 0 完成的修改（可運行基線）

### 3.1 修復的檔案（依時間序）

| 檔案 | 問題 → 修法 |
|---|---|
| `src/models.py` | `from sqlalchemy import ... Decimal ...` 不存在 → 改 `Numeric` 並以 `Decimal = Numeric` 別名最小化改動（SQLAlchemy 2.x 無頂層 Decimal） |
| `tests/conftest.py` | 原本是無效 Python（缺冒號、字串無引號）→ 重寫為純資料 fixtures（`sample_financial_statements`、`sample_dcf_parameters`、`sample_peer_companies`、`sample_industry_benchmark`、`sample_target_company` 等，不依賴 DB） |
| `src/services/risk_assessment.py` | 原本只有 162 行、缺 10+ helper、引用不存在的欄位 → **完整重寫**（見 §3.2） |
| `src/schemas/requests.py` | 缺 schema → 新增 `RiskAssessmentRequest`、`PeerCompanyDataInput`、`IndustryBenchmarkInput`、`PeerComparisonDataRequest` |
| `src/api/endpoints/analysis.py` | import 不存在的 `get_db`/`DCFRequest`/`RiskAssessmentRequest`、缺 `datetime` import、以錯誤簽名呼叫服務 → 重寫為對齊真實簽名（`/dcf` 無狀態、`/peer-comparison` 顯式資料、`/risk-assessment` DB-backed） |
| `src/api/routes.py` | `analysis` 未掛載 → 補 `include_router(analysis.router, prefix="/analysis", tags=["分析"])` |
| `src/api/main.py` | 引用未定義 `app` 的死碼 → 改為轉發 `src.main.app` 的 deprecation shim |
| `src/core/database.py` | `create_tables()` 的 `engine.begin()` 失敗會 `raise`，**無 DB 時 app 無法啟動** → 改為僅記 warning、不阻止啟動（實際建表由 init SQL 負責） |
| `src/main.py` | 例外處理器用 `exc.detail` → `AttributeError`（屬性其實是 `message`）→ 修正 |
| `tests/test_mcp_integration.py` | import 不存在的 `get_db` → `get_sync_session`；fixture 同步修正 |
| `tests/test_risk_assessment.py` | 舊測試測舊的記憶體 API 且用已移除的 `test_db` fixture → 重寫為測純計算邏輯（不需 DB） |

### 3.2 `risk_assessment.py` 重寫重點
- DB-backed：同步 session + 原始 SQL（`text()`），不依賴漂移的 ORM 模型
- 純函式 `compute_altman_z_score(x1..x5)`（可單測）
- 四個維度：`assess_financial_distress`（Altman Z-Score，EBIT 以 `operating_income` 近似、X4 無市值時以帳面權益/負債近似）、`assess_liquidity_risk`、`assess_profitability_trend`、`assess_leverage_risk`
- `assess_overall_risk` 加權整合，回傳 `overall_risk_score`／`risk_grade`（A~F）／`risk_level`（中文）／`risk_breakdown`／`key_concerns`／`recommendations`

---

## 4. Phase 1 完成的修改（資料庫與 DB 端點）

### 4.1 修復的檔案

| 檔案 | 問題 → 修法 |
|---|---|
| `database/init/02_sample_data.sql` | 最後 INIT 標記列 `market_type='SYSTEM'` 違反 CHECK 約束（僅允許 上市/上櫃/興櫃）→ 改 `'上市'` |
| `src/services/financial_service.py` | 趨勢查詢用到不存在的欄位 `calculated_at` → `calculation_date` |
| `src/services/financial_service.py` | `_generate_assessment_details` 回傳 list 與 schema 的 `Dict[str, str]` 不符 → 改回傳 `{"獲利能力": ..., "流動性": ..., "槓桿": ...}` |
| `src/schemas/responses.py` | `FinancialTrendResponse.data: Dict[str, List[TrendData]]` 與服務輸出不符 → 放寬 `Dict[str, Any]` |
| `.env` | `REDIS_URL=redis://:dev_redis_2024@localhost:6379` → WSL Redis 無密碼，改 `redis://localhost:6379`（消除每次快取寫入的 AUTH 錯誤） |

### 4.2 資料庫初始化（`scripts/init_db.py`，冪等可重跑）
套用 `database/init/01_create_tables.sql` + `02_sample_data.sql`，並補上種子檔原本缺少的財務資料：

| 資料表 | 筆數 | 內容 |
|---|---|---|
| companies | 51 | 台股前 50 大 + INIT 標記 |
| financial_statements | 9 | 2330 台積電 4 季 IS + 4 季 BS + 1 季 CF（數值範例） |
| financial_ratios | 1 | 2330 2024Q4（含 DSO 55/DIO 62/DPO 23/CCC 94、ROE 0.266 等） |
| industry_benchmarks | 5 | M2300/J/M1700/I/H 2024Q3 |
| users | 3 | admin / analyst / demo_user |
| user_watchlists | 10 | demo_user 的追蹤清單 |

### 4.3 DB 端點驗證結果（9/9 ✅）
`GET /companies/`（分頁正確）、`GET /companies/search?keyword=台積`、`GET /companies/2330`、
`GET /financials/2330/ratios`（ROE 0.266）、`GET /financials/2330/health`（77.5 分）、
`GET /financials/2330/trend`（4 期）、`POST /analysis/risk-assessment`（**2330 → Z-Score 5.58、綜合 92.8、等級 A**；無資料公司正確回 404）。

---

## 5. 新增的腳本（可重用）

| 腳本 | 用途 | 用法 |
|---|---|---|
| `scripts/import_smoke_test.py` | 全模組 import 檢查（45 必要 + 1 選用） | `py -3.14 scripts\import_smoke_test.py` |
| `scripts/boot_test.py` | 不連 DB 的啟動 + 無狀態端點驗證 | `py -3.14 scripts\boot_test.py` |
| `scripts/db_check.py` | DB 連線 + 資料表/筆數檢查 | `py -3.14 scripts\db_check.py` |
| `scripts/init_db.py` | 初始化 DB（建表 + 種子 + 2330 財務資料，冪等） | `py -3.14 scripts\init_db.py` |
| `scripts/api_db_test.py` | 9 個 DB 端點驗證 | `py -3.14 scripts\api_db_test.py` |

## 6. 驗證指令（Windows 主環境）

```powershell
py -3.14 -m pytest tests\ -q -W ignore --tb=line   # 59 passed, 2 skipped, 5 failed（已知漂移）
py -3.14 scripts\import_smoke_test.py              # 45/45 必要模組
py -3.14 scripts\boot_test.py                      # 啟動煙霧測試
py -3.14 scripts\db_check.py                       # DB 狀態
py -3.14 scripts\init_db.py                        # 冪等初始化（可重跑）
py -3.14 scripts\api_db_test.py                    # 9/9 DB 端點
```

---

## 7. 已知遺留問題（接手後的待辦）

### 7.1 立即可處理
1. **5 個 pytest 失敗（既有測試漂移，非 app bug）**
   - `test_document_upload_api.py::test_upload_invalid_file_format` — 端點已升級支援 PDF+Excel，期望應改為 422 +「僅支援 PDF 與 Excel」
   - `test_document_upload_api.py::test_upload_no_filename` — 期望 422 而非 400
   - `test_document_upload_api.py::test_upload_processing_failure` — 錯誤碼已改 `DOCUMENT_PROCESSING_FAILED`
   - `test_pdf_e2e.py::test_sync_upload_complete_workflow` — 測試用假 PDF 內容無法解析；需真實 PDF 或 mock
   - `test_pdf_processor.py::test_text_cleaning` — 負數格式：實作用會計括號 `(800,000)`，測試期待 `-800,000`
2. **`src/api/endpoints/ratios.py` 是 stub**（回傳假資料），真端點在 `/financials/{id}/ratios`
3. **機敏資料在 repo**：`.env`（含 ALPHA_VANTAGE_API_KEY、ANTHROPIC_API_KEY）、`Alpha Vantage_api key.txt`、`deploy/gcp/terraform/terraform.tfstate` → 應輪替 key 並清出 repo

### 7.2 環境備註
- WSL 內若要重跑專案 Python 環境（可選）：Ubuntu 24.04 預設 python3.12，而 `requirements.txt` 的 pin（numpy==1.25.2、scipy==1.11.4 等）是 3.11 世代、無 3.12 wheel → **勿直接 `pip install -r requirements.txt`**；建議在 WSL 裝 Python 3.11 或改用相容版本（numpy>=1.26 等）。
- 重建 venv：`python3 -m venv venv && source venv/bin/activate`（gitignored）。

### 7.3 中長期（對齊先前計畫的 Phase 2/3）
- **Phase 2 資料層對齊**：`src/models.py` 與 `01_create_tables.sql` 漂移（`users.user_id` Integer vs SQL UUID、`user_watchlists` 缺 `watchlist_name/notes/priority`、**缺 `valuation_results` 與 `stock_prices` ORM 模型**）
- **Phase 3 AI Agent/MCP 對齊**：`src/mcp_server/server.py` 以錯誤簽名呼叫服務層（`PDFProcessor` 未定義、`assess_overall_risk(assessment_scope=...)`、`compare_risk_with_industry` 等）；`agent.py` 同步呼叫 `anthropic` 會阻塞事件迴圈；`src/mcp_server/financial_tools.py` 是孤立檔（需 `mcp` SDK，未被引用）
- `src/api/endpoints/auth.py` 目前只有 stub（無真實 JWT 登入/註冊）
- 前端完全缺失（僅 `src/static/upload_test.html` 靜態測試頁）
- 舊文件（`project review-20251204.txt`、多份 `*_STATUS.md`）**完成度宣稱與實際不符**，接手評估一律以 `import_smoke_test.py` + `pytest` + `api_db_test.py` 的實測為準

---

## 8. 在 WSL + DSH 環境繼續開發

### 8.1 DSH（deepseek-v4-pro）在 WSL 的使用
```bash
# WSL Ubuntu 內安裝 Node.js 24
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt-get install -y nodejs

# 設定 API key（值從 C:\Users\Good Chang\.dsh\.credentials.yaml 複製）
echo 'export DEEPSEEK_API_KEY="你的key"' >> ~/.bashrc && source ~/.bashrc

# 啟動 Web UI（WSL 內 3081，避免與 Windows 側 3080 衝突；Windows 瀏覽器開 http://localhost:3081）
npx @deepseek-ai/dsh web --port 3081

# 無 GUI 單次問答（適合腳本化）
npx @deepseek-ai/dsh --profile headless "分析台積電 2330 的投資價值"
```

### 8.2 在專案 AI Agent 直接用 deepseek-v4-pro（OpenAI 相容）
```python
import os
from openai import OpenAI

client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"],
                base_url="https://api.deepseek.com")
resp = client.chat.completions.create(
    model="deepseek-v4-pro",
    messages=[{"role": "user", "content": "分析台積電 2330 的投資價值"}],
)
print(resp.choices[0].message.content)
```

### 8.3 接手新 DSH 會話的建議起始 prompt
> 「請閱讀 D:\Project\AEV-v2c\DEVELOPMENT_HANDOVER.md 與 CLAUDE.md，先用
> `py -3.14 scripts\import_smoke_test.py`、`pytest tests\ -q -W ignore`、
> `scripts\api_db_test.py` 建立基線，再從 §7 的待辦清單挑項目動工。」

---

## 9. 附錄：目前 API 路由（35 個端點）

```
GET    /api/v1/auth/
GET    /api/v1/companies/search
GET    /api/v1/companies/
GET    /api/v1/companies/{company_id}
GET    /api/v1/financials/{company_id}/ratios
GET    /api/v1/financials/{company_id}/health
GET    /api/v1/financials/{company_id}/trend
POST   /api/v1/financials/{company_id}/ratios/calculate
GET    /api/v1/ratios/                          ← stub
GET    /api/v1/ratios/{company_id}              ← stub
GET    /api/v1/health/
GET    /api/v1/health/detailed
GET    /api/v1/market/quote/{symbol}
GET    /api/v1/market/quotes/batch
GET    /api/v1/market/history/{symbol}
GET    /api/v1/market/market/summary
POST   /api/v1/market/sync/stocks
GET    /api/v1/market/health/yahoo-finance
GET    /api/v1/market/supported-markets
GET    /api/v1/market/v2/quote/{symbol}
GET    /api/v1/market/v2/quotes/batch
GET    /api/v1/market/v2/history/{symbol}
GET    /api/v1/market/v2/health/sources
GET    /api/v1/market/v2/sources/info
POST   /api/v1/documents/upload/financial-statement
GET    /api/v1/documents/processing-status/{document_id}
DELETE /api/v1/documents/processing-result/{document_id}
GET    /api/v1/documents/supported-formats
POST   /api/v1/documents/test-extraction
POST   /api/v1/agent/analyze
GET    /api/v1/agent/tasks/{task_id}            ← 未實作（回 Not implemented）
GET    /api/v1/agent/tools
POST   /api/v1/analysis/dcf                      ✅ 無狀態可跑
POST   /api/v1/analysis/peer-comparison          ✅ 無狀態可跑（顯式資料）
POST   /api/v1/analysis/risk-assessment          ✅ DB-backed 可跑
```

---

*文件產生日期：2026-08-15｜撰寫者：DSH agent（deepseek-v4-pro）｜涵蓋期間：2026-08-14 ~ 08-15*
