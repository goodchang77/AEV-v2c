"""
啟動煙霧測試 (Phase 0)
=======================
在不連接資料庫的前提下，驗證 FastAPI app 能啟動並回應：
- GET  /health
- GET  /
- POST /api/v1/analysis/dcf            （無狀態，不需 DB）
- POST /api/v1/analysis/peer-comparison（無狀態，不需 DB）

用法:
    python scripts/boot_test.py
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from src.main import app


def main() -> int:
    ok = True
    with TestClient(app) as client:
        # 1. 健康檢查
        r = client.get("/health")
        print(f"[health] {r.status_code} -> {r.json()}")
        ok &= r.status_code == 200 and r.json().get("status") == "healthy"

        # 2. 根路徑
        r = client.get("/")
        print(f"[root  ] {r.status_code} -> service={r.json().get('message')}")
        ok &= r.status_code == 200

        # 3. DCF 評價（無狀態）
        dcf_payload = {
            "company_id": "2330",
            "base_revenue": 573584904000,
            "forecast_years": 5,
            "revenue_growth_rates": [0.15, 0.12, 0.10, 0.08, 0.05],
            "ebitda_margin": 0.20,
            "tax_rate": 0.25,
            "capex_rate": 0.05,
            "working_capital_rate": 0.02,
            "discount_rate": 0.10,
            "terminal_growth_rate": 0.03,
            "sensitivity_analysis": True,
        }
        r = client.post("/api/v1/analysis/dcf", json=dcf_payload)
        body = r.json()
        print(f"[dcf   ] {r.status_code} -> success={body.get('success')}")
        if r.status_code == 200 and body.get("success"):
            fv = body["data"]["valuation"].get("fair_value_per_share")
            print(f"          fair_value_per_share={fv}")
            ok &= True
        else:
            print(f"          body={body}")
            ok = False

        # 4. 同業比較（無狀態，顯式資料）
        peer_payload = {
            "target": {
                "company_id": "2330", "company_name": "台積電",
                "market_cap": 15000000000000, "revenue": 573584904000,
                "net_income": 101584904000, "total_assets": 573584904000,
                "shareholders_equity": 507981284000, "roe": 0.266, "roa": 0.236,
                "current_ratio": 4.51, "debt_ratio": 0.11, "net_margin": 0.177,
                "pe_ratio": 25.0, "pb_ratio": 6.0,
            },
            "peers": [
                {"company_id": "2454", "company_name": "聯發科",
                 "market_cap": 1000000000000, "revenue": 300000000000,
                 "net_income": 50000000000, "total_assets": 600000000000,
                 "shareholders_equity": 400000000000, "roe": 0.28, "roa": 0.20,
                 "current_ratio": 2.5, "debt_ratio": 0.30, "net_margin": 0.30,
                 "pe_ratio": 20.0, "pb_ratio": 3.0},
                {"company_id": "2303", "company_name": "聯電",
                 "market_cap": 800000000000, "revenue": 200000000000,
                 "net_income": 30000000000, "total_assets": 500000000000,
                 "shareholders_equity": 300000000000, "roe": 0.18, "roa": 0.12,
                 "current_ratio": 2.0, "debt_ratio": 0.40, "net_margin": 0.22,
                 "pe_ratio": 15.0, "pb_ratio": 2.0},
            ],
            "industry_benchmark": {
                "industry_code": "SMI", "industry_name": "半導體", "company_count": 50,
                "avg_roe": 0.20, "avg_roa": 0.14, "avg_current_ratio": 2.0,
                "avg_debt_ratio": 0.40, "avg_gross_margin": 0.40, "avg_net_margin": 0.20,
                "avg_pe_ratio": 18.0, "avg_pb_ratio": 2.5,
                "median_roe": 0.18, "median_roa": 0.12, "median_current_ratio": 1.8,
                "median_debt_ratio": 0.42,
                "roe_25_percentile": 0.10, "roe_75_percentile": 0.25,
                "pe_25_percentile": 12.0, "pe_75_percentile": 24.0,
                "debt_25_percentile": 0.30, "debt_75_percentile": 0.55,
                "roe_std_dev": 0.06, "roa_std_dev": 0.05,
            },
        }
        r = client.post("/api/v1/analysis/peer-comparison", json=peer_payload)
        body = r.json()
        print(f"[peer  ] {r.status_code} -> success={body.get('success')}")
        if r.status_code == 200 and body.get("success"):
            score = body["data"].get("executive_summary", {}).get("composite_score")
            print(f"          composite_score={score}")
            ok &= True
        else:
            print(f"          body={body}")
            ok = False

    print("=" * 60)
    print("啟動煙霧測試結果:", "通過 ✅" if ok else "失敗 ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
