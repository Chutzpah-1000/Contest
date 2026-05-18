from __future__ import annotations

from app.components.sidebar import resolve_search_state


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
