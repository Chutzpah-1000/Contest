from __future__ import annotations

from typing import Final

import pandas as pd

from etl.transform.normalize import numeric_values

CARBON_TON_PER_WATER_TON: Final = 0.000332
DAYS_PER_YEAR: Final = 365.0


def build_epiphany_metrics(
    suppliers: pd.DataFrame,
    flows: pd.DataFrame,
    solution_id: str,
    coverage_rate: float,
) -> pd.DataFrame:
    """Build dashboard counter metrics from a matching solution.

    Returns:
        Epiphany metrics table following the gold schema.
    """
    total_discharge = sum(numeric_values(suppliers, ("daily_avg_supply_ton",), 0.0))
    matched_ton_day = sum(numeric_values(flows, ("ton_per_day",), 0.0)) if not flows.empty else 0.0
    savings_day = sum(numeric_values(flows, ("savings_krw",), 0.0)) if not flows.empty else 0.0
    savings_year = savings_day * DAYS_PER_YEAR
    return pd.DataFrame(
        {
            "metric_name": [
                "total_discharge_ton_day",
                "savings_krw_year",
                "co2_eq_year",
                "utilization_rate",
            ],
            "metric_value": [
                total_discharge,
                savings_year,
                matched_ton_day * DAYS_PER_YEAR * CARBON_TON_PER_WATER_TON,
                coverage_rate * 100,
            ],
            "unit": ["ton/day", "KRW/year", "tCO2eq/year", "percent"],
            "solution_id": [solution_id] * 4,
            "computed_at": [pd.Timestamp.now(tz="Asia/Seoul")] * 4,
        },
    )
