"""
技術指標計算模組
Technical Indicators (RSI / MACD / SMA / EMA)

純函式計算，供 API 與前端圖表使用。
"""

from typing import Dict, List


def sma(prices: List[float], period: int) -> List[float]:
    """簡單移動平均；回傳長度 len(prices)-period+1"""
    if period <= 0 or period > len(prices):
        return []
    return [round(sum(prices[i - period:i]) / period, 4) for i in range(period, len(prices) + 1)]


def ema(prices: List[float], period: int) -> List[float]:
    """指數移動平均；回傳與輸入等長"""
    if not prices or period <= 0:
        return []
    k = 2 / (period + 1)
    out = [float(prices[0])]
    for p in prices[1:]:
        out.append(p * k + out[-1] * (1 - k))
    return [round(v, 4) for v in out]


def rsi(prices: List[float], period: int = 14) -> List[float]:
    """相對強弱指標（Wilder 平滑）"""
    if len(prices) < period + 1:
        return []

    gains: List[float] = []
    losses: List[float] = []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))

    def _rsi(avg_gain: float, avg_loss: float) -> float:
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - 100.0 / (1.0 + rs)

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    out = [round(_rsi(avg_gain, avg_loss), 4)]

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        out.append(round(_rsi(avg_gain, avg_loss), 4))
    return out


def macd(
    prices: List[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Dict[str, List[float]]:
    """MACD：DIF 線、訊號線（EMA9）與柱狀圖"""
    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)
    dif = [round(f - s, 4) for f, s in zip(ema_fast, ema_slow)]
    signal_line = ema(dif, signal)
    histogram = [round(d - s, 4) for d, s in zip(dif, signal_line)]
    return {"macd": dif, "signal": signal_line, "histogram": histogram}


def compute_all(
    prices: List[float],
    sma_period: int = 20,
    rsi_period: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
) -> Dict[str, object]:
    """一次計算所有指標"""
    return {
        "sma": {"period": sma_period, "values": sma(prices, sma_period)},
        "ema": {"period": sma_period, "values": ema(prices, sma_period)},
        "rsi": {"period": rsi_period, "values": rsi(prices, rsi_period)},
        "macd": macd(prices, macd_fast, macd_slow, macd_signal),
        "last_price": round(prices[-1], 4) if prices else None,
    }
