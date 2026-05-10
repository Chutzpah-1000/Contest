from __future__ import annotations

from app.components.map import build_matching_map
from app.services.data import load_app_data
from app.services.matching import select_solution, solution_id_for_radius


def test_solution_id_for_radius() -> None:
    assert solution_id_for_radius(500) == "R500M"
    assert solution_id_for_radius(2000) == "R2000M"


def test_app_data_loads_gold_and_silver_tables() -> None:
    data = load_app_data()

    assert not data.suppliers.empty
    assert not data.match_solution.empty
    assert not data.epiphany_metrics.empty


def test_select_solution_filters_cached_tables() -> None:
    data = load_app_data()
    selected = select_solution(1000, data.match_solution, data.match_flows, data.epiphany_metrics)

    assert selected.solution_id == "R1000M"
    assert not selected.solution.empty
    assert set(selected.flows["solution_id"]) == {"R1000M"}


def test_matching_map_builds_with_required_layers() -> None:
    data = load_app_data()
    selected = select_solution(1000, data.match_solution, data.match_flows, data.epiphany_metrics)
    matching_map = build_matching_map(
        suppliers=data.suppliers,
        parks=data.demand_parks,
        roads=data.demand_roads,
        flows=selected.flows,
    )

    assert matching_map.location == [37.5665, 126.978]
