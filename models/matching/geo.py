from __future__ import annotations

import math
from typing import Final

EARTH_RADIUS_KM: Final = 6371.0088


def haversine_km(lat_a: float, lng_a: float, lat_b: float, lng_b: float) -> float:
    """Calculate great-circle distance between two WGS84 points.

    Returns:
        Distance in kilometers.
    """
    lat_a_rad = math.radians(lat_a)
    lat_b_rad = math.radians(lat_b)
    delta_lat = math.radians(lat_b - lat_a)
    delta_lng = math.radians(lng_b - lng_a)
    value = (math.sin(delta_lat / 2) ** 2) + (
        math.cos(lat_a_rad) * math.cos(lat_b_rad) * (math.sin(delta_lng / 2) ** 2)
    )
    return EARTH_RADIUS_KM * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))
