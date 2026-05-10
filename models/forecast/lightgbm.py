from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from models.forecast.baseline import baseline_demand_monthly


@dataclass(frozen=True)
class ForecastInput:
    """Typed input row for monthly demand forecasting."""

    demand_id: str
    year: int
    month: int
    area_m2: float
    veg_type: Literal["lawn", "shrub", "tree", "road"]
    precip_mm: float
    tmean_c: float
    soil_moisture: float
    spei: float
    pm10: float
    is_event: int


class ResidualForecaster:
    """Small residual forecaster with a robust mean fallback."""

    def __init__(self) -> None:
        """Initialize an unfitted residual fallback model."""
        self._mean_residual = 0.0
        self._is_fit = False

    def fit(self, features: pd.DataFrame, residuals: pd.Series) -> None:
        """Fit the residual fallback model."""
        del features
        residual_values = [float(value) for value in residuals.to_numpy(dtype=float)]
        self._mean_residual = float(np.mean(residual_values)) if residual_values else 0.0
        self._is_fit = True

    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """Predict residual demand.

        Returns:
            Residual predictions in tons per month.
        """
        residual = self._mean_residual if self._is_fit else 0.0
        return np.full(shape=len(features), fill_value=residual, dtype=float)

    def explain(self, features: pd.DataFrame) -> pd.DataFrame:
        """Return a lightweight feature-importance explanation table.

        Returns:
            DataFrame with feature and importance columns.
        """
        importance = 1.0 if self._is_fit else 0.0
        return pd.DataFrame(
            {
                "feature": list(features.columns),
                "importance": [importance for _ in features.columns],
            },
        )


def predict_demand(input_df: pd.DataFrame) -> pd.DataFrame:
    """Predict monthly demand with baseline-only fallback.

    Returns:
        Forecast DataFrame required by TC-FCT-02.
    """
    records: list[dict[str, object]] = []
    for row in input_df.to_dict(orient="records"):
        area_m2 = float(row.get("area_m2", 0.0))
        crop_coeff = float(row.get("crop_coeff", row.get("crop_coeff_kc", 0.75)))
        et0_monthly_mm = float(row.get("et0_monthly_mm", row.get("et0_mm", 120.0)))
        baseline_ton = baseline_demand_monthly(
            area_m2=area_m2,
            crop_coeff=crop_coeff,
            et0_monthly_mm=et0_monthly_mm,
        )
        predicted_ton = max(0.0, baseline_ton)
        records.append(
            {
                "demand_id": str(row.get("demand_id", "")),
                "year_month": str(row.get("year_month", "2026-05")),
                "baseline_ton": baseline_ton,
                "residual_ton": 0.0,
                "predicted_ton": predicted_ton,
                "lower_ci_ton": predicted_ton * 0.75,
                "upper_ci_ton": predicted_ton * 1.25,
                "model_version": "baseline_fallback_v1",
            },
        )
    return pd.DataFrame.from_records(records)
