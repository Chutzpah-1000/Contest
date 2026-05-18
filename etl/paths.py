from __future__ import annotations

from pathlib import Path

DATA_DIR = Path("data")
BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"

BRONZE_GROUNDWATER = "seoul_groundwater_data.csv"
BRONZE_PARKS = "seoul_parks_data.csv"
BRONZE_ROADS = "seoul_roads.csv"
BRONZE_BUILDINGS = "seoul_buildings_register.csv"
BRONZE_ASOS = "asos_monthly.csv"
BRONZE_SPEI = "spei_monthly.csv"
