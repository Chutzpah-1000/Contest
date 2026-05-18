from __future__ import annotations

import os

import streamlit as st
import streamlit.components.v1 as components

from app.components.cards import inject_design_css, render_epiphany_cards, render_solution_summary
from app.components.kakao_map import build_kakao_map_html
from app.components.sidebar import render_sidebar
from app.services.data import load_app_data
from app.services.matching import select_solution

_MAP_HEIGHT: int = 620


def _kakao_js_key() -> str:
    try:
        key = st.secrets.get("KAKAO_MAP_JS_KEY") or st.secrets.get("kakao_map_js_key")
        if key:
            return str(key)
    except (KeyError, FileNotFoundError):
        pass
    return os.getenv("KAKAO_MAP_JS_KEY") or os.getenv("KAKAO_MAP_REST_API_KEY") or ""


def main() -> None:
    """Render the Streamlit MVP app."""
    st.set_page_config(page_title="서울 유출지하수 매칭", layout="wide", page_icon="💧")
    inject_design_css()

    try:
        data = load_app_data()
    except FileNotFoundError:
        st.error(
            "데이터 파일을 찾을 수 없습니다. "
            "`uv run python -m etl.pipelines transform` 을 먼저 실행하세요.",
            icon="🗂️",
        )
        st.stop()
        return
    radius_m, search_term = render_sidebar(data.suppliers)

    st.markdown(
        "<h1 style='margin-bottom:4px;'>서울 유출지하수 매칭</h1>"
        "<p style='font-size:14px;color:#666A70;margin-bottom:16px;'>"
        "서울시 공공데이터 기반 유출지하수 공급처 · 수요처 매칭 분석</p>",
        unsafe_allow_html=True,
    )

    selected = select_solution(
        radius_m=radius_m,
        solutions=data.match_solution,
        flows=data.match_flows,
        metrics=data.epiphany_metrics,
    )
    render_epiphany_cards(selected.metrics)
    render_solution_summary(selected.solution, selected.flows)

    js_key = _kakao_js_key()
    if not js_key:
        st.warning(
            "KAKAO_MAP_JS_KEY 가 설정되지 않았습니다. "
            ".streamlit/secrets.toml 또는 환경변수를 확인하세요.",
            icon="⚠️",
        )

    components.html(
        build_kakao_map_html(
            suppliers=data.suppliers,
            parks=data.demand_parks,
            roads=data.demand_roads,
            flows=selected.flows,
            search_term=search_term,
            js_key=js_key,
        ),
        height=_MAP_HEIGHT,
    )
    st.caption("데이터 출처: 서울 열린데이터광장, 기상청 ASOS Open API")


if __name__ == "__main__":
    main()
