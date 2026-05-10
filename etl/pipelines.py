from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import TYPE_CHECKING

from etl.extract.kma_asos import download_kma_asos
from etl.extract.seoul_data import download_seoul_datasets
from etl.paths import (
    BRONZE_ASOS,
    BRONZE_BUILDINGS,
    BRONZE_DIR,
    BRONZE_GROUNDWATER,
    BRONZE_PARKS,
    BRONZE_ROADS,
    BRONZE_SPEI,
    DATA_DIR,
    SILVER_DIR,
)
from etl.sample_data import write_demo_bronze_tables
from etl.transform.demand import (
    build_crop_coefficients,
    build_demand_parks,
    build_demand_roads,
    build_drought_index,
    build_water_quality_grades,
    build_weather_monthly,
)
from etl.transform.normalize import read_csv_table, write_parquet_table
from etl.transform.suppliers import build_suppliers, build_supply_history

if TYPE_CHECKING:
    from collections.abc import Sequence


def run_extract(data_dir: Path = DATA_DIR, *, demo: bool = False) -> list[Path]:
    """Run bronze extraction for Seoul and KMA sources.

    Returns:
        Paths written to the bronze directory.
    """
    bronze_dir = data_dir / BRONZE_DIR.name
    if demo:
        return write_demo_bronze_tables(bronze_dir)

    seoul_key = _required_env("SEOUL_API_KEY")
    kma_key = _required_env("KMA_API_KEY")
    written = list(download_seoul_datasets(seoul_key, bronze_dir).values())
    written.append(
        download_kma_asos(
            api_key=kma_key,
            output_dir=bronze_dir,
            start_date="20250501",
            end_date="20260531",
        ),
    )
    return written


def run_transform(data_dir: Path = DATA_DIR) -> list[Path]:
    """Run bronze-to-silver transformations.

    Returns:
        Paths written to the silver directory.
    """
    bronze_dir = data_dir / BRONZE_DIR.name
    silver_dir = data_dir / SILVER_DIR.name
    groundwater = read_csv_table(_required_file(bronze_dir / BRONZE_GROUNDWATER))
    buildings = read_csv_table(_required_file(bronze_dir / BRONZE_BUILDINGS))
    parks = read_csv_table(_required_file(bronze_dir / BRONZE_PARKS))
    roads = read_csv_table(_required_file(bronze_dir / BRONZE_ROADS))
    asos = read_csv_table(_required_file(bronze_dir / BRONZE_ASOS))
    spei = read_csv_table(_required_file(bronze_dir / BRONZE_SPEI))

    suppliers = build_suppliers(groundwater, buildings)
    outputs = {
        "suppliers.parquet": suppliers,
        "supply_history.parquet": build_supply_history(suppliers, groundwater),
        "demand_parks.parquet": build_demand_parks(parks),
        "demand_roads.parquet": build_demand_roads(roads),
        "weather_monthly.parquet": build_weather_monthly(asos),
        "drought_index.parquet": build_drought_index(spei),
        "water_quality_grades.parquet": build_water_quality_grades(),
        "crop_coefficients.parquet": build_crop_coefficients(),
    }
    return [
        write_parquet_table(table, silver_dir / filename) for filename, table in outputs.items()
    ]


def main(argv: Sequence[str] | None = None) -> int:
    """Run ETL pipeline subcommands.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="Groundwater matching ETL pipeline.")
    parser.add_argument("command", choices=("extract", "transform"))
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "extract":
        written = run_extract(data_dir=args.data_dir, demo=args.demo)
    else:
        written = run_transform(data_dir=args.data_dir)
    for path in written:
        print(path)
    return 0


def _required_env(name: str) -> str:
    value = os.getenv(name, "")
    if value:
        return value
    raise ValueError(f"Environment variable {name} is required.")


def _required_file(path: Path) -> Path:
    if path.exists():
        return path
    raise FileNotFoundError(f"Missing bronze input: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
