from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING, NamedTuple

import streamlit as st

from app.services.matching import metric_value
from etl.transform.normalize import numeric_values

if TYPE_CHECKING:
    import pandas as pd

_DESIGN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700&display=swap');

/* ── Design tokens ── */
:root {
  --color-bg: #F7F7F5;
  --color-surface: #FFFFFF;
  --color-text: #111111;
  --color-muted: #666A70;
  --color-border: #E4E4E0;
  --color-primary: #0071E3;
  --color-data: #1D7F5F;
  --color-risk: #B54708;
}

/* ── Hide Streamlit chrome (but keep sidebar collapse/expand button) ── */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stDecoration"] {display: none;}
header[data-testid="stHeader"] {
  background: transparent !important;
  visibility: visible !important;
  height: auto !important;
}
/* Hide only the hamburger/toolbar items inside the header, not the whole header */
header[data-testid="stHeader"] [data-testid="stToolbar"] {visibility: hidden !important;}

/* Force every known variant of the sidebar collapse/expand button to stay visible */
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"],
[data-testid="baseButton-headerNoPadding"],
button[kind="headerNoPadding"] {
  visibility: visible !important;
  opacity: 1 !important;
  display: flex !important;
  z-index: 999999 !important;
}

/* ── Global ── */
html, body, [data-testid="stAppViewContainer"] {
  background: var(--color-bg) !important;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR",
    "Apple SD Gothic Neo", sans-serif !important;
}
[data-testid="stMainBlockContainer"] {padding-top: 1.25rem !important;}

h1 {
  font-size:24px !important; font-weight:700 !important;
  color:var(--color-text) !important; margin-bottom:0 !important;
}
.page-subtitle {
  font-size:14px;color:var(--color-muted);
  margin-top:4px;margin-bottom:18px;line-height:1.45;
}

/* ── KPI grid ── */
.kpi-grid {
  display:grid;
  grid-template-columns:repeat(4,1fr);
  gap:1px;
  background:var(--color-border);
  border:1px solid var(--color-border);
  border-radius:8px;
  overflow:hidden;
  margin-bottom:1rem;
}
@media(max-width:720px){.kpi-grid{grid-template-columns:repeat(2,1fr);}}
.kpi-cell {background:var(--color-surface);padding:14px 18px;}
.kpi-label {
  font-size:11px;font-weight:600;color:var(--color-muted);
  text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px;
}
.kpi-value {font-size:22px;font-weight:700;color:var(--color-text);line-height:1.15;}
.kpi-value.data {color:var(--color-data);}

/* ── KPI 소스 disclosure (ⓘ popover) ── */
.kpi-source {margin-top:6px;}
.kpi-source > summary {
  list-style:none;cursor:pointer;display:inline-flex;align-items:center;gap:5px;
  font-size:10px;color:var(--color-muted);user-select:none;line-height:1.4;
  padding:1px 0;border-radius:3px;
}
.kpi-source > summary::-webkit-details-marker {display:none;}
.kpi-source > summary:hover {color:var(--color-primary);}
.kpi-source > summary:focus-visible {outline:2px solid var(--color-primary);outline-offset:2px;}
.kpi-source .info-icon {
  display:inline-flex;align-items:center;justify-content:center;
  width:13px;height:13px;border-radius:50%;border:1px solid currentColor;
  font-size:9px;font-weight:700;font-style:normal;line-height:1;flex-shrink:0;
}
.kpi-source[open] > summary {color:var(--color-primary);}
.kpi-source-body {
  margin-top:6px;padding:8px 10px;background:#FAFAF8;border:1px solid var(--color-border);
  border-radius:6px;font-size:10px;color:var(--color-muted);line-height:1.5;
}
.kpi-source-body b {color:var(--color-text);font-weight:600;}
.kpi-source-body div + div {margin-top:3px;}

/* ── Section header (label + meta) ── */
.section-header {
  display:flex;align-items:baseline;justify-content:space-between;gap:12px;
  margin-bottom:6px;margin-top:2px;
}
.section-label {
  font-size:11px;font-weight:600;color:var(--color-muted);
  text-transform:uppercase;letter-spacing:.05em;
}
.section-meta {
  font-size:11px;color:var(--color-muted);font-weight:500;
}
.section-meta b {color:var(--color-text);font-weight:600;}

