from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

import streamlit as st

from app.services.roi import building_roi

if TYPE_CHECKING:
    import pandas as pd


def render_sidebar(suppliers: pd.DataFrame) -> tuple[int, str]:
    """Render the sidebar with search, radius controls, and a building detail card.

    Returns:
        Tuple of (selected matching radius in meters, building search term).
    """
    with st.sidebar:
        st.markdown(
            """
            <style>
            [data-testid="stSidebar"] {background:#ffffff;border-right:1px solid #E4E4E0;}
            [data-testid="stSidebarContent"] {padding-top:0 !important;}
            .sb-header {
                padding:14px 16px 12px;
                border-bottom:1px solid #E4E4E0;
                display:flex;align-items:center;gap:10px;
                margin-bottom:14px;
            }
            .sb-icon {font-size:22px;line-height:1;}
            .sb-title {font-size:14px;font-weight:700;color:#111111;line-height:1.2;}
            .sb-subtitle {font-size:10px;color:#666A70;margin-top:2px;}
            .sb-ctrl-label {
                font-size:11px;font-weight:600;color:#666A70;
                text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;
            }
            .building-card {
                background:#F7F7F5;border:1px solid #E4E4E0;border-radius:8px;
                padding:16px;margin-top:12px;
            }
            .building-name {font-size:15px;font-weight:700;color:#111111;line-height:1.35;margin-bottom:4px;}
            .building-addr {font-size:12px;color:#666A70;margin-bottom:12px;}
            .discharge-label {font-size:11px;font-weight:600;color:#666A70;text-transform:uppercase;letter-spacing:.04em;}
            .discharge-value {font-size:28px;font-weight:700;color:#1D7F5F;line-height:1.15;margin:2px 0 12px;}
            .discharge-unit {font-size:13px;font-weight:400;color:#666A70;}
            .meta-row {display:flex;gap:16px;margin-top:4px;}
            .meta-block {flex:1;}
            .meta-label {font-size:11px;color:#666A70;font-weight:600;text-transform:uppercase;letter-spacing:.04em;}
            .meta-value {font-size:13px;font-weight:600;color:#111111;margin-top:2px;}
            .reportable-badge {
                display:inline-block;padding:2px 8px;border-radius:4px;
                font-size:11px;font-weight:600;background:#E6F4EE;color:#1D7F5F;
                margin-top:8px;
            }
            .roi-block {
                margin-top:14px;padding-top:12px;border-top:1px solid #E4E4E0;
                display:grid;grid-template-columns:1fr 1fr;gap:12px;
            }
            .roi-label {font-size:11px;color:#666A70;font-weight:600;text-transform:uppercase;letter-spacing:.04em;}
            .roi-value {font-size:16px;font-weight:700;color:#1D7F5F;margin-top:2px;line-height:1.2;}
            .roi-unit {font-size:11px;font-weight:400;color:#666A70;}
            .roi-caption {font-size:10px;color:#888;margin-top:8px;line-height:1.4;}
            .sb-footer {
                margin-top:16px;padding-top:12px;border-top:1px solid #E4E4E0;
                font-size:10px;color:#888;line-height:1.6;
            }
            /* 사이드바 검색 폼 버튼 톤 — Design.md monochrome data-product */
            [data-testid="stSidebar"] [data-testid="stForm"] button {
                background:#FFFFFF !important;
                border:1px solid #E4E4E0 !important;
                color:#111111 !important;
                font-size:12px !important;
                font-weight:600 !important;
                border-radius:6px !important;
                padding:6px 10px !important;
                box-shadow:none !important;
                transition:border-color .12s ease, color .12s ease, background .12s ease;
            }
            [data-testid="stSidebar"] [data-testid="stForm"] button:hover {
                border-color:#0071E3 !important;
                color:#0071E3 !important;
                background:#F5F9FF !important;
            }
            [data-testid="stSidebar"] [data-testid="stForm"] button:focus {
                outline:none !important;
                border-color:#0071E3 !important;
                box-shadow:0 0 0 2px rgba(0,113,227,.18) !important;
            }
            [data-testid="stSidebar"] [data-testid="stForm"] button:active {
                background:#EAF2FB !important;
            }
            </style>
            <div class="sb-header">
              <span class="sb-icon">&#128167;</span>
              <div>
                <div class="sb-title">유출지하수 매칭</div>
                <div class="sb-subtitle">서울시 공공데이터 분석 플랫폼</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            "<p class='sb-ctrl-label'>건물 검색</p>",
            unsafe_allow_html=True,
        )
        search_term = _render_search_form()

        matched = _find_building(suppliers, search_term)
        if matched is not None:
            _render_building_card(matched)
        elif search_term:
            st.caption("검색 결과가 없습니다.")

        st.divider()

        st.markdown(
            "<p class='sb-ctrl-label'>매칭 반경</p>",
            unsafe_allow_html=True,
        )
        radius_m: int = st.radio(
            "반경",
            options=[500, 1000, 2000],
            format_func=lambda v: f"{v:,}m" if v < 1000 else f"{v // 1000}km",
            index=1,
            horizontal=True,
            label_visibility="collapsed",
        )  # type: ignore[assignment]  # st.radio returns Any; guaranteed int from options list

        st.markdown(
            "<div class='sb-footer'>"
            "서울 열린데이터광장 · 기상청 ASOS<br>"
            "2026 서울시 빅데이터 경진대회 창업 부문"
            "</div>",
            unsafe_allow_html=True,
        )

        return radius_m, search_term


_SEARCH_APPLIED_KEY: str = "sidebar_search_applied"


def resolve_search_state(*, raw: str, submitted: bool, cleared: bool, current_applied: str) -> str:
    """Compute the next applied search term given form state.

    Args:
        raw: Latest text_input value.
        submitted: True if the "검색" submit button fired this rerun.
        cleared: True if the "초기화" submit button fired this rerun.
        current_applied: Previously applied search term (from session state).

    Returns:
        The search term to apply (and persist) for this rerun.
    """
    if cleared:
        return ""
    if submitted:
        return raw
    return current_applied


def _render_search_form() -> str:
    """Render the building search form with explicit submit to avoid per-keystroke reruns.

    Returns:
        The applied search term (only updates on form submit / Enter).
    """
    applied: str = st.session_state.get(_SEARCH_APPLIED_KEY, "")
    with st.form("sidebar_building_search", clear_on_submit=False, border=False):
        raw: str = st.text_input(
            "건물 검색",
            value=applied,
            placeholder="건물명으로 검색 (예: Heliocity)",
            label_visibility="collapsed",
            key="sidebar_search_raw",
        )
        cols = st.columns([3, 1])
        with cols[0]:
            submitted = st.form_submit_button("검색", use_container_width=True)
        with cols[1]:
            cleared = st.form_submit_button("초기화", use_container_width=True)
    next_applied = resolve_search_state(
        raw=raw, submitted=submitted, cleared=cleared, current_applied=applied
    )
    if next_applied != applied:
        st.session_state[_SEARCH_APPLIED_KEY] = next_applied
    return next_applied


def _find_building(suppliers: pd.DataFrame, search_term: str) -> dict[str, object] | None:
    if not search_term or suppliers.empty or "name" not in suppliers.columns:
        return None
    term = search_term.lower()
    mask = suppliers["name"].astype(str).str.lower().str.contains(term, regex=False, na=False)
    matched = suppliers.loc[mask]
    if matched.empty:
        return None
    row = matched.iloc[0]
    return {
        "name": str(row.get("name", "")),
        "address": str(row.get("address", "")),
        "daily_avg_supply_ton": float(row.get("daily_avg_supply_ton", 0.0)),
        "water_quality_grade": int(row.get("water_quality_grade", 0)),
        "report_status": str(row.get("report_status", "")),
        "reportable": bool(row.get("reportable", False)),
    }


def _render_building_card(b: dict[str, object]) -> None:
    ton = float(b["daily_avg_supply_ton"])  # type: ignore[arg-type]
    grade = int(b["water_quality_grade"])  # type: ignore[arg-type]
    status_map = {"discharging": "방류중", "reported": "신고완료"}
    status_raw = str(b["report_status"])
    status = status_map.get(status_raw, status_raw)
    reportable = bool(b["reportable"])
    roi = building_roi(ton)
    savings_eok = roi.annual_savings_krw / 1e8

    st.markdown(
        f"""
        <div class="building-card">
          <div class="building-name">{escape(str(b["name"]))}</div>
          <div class="building-addr">{escape(str(b["address"]))}</div>
          <div class="discharge-label">일 발생량</div>
          <div class="discharge-value">{ton:,.0f}<span class="discharge-unit"> 톤/일</span></div>
          <div class="meta-row">
            <div class="meta-block">
              <div class="meta-label">수질등급</div>
              <div class="meta-value">{grade}등급</div>
            </div>
            <div class="meta-block">
              <div class="meta-label">신고상태</div>
              <div class="meta-value">{escape(status)}</div>
            </div>
          </div>
          {"<div class='reportable-badge'>신고대상 ✓</div>" if reportable else ""}
          <div class="roi-block">
            <div>
              <div class="roi-label">연 하수요금 절감</div>
              <div class="roi-value">{savings_eok:,.2f}<span class="roi-unit"> 억원/년</span></div>
            </div>
            <div>
              <div class="roi-label">연 탄소 절감</div>
              <div class="roi-value">{roi.annual_co2_tons:,.1f}<span class="roi-unit"> t-CO₂/년</span></div>
            </div>
          </div>
          <div class="roi-caption">100% 재이용 시 추정치. 하수도요금 50% 감면 조례·전력 배출계수 0.4594 tCO₂eq/MWh 기준.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
