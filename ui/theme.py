"""Tema visual da aplicacao."""

import streamlit as st


PRIMARY = "#EFA828"
TEXT = "#34383b"
BACKGROUND = "#FFFFFF"
BORDER = "#E7E2D8"
SOFT = "#FFF7E8"


def apply_brand_theme() -> None:
    st.markdown(
        f"""
        <style>
        :root {{
            --cassol-primary: {PRIMARY};
            --cassol-text: {TEXT};
            --cassol-background: {BACKGROUND};
            --cassol-border: {BORDER};
            --cassol-soft: {SOFT};
        }}

        html,
        body,
        [data-testid="stAppViewContainer"],
        [data-testid="stHeader"] {{
            background: var(--cassol-background);
            color: var(--cassol-text);
        }}

        [data-testid="stHeader"] {{
            border-bottom: 1px solid var(--cassol-border);
        }}

        .block-container {{
            max-width: 1210px;
            padding-top: 2.6rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }}

        [data-testid="stSidebar"] {{
            background: #fbfaf7;
            border-right: 1px solid var(--cassol-border);
        }}

        [data-testid="stSidebar"] * ,
        [data-testid="stAppViewContainer"] * {{
            color: var(--cassol-text);
        }}

        h1, h2, h3, h4, h5, h6 {{
            color: var(--cassol-text);
            font-weight: 750;
            letter-spacing: 0;
        }}

        p,
        label,
        span,
        div {{
            letter-spacing: 0;
        }}

        [data-testid="stCaptionContainer"] {{
            color: rgba(52, 56, 59, 0.72);
        }}

        .cassol-home-copy {{
            color: rgba(52, 56, 59, 0.58);
            font-size: 0.94rem;
            margin: 0.6rem 0 1.2rem;
        }}

        .cassol-home-logo {{
            display: block;
            width: 100%;
            max-width: 560px;
            height: auto;
            margin: 0;
            user-select: none;
            pointer-events: none;
        }}

        div[data-testid="stMetric"] {{
            background: var(--cassol-background);
            border: 1px solid var(--cassol-border);
            border-left: 4px solid var(--cassol-primary);
            border-radius: 8px;
            padding: 12px 14px;
        }}

        div[data-testid="stMetric"] label,
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
            color: var(--cassol-text);
        }}

        .stButton > button,
        .stDownloadButton > button,
        button[kind="primary"] {{
            background: var(--cassol-primary);
            border: 1px solid var(--cassol-primary);
            color: var(--cassol-text);
            border-radius: 8px;
            font-weight: 700;
            box-shadow: none;
        }}

        .stButton > button:hover,
        .stDownloadButton > button:hover,
        button[kind="primary"]:hover {{
            background: #f4b845;
            border-color: #d89117;
            color: var(--cassol-text);
        }}

        .stButton > button:focus,
        .stDownloadButton > button:focus,
        button[kind="primary"]:focus {{
            box-shadow: 0 0 0 3px rgba(239, 168, 40, 0.28);
            color: var(--cassol-text);
        }}

        [data-baseweb="input"],
        [data-baseweb="select"],
        [data-baseweb="textarea"],
        [data-baseweb="tag"],
        [data-testid="stFileUploaderDropzone"] {{
            border-color: var(--cassol-border);
            background: var(--cassol-background);
            color: var(--cassol-text);
        }}

        [data-baseweb="tag"] {{
            background-color: var(--cassol-soft);
        }}

        [data-testid="stAlert"] {{
            background: #f2f4f3;
            border: 1px solid rgba(239, 168, 40, 0.48);
            color: var(--cassol-text);
        }}

        [data-testid="stDataFrame"],
        [data-testid="stTable"] {{
            border: 1px solid var(--cassol-border);
            border-radius: 8px;
            overflow: hidden;
        }}

        [data-testid="stFileUploaderDropzone"] {{
            min-height: 42px;
            padding: 0.35rem 0.65rem;
        }}

        hr {{
            border-color: var(--cassol-border);
        }}

        a {{
            color: #b87400;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
