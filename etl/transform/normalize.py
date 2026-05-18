from __future__ import annotations

import hashlib
import math
import re
from typing import TYPE_CHECKING, Final, cast

import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

SEOUL_LAT_RANGE: Final[tuple[float, float]] = (33.0, 39.0)
SEOUL_LNG_RANGE: Final[tuple[float, float]] = (124.0, 132.0)
DEFAULT_SEOUL_LAT: Final = 37.5665
DEFAULT_SEOUL_LNG: Final = 126.9780
SEOUL_BBOX_LAT_RANGE: Final[tuple[float, float]] = (37.43, 37.70)
SEOUL_BBOX_LNG_RANGE: Final[tuple[float, float]] = (126.78, 127.18)


def read_csv_table(path: Path) -> pd.DataFrame:
    """Read a CSV table with Korean-friendly encoding fallback.

    Returns:
        Loaded CSV table.
    """
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp949")


def write_parquet_table(table: pd.DataFrame, path: Path) -> Path:
    """Write a Parquet table, creating the parent directory as needed.

    Returns:
        Path to the written Parquet file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(path, index=False)
    return path


def first_available_column(table: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    """Return the first present column from a candidate list."""
    for candidate in candidates:
        if candidate in table.columns:
            return candidate
    return None


def string_values(
    table: pd.DataFrame,
    candidates: Iterable[str],
    default: str,
) -> list[str]:
    """Return string values from the first matching column.

    Returns:
        String values with missing entries replaced by the default.
    """
    column = first_available_column(table, candidates)
    if column is None:
        return [default for _ in range(len(table))]
    return [_clean_string(value, default) for value in _column_values(table, column)]


def numeric_values(
    table: pd.DataFrame,
    candidates: Iterable[str],
    default: float,
) -> list[float]:
    """Return numeric values from the first matching column.

    Returns:
        Float values with unparsable entries replaced by the default.
    """
    column = first_available_column(table, candidates)
    if column is None:
        return [default for _ in range(len(table))]
    return [_clean_float(value, default) for value in _column_values(table, column)]


def normalize_year_month_values(
    table: pd.DataFrame,
    candidates: Iterable[str] = ("year_month", "month", "date", "ym"),
    default: str = "2026-05",
) -> list[str]:
    """Normalize date-like source columns into YYYY-MM strings.

    Returns:
        String values formatted as YYYY-MM.
    """
    column = first_available_column(table, candidates)
    if column is None:
        return [default for _ in range(len(table))]

    pattern = re.compile(r"(?P<year>\d{4})[-./]?(?P<month>\d{2})")
    normalized: list[str] = []
    for value in _column_values(table, column):
        match = pattern.search(_clean_string(value, default))
        normalized.append(f"{match.group('year')}-{match.group('month')}" if match else default)
    return normalized


def fill_missing_seoul_coordinates(
    latitudes: list[float],
    longitudes: list[float],
) -> tuple[list[float], list[float]]:
    """Fill missing coordinates with deterministic points inside Seoul.

    Returns:
        Filled latitude and longitude values.
    """
    filled_latitudes: list[float] = []
    filled_longitudes: list[float] = []
    for index, latitude in enumerate(latitudes):
        longitude = longitudes[index]
        offset = float(index % 10) * 0.01
        filled_latitudes.append(DEFAULT_SEOUL_LAT + offset if math.isnan(latitude) else latitude)
        filled_longitudes.append(DEFAULT_SEOUL_LNG + offset if math.isnan(longitude) else longitude)
    return filled_latitudes, filled_longitudes


def geocode_with_hash_fallback(
    latitudes: list[float],
    longitudes: list[float],
    seeds: list[str],
) -> tuple[list[float], list[float], list[str]]:
    """Use original coordinates when finite, otherwise hash-scatter inside Seoul bbox.

    Returns:
        (latitudes, longitudes, geo_method) where geo_method is 'original' or 'hash_scatter'.
    """
    lat_lo, lat_hi = SEOUL_BBOX_LAT_RANGE
    lng_lo, lng_hi = SEOUL_BBOX_LNG_RANGE
    out_lat: list[float] = []
    out_lng: list[float] = []
    method: list[str] = []
    for index, latitude in enumerate(latitudes):
        longitude = longitudes[index]
        if math.isfinite(latitude) and math.isfinite(longitude):
            out_lat.append(latitude)
            out_lng.append(longitude)
            method.append("original")
            continue
        seed = seeds[index] if index < len(seeds) else f"row-{index}"
        digest = hashlib.md5(seed.encode("utf-8"), usedforsecurity=False).digest()
        out_lat.append(lat_lo + (digest[0] / 255.0) * (lat_hi - lat_lo))
        out_lng.append(lng_lo + (digest[1] / 255.0) * (lng_hi - lng_lo))
        method.append("hash_scatter")
    return out_lat, out_lng, method


def parse_leading_number(value: object, default: float) -> float:
    """Extract the leading numeric token from a possibly-noisy string ('2896887㎡ …' → 2896887).

    Returns:
        Leading float, or default when no number can be recovered.
    """
    if value is None:
        return default
    if isinstance(value, float) and math.isnan(value):
        return default
    text = str(value).strip().replace(",", "")
    match = re.match(r"[-+]?\d+(?:\.\d+)?", text)
    if match is None:
        return default
    try:
        return float(match.group(0))
    except (TypeError, ValueError):
        return default


def permissive_numeric_values(
    table: pd.DataFrame,
    candidates: Iterable[str],
    default: float,
) -> list[float]:
    """Like numeric_values but tolerates non-numeric suffixes such as units.

    Returns:
        Float values parsed from the leading numeric token of each cell.
    """
    column = first_available_column(table, candidates)
    if column is None:
        return [default for _ in range(len(table))]
    return [parse_leading_number(value, default) for value in _column_values(table, column)]


def parse_floor_count(value: object, default: int = 0) -> int:
    """Parse '20/8' (지상/지하) style or plain numeric floor count to above-ground floors.

    Returns:
        Above-ground floor count, or default when unparsable.
    """
    if value is None:
        return default
    if isinstance(value, float) and math.isnan(value):
        return default
    text = str(value).strip()
    if not text:
        return default
    head = text.split("/")[0].strip()
    try:
        return int(float(head))
    except (TypeError, ValueError):
        return default


def validate_seoul_bbox(
    table: pd.DataFrame,
    lat_col: str = "latitude",
    lng_col: str = "longitude",
) -> None:
    """Validate that all coordinates fit the broad Seoul bounding box.

    Raises:
        ValueError: If any row falls outside the accepted coordinate range.
    """
    latitudes = numeric_values(table, (lat_col,), default=float("nan"))
    longitudes = numeric_values(table, (lng_col,), default=float("nan"))
    invalid_count = sum(
        not _is_in_range(latitude, SEOUL_LAT_RANGE) or not _is_in_range(longitude, SEOUL_LNG_RANGE)
        for latitude, longitude in zip(latitudes, longitudes, strict=True)
    )
    if invalid_count > 0:
        raise ValueError(f"{invalid_count} rows are outside the Seoul coordinate bounds.")


def _column_values(table: pd.DataFrame, column: str) -> list[object]:
    return list(cast("Iterable[object]", table[column]))


def _clean_string(value: object, default: str) -> str:
    if value is None:
        return default
    if isinstance(value, float) and math.isnan(value):
        return default
    text = str(value).strip()
    return text or default


def _clean_float(value: object, default: float) -> float:
    if value is None:
        return default
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return default
    return default if math.isnan(number) else number


def _is_in_range(value: float, bounds: tuple[float, float]) -> bool:
    return not math.isnan(value) and bounds[0] <= value <= bounds[1]
