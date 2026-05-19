"""환영 온보딩 모달 — 페이지 첫 진입 시 4개 주요 기능을 순차 소개."""

from __future__ import annotations

from html import escape
from typing import Final, NamedTuple

import streamlit as st

_WELCOME_SEEN_KEY: Final[str] = "welcome_modal_seen"
_WELCOME_STEP_KEY: Final[str] = "welcome_step"
_DIALOG_TITLE: Final[str] = "서울 유출지하수 매칭에 오신 것을 환영합니다"


class WelcomeStep(NamedTuple):
    """온보딩 단계 1개를 표현하는 불변 데이터 모델.

    Attributes:
        tag: PRD 요구사항 매핑 라벨 (예: ``FR-01 · 검색``).
        icon: 단계를 대표하는 이모지 1글자.
        title: 카드 제목 (h3 톤).
        body: 카드 본문 1~2줄 설명.
    """

    tag: str
    icon: str
    title: str
    body: str


_STEPS: Final[tuple[WelcomeStep, ...]] = (
    WelcomeStep(
        tag="FR-01 · 검색",
        icon="🔍",
        title="건물별 유출지하수 검색",
        body=(
            "건물명·주소로 공급처를 즉시 찾고, 일 발생량·수질등급·신고상태를 "
            "사이드바 카드에서 한눈에 확인할 수 있습니다."
        ),
    ),
    WelcomeStep(
        tag="FR-02 · AI 예측",
        icon="🤖",
        title="AI 발생량 예측",
        body=(
            "LightGBM 기반 30일 재이용 가능량 예측과 강수·계절성 SHAP 기여도로 "
            "수자원 공급 계획을 미리 세웁니다."
        ),
    ),
    WelcomeStep(
        tag="FR-03 · ROI",
        icon="💰",
        title="절감액·ROI·회수기간 자동 계산",
        body=(
            "100% 재이용 시 연 하수도 절감액·탄소 절감량·투자 회수기간을 "
            "사이드바 ROI 블록에서 즉시 산출해 보여드립니다."
        ),
    ),
    WelcomeStep(
        tag="FR-05 · 매칭",
        icon="🗺️",
        title="공급-수요 매칭 지도",
        body=(
            "공원·도로 등 수요처를 PuLP ILP 최적화로 자동 매칭하고, "
            "공급-수요 흐름을 지도 위에서 시각적으로 추적합니다."
        ),
    ),
)

_TOTAL_STEPS: Final[int] = len(_STEPS)

_MODAL_CSS: Final[str] = """
<style>
.welcome-step-tag {
  display:inline-block;padding:3px 10px;border-radius:4px;
  font-size:10px;font-weight:700;background:#E6F0FC;color:#0071E3;
  letter-spacing:.06em;text-transform:uppercase;margin-bottom:14px;
}
.welcome-progress {display:flex;gap:6px;margin:0 0 18px;}
.welcome-progress-dot {
  height:4px;flex:1;background:#E4E4E0;border-radius:2px;
  transition:background-color .15s ease;
}
.welcome-progress-dot.active {background:#0071E3;}
.welcome-feature-card {
  background:#F7F7F5;border:1px solid #E4E4E0;border-radius:10px;
  padding:22px 20px;margin-bottom:6px;
}
.welcome-feature-icon {font-size:36px;line-height:1;margin-bottom:10px;}
.welcome-feature-title {
  font-size:18px;font-weight:700;color:#111111;
  line-height:1.35;margin-bottom:8px;
}
.welcome-feature-body {font-size:13px;color:#333A40;line-height:1.6;}
.welcome-step-counter {
  font-size:11px;font-weight:600;color:#666A70;
  letter-spacing:.05em;text-transform:uppercase;text-align:center;
  margin-top:12px;margin-bottom:4px;
}
</style>
"""


