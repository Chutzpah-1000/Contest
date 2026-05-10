from __future__ import annotations

import streamlit as st


def render_sidebar() -> int:
    """Render app controls in the sidebar.

    Returns:
        Selected matching radius in meters.
    """
    with st.sidebar:
        st.header("조건")
        return st.radio(
            "반경",
            options=[500, 1000, 2000],
            format_func=lambda value: f"{value:,}m" if value < 1000 else f"{value // 1000}km",
            index=1,
            horizontal=True,
        )
