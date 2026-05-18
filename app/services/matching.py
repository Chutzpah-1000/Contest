from __future__ import annotations

from dataclasses import dataclass
import math

import pandas as pd


@dataclass(frozen=True)
class SelectedSolution:
    """Selected matching solution and its derived tables."""

    solution_id: str
    radius_m: int
    solution: pd.DataFrame
    flows: pd.DataFrame
    metrics: pd.DataFrame


def solution_id_for_radius(radius_m: int) -> str:
    """Return the cached solution id for a radius.

    Returns:
        Solution id matching the gold cache convention.
    """
    return f"R{radius_m}M"


def _filter_by_solution_id(table: pd.DataFrame, solution_id: str) -> pd.DataFrame:
    if "solution_id" not in table.columns:
        return pd.DataFrame(columns=list(table.columns))
    return table.loc[table["solution_id"] == solution_id].reset_index(drop=True)


def select_solution(
    radius_m: int,
    solutions: pd.DataFrame,
    flows: pd.DataFrame,
    metrics: pd.DataFrame,
) -> SelectedSolution:
    """Filter gold tables to one precomputed solution.

    Returns:
        Selected solution data for UI rendering.
    """
    solution_id = solution_id_for_radius(radius_m)
    return SelectedSolution(
        solution_id=solution_id,
        radius_m=radius_m,
        solution=_filter_by_solution_id(solutions, solution_id),
        flows=_filter_by_solution_id(flows, solution_id),
        metrics=_filter_by_solution_id(metrics, solution_id),
    )


def metric_value(metrics: pd.DataFrame, metric_name: str) -> float:
    """Read a single metric value from a metrics table.

    Returns:
        Metric value or 0.0 when missing.
    """
    if (
        metrics.empty
        or "metric_name" not in metrics.columns
        or "metric_value" not in metrics.columns
    ):
        return 0.0
    mask = metrics["metric_name"] == metric_name
    if not mask.any():
        return 0.0
    raw: object = metrics.loc[mask, "metric_value"].iloc[0]
    try:
        value = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    return value if math.isfinite(value) else 0.0
