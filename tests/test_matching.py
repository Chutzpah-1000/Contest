from __future__ import annotations

import pytest

from models.matching.greedy import solve_greedy
from models.matching.ilp import Demand, Supplier, solve


def test_small_ilp_matches_manual_solution() -> None:
    solution = solve(
        suppliers=_suppliers(),
        demands=_demands(),
        radius_km=1.0,
        transport_cost_per_ton_km=0.0,
        tap_water_price_per_ton=1000.0,
        unmet_penalty=0.0,
    )

    assert solution.solver_status == "Optimal"
    assert solution.objective_krw == pytest.approx(240_000.0)
    assert solution.flows["ton_per_day"].sum() == pytest.approx(240.0)


def test_greedy_is_not_better_than_ilp() -> None:
    ilp_solution = solve(_suppliers(), _demands(), radius_km=1.0)
    greedy_solution = solve_greedy(_suppliers(), _demands(), radius_km=1.0)

    assert ilp_solution.objective_krw >= greedy_solution.objective_krw - 1


def test_radius_constraint_filters_far_pairs() -> None:
    solution = solve(
        suppliers=[Supplier("S1", 37.0, 127.0, 100.0, 2)],
        demands=[Demand("D1", 38.0, 128.0, 100.0, 3)],
        radius_km=1.0,
    )

    assert solution.flows.empty
    assert solution.objective_krw == 0


def test_quality_constraint_blocks_incompatible_pairs() -> None:
    solution = solve(
        suppliers=[Supplier("S1", 37.0, 127.0, 100.0, 4)],
        demands=[Demand("D1", 37.0, 127.0, 100.0, 1)],
        radius_km=1.0,
    )

    assert solution.flows.empty


def test_capacity_constraints_are_respected() -> None:
    solution = solve(_suppliers(), _demands(), radius_km=1.0)

    by_supplier = solution.flows.groupby("supplier_id")["ton_per_day"].sum()
    by_demand = solution.flows.groupby("demand_id")["ton_per_day"].sum()

    assert all(value <= 100.0 for value in by_supplier)
    assert all(value <= 80.0 for value in by_demand)


def _suppliers() -> list[Supplier]:
    return [
        Supplier("S1", 37.5665, 126.9780, 100.0, 2),
        Supplier("S2", 37.5666, 126.9781, 100.0, 2),
        Supplier("S3", 37.5667, 126.9782, 100.0, 2),
    ]


def _demands() -> list[Demand]:
    return [
        Demand("D1", 37.5665, 126.9780, 80.0, 3),
        Demand("D2", 37.5666, 126.9781, 80.0, 3),
        Demand("D3", 37.5667, 126.9782, 80.0, 3),
    ]
