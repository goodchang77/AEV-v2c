"""
Phase 1 DB 端點驗證
====================
連接真實資料庫（WSL PostgreSQL via localhost:5432），逐一驗證：
- /health
- /api/v1/companies/（列表、搜尋、詳情）
- /api/v1/financials/{id}/ratios、/health、/trend
- /api/v1/analysis/risk-assessment

用法:
    py -3.14 scripts/api_db_test.py
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


def check(label: str, resp, expect_status: int = 200) -> bool:
    ok = resp.status_code == expect_status
    body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else None
    if ok:
        print(f"[OK] {label} -> {resp.status_code}")
        return True
    print(f"[FAIL] {label} -> 期望 {expect_status}, 實際 {resp.status_code}")
    if body:
        import json
        print(f"      body: {json.dumps(body, ensure_ascii=False)[:400]}")
    return False


def main() -> int:
    results = []
    with TestClient(app) as client:
        r = client.get("/health")
        results.append(check("GET /health", r))

        r = client.get("/api/v1/companies/")
        results.append(check("GET /companies/（列表）", r))
        if r.status_code == 200:
            data = r.json()
            print(f"      回傳公司數: {len(data.get('data', []))}, meta: {data.get('meta')}")

        r = client.get("/api/v1/companies/search", params={"keyword": "台積"})
        results.append(check("GET /companies/search?keyword=台積", r))
        if r.status_code == 200:
            data = r.json()
            names = [c["company_name"] for c in data.get("data", [])]
            print(f"      搜尋結果: {names}")

        r = client.get("/api/v1/companies/2330")
        results.append(check("GET /companies/2330", r))
        if r.status_code == 200:
            c = r.json().get("data", {})
            print(f"      公司: {c.get('company_name')} | 產業: {c.get('industry_name')} | 市場: {c.get('market_type')}")

        r = client.get("/api/v1/financials/2330/ratios")
        results.append(check("GET /financials/2330/ratios", r))
        if r.status_code == 200:
            body = r.json()
            print(f"      year_quarter={body.get('year_quarter')}, roe={body.get('data', {}).get('roe')}")

        r = client.get("/api/v1/financials/2330/health")
        results.append(check("GET /financials/2330/health", r))
        if r.status_code == 200:
            body = r.json()
            d = body.get("data", {})
            print(f"      健康度: {d.get('overall_grade')} / {d.get('overall_score')}")

        r = client.get("/api/v1/financials/2330/trend", params={"periods": 4})
        results.append(check("GET /financials/2330/trend?periods=4", r))

        r = client.post("/api/v1/analysis/risk-assessment", json={"company_id": "2330"})
        results.append(check("POST /analysis/risk-assessment (2330)", r))
        if r.status_code == 200:
            body = r.json()
            d = body.get("data", {})
            print(f"      綜合風險分數: {d.get('overall_risk_score')} | 等級: {d.get('risk_grade')} ({d.get('risk_level')})")
            distress = d.get("risk_breakdown", {}).get("financial_distress", {})
            print(f"      Altman Z-Score: {distress.get('z_score')} | {distress.get('risk_level')}")

        # 無資料公司應回 404
        r = client.post("/api/v1/analysis/risk-assessment", json={"company_id": "1301"})
        results.append(check("POST /analysis/risk-assessment (1301 無報表→404)", r, expect_status=404))

    print("=" * 60)
    passed = sum(results)
    print(f"結果: {passed}/{len(results)} 通過")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
