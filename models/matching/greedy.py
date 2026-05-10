from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from models.matching.geo import haversine_km
from models.matching.ilp import MatchSolution

if TYPE_CHECKING:
    from models.matching.ilp import Demand, Supplier


def solve_greedy(
    suppliers: list[Supplier],
    demands: list[Demand],
    radius_km: float = 1.0,
    transport_cost_per_ton_km: float = 500,
    tap_water_price_per_ton: float = 1200,
) -> MatchSolution:
    """Solve matching with a nearest-pair greedy baseline.

    Returns:
        Greedy matching solution.
    """
    remaining_supply = {supplier.id: supplier.daily_supply_ton for supplier in suppliers}
    remaining_demand = {demand.id: demand.daily_demand_ton for demand in demands}
    pairs = sorted(
        _candidate_pairs(
            suppliers,
            demands,
            radius_km,
            transport_cost_per_ton_km,
            tap_water_price_per_ton,
        ),
        key=lambda record: float(str(record["distance_km"])),
    )
    records: list[dict[str, object]] = []
    objective_krw = 0.0
    matched = 0.0
    for pair in pairs:
        supplier_id = str(pair["supplier_id"])
        demand_id = str(pair["demand_id"])
        ton_per_day = min(remaining_supply[supplier_id], remaining_demand[demand_id])
        if ton_per_day <= 0:
            continue
        remaining_supply[supplier_id] -= ton_per_day
        remaining_demand[demand_id] -= ton_per_day
        distance_km = float(str(pair["distance_km"]))
        savings_per_ton = float(str(pair["savings_per_ton"]))
        savings = savings_per_ton * ton_per_day
        objective_krw += savings
        matched += ton_per_day
        records.append(
            {
                "supplier_id": supplier_id,
                "demand_id": demand_id,
                "ton_per_day": ton_per_day,
                "distance_km": distance_km,
                "transport_cost_krw": distance_km * transport_cost_per_ton_km * ton_per_day,
                "savings_krw": savings,
            },
        )
    flows = pd.DataFrame.from_records(records)
    total_demand = sum(demand.daily_demand_ton for demand in demands)
    return MatchSolution(
        flows=flows,
        objective_krw=objective_krw,
        coverage_rate=matched / total_demand if total_demand > 0 else 0.0,
        solver_status="Greedy",
    )


def _candidate_pairs(
    suppliers: list[Supplier],
    demands: list[Demand],
    radius_km: float,
    transport_cost_per_ton_km: float,
    tap_water_price_per_ton: float,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for supplier in suppliers:
        for demand in demands:
            distance_km = haversine_km(supplier.lat, supplier.lng, demand.lat, demand.lng)
            savings_per_ton = tap_water_price_per_ton - (transport_cost_per_ton_km * distance_km)
            if (
                distance_km <= radius_km
                and supplier.quality_grade <= demand.min_quality_grade
                and savings_per_ton > 0
            ):
                records.append(
                    {
                        "supplier_id": supplier.id,
                        "demand_id": demand.id,
                        "distance_km": distance_km,
                        "savings_per_ton": savings_per_ton,
                    },
                )
    return records
