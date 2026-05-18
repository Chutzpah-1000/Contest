from __future__ import annotations

import math

import pandas as pd

from app.components.kakao_map import build_kakao_map_html
from app.services.data import KST, last_data_refresh, load_app_data
from app.services.matching import (
    _filter_by_solution_id,
    metric_value,
    select_solution,
    solution_id_for_radius,
)


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

    assert "dapi.kakao.com/v2/maps/sdk.js" in html
    assert "test-key" in html
    assert "SUPPLIERS" in html
    assert "kakao.maps.Map" in html
    assert "Node.prototype.appendChild" in html


def test_kakao_map_html_includes_round10_perf_tokens() -> None:
    """Round 10 성능 개선(idle 뷰포트 컬링·rAF·플로우 줌 컷오프)이 깨지지 않도록 토큰 회귀 가드."""
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

    for token in (
        "FLOW_HIDE_LEVEL=8",
        "_scheduleCull",
        "_cullDemand",
        "requestAnimationFrame",
        "'idle'",
    ):
        assert token in html, f"missing perf token: {token}"


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


def test_filter_by_solution_id_missing_column_returns_empty() -> None:
    table = pd.DataFrame({"other_col": [1, 2, 3]})
    result = _filter_by_solution_id(table, "R1000M")
    assert result.empty
    assert list(result.columns) == ["other_col"]


def test_filter_by_solution_id_no_match_returns_empty() -> None:
    table = pd.DataFrame({"solution_id": ["R500M", "R2000M"], "value": [1.0, 2.0]})
    result = _filter_by_solution_id(table, "R1000M")
    assert result.empty


def test_filter_by_solution_id_preserves_dtypes() -> None:
    table = pd.DataFrame({"solution_id": ["R1000M", "R500M"], "ton": [10.5, 20.0]})
    result = _filter_by_solution_id(table, "R1000M")
    assert len(result) == 1
    assert math.isclose(result["ton"].iloc[0], 10.5)


def test_metric_value_empty_returns_zero() -> None:
    assert metric_value(pd.DataFrame(), "any") == 0.0


def test_metric_value_missing_columns_returns_zero() -> None:
    assert metric_value(pd.DataFrame({"other": [1]}), "any") == 0.0


def test_metric_value_missing_metric_returns_zero() -> None:
    metrics = pd.DataFrame({"metric_name": ["total_discharge_ton_day"], "metric_value": [100.0]})
    assert metric_value(metrics, "nonexistent") == 0.0


def test_metric_value_nan_returns_zero() -> None:
    metrics = pd.DataFrame(
        {"metric_name": ["total_discharge_ton_day"], "metric_value": [float("nan")]}
    )
    assert metric_value(metrics, "total_discharge_ton_day") == 0.0


def test_last_data_refresh_returns_kst_datetime(tmp_path) -> None:  # type: ignore[no-untyped-def]
    silver = tmp_path / "silver"
    silver.mkdir()
    p = silver / "suppliers.parquet"
    p.write_bytes(b"\x00")
    result = last_data_refresh(str(tmp_path))
    assert result is not None
    assert result.tzinfo == KST


def test_last_data_refresh_returns_none_when_no_parquet(tmp_path) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "silver").mkdir()
    (tmp_path / "gold").mkdir()
    assert last_data_refresh(str(tmp_path)) is None


def test_metric_value_returns_correct_float() -> None:
    metrics = pd.DataFrame(
        {"metric_name": ["utilization_rate", "savings_krw_year"], "metric_value": [0.15, 5e8]}
    )
    assert math.isclose(metric_value(metrics, "utilization_rate"), 0.15)
    assert math.isclose(metric_value(metrics, "savings_krw_year"), 5e8)
