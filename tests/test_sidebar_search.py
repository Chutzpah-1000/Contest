from __future__ import annotations

import pandas as pd

from app.components.sidebar import _SIDEBAR_CSS, _find_building, resolve_search_state


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


def test_find_building_empty_dataframe_returns_none() -> None:
    assert _find_building(pd.DataFrame(), "anything") is None


def test_find_building_missing_name_column_returns_none() -> None:
    suppliers = pd.DataFrame({"other_col": ["x", "y"]})
    assert _find_building(suppliers, "search") is None


def test_find_building_empty_search_term_returns_none() -> None:
    suppliers = pd.DataFrame([{"name": "A", "address": "a"}])
    assert _find_building(suppliers, "") is None


def test_find_building_no_match_returns_none() -> None:
    suppliers = pd.DataFrame(
        [
            {
                "name": "광역자원순환센터",
                "address": "마포구",
                "daily_avg_supply_ton": 100.0,
                "water_quality_grade": 2,
                "report_status": "discharging",
                "reportable": True,
            }
        ]
    )
    assert _find_building(suppliers, "존재하지않는검색어xyz") is None


def test_sidebar_footer_mobile_breakpoint_tokens_present() -> None:
    # Round 30 회귀 가드 — 720px 이하 사이드바 footer 축소 분기.
    assert "@media(max-width:720px)" in _SIDEBAR_CSS
    assert ".sb-footer {font-size:9px" in _SIDEBAR_CSS
    assert ".sb-title {font-size:13px" in _SIDEBAR_CSS


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
