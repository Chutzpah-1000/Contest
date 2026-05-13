from __future__ import annotations

from dataclasses import dataclass

DAYS_PER_YEAR: int = 365
SEWAGE_FEE_KRW_PER_TON: int = 400
SEWAGE_DISCOUNT_RATE: float = 0.50
TAP_WATER_ENERGY_KWH_PER_TON: float = 0.4
GRID_EMISSION_FACTOR_TCO2_PER_MWH: float = 0.4594
KWH_PER_MWH: int = 1000


@dataclass(frozen=True)
class BuildingRoi:
    """Annualized sewage savings and CO2 reduction for one building."""

    annual_supply_ton: float
    annual_savings_krw: float
    annual_co2_tons: float


def building_roi(daily_supply_ton: float) -> BuildingRoi:
    """Compute annual sewage savings and CO2 reduction for a building.

    Formula derived from 기획서.pdf §2-3 ROI 로직:
        annual_supply  = daily_supply * 365
        annual_savings = annual_supply * 400원/톤 * 50% (하수도요금 감면)
        annual_co2     = annual_supply * 0.4 kWh/톤 * 0.4594 tCO2eq/MWh

    Args:
        daily_supply_ton: 일평균 유출지하수 발생량(톤/일). 음수는 0으로 절단.

    Returns:
        BuildingRoi with annual supply, KRW savings, and CO2 tons reduced.
    """
    annual_supply = max(daily_supply_ton, 0.0) * DAYS_PER_YEAR
    annual_savings = annual_supply * SEWAGE_FEE_KRW_PER_TON * SEWAGE_DISCOUNT_RATE
    annual_co2 = (
        annual_supply
        * TAP_WATER_ENERGY_KWH_PER_TON
        / KWH_PER_MWH
        * GRID_EMISSION_FACTOR_TCO2_PER_MWH
    )
    return BuildingRoi(
        annual_supply_ton=annual_supply,
        annual_savings_krw=annual_savings,
        annual_co2_tons=annual_co2,
    )
