from __future__ import annotations

import math
from typing import Final

ALBEDO: Final = 0.23
SOLAR_CONSTANT: Final = 0.0820
STEFAN_BOLTZMANN: Final = 4.903e-9
DEFAULT_ATMOSPHERIC_PRESSURE_KPA: Final = 101.3


def et0_penman_monteith(
    tmean_c: float,
    tmin_c: float,
    tmax_c: float,
    rh: float,
    wind_ms: float,
    rs_mj_m2: float,
    lat_rad: float,
    doy: int,
) -> float:
    """Calculate FAO-56 reference evapotranspiration.

    Returns:
        Reference evapotranspiration in mm/day.
    """
    saturation_vapor_pressure = (_sat_vapor_pressure(tmax_c) + _sat_vapor_pressure(tmin_c)) / 2
    actual_vapor_pressure = saturation_vapor_pressure * max(0.0, min(rh, 100.0)) / 100
    slope = _slope_vapor_pressure_curve(tmean_c)
    psychrometric = 0.000665 * DEFAULT_ATMOSPHERIC_PRESSURE_KPA
    net_radiation = _net_radiation(
        tmin_c=tmin_c,
        tmax_c=tmax_c,
        actual_vapor_pressure=actual_vapor_pressure,
        solar_radiation=rs_mj_m2,
        clear_sky_radiation=_clear_sky_radiation(lat_rad=lat_rad, doy=doy),
    )
    numerator = (0.408 * slope * net_radiation) + (
        psychrometric
        * (900 / (tmean_c + 273))
        * wind_ms
        * (saturation_vapor_pressure - actual_vapor_pressure)
    )
    denominator = slope + psychrometric * (1 + (0.34 * wind_ms))
    return max(0.0, numerator / denominator)


def baseline_demand_monthly(
    area_m2: float,
    crop_coeff: float,
    et0_monthly_mm: float,
    irrigation_efficiency: float = 0.7,
) -> float:
    """Estimate monthly non-potable irrigation demand.

    Returns:
        Demand in tons per month.

    Raises:
        ValueError: If irrigation efficiency is not positive.
    """
    if irrigation_efficiency <= 0:
        raise ValueError("Irrigation efficiency must be positive.")
    return max(0.0, area_m2 * et0_monthly_mm * crop_coeff / irrigation_efficiency / 1000)


def _sat_vapor_pressure(temperature_c: float) -> float:
    return 0.6108 * math.exp((17.27 * temperature_c) / (temperature_c + 237.3))


def _slope_vapor_pressure_curve(temperature_c: float) -> float:
    saturation = _sat_vapor_pressure(temperature_c)
    return 4098 * saturation / ((temperature_c + 237.3) ** 2)


def _clear_sky_radiation(lat_rad: float, doy: int) -> float:
    inverse_relative_distance = 1 + (0.033 * math.cos(2 * math.pi * doy / 365))
    solar_declination = 0.409 * math.sin((2 * math.pi * doy / 365) - 1.39)
    sunset_hour_angle = math.acos(-math.tan(lat_rad) * math.tan(solar_declination))
    extraterrestrial_radiation = (
        (24 * 60 / math.pi)
        * SOLAR_CONSTANT
        * inverse_relative_distance
        * (
            sunset_hour_angle * math.sin(lat_rad) * math.sin(solar_declination)
            + math.cos(lat_rad) * math.cos(solar_declination) * math.sin(sunset_hour_angle)
        )
    )
    return 0.75 * extraterrestrial_radiation


def _net_radiation(
    tmin_c: float,
    tmax_c: float,
    actual_vapor_pressure: float,
    solar_radiation: float,
    clear_sky_radiation: float,
) -> float:
    shortwave = (1 - ALBEDO) * solar_radiation
    tmin_k = tmin_c + 273.16
    tmax_k = tmax_c + 273.16
    cloudiness = (1.35 * min(solar_radiation / clear_sky_radiation, 1.0)) - 0.35
    longwave = (
        STEFAN_BOLTZMANN
        * (((tmax_k**4) + (tmin_k**4)) / 2)
        * (0.34 - (0.14 * math.sqrt(max(actual_vapor_pressure, 0.0))))
        * cloudiness
    )
    return shortwave - longwave
