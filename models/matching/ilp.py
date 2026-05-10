from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import pandas as pd
import pulp

from models.matching.geo import haversine_km

SOLVER_OPTIMAL_STATUS: Final = "Optimal"


@dataclass(frozen=True)
class Supplier:
    """Supplier node for capacitated matching."""

    id: str
    lat: float
    lng: float
    daily_supply_ton: float
    quality_grade: int


@dataclass(frozen=True)
class Demand:
    """Demand node for capacitated matching."""

    id: str
    lat: float
    lng: float
    daily_demand_ton: float
    min_quality_grade: int


@dataclass(frozen=True)
class MatchSolution:
    """Matching solution result."""

    flows: pd.DataFrame
    objective_krw: float
    coverage_rate: float
    solver_status: str


@dataclass(frozen=True)
class _Candidate:
    supplier: Supplier
    demand: Demand
    distance_km: float
    savings_per_ton: float


def solve(
    suppliers: list[Supplier],
    demands: list[Demand],
    radius_km: float = 1.0,
    transport_cost_per_ton_km: float = 500,
    tap_water_price_per_ton: float = 1200,
    unmet_penalty: float = 5000,
    solver_time_limit_s: int = 30,
) -> MatchSolution:
    """Solve capacitated supplier-demand matching with PuLP.

    Returns:
        Optimal or best-effort matching solution.
    """
    candidates = _compatible_candidates(
        suppliers=suppliers,
        demands=demands,
        radius_km=radius_km,
        transport_cost_per_ton_km=transport_cost_per_ton_km,
        tap_water_price_per_ton=tap_water_price_per_ton,
    )
    if not candidates:
        return _empty_solution("No compatible pairs")

    problem = pulp.LpProblem("groundwater_matching", pulp.LpMaximize)
    variables = {
        (candidate.supplier.id, candidate.demand.id): problem.add_variable(
            f"x_{candidate.supplier.id}_{candidate.demand.id}",
            lowBound=0,
            cat="Continuous",
        )
        for candidate in candidates
    }
    problem += pulp.lpSum(
        variables[candidate.supplier.id, candidate.demand.id]
        * (candidate.savings_per_ton + unmet_penalty)
        for candidate in candidates
    )
    for supplier in suppliers:
        supplier_variables = [
            variables[candidate.supplier.id, candidate.demand.id]
            for candidate in candidates
            if candidate.supplier.id == supplier.id
        ]
        if supplier_variables:
            problem += pulp.lpSum(supplier_variables) <= supplier.daily_supply_ton
    for demand in demands:
        demand_variables = [
            variables[candidate.supplier.id, candidate.demand.id]
            for candidate in candidates
            if candidate.demand.id == demand.id
        ]
        if demand_variables:
            problem += pulp.lpSum(demand_variables) <= demand.daily_demand_ton

    solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=solver_time_limit_s)
    status_code = problem.solve(solver)
    solver_status = str(pulp.LpStatus.get(status_code, "Unknown"))
    return _solution_from_variables(
        candidates,
        variables,
        solver_status,
        transport_cost_per_ton_km,
    )


def _compatible_candidates(
    suppliers: list[Supplier],
    demands: list[Demand],
    radius_km: float,
    transport_cost_per_ton_km: float,
    tap_water_price_per_ton: float,
) -> list[_Candidate]:
    candidates: list[_Candidate] = []
    for supplier in suppliers:
        for demand in demands:
            distance_km = haversine_km(supplier.lat, supplier.lng, demand.lat, demand.lng)
            savings_per_ton = tap_water_price_per_ton - (transport_cost_per_ton_km * distance_km)
            if (
                distance_km <= radius_km
                and supplier.quality_grade <= demand.min_quality_grade
                and savings_per_ton > 0
            ):
                candidates.append(
                    _Candidate(
                        supplier=supplier,
                        demand=demand,
                        distance_km=distance_km,
                        savings_per_ton=savings_per_ton,
                    ),
                )
    return candidates


def _solution_from_variables(
    candidates: list[_Candidate],
    variables: dict[tuple[str, str], pulp.LpVariable],
    solver_status: str,
    transport_cost_per_ton_km: float,
) -> MatchSolution:
    records: list[dict[str, object]] = []
    objective_krw = 0.0
    matched = 0.0
    for candidate in candidates:
        variable = variables[candidate.supplier.id, candidate.demand.id]
        ton_per_day = float(variable.value() or 0.0)
        if ton_per_day <= 1e-9:
            continue
        transport_cost = candidate.distance_km * transport_cost_per_ton_km * ton_per_day
        savings = candidate.savings_per_ton * ton_per_day
        objective_krw += savings
        matched += ton_per_day
        records.append(
            {
                "supplier_id": candidate.supplier.id,
                "demand_id": candidate.demand.id,
                "ton_per_day": ton_per_day,
                "distance_km": candidate.distance_km,
                "transport_cost_krw": transport_cost,
                "savings_krw": savings,
            },
        )
    flows = pd.DataFrame.from_records(records)
    total_demand = sum(candidate.demand.daily_demand_ton for candidate in candidates)
    coverage_rate = matched / total_demand if total_demand > 0 else 0.0
    return MatchSolution(
        flows=flows,
        objective_krw=objective_krw,
        coverage_rate=coverage_rate,
        solver_status=solver_status,
    )


def _empty_solution(status: str) -> MatchSolution:
    return MatchSolution(
        flows=pd.DataFrame(
            columns=[
                "supplier_id",
                "demand_id",
                "ton_per_day",
                "distance_km",
                "transport_cost_krw",
                "savings_krw",
            ],
        ),
        objective_krw=0.0,
        coverage_rate=0.0,
        solver_status=status,
    )
