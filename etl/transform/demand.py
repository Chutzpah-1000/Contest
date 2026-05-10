from __future__ import annotations

from typing import Final

import pandas as pd

from etl.transform.normalize import (
    fill_missing_seoul_coordinates,
    normalize_year_month_values,
    numeric_values,
    string_values,
    validate_seoul_bbox,
)

PARK_QUALITY_GRADE: Final = 3
ROAD_QUALITY_GRADE: Final = 3
CROP_COEFFICIENTS: Final[dict[str, float]] = {
    "lawn": 0.85,
    "shrub": 0.70,
    "tree": 0.65,
    "mixed": 0.75,
    "road": 1.00,
}


def build_demand_parks(parks: pd.DataFrame) -> pd.DataFrame:
    """Build the silver park demand table.

    Returns:
        Park demand table following the silver schema.
    """
    latitudes, longitudes = fill_missing_seoul_coordinates(
        numeric_values(parks, ("latitude", "lat", "위도"), default=float("nan")),
        numeric_values(parks, ("longitude", "lng", "lon", "경도"), default=float("nan")),
    )
    names = string_values(parks, ("name", "park_name", "공원명"), "Unknown park")
    districts = string_values(parks, ("district", "자치구"), "Seoul")
    areas = numeric_values(parks, ("area_m2", "area", "면적"), default=0.0)
    vegetation = [
        value.lower()
        for value in string_values(parks, ("veg_type", "vegetation", "식재유형"), "mixed")
    ]
    sources = string_values(parks, ("source",), "seoul_parks")
    records: list[dict[str, object]] = []
    for index, area in enumerate(areas):
        if area <= 0:
            continue
        veg_type = vegetation[index] if vegetation[index] in CROP_COEFFICIENTS else "mixed"
        records.append(
            {
                "demand_id": f"PRK-{len(records) + 1:05d}",
                "name": names[index],
                "district": districts[index],
                "latitude": latitudes[index],
                "longitude": longitudes[index],
                "area_m2": area,
                "veg_type": veg_type,
                "crop_coeff_kc": CROP_COEFFICIENTS[veg_type],
                "min_quality_grade": PARK_QUALITY_GRADE,
                "source": sources[index],
            },
        )
    demand_parks = pd.DataFrame.from_records(records)
    validate_seoul_bbox(demand_parks)
    return demand_parks


def build_demand_roads(roads: pd.DataFrame) -> pd.DataFrame:
    """Build the silver road demand table.

    Returns:
        Road demand table following the silver schema.
    """
    latitudes, longitudes = fill_missing_seoul_coordinates(
        numeric_values(roads, ("centroid_lat", "latitude", "lat", "위도"), default=float("nan")),
        numeric_values(
            roads, ("centroid_lng", "longitude", "lng", "lon", "경도"), default=float("nan")
        ),
    )
    names = string_values(roads, ("name", "road_name", "도로명"), "Unknown road")
    districts = string_values(roads, ("district", "자치구"), "Seoul")
    lengths = numeric_values(roads, ("length_m", "length", "연장"), default=0.0)
    road_types = string_values(roads, ("road_type", "도로유형"), "local")
    sources = string_values(roads, ("source",), "seoul_roads")
    records: list[dict[str, object]] = []
    for index, length_m in enumerate(lengths):
        if length_m <= 0:
            continue
        records.append(
            {
                "demand_id": f"RDS-{len(records) + 1:05d}",
                "name": names[index],
                "district": districts[index],
                "centroid_lat": latitudes[index],
                "centroid_lng": longitudes[index],
                "length_m": length_m,
                "road_type": road_types[index],
                "min_quality_grade": ROAD_QUALITY_GRADE,
                "source": sources[index],
            },
        )
    demand_roads = pd.DataFrame.from_records(records)
    validate_seoul_bbox(demand_roads, lat_col="centroid_lat", lng_col="centroid_lng")
    return demand_roads


def build_weather_monthly(asos: pd.DataFrame) -> pd.DataFrame:
    """Build the silver monthly weather table.

    Returns:
        Monthly weather table following the silver schema.
    """
    return pd.DataFrame(
        {
            "station_id": string_values(asos, ("station_id", "stn_id", "지점"), "108"),
            "station_lat": numeric_values(asos, ("station_lat", "lat"), default=37.5714),
            "station_lng": numeric_values(asos, ("station_lng", "lng", "lon"), default=126.9658),
            "year_month": normalize_year_month_values(asos),
            "tmean_c": numeric_values(asos, ("tmean_c", "avg_ta", "평균기온"), default=18.0),
            "tmin_c": numeric_values(asos, ("tmin_c", "min_ta", "최저기온"), default=13.0),
            "tmax_c": numeric_values(asos, ("tmax_c", "max_ta", "최고기온"), default=24.0),
            "precip_mm": numeric_values(asos, ("precip_mm", "sum_rn", "강수량"), default=100.0),
            "rh": numeric_values(asos, ("rh", "avg_rhm", "상대습도"), default=60.0),
            "wind_ms": numeric_values(asos, ("wind_ms", "avg_ws", "풍속"), default=2.0),
            "sunshine_hr": numeric_values(asos, ("sunshine_hr", "sum_ss_hr"), default=200.0),
            "pm10_ugm3": numeric_values(asos, ("pm10_ugm3", "pm10"), default=35.0),
            "source": string_values(asos, ("source",), "kma_asos"),
        },
    )


def build_drought_index(spei: pd.DataFrame) -> pd.DataFrame:
    """Build the silver drought index table.

    Returns:
        Drought index table following the silver schema.
    """
    return pd.DataFrame(
        {
            "region_code": string_values(spei, ("region_code", "region"), "11"),
            "year_month": normalize_year_month_values(spei),
            "spei_3m": numeric_values(spei, ("spei_3m", "spei"), default=0.0),
            "spei_6m": numeric_values(spei, ("spei_6m",), default=0.0),
            "source": string_values(spei, ("source",), "spei"),
        },
    )


def build_water_quality_grades() -> pd.DataFrame:
    """Build the static water quality reference table.

    Returns:
        Static water quality reference table.
    """
    return pd.DataFrame(
        {
            "grade": [1, 2, 3, 4],
            "label": ["best", "industrial", "landscape", "treatment_required"],
            "allowed_uses": ["all", "industry_landscape_road", "landscape_road", "after_treatment"],
        },
    )


def build_crop_coefficients() -> pd.DataFrame:
    """Build the static crop coefficient reference table.

    Returns:
        Static crop coefficient reference table.
    """
    return pd.DataFrame(
        {
            "veg_type": list(CROP_COEFFICIENTS),
            "kc": list(CROP_COEFFICIENTS.values()),
            "source": ["FAO-56 reference"] * len(CROP_COEFFICIENTS),
        },
    )
