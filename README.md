# AEV-v2c｜財務分析與企業評價系統

[![CI](https://github.com/goodchang77/AEV-v2c/actions/workflows/ci.yml/badge.svg)](https://github.com/goodchang77/AEV-v2c/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**AEV-v2c is an early-stage Python/FastAPI project for financial analysis and business valuation, focused on Taiwan-market workflows and Traditional Chinese users.** It includes valuation models, financial-ratio services, a browser workbench, tests, and deployment examples. Public adoption remains limited; no broad ecosystem adoption is claimed.

AEV-v2c 提供財務報表分析、企業評價及風險分析工具，主要面向台灣市場與繁體中文使用者。專案由 [Good Chang（goodchang77）](https://github.com/goodchang77) 維護，歡迎提出可重現的問題與小範圍改進。

> **專案狀態：早期開發。** 下列功能已有原始碼或測試，不代表所有外部資料來源、部署環境或完整使用流程均已驗證。模型輸出是研究與教學輔助，不是投資建議、會計師查核意見或 IFRS 13 合規認證。請自行核對資料、假設、幣別及單位。

## 已有實作與證據

| 範圍 | 原始碼／測試 | 限制與注意事項 |
| --- | --- | --- |
| 財務比率計算 | [計算服務](src/services/financial_calculator.py)、[測試](tests/test_financial_calculator.py) | 結果取決於輸入資料與單位一致性 |
| DCF、DDM、相對評價 | [評價模型](src/services/valuation_models.py)、[API](src/api/endpoints/valuation.py)、[測試](tests/test_valuation.py) | 不是經獨立驗證的專業估值報告 |
| PEG 與蒙地卡羅 DCF | [模擬服務](src/services/monte_carlo.py)、[測試](tests/test_valuation.py) | 模擬依賴假設；機率不代表報酬保證 |
| 同業與風險分析 | [同業服務](src/services/peer_analysis.py)、[風險服務](src/services/risk_assessment.py) | 需核對同業範圍、期間及資料品質 |
| 文件處理與報告 | [PDF 處理](src/services/pdf_processor.py)、[報告服務](src/services/report_service.py) | 擷取結果需人工複核；勿將機密文件送至未核准服務 |
| 瀏覽器工作區 | [靜態介面](src/static/index.html) | 與後端及資料來源整合狀態依環境而異 |
| AI Agent 與 MCP | [Agent 端點](src/api/endpoints/agent.py)、[MCP server](src/mcp_server/server.py) | 實驗性整合，可能需要額外依賴、API 金鑰與費用 |
| 自動化檢查 | [GitHub Actions](.github/workflows/ci.yml) | 最新實際結果請見 CI，不以歷史測試數量作保證 |

## 本機開發

### 環境需求

- Python **3.11**（目前 CI 使用的版本）。
- Docker 與 Docker Compose v2，用於隔離的本機 PostgreSQL／Redis。
- Git；目前的靜態前端不需要 Node.js 建置步驟。
- 額外的 OCR、AI 或市場資料服務，可能需要自行設定相應工具與金鑰。

### 安裝與設定

```bash
git clone https://github.com/goodchang77/AEV-v2c.git
cd AEV-v2c
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Windows 可使用 `py -3.11 -m venv .venv`，並執行 `.venv\Scripts\Activate.ps1` 啟用環境。已有 `.env` 時不要覆寫。

**啟動前先編輯 `.env`：**

- `DATABASE_URL`：必須與本機 PostgreSQL 的帳號、密碼、資料庫及連接埠一致。
- `REDIS_URL`：須包含與 Compose 設定相符的 Redis 認證資訊。
- `SECRET_KEY`：自行產生至少 32 字元的隨機值，例如 `python -c "import secrets; print(secrets.token_hex(32))"`。
- 本機如需 API 文件，可設定 `DEBUG=true`；正式環境請關閉。
- `.env`、正式環境金鑰及客戶資料不得提交至 Git。

### 啟動本機服務

```bash
# 僅供隔離的開發環境；先確認連接埠與現有服務不衝突
docker compose -f docker-compose.dev.yml up -d postgres redis

# 在設定正確的本機測試資料庫初始化範例資料
python scripts/init_db.py

# 將 API 限制在本機介面
uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

`docker-compose.dev.yml` 是開發範例，包含示範憑證及對主機發布的資料庫連接埠；**不得直接作為公開服務的正式設定**。請在受控開發環境使用，必要時先調整主機綁定位址與防火牆。

- 工作區：`http://127.0.0.1:8000/static/index.html`
- 健康檢查：`http://127.0.0.1:8000/health`
- API 文件：`http://127.0.0.1:8000/docs`（僅 `DEBUG=true` 時提供）
- [初始化程式](scripts/init_db.py) 內含示範財務數值，不應當作已查核的公司正式財報。
- 資料庫管理與 TimescaleDB 是選用服務，請按實際需要啟動。

舊版 [start.sh](start.sh) 仍可作參考，但它使用 `docker-compose` 執行檔，且 API 綁定 `0.0.0.0`；只有 `docker compose` 的環境需另作相容處理。本 README 的明確步驟優先，不宣稱跨平台一鍵安裝已驗證。

## 測試與 CI

測試依賴已列在 [requirements.txt](requirements.txt)，沒有獨立的 `requirements-dev.txt`。

```bash
python scripts/import_smoke_test.py
python -m pytest tests/ -q -W ignore
python scripts/api_db_test.py
```

完整流程需要正確設定的測試用 PostgreSQL／Redis，部分測試涉及額外工具或可選整合。請勿將測試指向正式資料庫。

[CI 設定](.github/workflows/ci.yml) 會在推送 `main` 或提出 PR 時執行依賴安裝、匯入檢查、資料庫初始化、pytest、資料庫端點整合檢查及 Docker 建置。請以[該次工作流程結果](https://github.com/goodchang77/AEV-v2c/actions)判讀，不將通過 CI 等同於安全稽核或財務模型正確性認證。

## 專案結構

```text
src/
  api/endpoints/     # FastAPI 端點
  core/              # 設定、資料庫、快取與日誌
  services/          # 財務、評價、風險、報告等服務
  ai_agent/          # AI 整合
  mcp_server/        # MCP 整合
  static/            # 瀏覽器工作區
  models.py          # 資料模型
scripts/             # 初始化與檢查程式
tests/               # 自動化測試
database/            # SQL 與示範資料
deploy/azure/        # 選用的 Azure 部署範例
```

## 後續維護方向

以下為待持續改善的方向，**不是已完成項目或交付承諾**：

- 擴充估值邊界條件、財務資料驗證及回歸測試。
- 改善安裝流程、文件一致性與可重現示範。
- 強化依賴維護、部署安全與私密設定管理。
- 驗證外部資料來源可用性、權利限制及資料品質。
- 以真實使用回饋決定功能優先順序，不虛構使用者或下載量。

[DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) 等早期設計文件包含歷史規劃，不能當作目前全部功能均已完成的證據。

## 貢獻與安全

- 請見 [CONTRIBUTING.md](CONTRIBUTING.md)。
- 一般問題請透過 [Issues](https://github.com/goodchang77/AEV-v2c/issues) 提供去識別化的重現步驟。
- 安全問題請依 [SECURITY.md](SECURITY.md) 私下回報；不要在公開 issue 張貼金鑰、客戶資料或可直接利用的細節。
- 部署請先閱讀 [Azure 部署範例](deploy/azure/README.md) 與[公開交接檢查清單](NEW_PROJECT_HANDOVER.md)，自行預覽成本與設定；本機開發不需要 Azure。

## 授權與聯絡

本專案原創程式碼採 [MIT License](LICENSE)。第三方依賴、商標、外部市場資料及第三方財報／PDF 等內容仍受其各自條款與權利限制；本授權不授予對第三方資料的額外權利。

- 維護者：[Good Chang](https://github.com/goodchang77)
- Email：goodchang77@gmail.com
