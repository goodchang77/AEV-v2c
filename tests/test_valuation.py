"""
評價模型測試（不依賴 DB）
DDM / 相對評價 / PEG / 蒙地卡羅 DCF。
"""

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.services.monte_carlo import MonteCarloDCF


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def test_ddm_endpoint(client):
    r = client.post("/api/v1/valuation/ddm", json={
        "company_id": "2330", "current_dividend": 15.0,
        "dividend_growth_rate": 0.05, "discount_rate": 0.09, "stable_growth_rate": 0.03,
    })
    assert r.status_code == 200
    fair = r.json()["data"]["fair_value_per_share"]
    assert fair > 0


def test_ddm_rejects_discount_below_growth(client):
    r = client.post("/api/v1/valuation/ddm", json={
        "company_id": "2330", "current_dividend": 15.0,
        "dividend_growth_rate": 0.10, "discount_rate": 0.05,
    })
    assert r.status_code == 422


def test_relative_valuation_endpoint(client):
    r = client.post("/api/v1/valuation/relative", json={
        "company_id": "2330", "target_eps": 45.0, "target_bvps": 140.0,
        "peer_pe_ratios": [12, 18, 11], "peer_pb_ratios": [1.5, 5.0, 1.8],
    })
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["pe"]["fair_value_per_share"] == pytest.approx(45.0 * 12)  # 中位數 PE=12
    assert data["pb"]["fair_value_per_share"] == pytest.approx(140.0 * 1.8)  # 中位數 PB=1.8


def test_peg_endpoint(client):
    r = client.post("/api/v1/valuation/peg", json={
        "company_id": "2330", "pe_ratio": 25.0, "eps_growth_rate": 20.0,
    })
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["peg"] == pytest.approx(1.25)
    assert data["rating"] == "合理"


def test_monte_carlo_endpoint_stateless(client):
    r = client.post("/api/v1/valuation/monte-carlo", json={
        "company_id": "2330", "base_revenue": 100_000_000_000,
        "shares_outstanding": 1_000_000_000, "simulations": 200, "seed": 42,
    })
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["simulations"] == 200
    assert data["mean"] > 0
    p = data["percentiles"]
    assert p["p5"] <= p["p50"] <= p["p95"]


def test_monte_carlo_deterministic():
    mc = MonteCarloDCF(base_revenue=1e11, shares_outstanding=1e9, seed=42)
    r1 = mc.simulate(200)
    r2 = mc.simulate(200)
    assert r1["mean"] == r2["mean"]
    assert r1["percentiles"]["p50"] == r2["percentiles"]["p50"]


def test_monte_carlo_probability_above_price():
    mc = MonteCarloDCF(base_revenue=1e11, shares_outstanding=1e9, current_price=0.01, seed=1)
    stats = mc.simulate(200)
    assert stats["probability_above_current_price"] is not None
    assert 0.0 <= stats["probability_above_current_price"] <= 1.0
