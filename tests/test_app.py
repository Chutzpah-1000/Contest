from __future__ import annotations

from app.components.kakao_map import build_kakao_map_html
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


def test_kakao_map_html_contains_required_elements() -> None:
    data = load_app_data()
    selected = select_solution(1000, data.match_solution, data.match_flows, data.epiphany_metrics)
    html = build_kakao_map_html(
        suppliers=data.suppliers,
        parks=data.demand_parks,
        roads=data.demand_roads,
        flows=selected.flows,
        search_term="",
        js_key="test-key",
    )

    assert "dapi.kakao.com" in html
    assert "test-key" in html
    assert "SUPPLIERS" in html
    assert "kakao.maps.Map" in html


def test_kakao_map_html_centers_on_search_match() -> None:
    data = load_app_data()
    selected = select_solution(1000, data.match_solution, data.match_flows, data.epiphany_metrics)
    first_name: str = str(data.suppliers["name"].iloc[0])
    html = build_kakao_map_html(
        suppliers=data.suppliers,
        parks=data.demand_parks,
        roads=data.demand_roads,
        flows=selected.flows,
        search_term=first_name,
        js_key="test-key",
    )

    assert first_name in html
