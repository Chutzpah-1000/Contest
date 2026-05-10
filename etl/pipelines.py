from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pandas as pd

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
    GOLD_DIR,
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
from etl.transform.normalize import (
    numeric_values,
    read_csv_table,
    string_values,
    write_parquet_table,
)
from etl.transform.suppliers import build_suppliers, build_supply_history
from models.aggregate import build_epiphany_metrics
from models.forecast.baseline import et0_penman_monteith
from models.forecast.lightgbm import predict_demand
from models.matching.ilp import Demand, Supplier, solve

if TYPE_CHECKING:
    from collections.abc import Sequence

KMA_API_KEY_ALIASES: Final = ("KMA_API_KEY", "기상청_API_KEY")
ENV_FILE: Final = Path(".env")


def run_extract(data_dir: Path = DATA_DIR, *, demo: bool = False) -> list[Path]:
    """Run bronze extraction for Seoul and KMA sources.

    Returns:
        Paths written to the bronze directory.
    """
    bronze_dir = data_dir / BRONZE_DIR.name
    if demo:
        return write_demo_bronze_tables(bronze_dir)

    dotenv = _read_dotenv(ENV_FILE)
    seoul_key = _required_env("SEOUL_API_KEY", dotenv=dotenv)
    kma_key = _required_env("KMA_API_KEY", aliases=KMA_API_KEY_ALIASES, dotenv=dotenv)
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


def run_train(data_dir: Path = DATA_DIR) -> list[Path]:
    """Run baseline demand forecast and write gold demand tables.

    Returns:
        Paths written to the gold directory.
    """
    silver_dir = data_dir / SILVER_DIR.name
    gold_dir = data_dir / GOLD_DIR.name
    parks = pd.read_parquet(silver_dir / "demand_parks.parquet")
    roads = pd.read_parquet(silver_dir / "demand_roads.parquet")
    weather = pd.read_parquet(silver_dir / "weather_monthly.parquet")
    forecast_input = _forecast_input(parks=parks, roads=roads, weather=weather)
    forecast = predict_demand(forecast_input)
    baseline = pd.DataFrame(
        {
            "demand_id": string_values(forecast, ("demand_id",), ""),
            "year_month": string_values(forecast, ("year_month",), ""),
            "et0_mm": numeric_values(forecast_input, ("et0_monthly_mm",), 0.0),
            "baseline_demand_ton": numeric_values(forecast, ("baseline_ton",), 0.0),
        },
    )
    return [
        write_parquet_table(baseline, gold_dir / "baseline_demand.parquet"),
        write_parquet_table(forecast, gold_dir / "forecast_monthly.parquet"),
    ]


def run_match(data_dir: Path = DATA_DIR) -> list[Path]:
    """Run radius-based matching and write gold solution tables.

    Returns:
        Paths written to the gold directory.
    """
    silver_dir = data_dir / SILVER_DIR.name
    gold_dir = data_dir / GOLD_DIR.name
    suppliers_table = pd.read_parquet(silver_dir / "suppliers.parquet")
    parks = pd.read_parquet(silver_dir / "demand_parks.parquet")
    roads = pd.read_parquet(silver_dir / "demand_roads.parquet")
    forecast = pd.read_parquet(gold_dir / "forecast_monthly.parquet")
    suppliers = _supplier_nodes(suppliers_table)
    demands = _demand_nodes(parks=parks, roads=roads, forecast=forecast)

    solution_rows, flow_tables, metric_tables = _radius_solutions(
        suppliers_table=suppliers_table,
        suppliers=suppliers,
        demands=demands,
    )
    match_solution = pd.DataFrame(solution_rows)
    match_flows = pd.concat(flow_tables, ignore_index=True)
    epiphany_metrics = pd.concat(metric_tables, ignore_index=True)
    return [
        write_parquet_table(match_solution, gold_dir / "match_solution.parquet"),
        write_parquet_table(match_flows, gold_dir / "match_flows.parquet"),
        write_parquet_table(epiphany_metrics, gold_dir / "epiphany_metrics.parquet"),
    ]


def _radius_solutions(
    suppliers_table: pd.DataFrame,
    suppliers: list[Supplier],
    demands: list[Demand],
) -> tuple[list[dict[str, object]], list[pd.DataFrame], list[pd.DataFrame]]:
    solution_rows: list[dict[str, object]] = []
    flow_tables: list[pd.DataFrame] = []
    metric_tables: list[pd.DataFrame] = []
    for radius_km in (0.5, 1.0, 2.0):
        solution_id = f"R{int(radius_km * 1000)}M"
        solution = solve(suppliers=suppliers, demands=demands, radius_km=radius_km)
        flows = solution.flows.copy()
        if not flows.empty:
            flows.insert(0, "solution_id", solution_id)
        flow_tables.append(flows)
        solution_rows.append(
            {
                "solution_id": solution_id,
                "radius_km": radius_km,
                "lambda_unmet": 5000.0,
                "run_at": pd.Timestamp.now(tz="Asia/Seoul"),
                "objective_krw": solution.objective_krw,
                "coverage_rate": solution.coverage_rate,
                "solver_status": solution.solver_status,
            },
        )
        metric_tables.append(
            build_epiphany_metrics(
                suppliers=suppliers_table,
                flows=flows,
                solution_id=solution_id,
                coverage_rate=solution.coverage_rate,
            ),
        )
    return solution_rows, flow_tables, metric_tables


