from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

import streamlit as st

from app.services.matching import metric_value
from etl.transform.normalize import numeric_values

if TYPE_CHECKING:
    from collections.abc import Sequence

    import pandas as pd


def _render_metric_grid(items: Sequence[tuple[str, str]]) -> None:
    metric_html = "".join(
        f"""
        <div class="metric-block">
            <div class="metric-label">{escape(label)}</div>
            <div class="metric-value">{escape(value)}</div>
        </div>
        """
        for label, value in items
    )
    st.markdown(
        f"""
        <style>
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            column-gap: 2rem;
            row-gap: 1.25rem;
            width: 100%;
            margin: 0.5rem 0 1.25rem;
        }}
        .metric-block {{
            min-width: 0;
        }}
        .metric-label {{
            font-size: 0.92rem;
            font-weight: 700;
            line-height: 1.35;
            margin-bottom: 0.35rem;
        }}
        .metric-value {{
            font-size: 1.55rem;
            font-weight: 700;
            line-height: 1.15;
            overflow-wrap: anywhere;
        }}
        @media (max-width: 720px) {{
            .metric-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        </style>
        <div class="metric-grid">{metric_html}</div>
        """,
        unsafe_allow_html=True,
    )


def render_epiphany_cards(metrics: pd.DataFrame) -> None:
    """Render the four PRD epiphany counters."""
    total_discharge = metric_value(metrics, "total_discharge_ton_day")
    savings_year = metric_value(metrics, "savings_krw_year")
    carbon_year = metric_value(metrics, "co2_eq_year")
    utilization_rate = metric_value(metrics, "utilization_rate")

    _render_metric_grid(
        [
            ("오늘 하수도행", f"{total_discharge:,.0f}톤"),
            ("연 절감액", f"{savings_year / 100_000_000:,.2f}억원"),
            ("탄소 절감", f"{carbon_year:,.1f}tCO2eq"),
            ("활용률", f"0% → {utilization_rate:,.1f}%"),
        ],
    )


def render_solution_summary(solution: pd.DataFrame, flows: pd.DataFrame) -> None:
    """Render a compact matching solution summary."""
    objective = sum(numeric_values(solution, ("objective_krw",), 0.0))
    coverage = sum(numeric_values(solution, ("coverage_rate",), 0.0))
    matched = sum(numeric_values(flows, ("ton_per_day",), 0.0))
    _render_metric_grid(
        [
            ("일 매칭량", f"{matched:,.1f}톤"),
            ("목적함수", f"{objective / 1_000_000:,.2f}백만원/일"),
            ("수요 충족률", f"{coverage * 100:,.1f}%"),
        ],
    )
