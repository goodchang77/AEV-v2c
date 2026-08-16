"""
技術指標測試（純函式 + 端點）
RSI / MACD / SMA / EMA
"""

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.services.technical_indicators import compute_all, macd, rsi, sma


def test_sma_known_values():
    prices = [1, 2, 3, 4, 5]
    assert sma(prices, 3) == [2.0, 3.0, 4.0]


def test_rsi_bounds_and_uptrend():
    up = list(range(1, 31))  # 連續上漲
    down = list(range(30, 0, -1))  # 連續下跌
    rsi_up = rsi(up)
    rsi_down = rsi(down)
    assert all(0 <= v <= 100 for v in rsi_up)
    assert all(0 <= v <= 100 for v in rsi_down)
    assert rsi_up[-1] > 70  # 超買
    assert rsi_down[-1] < 30  # 超賣


def test_macd_structure():
    prices = [float(i) for i in range(1, 61)]
    m = macd(prices)
    assert set(m.keys()) == {"macd", "signal", "histogram"}
    assert len(m["macd"]) == len(prices)
    assert len(m["signal"]) == len(prices)
    assert len(m["histogram"]) == len(prices)


def test_compute_all_keys():
    prices = [float(i) for i in range(1, 41)]
    result = compute_all(prices)
    assert set(result.keys()) == {"sma", "ema", "rsi", "macd", "last_price"}
    assert result["last_price"] == 40.0


def test_indicators_endpoint():
    c = TestClient(app, raise_server_exceptions=False)
    r = c.post("/api/v1/indicators/calculate", json={"prices": list(range(1, 41))})
    assert r.status_code == 200
    data = r.json()["data"]
    assert "rsi" in data and "macd" in data and "sma" in data


def test_indicators_endpoint_rejects_short_input():
    c = TestClient(app, raise_server_exceptions=False)
    r = c.post("/api/v1/indicators/calculate", json={"prices": [1, 2, 3]})
    assert r.status_code == 422