/* ── Match summary grid ── */
.match-grid {
  display:grid;grid-template-columns:repeat(3,1fr);gap:1px;
  background:var(--color-border);border:1px solid var(--color-border);
  border-radius:8px;overflow:hidden;margin-bottom:1rem;
}
.match-cell {background:var(--color-surface);padding:10px 16px;}
.match-label {
  font-size:10px;font-weight:600;color:var(--color-muted);
  text-transform:uppercase;letter-spacing:.05em;margin-bottom:2px;
}
.match-value {font-size:17px;font-weight:700;color:var(--color-text);}
.match-value.data {color:var(--color-data);}
</style>
"""


def inject_design_css() -> None:
    """Inject global Design.md CSS tokens into the Streamlit page."""
    st.markdown(_DESIGN_CSS, unsafe_allow_html=True)


class _KpiSource(NamedTuple):
    caption: str
    dataset: str
    formula: str
    refresh: str


_KPI_SOURCES: tuple[_KpiSource, ...] = (
    _KpiSource(
        caption="서울시 유출지하수 신고·측정 데이터 기준",
        dataset="서울 열린데이터광장 — 유출지하수 측정 데이터",
        formula="Σ(supplier.daily_avg_supply_ton)",
        refresh="월 1회 (서울시 갱신 주기 기준)",
    ),
    _KpiSource(
        caption="100% 재이용 시 추정치. 하수도요금 50% 감면 조례 기준",
        dataset="측정 데이터 + 서울시 하수도사용조례 (요율표)",
        formula="Σ(ton/day * 365 * 톤당요금 * 0.5)",
        refresh="조례·요율표 변경 시",
    ),
    _KpiSource(
        caption="전력 배출계수 0.4594 tCO₂eq/MWh 기준",
        dataset="측정 데이터 + KEPCO 전력 배출계수 공시",
        formula="Σ(ton * 펌프 kWh/ton * 0.4594) / 1000",
        refresh="연 1회 (배출계수 갱신)",
    ),
    _KpiSource(
        caption="현재 0% → 전량 매칭 시 추정치",
        dataset="측정 데이터 + 매칭 최적해 (PuLP/CBC)",
        formula="Σ(matched_ton) / Σ(total_discharge_ton)",
        refresh="매칭 파이프라인 실행 시",
    ),
)


def _kpi_source_html(src: _KpiSource) -> str:
    """Render the caption + collapsible source disclosure for one KPI cell.

    Args:
        src: 데이터셋·계산식·갱신주기 메타데이터.

    Returns:
        ``<details>`` 디스클로저 HTML 조각. 부모 그리드 셀 안에 직접 삽입한다.
    """
    return (
        f'<details class="kpi-source">'
        f'<summary><span class="info-icon">i</span>'
        f"<span>{escape(src.caption)}</span></summary>"
        f'<div class="kpi-source-body">'
        f"<div><b>데이터셋</b> · {escape(src.dataset)}</div>"
        f"<div><b>계산식</b> · {escape(src.formula)}</div>"
        f"<div><b>갱신주기</b> · {escape(src.refresh)}</div>"
        f"</div></details>"
    )


def render_epiphany_cards(metrics: pd.DataFrame) -> None:
    """Render the four PRD epiphany KPI counters with source disclosures."""
    total_discharge = metric_value(metrics, "total_discharge_ton_day")
    savings_year = metric_value(metrics, "savings_krw_year")
    carbon_year = metric_value(metrics, "co2_eq_year")
    utilization_rate = metric_value(metrics, "utilization_rate")

    rows = [
        ("오늘 하수도행", f"{total_discharge:,.0f} 톤", "", _KPI_SOURCES[0]),
        (
            "연 절감 가능액",
            f"{savings_year / 1e8:,.1f} 억원",
            " data",
            _KPI_SOURCES[1],
        ),
        ("탄소 절감", f"{carbon_year:,.0f} t-CO₂", "", _KPI_SOURCES[2]),
        ("활용률", f"0% → {utilization_rate:.1f}%", " data", _KPI_SOURCES[3]),
    ]
    cells = "".join(
        f'<div class="kpi-cell">'
        f'<div class="kpi-label">{escape(label)}</div>'
        f'<div class="kpi-value{cls}">{escape(value)}</div>'
        f"{_kpi_source_html(src)}"
        f"</div>"
        for label, value, cls, src in rows
    )
    st.markdown(f'<div class="kpi-grid">{cells}</div>', unsafe_allow_html=True)


def render_solution_summary(
    solution: pd.DataFrame,
    flows: pd.DataFrame,
    radius_m: int | None = None,
) -> None:
    """Render a compact matching solution summary.

    Args:
        solution: 선택된 매칭 솔루션 1행 데이터프레임.
        flows: 솔루션에 포함된 공급-수요 매칭 라인.
        radius_m: 사이드바에서 선택된 매칭 반경(m). 전달되면 섹션 레이블 옆에 메타가 표기된다.
    """
    objective = sum(numeric_values(solution, ("objective_krw",), 0.0))
    coverage = sum(numeric_values(solution, ("coverage_rate",), 0.0))
    matched = sum(numeric_values(flows, ("ton_per_day",), 0.0))
    n_flows = len(flows)

    rows = [
        ("일 매칭량", f"{matched:,.0f} 톤", ""),
        ("목적함수", f"{objective / 1e6:,.1f} 백만원/일", ""),
        ("수요 충족률", f"{coverage * 100:.1f}%", " data"),
    ]
    cells = "".join(
        f'<div class="match-cell">'
        f'<div class="match-label">{escape(label)}</div>'
        f'<div class="match-value{cls}">{escape(value)}</div>'
        f"</div>"
        for label, value, cls in rows
    )

    meta_html = ""
    if radius_m is not None:
        radius_label = f"{radius_m:,}m" if radius_m < 1000 else f"{radius_m // 1000}km"
        meta_html = (
            f'<span class="section-meta">반경 {escape(radius_label)} · 매칭 {n_flows}건</span>'
        )

    st.markdown(
        f'<div class="section-header">'
        f'<span class="section-label">매칭 솔루션 요약</span>{meta_html}'
        f"</div>"
        f'<div class="match-grid">{cells}</div>',
        unsafe_allow_html=True,
    )
