"""
回測引擎測試（純函式）
"""

from src.services.backtest import run_buy_and_hold, run_sma_crossover_backtest


def test_sma_crossover_v_shape_buys_at_bottom():
    # 先跌後漲：應在回升段出現金叉買進
    prices = [200 - i for i in range(60)] + [140 + i for i in range(60)]
    result = run_sma_crossover_backtest(prices, fast_period=5, slow_period=10)
    assert result["num_trades"] >= 1
    assert result["trades"][0]["action"] == "buy"
    assert result["total_return_pct"] > 0


def test_sma_crossover_insufficient_data():
    result = run_sma_crossover_backtest([100.0] * 20, fast_period=5, slow_period=50)
    assert "error" in result


def test_buy_and_hold_uptrend_profitable():
    prices = [100 + i for i in range(50)]
    result = run_buy_and_hold(prices, 100_000)
    assert result["total_return_pct"] > 0
    assert result["final_value"] == 100_000 / 100 * 149


def test_backtest_endpoint():
    from fastapi.testclient import TestClient

    from src.main import app

    c = TestClient(app, raise_server_exceptions=False)
    prices = [200 - i for i in range(60)] + [140 + i for i in range(60)]
    r = c.post("/api/v1/analysis/backtest", json={"prices": prices, "strategy": "buy_and_hold"})
    assert r.status_code == 200
    assert "total_return_pct" in r.json()["data"]