def clamp_step(idx: int) -> int:
    """단계 인덱스를 ``0..N-1`` 범위로 강제.

    Args:
        idx: 입력 인덱스. 음수 또는 ``_TOTAL_STEPS`` 이상도 허용.

    Returns:
        ``0`` 이상 ``_TOTAL_STEPS - 1`` 이하의 안전한 인덱스.
    """
    if idx < 0:
        return 0
    if idx >= _TOTAL_STEPS:
        return _TOTAL_STEPS - 1
    return idx


def get_steps() -> tuple[WelcomeStep, ...]:
    """온보딩 단계 정의를 반환 (테스트·외부 검증용).

    Returns:
        ``_STEPS`` 튜플 — 모달이 순차로 보여주는 4개 단계 정의.
    """
    return _STEPS


def render_welcome_modal() -> None:
    """페이지 첫 진입 시 환영 모달을 자동 표시.

    ``st.session_state[_WELCOME_SEEN_KEY]`` 가 ``True`` 면 아무 동작도 하지 않는다.
    사이드바 "튜토리얼 다시 보기" 버튼이 키를 ``False`` 로 리셋하면 다시 표시된다.
    """
    if bool(st.session_state.get(_WELCOME_SEEN_KEY, False)):
        return
    if _WELCOME_STEP_KEY not in st.session_state:
        st.session_state[_WELCOME_STEP_KEY] = 0
    _open_dialog()


def reset_welcome_modal() -> None:
    """튜토리얼을 처음 단계부터 다시 표시하도록 세션 상태를 리셋."""
    st.session_state[_WELCOME_SEEN_KEY] = False
    st.session_state[_WELCOME_STEP_KEY] = 0


def _render_step_card(step: WelcomeStep, step_idx: int) -> None:
    """단계 카드 1개를 HTML로 렌더 (진행 dots + 카드 + 카운터)."""
    progress_html = "".join(
        f'<div class="welcome-progress-dot{" active" if i <= step_idx else ""}"></div>'
        for i in range(_TOTAL_STEPS)
    )
    st.markdown(
        f'<div class="welcome-progress">{progress_html}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="welcome-feature-card">'
        f'<div class="welcome-feature-icon">{escape(step.icon)}</div>'
        f'<span class="welcome-step-tag">{escape(step.tag)}</span>'
        f'<div class="welcome-feature-title">{escape(step.title)}</div>'
        f'<div class="welcome-feature-body">{escape(step.body)}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="welcome-step-counter">{step_idx + 1} / {_TOTAL_STEPS}</div>',
        unsafe_allow_html=True,
    )


@st.dialog(_DIALOG_TITLE, width="large")  # pyright: ignore[reportUnknownMemberType]
def _open_dialog() -> None:
    """환영 모달 다이얼로그 본체 — Streamlit @st.dialog 데코레이션."""
    st.markdown(_MODAL_CSS, unsafe_allow_html=True)

    step_idx: int = clamp_step(int(st.session_state.get(_WELCOME_STEP_KEY, 0)))
    step: WelcomeStep = _STEPS[step_idx]
    _render_step_card(step, step_idx)

    is_first: bool = step_idx == 0
    is_last: bool = step_idx == _TOTAL_STEPS - 1
    cols = st.columns(2)

    with cols[0]:
        prev_clicked: bool = st.button(
            "이전",
            key="welcome_prev",
            disabled=is_first,
            use_container_width=True,
        )
    with cols[1]:
        cta_label = "시작하기" if is_last else "다음"
        cta_clicked: bool = st.button(
            cta_label,
            key="welcome_next",
            type="primary",
            use_container_width=True,
        )

    if prev_clicked and not is_first:
        st.session_state[_WELCOME_STEP_KEY] = step_idx - 1
        st.rerun()
    if cta_clicked:
        if is_last:
            st.session_state[_WELCOME_SEEN_KEY] = True
            st.session_state[_WELCOME_STEP_KEY] = 0
        else:
            st.session_state[_WELCOME_STEP_KEY] = step_idx + 1
        st.rerun()
