from __future__ import annotations

import pandas as pd

from app.components.sidebar import _find_building, resolve_search_state


def test_resolve_idle_keeps_previous_applied() -> None:
    # No submit, no clear — previous applied term wins regardless of raw input.
    assert (
        resolve_search_state(
            raw="typing in progress", submitted=False, cleared=False, current_applied="광화문"
        )
        == "광화문"
    )


def test_resolve_submit_promotes_raw_to_applied() -> None:
    assert (
        resolve_search_state(raw="서울시청", submitted=True, cleared=False, current_applied="")
        == "서울시청"
    )


def test_resolve_clear_wins_over_submit() -> None:
    # Both buttons cannot actually be true in Streamlit, but defensively cleared dominates.
    assert not resolve_search_state(
        raw="동대문", submitted=True, cleared=True, current_applied="강남"
    )


def test_resolve_clear_with_no_prior_state() -> None:
    assert not resolve_search_state(raw="", submitted=False, cleared=True, current_applied="")


def test_resolve_idle_with_empty_state_returns_empty() -> None:
    assert not resolve_search_state(raw="", submitted=False, cleared=False, current_applied="")


def test_find_building_matches_korean_substring() -> None:
    suppliers = pd.DataFrame(
        [
            {
                "name": "서울 광역자원순환센터",
                "address": "서울특별시 마포구",
                "daily_avg_supply_ton": 1234.0,
                "water_quality_grade": 2,
                "report_status": "discharging",
                "reportable": True,
            },
            {
                "name": "강남 헬리오시티",
                "address": "서울특별시 강남구",
                "daily_avg_supply_ton": 80.0,
                "water_quality_grade": 3,
                "report_status": "reported",
                "reportable": False,
            },
        ]
    )
    matched = _find_building(suppliers, "헬리오")
    assert matched is not None
    assert matched["name"] == "강남 헬리오시티"
