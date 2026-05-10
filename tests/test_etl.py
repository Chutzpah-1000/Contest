from __future__ import annotations

import re

import pandas as pd

from etl.paths import SILVER_DIR
from etl.pipelines import run_extract, run_transform
from etl.sample_data import build_demo_bronze_tables
from etl.transform.demand import build_demand_parks, build_demand_roads
from etl.transform.normalize import validate_seoul_bbox
from etl.transform.suppliers import build_suppliers


def test_transform_writes_day_one_silver_tables(tmp_path) -> None:
    run_extract(data_dir=tmp_path, demo=True)

    written = run_transform(data_dir=tmp_path)

    expected = {
        "suppliers.parquet",
        "supply_history.parquet",
        "demand_parks.parquet",
        "demand_roads.parquet",
        "weather_monthly.parquet",
        "drought_index.parquet",
    }
    assert expected.issubset({path.name for path in written})
    assert all((tmp_path / SILVER_DIR.name / filename).exists() for filename in expected)


def test_seoul_bbox() -> None:
    tables = build_demo_bronze_tables()
    suppliers = build_suppliers(
        tables["seoul_groundwater_discharge.csv"],
        tables["seoul_buildings_register.csv"],
    )
    parks = build_demand_parks(tables["seoul_parks.csv"])
    roads = build_demand_roads(tables["seoul_roads.csv"])

    validate_seoul_bbox(suppliers)
    validate_seoul_bbox(parks)
    validate_seoul_bbox(roads, lat_col="centroid_lat", lng_col="centroid_lng")


def test_reportable_suppliers_are_identified() -> None:
    tables = build_demo_bronze_tables()
    suppliers = build_suppliers(
        tables["seoul_groundwater_discharge.csv"],
        tables["seoul_buildings_register.csv"],
    )

    matched = suppliers[
        suppliers["name"].isin(
            ["Seoul Resource Recovery Center", "Changdong Culture Industry Complex"]
        )
    ]

    assert matched["reportable"].all()


def test_no_nan_in_core_silver_fields() -> None:
    tables = build_demo_bronze_tables()
    suppliers = build_suppliers(
        tables["seoul_groundwater_discharge.csv"],
        tables["seoul_buildings_register.csv"],
    )
    parks = build_demand_parks(tables["seoul_parks.csv"])

    supplier_columns = ["daily_avg_supply_ton", "latitude", "longitude"]
    park_columns = ["area_m2", "latitude", "longitude"]
    assert not suppliers[supplier_columns].isna().any().any()
    assert not parks[park_columns].isna().any().any()


def test_year_month_fields_use_month_grain(tmp_path) -> None:
    run_extract(data_dir=tmp_path, demo=True)
    run_transform(data_dir=tmp_path)

    supply_history = pd.read_parquet(tmp_path / SILVER_DIR.name / "supply_history.parquet")
    weather = pd.read_parquet(tmp_path / SILVER_DIR.name / "weather_monthly.parquet")
    drought = pd.read_parquet(tmp_path / SILVER_DIR.name / "drought_index.parquet")
    pattern = re.compile(r"^\d{4}-\d{2}$")

    assert supply_history["year_month"].map(lambda value: bool(pattern.match(value))).all()
    assert weather["year_month"].map(lambda value: bool(pattern.match(value))).all()
    assert drought["year_month"].map(lambda value: bool(pattern.match(value))).all()
