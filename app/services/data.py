from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

from etl.paths import DATA_DIR, GOLD_DIR, SILVER_DIR

KST: timezone = timezone(timedelta(hours=9))


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


@st.cache_data(show_spinner=False, ttl=300)
def last_data_refresh(data_dir: str = str(DATA_DIR)) -> datetime | None:
    """Return the most recent mtime across silver+gold parquet caches.

    Args:
        data_dir: 데이터 루트 디렉토리. 기본값은 :data:`etl.paths.DATA_DIR`.

    Returns:
        가장 최근 parquet 의 mtime (KST). 캐시 파일이 하나도 없으면 ``None``.
    """
    root = Path(data_dir)
    candidates = list((root / SILVER_DIR.name).glob("*.parquet")) + list(
        (root / GOLD_DIR.name).glob("*.parquet")
    )
    if not candidates:
        return None
    latest = max(c.stat().st_mtime for c in candidates)
    return datetime.fromtimestamp(latest, tz=KST)


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
