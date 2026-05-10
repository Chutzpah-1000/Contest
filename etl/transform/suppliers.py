from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import pandas as pd

from etl.transform.normalize import (
    fill_missing_seoul_coordinates,
    normalize_year_month_values,
    numeric_values,
    string_values,
    validate_seoul_bbox,
)

REPORTABLE_MIN_FLOORS: Final = 21
REPORTABLE_MIN_AREA_M2: Final = 100_000.0
DAYS_PER_MONTH: Final = 30.0


@dataclass(frozen=True)
class _SupplierColumns:
    names: list[str]
    addresses: list[str]
    latitudes: list[float]
    longitudes: list[float]
    daily_supplies: list[float]
    floors: list[int]
    areas: list[float]
    quality_grades: list[int]
    statuses: list[str]
    sources: list[str]


def build_suppliers(
    groundwater: pd.DataFrame, buildings: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Build the silver suppliers table from groundwater and building records.

    Returns:
        Supplier table following the silver schema.
    """
    building_lookup = _building_lookup(buildings) if buildings is not None else {}
    columns = _supplier_columns(groundwater)
    records: list[dict[str, object]] = []
    for index, name in enumerate(columns.names):
        daily_supply = columns.daily_supplies[index]
        if daily_supply <= 0:
            continue
        building_area, building_floors = building_lookup.get(name, (0.0, 0))
        total_area = columns.areas[index] or building_area
        total_floors = columns.floors[index] or building_floors
        records.append(
            {
                "supplier_id": f"SUP-{len(records) + 1:05d}",
                "name": name,
                "address": columns.addresses[index],
                "latitude": columns.latitudes[index],
                "longitude": columns.longitudes[index],
                "total_floor_area_m2": total_area,
                "floors": total_floors,
                "daily_avg_supply_ton": daily_supply,
                "water_quality_grade": columns.quality_grades[index],
                "report_status": columns.statuses[index],
                "reportable": total_floors >= REPORTABLE_MIN_FLOORS
                or total_area >= REPORTABLE_MIN_AREA_M2,
                "source": columns.sources[index],
                "ingested_at": pd.Timestamp.now(tz="Asia/Seoul"),
            },
        )

    suppliers = pd.DataFrame.from_records(records)
    validate_seoul_bbox(suppliers)
    return suppliers


def build_supply_history(suppliers: pd.DataFrame, source: pd.DataFrame) -> pd.DataFrame:
    """Build monthly supplier history from daily average supply.

    Returns:
        Monthly supply history table following the silver schema.
    """
    year_months = normalize_year_month_values(source)
    supplier_ids = string_values(suppliers, ("supplier_id",), "")
    daily_supplies = numeric_values(suppliers, ("daily_avg_supply_ton",), 0.0)
    sources = string_values(suppliers, ("source",), "seoul_open_data")
    return pd.DataFrame(
        {
            "supplier_id": supplier_ids,
            "year_month": year_months[: len(supplier_ids)],
            "supply_ton": [daily_supply * DAYS_PER_MONTH for daily_supply in daily_supplies],
            "source": sources,
        },
    )


def _supplier_columns(groundwater: pd.DataFrame) -> _SupplierColumns:
    latitudes, longitudes = fill_missing_seoul_coordinates(
        numeric_values(groundwater, ("latitude", "lat", "위도"), default=float("nan")),
        numeric_values(groundwater, ("longitude", "lng", "lon", "경도"), default=float("nan")),
    )
    return _SupplierColumns(
        names=string_values(
            groundwater, ("name", "building_name", "시설물명", "건축물명"), "Unknown"
        ),
        addresses=string_values(groundwater, ("address", "location", "위치", "주소"), "Seoul"),
        latitudes=latitudes,
        longitudes=longitudes,
        daily_supplies=numeric_values(
            groundwater,
            ("daily_avg_supply_ton", "daily_supply_ton", "일평균발생량", "발생량"),
            default=0.0,
        ),
        floors=[
            int(value)
            for value in numeric_values(groundwater, ("floors", "floor_count", "층수"), 0.0)
        ],
        areas=numeric_values(groundwater, ("total_floor_area_m2", "floor_area_m2", "연면적"), 0.0),
        quality_grades=[
            min(4, max(1, int(value)))
            for value in numeric_values(
                groundwater, ("water_quality_grade", "quality_grade", "수질등급"), 3.0
            )
        ],
        statuses=string_values(groundwater, ("report_status", "신고상태"), "discharging"),
        sources=string_values(groundwater, ("source",), "seoul_open_data"),
    )


def _building_lookup(buildings: pd.DataFrame) -> dict[str, tuple[float, int]]:
    names = string_values(buildings, ("name", "building_name", "시설물명", "건축물명"), "Unknown")
    areas = numeric_values(buildings, ("total_floor_area_m2", "floor_area_m2", "연면적"), 0.0)
    floors = [
        int(value) for value in numeric_values(buildings, ("floors", "floor_count", "층수"), 0.0)
    ]
    return {name: (areas[index], floors[index]) for index, name in enumerate(names)}
