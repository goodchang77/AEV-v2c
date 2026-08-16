"""
蒙地卡羅模擬風險分析
Monte Carlo Simulation for DCF Valuation

以常態分佈抽樣折現率與成長率，模擬大量 DCF 情境，
產生公允價值分佈（均值、中位數、分位數）與風險指標。
"""

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np

from src.services.valuation_models import DCFParameters, DCFValuationModel


@dataclass
class MonteCarloDCF:
    """蒙地卡羅 DCF 模擬器"""

    base_revenue: float
    discount_rate_mean: float = 0.10
    discount_rate_std: float = 0.01
    growth_rate_mean: float = 0.05
    growth_rate_std: float = 0.02
    forecast_years: int = 5
    ebitda_margin: float = 0.15
    tax_rate: float = 0.25
    capex_rate: float = 0.04
    working_capital_rate: float = 0.02
    terminal_growth_rate: float = 0.03
    shares_outstanding: int = 1_000_000
    net_debt: float = 0.0
    current_price: Optional[float] = None
    seed: Optional[int] = 42

    def simulate(self, simulations: int = 1000) -> Dict:
        """執行蒙地卡羅模擬，回傳統計摘要（seed 固定可重現）"""
        rng = np.random.default_rng(self.seed)
        discount_rates = rng.normal(self.discount_rate_mean, self.discount_rate_std, simulations)
        growth_rates = rng.normal(self.growth_rate_mean, self.growth_rate_std, simulations)

        # 裁切到合理範圍
        discount_rates = np.clip(discount_rates, 0.03, 0.30)
        growth_rates = np.clip(growth_rates, -0.20, 0.30)

        fair_values = np.empty(simulations)
        for i in range(simulations):
            params = DCFParameters(
                forecast_years=self.forecast_years,
                revenue_growth_rates=[float(growth_rates[i])] * self.forecast_years,
                ebitda_margin=self.ebitda_margin,
                tax_rate=self.tax_rate,
                capex_rate=self.capex_rate,
                working_capital_rate=self.working_capital_rate,
                discount_rate=float(discount_rates[i]),
                terminal_growth_rate=self.terminal_growth_rate,
            )
            model = DCFValuationModel(params)
            try:
                result = model.calculate_enterprise_value(
                    self.base_revenue, self.net_debt, self.shares_outstanding
                )
                fair_values[i] = result.fair_value_per_share
            except Exception:
                fair_values[i] = 0.0

        stats = {
            "simulations": simulations,
            "mean": round(float(np.mean(fair_values)), 2),
            "median": round(float(np.median(fair_values)), 2),
            "std_dev": round(float(np.std(fair_values)), 2),
            "min": round(float(np.min(fair_values)), 2),
            "max": round(float(np.max(fair_values)), 2),
            "percentiles": {
                "p5": round(float(np.percentile(fair_values, 5)), 2),
                "p25": round(float(np.percentile(fair_values, 25)), 2),
                "p50": round(float(np.percentile(fair_values, 50)), 2),
                "p75": round(float(np.percentile(fair_values, 75)), 2),
                "p95": round(float(np.percentile(fair_values, 95)), 2),
            },
            "probability_above_current_price": None,
        }
        if self.current_price and self.current_price > 0:
            stats["probability_above_current_price"] = round(
                float((fair_values > self.current_price).mean()), 4
            )
        return stats
