"""BuildTrust Streamlit v3 entrypoint.

This is the single maintained frontend app.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from cipher_genius.ui.web_v3.pages import (
    render_dashboard_page,
    render_export_page,
    render_generate_page,
    render_results_page,
    render_tools_page,
)
from cipher_genius.ui.web_v3.state import init_state
from cipher_genius.ui.web_v3.styles import inject_styles


st.set_page_config(
    page_title="BuildTrust Studio",
    page_icon="BT",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _render_sidebar() -> str:
    st.sidebar.markdown(
        """
        <div class="cg-brand">
            <div class="cg-brand-title">BuildTrust Studio</div>
            <div class="cg-brand-sub">Construction Trust Workspace</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    pages = ["Dashboard", "Generate", "Results", "Tools", "Export"]
    current_page = st.session_state.active_page
    if current_page not in pages:
        current_page = "Dashboard"
        st.session_state.active_page = current_page
    active_page = st.sidebar.radio(
        "Navigation",
        pages,
        index=pages.index(current_page),
        label_visibility="collapsed",
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Environment")
    st.sidebar.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    st.sidebar.write("Mode: Enterprise Prototype")
    st.sidebar.write("Theme: Light Operations Dashboard")
    st.sidebar.info("Generated schemes require independent cryptographic review before production.")
    return active_page


def _render_topbar(active_page: str) -> None:
    nav_items = ["Dashboard", "Generate", "Results", "Tools", "Export"]
    nav_html = "".join(
        f'<span class="cg-tag" style="margin-right:0.4rem;{"background:#eaf1ff;border-color:#cddfff;color:#1849a9;" if item == active_page else "background:#f8f9fc;border-color:#dbe2ec;color:#475467;"}">{item}</span>'
        for item in nav_items
    )

    st.markdown(
        f"""
        <div class="cg-topbar">
            <div>{nav_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([5, 1.2])
    with col1:
        st.text_input(
            "Search",
            value="",
            placeholder="Search schemes, components, constraints...",
            label_visibility="collapsed",
            key="global_search_input",
        )
    with col2:
        st.selectbox(
            "Widgets",
            ["Widgets", "Security", "Compliance", "Performance"],
            label_visibility="collapsed",
            key="widgets_select",
        )

    st.markdown(
        f"""
        <p class="cg-page-title">{active_page}</p>
        <p class="cg-page-sub">Operational cockpit for cryptographic scheme generation, validation, and reporting.</p>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    init_state()
    inject_styles()

    active_page = _render_sidebar()
    st.session_state.active_page = active_page
    _render_topbar(active_page)

    page_map = {
        "Dashboard": render_dashboard_page,
        "Generate": render_generate_page,
        "Results": render_results_page,
        "Tools": render_tools_page,
        "Export": render_export_page,
    }

    page_map[active_page]()


if __name__ == "__main__":
    main()
