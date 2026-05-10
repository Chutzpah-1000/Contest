from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st

from etl.paths import DATA_DIR, GOLD_DIR, SILVER_DIR


@dataclass(frozen=True)
class AppData:
    """Read-only app data loaded from silver and gold Parquet caches."""

    suppliers: pd.DataFrame
    demand_parks: pd.DataFrame
    demand_roads: pd.DataFrame
    forecast_monthly: pd.DataFrame
    match_solution: pd.DataFrame
    match_flows: pd.DataFrame
    epiphany_metrics: pd.DataFrame


@st.cache_data(show_spinner=False)
def load_app_data(data_dir: str = str(DATA_DIR)) -> AppData:
    """Load all Streamlit-facing cached tables.

    Returns:
        AppData container with silver and gold tables.
    """
    root = Path(data_dir)
    silver_dir = root / SILVER_DIR.name
    gold_dir = root / GOLD_DIR.name
    return AppData(
        suppliers=pd.read_parquet(silver_dir / "suppliers.parquet"),
        demand_parks=pd.read_parquet(silver_dir / "demand_parks.parquet"),
        demand_roads=pd.read_parquet(silver_dir / "demand_roads.parquet"),
        forecast_monthly=pd.read_parquet(gold_dir / "forecast_monthly.parquet"),
        match_solution=pd.read_parquet(gold_dir / "match_solution.parquet"),
        match_flows=pd.read_parquet(gold_dir / "match_flows.parquet"),
        epiphany_metrics=pd.read_parquet(gold_dir / "epiphany_metrics.parquet"),
    )
