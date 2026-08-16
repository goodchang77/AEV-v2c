"""
Import 煙霧測試 (Phase 0)
=========================
逐一匯入專案所有模組，偵測 import 錯誤與模組層級的執行期錯誤。
這不執行任何業務邏輯，只驗證「每個模組都能被匯入」。

用法:
    python scripts/import_smoke_test.py
"""

import sys
import traceback
from pathlib import Path

# 確保 Windows 主控台以 UTF-8 輸出，避免中文/表情符號編碼錯誤
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 確保專案根目錄在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MODULES = [
    # core
    "src.core.config",
    "src.core.logging",
    "src.core.exceptions",
    "src.core.cache",
    "src.core.database",
    # models & schemas
    "src.models",
    "src.schemas.requests",
    "src.schemas.responses",
    "src.schemas.market_data",
    # services - business logic
    "src.services.financial_calculator",
    "src.services.valuation_models",
    "src.services.peer_analysis",
    "src.services.risk_assessment",
    "src.services.report_service",
    "src.services.alert_monitor",
    # services - data
    "src.services.data_service",
    "src.services.company_service",
    "src.services.financial_service",
    "src.services.simple_data_service",
    # services - external sources
    "src.services.external_data_manager",
    "src.services.twse_service",
    "src.services.yahoo_finance_service",
    "src.services.market_data_sources",
    "src.services.taiwan_mock_source",
    "src.services.twse_backup",
    "src.services.yahoo_tw_source",
    # services - file processing
    "src.services.excel_processor",
    "src.services.pdf_processor",
    "src.services.monte_carlo",
    # MCP & AI agent
    "src.mcp_server.tools",
    "src.mcp_server.server",
    "src.ai_agent.agent",
    "src.ai_agent.financial_analyst_agent",
    # api endpoints
    "src.api.endpoints.auth",
    "src.api.endpoints.companies",
    "src.api.endpoints.financials",
    "src.api.endpoints.ratios",
    "src.api.endpoints.health",
    "src.api.endpoints.market_data",
    "src.api.endpoints.market_data_v2",
    "src.api.endpoints.document_upload",
    "src.api.endpoints.analysis",
    "src.api.endpoints.agent",
    "src.api.endpoints.valuation",
    # api routes + app entry
    "src.api.routes",
    "src.api.main",
    "src.main",
]

# 選用模組：需要額外外部套件，或屬孤立/替代實作，不列入必要模組清單。
OPTIONAL_MODULES = []


def _import_one(name: str) -> bool:
    try:
        __import__(name)
        print(f"[ OK ] {name}")
        return True
    except Exception:
        print(f"[FAIL] {name}")
        tb = traceback.format_exc()
        lines = tb.strip().splitlines()
        print("\n".join(f"        {ln}" for ln in lines[-6:]))
        print()
        return False


def main() -> int:
    failures = []

    for name in MODULES:
        if not _import_one(name):
            failures.append(name)

    print("=" * 70)
    print(f"必要模組: {len(MODULES)} 個, 成功 {len(MODULES) - len(failures)}, 失敗 {len(failures)}")
    if failures:
        print("\n失敗模組清單:")
        for f in failures:
            print(f"  - {f}")

    if OPTIONAL_MODULES:
        print("\n--- 選用模組（需額外套件，不影響 app 啟動）---")
        for name in OPTIONAL_MODULES:
            _import_one(name)

    if failures:
        return 1
    print("全部必要模組匯入成功 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
