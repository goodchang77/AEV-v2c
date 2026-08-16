"""
回測引擎（Backtest Engine）
==========================

簡單的回測：SMA 交叉策略與買進持有（Buy & Hold）。
純函式，供 API 使用。
"""

from typing import Dict, List, Optional

from src.services.technical_indicators import sma


def run_sma_crossover_backtest(
    prices: List[float],
    fast_period: int = 20,
    slow_period: int = 50,
    initial_capital: float = 1_000_000.0,
) -> Dict:
    """SMA 交叉策略回測：金叉買入、死叉賣出（全進全出）"""
    if len(prices) < slow_period + 1:
        return {
            "strategy": "sma_crossover",
            "error": f"需要至少 {slow_period + 1} 筆價格，目前 {len(prices)} 筆",
        }

    fast = sma(prices, fast_period)   # 長度 n-fast+1
    slow = sma(prices, slow_period)   # 長度 n-slow+1

    capital = initial_capital
    shares = 0.0
    trades = []
    position = False

    # 對齊兩條 SMA：以 slow 的索引為基準（slow 較短）
    offset = len(fast) - len(slow)
    for i in range(1, len(slow)):
        idx = i + offset  # fast 的對應索引
        price = prices[i + slow_period - 1]  # 當日價格（slow 的最新點）
        prev_fast, prev_slow = fast[idx - 1], slow[i - 1]
        cur_fast, cur_slow = fast[idx], slow[i]

        crossed_up = prev_fast <= prev_slow and cur_fast > cur_slow
        crossed_down = prev_fast >= prev_slow and cur_fast < cur_slow

        if crossed_up and not position:
            shares = capital / price
            capital = 0.0
            position = True
            trades.append({"action": "buy", "price": round(price, 2), "shares": round(shares, 2)})
        elif crossed_down and position:
            capital = shares * price
            shares = 0.0
            position = False
            trades.append({"action": "sell", "price": round(price, 2), "value": round(capital, 2)})

    final_price = prices[-1]
    final_value = capital + shares * final_price
    buy_hold_value = initial_capital / prices[0] * final_price

    return {
        "strategy": "sma_crossover",
        "fast_period": fast_period,
        "slow_period": slow_period,
        "initial_capital": initial_capital,
        "final_value": round(final_value, 2),
        "total_return_pct": round((final_value - initial_capital) / initial_capital * 100, 2),
        "buy_hold_value": round(buy_hold_value, 2),
        "buy_hold_return_pct": round((buy_hold_value - initial_capital) / initial_capital * 100, 2),
        "num_trades": len(trades),
        "trades": trades,
    }


def run_buy_and_hold(
    prices: List[float],
    initial_capital: float = 1_000_000.0,
) -> Dict:
    """買進持有回測"""
    final_value = initial_capital / prices[0] * prices[-1]
    return {
        "strategy": "buy_and_hold",
        "initial_capital": initial_capital,
        "final_value": round(final_value, 2),
        "total_return_pct": round((final_value - initial_capital) / initial_capital * 100, 2),
    }
