from __future__ import annotations

import pandas as pd
import pytest

from models.forecast.baseline import baseline_demand_monthly, et0_penman_monteith
from models.forecast.eval import mape, rmse, smape
from models.forecast.lightgbm import predict_demand


def test_et0_reference_fixture() -> None:
    et0 = et0_penman_monteith(
        tmean_c=20.0,
        tmin_c=15.0,
        tmax_c=25.0,
        rh=60.0,
        wind_ms=2.0,
        rs_mj_m2=18.0,
        lat_rad=0.655,
        doy=135,
    )

    assert et0 == pytest.approx(4.08, abs=0.01)


def test_baseline_demand_monthly() -> None:
    demand = baseline_demand_monthly(
        area_m2=10_000,
        crop_coeff=0.75,
        et0_monthly_mm=120,
        irrigation_efficiency=0.6,
    )

    assert demand == pytest.approx(1500.0)


def test_predict_demand_falls_back_to_baseline() -> None:
    forecast = predict_demand(
        input_df=pd.DataFrame(
            [
                {
                    "demand_id": "PRK-00001",
                    "year_month": "2026-05",
                    "area_m2": 1000.0,
                    "crop_coeff_kc": 0.75,
                    "et0_monthly_mm": 120.0,
                },
            ],
        ),
    )

    expected_columns = [
        "demand_id",
        "year_month",
        "baseline_ton",
        "residual_ton",
        "predicted_ton",
        "lower_ci_ton",
        "upper_ci_ton",
        "model_version",
    ]
    assert list(forecast.columns) == expected_columns
    assert forecast.loc[0, "residual_ton"] == 0
    assert forecast.loc[0, "predicted_ton"] >= 0
    assert forecast.loc[0, "lower_ci_ton"] <= forecast.loc[0, "predicted_ton"]
    assert forecast.loc[0, "predicted_ton"] <= forecast.loc[0, "upper_ci_ton"]


def test_forecast_metrics() -> None:
    actual = [100.0, 120.0, 80.0]
    predicted = [90.0, 110.0, 100.0]

    assert mape(actual, predicted) > 0
    assert rmse(actual, predicted) > 0
    assert smape(actual, predicted) > 0
