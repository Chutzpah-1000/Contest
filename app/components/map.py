from __future__ import annotations

from typing import TYPE_CHECKING, Final

import folium

from etl.transform.normalize import numeric_values, string_values

if TYPE_CHECKING:
    import pandas as pd

SEOUL_CENTER: Final = [37.5665, 126.9780]


def build_matching_map(
    suppliers: pd.DataFrame,
    parks: pd.DataFrame,
    roads: pd.DataFrame,
    flows: pd.DataFrame,
) -> folium.Map:
    """Build the main Folium matching map.

    Returns:
        Folium map with supplier, demand, and flow layers.
    """
    matching_map = folium.Map(location=SEOUL_CENTER, zoom_start=11, tiles="CartoDB positron")
    supplier_lookup = _supplier_lookup(suppliers)
    demand_lookup = _demand_lookup(parks, roads)
    _add_suppliers(matching_map, suppliers, flows)
    _add_parks(matching_map, parks)
    _add_roads(matching_map, roads)
    _add_flows(matching_map, flows, supplier_lookup, demand_lookup)
    return matching_map


def _add_suppliers(map_obj: folium.Map, suppliers: pd.DataFrame, flows: pd.DataFrame) -> None:
    matched_supplier_ids = set(string_values(flows, ("supplier_id",), ""))
    ids = string_values(suppliers, ("supplier_id",), "")
    names = string_values(suppliers, ("name",), "Unknown")
    latitudes = numeric_values(suppliers, ("latitude",), 0.0)
    longitudes = numeric_values(suppliers, ("longitude",), 0.0)
    supplies = numeric_values(suppliers, ("daily_avg_supply_ton",), 0.0)
    qualities = numeric_values(suppliers, ("water_quality_grade",), 0.0)
    statuses = string_values(suppliers, ("report_status",), "")
    for index, supplier_id in enumerate(ids):
        color = "blue" if supplier_id in matched_supplier_ids else "red"
        folium.CircleMarker(
            location=[latitudes[index], longitudes[index]],
            radius=max(6.0, min(18.0, supplies[index] / 90)),
            color=color,
            fill=True,
            fill_opacity=0.75,
            popup=(
                f"{names[index]}<br>{supplies[index]:,.0f} ton/day"
                f"<br>quality {qualities[index]:.0f}<br>{statuses[index]}"
            ),
        ).add_to(map_obj)


def _add_parks(map_obj: folium.Map, parks: pd.DataFrame) -> None:
    names = string_values(parks, ("name",), "Park")
    latitudes = numeric_values(parks, ("latitude",), 0.0)
    longitudes = numeric_values(parks, ("longitude",), 0.0)
    areas = numeric_values(parks, ("area_m2",), 0.0)
    for index, name in enumerate(names):
        folium.CircleMarker(
            location=[latitudes[index], longitudes[index]],
            radius=max(5.0, min(14.0, areas[index] / 180_000)),
            color="orange",
            fill=True,
            fill_opacity=0.55,
            popup=f"{name}<br>{areas[index]:,.0f} m2",
        ).add_to(map_obj)


def _add_roads(map_obj: folium.Map, roads: pd.DataFrame) -> None:
    names = string_values(roads, ("name",), "Road")
    latitudes = numeric_values(roads, ("centroid_lat",), 0.0)
    longitudes = numeric_values(roads, ("centroid_lng",), 0.0)
    lengths = numeric_values(roads, ("length_m",), 0.0)
    for index, name in enumerate(names):
        folium.CircleMarker(
            location=[latitudes[index], longitudes[index]],
            radius=5,
            color="darkorange",
            fill=True,
            fill_opacity=0.65,
            popup=f"{name}<br>{lengths[index]:,.0f} m",
        ).add_to(map_obj)


def _add_flows(
    map_obj: folium.Map,
    flows: pd.DataFrame,
    suppliers: dict[str, tuple[float, float]],
    demands: dict[str, tuple[float, float]],
) -> None:
    supplier_ids = string_values(flows, ("supplier_id",), "")
    demand_ids = string_values(flows, ("demand_id",), "")
    tons = numeric_values(flows, ("ton_per_day",), 0.0)
    for index, supplier_id in enumerate(supplier_ids):
        demand_id = demand_ids[index]
        if supplier_id not in suppliers or demand_id not in demands:
            continue
        folium.PolyLine(
            locations=[suppliers[supplier_id], demands[demand_id]],
            color="green",
            weight=max(2.0, min(7.0, tons[index] / 30)),
            opacity=0.65,
            tooltip=f"{tons[index]:,.1f} ton/day",
        ).add_to(map_obj)


def _supplier_lookup(suppliers: pd.DataFrame) -> dict[str, tuple[float, float]]:
    ids = string_values(suppliers, ("supplier_id",), "")
    latitudes = numeric_values(suppliers, ("latitude",), 0.0)
    longitudes = numeric_values(suppliers, ("longitude",), 0.0)
    return {
        supplier_id: (latitudes[index], longitudes[index]) for index, supplier_id in enumerate(ids)
    }


def _demand_lookup(parks: pd.DataFrame, roads: pd.DataFrame) -> dict[str, tuple[float, float]]:
    demand_ids = string_values(parks, ("demand_id",), "")
    latitudes = numeric_values(parks, ("latitude",), 0.0)
    longitudes = numeric_values(parks, ("longitude",), 0.0)
    lookup = {
        demand_id: (latitudes[index], longitudes[index])
        for index, demand_id in enumerate(demand_ids)
    }
    road_ids = string_values(roads, ("demand_id",), "")
    road_latitudes = numeric_values(roads, ("centroid_lat",), 0.0)
    road_longitudes = numeric_values(roads, ("centroid_lng",), 0.0)
    lookup.update(
        {
            demand_id: (road_latitudes[index], road_longitudes[index])
            for index, demand_id in enumerate(road_ids)
        },
    )
    return lookup
