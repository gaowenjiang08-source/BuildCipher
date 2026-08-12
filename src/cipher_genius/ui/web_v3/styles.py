"""Design tokens and style injection for Streamlit v3 app."""

from __future__ import annotations

import streamlit as st


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&display=swap');

        :root {
            --cg-bg: #f4f6fa;
            --cg-panel: #ffffff;
            --cg-panel-soft: #f8f9fc;
            --cg-border: #dbe2ec;
            --cg-text: #1b2432;
            --cg-muted: #667085;
            --cg-accent: #2f6fed;
            --cg-accent-soft: #eaf1ff;
            --cg-success: #16a34a;
            --cg-danger: #dc2626;
            --cg-warn: #b45309;
        }

        .stApp {
            font-family: 'Manrope', sans-serif;
            background:
                radial-gradient(circle at 85% 5%, rgba(47, 111, 237, 0.06), transparent 30%),
                var(--cg-bg);
            color: var(--cg-text);
        }

        [data-testid="stAppViewContainer"] {
            background: transparent;
        }

        .block-container {
            padding-top: 1.15rem;
            padding-bottom: 1.5rem;
        }

        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid var(--cg-border);
        }

        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] div {
            color: var(--cg-text);
        }

        .cg-brand {
            background: var(--cg-panel-soft);
            border: 1px solid var(--cg-border);
            border-radius: 12px;
            padding: 0.85rem 0.95rem;
            margin-bottom: 0.95rem;
        }

        .cg-brand-title {
            font-size: 1.03rem;
            font-weight: 700;
            color: #1247a0;
            margin-bottom: 0.2rem;
        }

        .cg-brand-sub {
            font-size: 0.82rem;
            color: var(--cg-muted);
        }

        .cg-topbar {
            background: var(--cg-panel);
            border: 1px solid var(--cg-border);
            border-radius: 14px;
            padding: 0.95rem 1.05rem;
            margin-bottom: 0.8rem;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
        }

        .cg-page-title {
            font-size: 1.28rem;
            font-weight: 700;
            color: var(--cg-text);
            margin: 0;
        }

        .cg-page-sub {
            color: var(--cg-muted);
            font-size: 0.88rem;
            margin-top: 0.22rem;
        }

        .cg-kpi-card {
            background: var(--cg-panel);
            border: 1px solid var(--cg-border);
            border-radius: 12px;
            padding: 0.85rem 0.9rem;
            margin-bottom: 0.55rem;
        }

        .cg-kpi-value {
            font-size: 1.33rem;
            font-weight: 700;
            color: #1247a0;
            margin: 0;
        }

        .cg-kpi-label {
            font-size: 0.82rem;
            color: var(--cg-muted);
            margin-top: 0.16rem;
        }

        .cg-section-title {
            font-size: 1.03rem;
            font-weight: 700;
            color: var(--cg-text);
            margin: 0.2rem 0 0.6rem;
        }

        .cg-mini-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.62rem;
            margin-bottom: 0.6rem;
        }

        .cg-mini-card {
            background: var(--cg-panel);
            border: 1px solid var(--cg-border);
            border-radius: 12px;
            padding: 0.72rem 0.8rem;
        }

        .cg-mini-title {
            font-size: 0.74rem;
            color: var(--cg-muted);
            text-transform: uppercase;
            letter-spacing: 0.03em;
            margin-bottom: 0.24rem;
        }

        .cg-mini-value {
            font-size: 1.16rem;
            font-weight: 700;
            color: var(--cg-text);
            line-height: 1.2;
        }

        .cg-mini-trend {
            font-size: 0.77rem;
            font-weight: 600;
            color: var(--cg-success);
            margin-top: 0.2rem;
        }

        .cg-list-item {
            background: var(--cg-panel);
            border: 1px solid var(--cg-border);
            border-radius: 12px;
            padding: 0.72rem 0.82rem;
            margin-bottom: 0.55rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 0.8rem;
        }

        .cg-item-title {
            font-weight: 600;
            color: var(--cg-text);
            font-size: 0.94rem;
        }

        .cg-item-sub {
            font-size: 0.79rem;
            color: var(--cg-muted);
            margin-top: 0.2rem;
            line-height: 1.42;
        }

        .cg-tag {
            font-size: 0.72rem;
            color: #1247a0;
            background: var(--cg-accent-soft);
            border: 1px solid #cddfff;
            padding: 0.14rem 0.44rem;
            border-radius: 999px;
            font-weight: 700;
            white-space: nowrap;
        }

        .cg-pill {
            display: inline-block;
            padding: 0.2rem 0.52rem;
            border-radius: 999px;
            border: 1px solid #cddfff;
            color: #1247a0;
            background: var(--cg-accent-soft);
            font-size: 0.74rem;
            margin: 0.12rem;
        }

        .cg-note {
            background: var(--cg-panel-soft);
            border: 1px solid var(--cg-border);
            border-radius: 11px;
            padding: 0.7rem 0.82rem;
            color: #475467;
            font-size: 0.82rem;
            margin-bottom: 0.62rem;
        }

        .stButton > button {
            border-radius: 10px !important;
            border: 1px solid #c6d6fb !important;
            background: #f4f8ff !important;
            color: #1849a9 !important;
            font-weight: 600 !important;
        }

        .stButton > button[kind="primary"] {
            background: #2f6fed !important;
            color: #ffffff !important;
            border-color: #2f6fed !important;
        }

        .stDownloadButton > button {
            border-radius: 10px !important;
            border: 1px solid #c6d6fb !important;
            background: #f4f8ff !important;
            color: #1849a9 !important;
            font-weight: 600 !important;
        }

        .stTextArea textarea,
        .stTextInput input,
        .stSelectbox div[data-baseweb="select"] > div,
        .stMultiSelect div[data-baseweb="select"] > div {
            background: #ffffff !important;
            color: var(--cg-text) !important;
            border: 1px solid var(--cg-border) !important;
            border-radius: 10px !important;
        }

        [data-testid="stMetric"] {
            background: var(--cg-panel);
            border: 1px solid var(--cg-border);
            border-radius: 12px;
            padding: 0.36rem 0.75rem;
        }

        [data-testid="stMetricValue"] {
            color: #1247a0 !important;
            font-weight: 700;
        }

        [data-testid="stMetricLabel"] {
            color: var(--cg-muted) !important;
        }

        [data-testid="stDataFrame"] {
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid var(--cg-border);
            background: #ffffff;
        }

        .stAlert {
            border-radius: 10px;
            border: 1px solid var(--cg-border);
        }

        .stInfo {
            background: #f6f9ff;
        }

        .stWarning {
            background: #fff9f0;
        }

        .stError {
            background: #fff5f5;
        }

        .stSuccess {
            background: #f3fcf5;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
