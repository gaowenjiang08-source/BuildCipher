"""Shared state helpers for Streamlit v3 app."""

from __future__ import annotations

import streamlit as st

DEFAULT_STATE = {
    "generated_schemes": [],
    "parsed_requirement": None,
    "last_input": "",
    "last_error": None,
    "selected_scheme_index": 0,
    "active_page": "Dashboard",
}


def init_state() -> None:
    """Initialize session state keys once."""
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_generation() -> None:
    """Reset generation-related state."""
    st.session_state.generated_schemes = []
    st.session_state.parsed_requirement = None
    st.session_state.last_error = None
    st.session_state.selected_scheme_index = 0
