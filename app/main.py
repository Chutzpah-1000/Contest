from __future__ import annotations

import streamlit as st
from streamlit_folium import st_folium

from app.components.cards import render_epiphany_cards, render_solution_summary
from app.components.map import build_matching_map
from app.components.sidebar import render_sidebar
from app.services.data import load_app_data
from app.services.matching import select_solution


def main() -> None:
    """Render the Streamlit MVP app."""
    st.set_page_config(page_title="서울 유출지하수 매칭", layout="wide")
    st.title("서울 유출지하수 매칭")

    data = load_app_data()
    radius_m = render_sidebar()
    selected = select_solution(
        radius_m=radius_m,
        solutions=data.match_solution,
        flows=data.match_flows,
        metrics=data.epiphany_metrics,
    )
    render_epiphany_cards(selected.metrics)
    render_solution_summary(selected.solution, selected.flows)

    st_folium(
        build_matching_map(
            suppliers=data.suppliers,
            parks=data.demand_parks,
            roads=data.demand_roads,
            flows=selected.flows,
        ),
        height=620,
        use_container_width=True,
    )
    st.caption("데이터 출처: 서울 열린데이터광장, 기상청 ASOS Open API")


if __name__ == "__main__":
    main()