def main(argv: Sequence[str] | None = None) -> int:
    """Run ETL pipeline subcommands.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="Groundwater matching ETL pipeline.")
    parser.add_argument("command", choices=("extract", "transform", "train", "match"))
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "extract":
        written = run_extract(data_dir=args.data_dir, demo=args.demo)
    elif args.command == "transform":
        written = run_transform(data_dir=args.data_dir)
    elif args.command == "train":
        written = run_train(data_dir=args.data_dir)
    else:
        written = run_match(data_dir=args.data_dir)
    for path in written:
        print(path)
    return 0


def _required_env(
    name: str,
    *,
    aliases: tuple[str, ...] = (),
    dotenv: dict[str, str] | None = None,
) -> str:
    candidates = (name, *aliases)
    for candidate in candidates:
        value = os.getenv(candidate, "") or (dotenv or {}).get(candidate, "")
        if value:
            return value
    raise ValueError(f"Environment variable {name} is required.")


def _required_file(path: Path) -> Path:
    if path.exists():
        return path
    raise FileNotFoundError(f"Missing bronze input: {path}")


def _read_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def _forecast_input(
    parks: pd.DataFrame, roads: pd.DataFrame, weather: pd.DataFrame
) -> pd.DataFrame:
    weather_row = weather.iloc[0].to_dict()
    et0_daily = et0_penman_monteith(
        tmean_c=float(weather_row["tmean_c"]),
        tmin_c=float(weather_row["tmin_c"]),
        tmax_c=float(weather_row["tmax_c"]),
        rh=float(weather_row["rh"]),
        wind_ms=float(weather_row["wind_ms"]),
        rs_mj_m2=18.0,
        lat_rad=0.655,
        doy=135,
    )
    year_month = str(weather_row["year_month"])
    records: list[dict[str, object]] = [
        {
            "demand_id": row["demand_id"],
            "year_month": year_month,
            "area_m2": row["area_m2"],
            "crop_coeff_kc": row["crop_coeff_kc"],
            "et0_monthly_mm": et0_daily * 30,
        }
        for row in parks.to_dict(orient="records")
    ]
    records.extend(
        {
            "demand_id": row["demand_id"],
            "year_month": year_month,
            "area_m2": float(row["length_m"]) * 3.0,
            "crop_coeff_kc": 1.0,
            "et0_monthly_mm": et0_daily * 30,
        }
        for row in roads.to_dict(orient="records")
    )
    return pd.DataFrame(records)


def _supplier_nodes(suppliers: pd.DataFrame) -> list[Supplier]:
    records = suppliers.to_dict(orient="records")
    return [
        Supplier(
            id=str(row["supplier_id"]),
            lat=float(row["latitude"]),
            lng=float(row["longitude"]),
            daily_supply_ton=float(row["daily_avg_supply_ton"]),
            quality_grade=int(row["water_quality_grade"]),
        )
        for row in records
        if bool(row["reportable"])
    ]


def _demand_nodes(parks: pd.DataFrame, roads: pd.DataFrame, forecast: pd.DataFrame) -> list[Demand]:
    forecast_by_id = {
        str(row["demand_id"]): float(row["predicted_ton"]) / 30.0
        for row in forecast.to_dict(orient="records")
    }
    demands: list[Demand] = []
    for row in parks.to_dict(orient="records"):
        demand_id = str(row["demand_id"])
        demands.append(
            Demand(
                id=demand_id,
                lat=float(row["latitude"]),
                lng=float(row["longitude"]),
                daily_demand_ton=forecast_by_id.get(demand_id, 0.0),
                min_quality_grade=int(row["min_quality_grade"]),
            ),
        )
    for row in roads.to_dict(orient="records"):
        demand_id = str(row["demand_id"])
        demands.append(
            Demand(
                id=demand_id,
                lat=float(row["centroid_lat"]),
                lng=float(row["centroid_lng"]),
                daily_demand_ton=forecast_by_id.get(demand_id, 0.0),
                min_quality_grade=int(row["min_quality_grade"]),
            ),
        )
    return demands


if __name__ == "__main__":
    raise SystemExit(main())
