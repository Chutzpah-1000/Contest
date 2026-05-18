from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

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

/* ── Hide Streamlit chrome ── */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header[data-testid="stHeader"] {visibility: hidden;}
[data-testid="stToolbar"] {visibility: hidden;}
[data-testid="stDecoration"] {display: none;}

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
.kpi-caption {font-size:10px;color:var(--color-muted);margin-top:5px;line-height:1.4;}

/* ── Section label ── */
.section-label {
  font-size:11px;font-weight:600;color:var(--color-muted);
  text-transform:uppercase;letter-spacing:.05em;
  margin-bottom:6px;margin-top:2px;
}

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


_KPI_CAPTIONS: tuple[str, ...] = (
    "서울시 유출지하수 신고·측정 데이터 기준",
    "100% 재이용 시 추정치. 하수도요금 50% 감면 조례 기준",
    "전력 배출계수 0.4594 tCO\u2082eq/MWh 기준",
    "현재 0% \u2192 전량 매칭 시 추정치",
)


def render_epiphany_cards(metrics: pd.DataFrame) -> None:
    """Render the four PRD epiphany KPI counters."""
    total_discharge = metric_value(metrics, "total_discharge_ton_day")
    savings_year = metric_value(metrics, "savings_krw_year")
    carbon_year = metric_value(metrics, "co2_eq_year")
    utilization_rate = metric_value(metrics, "utilization_rate")

    rows = [
        ("오늘 하수도행", f"{total_discharge:,.0f} 톤", "", _KPI_CAPTIONS[0]),
        ("연 절감 가능액", f"{savings_year / 1e8:,.1f} 억원", " data", _KPI_CAPTIONS[1]),
        ("탄소 절감", f"{carbon_year:,.0f} t-CO\u2082", "", _KPI_CAPTIONS[2]),
        ("활용률", f"0% \u2192 {utilization_rate:.1f}%", " data", _KPI_CAPTIONS[3]),
    ]
    cells = "".join(
        f'<div class="kpi-cell">'
        f'<div class="kpi-label">{escape(label)}</div>'
        f'<div class="kpi-value{cls}">{escape(value)}</div>'
        f'<div class="kpi-caption">{escape(caption)}</div>'
        f"</div>"
        for label, value, cls, caption in rows
    )
    st.markdown(f'<div class="kpi-grid">{cells}</div>', unsafe_allow_html=True)


def render_solution_summary(solution: pd.DataFrame, flows: pd.DataFrame) -> None:
    """Render a compact matching solution summary."""
    objective = sum(numeric_values(solution, ("objective_krw",), 0.0))
    coverage = sum(numeric_values(solution, ("coverage_rate",), 0.0))
    matched = sum(numeric_values(flows, ("ton_per_day",), 0.0))

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
    st.markdown(
        f'<div class="section-label">매칭 솔루션 요약</div><div class="match-grid">{cells}</div>',
        unsafe_allow_html=True,
    )
