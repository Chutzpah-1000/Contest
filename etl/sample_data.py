from __future__ import annotations

from typing import TYPE_CHECKING, Final

import pandas as pd

from etl.paths import (
    BRONZE_ASOS,
    BRONZE_BUILDINGS,
    BRONZE_GROUNDWATER,
    BRONZE_PARKS,
    BRONZE_ROADS,
    BRONZE_SPEI,
)

if TYPE_CHECKING:
    from pathlib import Path

DEMO_MONTH: Final = "2026-05"


def build_demo_bronze_tables() -> dict[str, pd.DataFrame]:
    """Return deterministic bronze-like tables for offline demos and tests."""
    groundwater = pd.DataFrame(
        {
            "name": [
                "Seoul Resource Recovery Center",
                "Changdong Culture Industry Complex",
                "Seoul Station Complex",
                "Jamsil Transit Center",
            ],
            "address": [
                "Mapo-gu, Seoul",
                "Dobong-gu, Seoul",
                "Jung-gu, Seoul",
                "Songpa-gu, Seoul",
            ],
            "latitude": [37.5661, 37.6534, 37.5547, 37.5133],
            "longitude": [126.9019, 127.0476, 126.9707, 127.1002],
            "daily_avg_supply_ton": [1326.0, 1136.0, 280.0, 420.0],
            "water_quality_grade": [2, 2, 3, 3],
            "report_status": ["discharging", "discharging", "reported", "reported"],
            "year_month": [DEMO_MONTH, DEMO_MONTH, DEMO_MONTH, DEMO_MONTH],
            "source": ["demo_seoul_open_data"] * 4,
        },
    )
    buildings = pd.DataFrame(
        {
            "name": groundwater["name"],
            "total_floor_area_m2": [140000.0, 120000.0, 85000.0, 92000.0],
            "floors": [14, 22, 18, 24],
            "source": ["demo_building_register"] * 4,
        },
    )
    parks = pd.DataFrame(
        {
            "name": ["World Cup Park", "Seoul Forest", "Dream Forest", "Olympic Park"],
            "district": ["Mapo-gu", "Seongdong-gu", "Gangbuk-gu", "Songpa-gu"],
            "latitude": [37.5683, 37.5444, 37.6204, 37.5205],
            "longitude": [126.8972, 127.0374, 127.0417, 127.1219],
            "area_m2": [2284085.0, 480994.0, 662627.0, 1447122.0],
            "veg_type": ["mixed", "tree", "mixed", "lawn"],
            "source": ["demo_seoul_parks"] * 4,
        },
    )
    roads = pd.DataFrame(
        {
            "name": ["Mapo-daero", "Seongsu Bridge Road", "Dobong-ro", "Olympic-ro"],
            "district": ["Mapo-gu", "Seongdong-gu", "Dobong-gu", "Songpa-gu"],
            "centroid_lat": [37.5484, 37.5396, 37.6641, 37.5151],
            "centroid_lng": [126.9558, 127.0449, 127.0411, 127.1061],
            "length_m": [4200.0, 1800.0, 3600.0, 5100.0],
            "road_type": ["arterial", "arterial", "collector", "arterial"],
            "source": ["demo_seoul_roads"] * 4,
        },
    )
    asos = pd.DataFrame(
        {
            "station_id": ["108"],
            "station_lat": [37.5714],
            "station_lng": [126.9658],
            "year_month": [DEMO_MONTH],
            "tmean_c": [18.7],
            "tmin_c": [13.1],
            "tmax_c": [24.3],
            "precip_mm": [102.4],
            "rh": [63.0],
            "wind_ms": [2.4],
            "sunshine_hr": [212.0],
            "pm10_ugm3": [38.0],
            "source": ["demo_kma_asos"],
        },
    )
    spei = pd.DataFrame(
        {
            "region_code": ["11"],
            "year_month": [DEMO_MONTH],
            "spei_3m": [-0.2],
            "spei_6m": [0.1],
            "source": ["demo_spei"],
        },
    )
    return {
        BRONZE_GROUNDWATER: groundwater,
        BRONZE_BUILDINGS: buildings,
        BRONZE_PARKS: parks,
        BRONZE_ROADS: roads,
        BRONZE_ASOS: asos,
        BRONZE_SPEI: spei,
    }


def write_demo_bronze_tables(bronze_dir: Path) -> list[Path]:
    """Write deterministic bronze CSV files.

    Returns:
        Paths to the written CSV files.
    """
    bronze_dir.mkdir(parents=True, exist_ok=True)
    written_paths: list[Path] = []
    for filename, table in build_demo_bronze_tables().items():
        path = bronze_dir / filename
        table.to_csv(path, index=False, encoding="utf-8-sig")
        written_paths.append(path)
    return written_paths
