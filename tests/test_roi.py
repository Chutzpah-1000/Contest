from __future__ import annotations

import math

import pytest

from app.services.roi import (
    DAYS_PER_YEAR,
    GRID_EMISSION_FACTOR_TCO2_PER_MWH,
    KWH_PER_MWH,
    SEWAGE_DISCOUNT_RATE,
    SEWAGE_FEE_KRW_PER_TON,
    TAP_WATER_ENERGY_KWH_PER_TON,
    building_roi,
)


def test_building_roi_zero_supply_returns_zero() -> None:
    result = building_roi(0.0)

    assert result.annual_supply_ton == pytest.approx(0.0)
    assert result.annual_savings_krw == pytest.approx(0.0)
    assert result.annual_co2_tons == pytest.approx(0.0)


def test_building_roi_negative_supply_clamped_to_zero() -> None:
    result = building_roi(-12.5)

    assert result.annual_supply_ton == pytest.approx(0.0)
    assert result.annual_savings_krw == pytest.approx(0.0)
    assert result.annual_co2_tons == pytest.approx(0.0)


def test_building_roi_uses_published_savings_formula() -> None:
    daily = 100.0
    result = building_roi(daily)

    expected_supply = daily * DAYS_PER_YEAR
    expected_savings = expected_supply * SEWAGE_FEE_KRW_PER_TON * SEWAGE_DISCOUNT_RATE
    expected_co2 = (
        expected_supply
        * TAP_WATER_ENERGY_KWH_PER_TON
        / KWH_PER_MWH
        * GRID_EMISSION_FACTOR_TCO2_PER_MWH
    )

    assert result.annual_supply_ton == pytest.approx(expected_supply)
    assert result.annual_savings_krw == pytest.approx(expected_savings)
    assert result.annual_co2_tons == pytest.approx(expected_co2)


def test_building_roi_matches_helio_city_reference() -> None:
    """기획서.pdf §2-4 헬리오시티: 연 387,000톤 → 7,740만원 / 71.1 tCO2eq."""
    daily = 387_000.0 / DAYS_PER_YEAR
    result = building_roi(daily)

    assert math.isclose(result.annual_savings_krw, 77_400_000.0, rel_tol=1e-3)
    assert math.isclose(result.annual_co2_tons, 71.1, abs_tol=0.5)
