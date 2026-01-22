"""
UI component helpers for Streamlit.
"""

import streamlit as st
import pandas as pd
from typing import Optional


def render_kpi_card(label: str, value: str, delta: Optional[str] = None):
    """Render a KPI metric card."""
    st.metric(label, value, delta=delta)


def format_currency(value: float) -> str:
    """Format value as EUR currency."""
    return f"€{value:,.0f}"


def format_percentage(value: float) -> str:
    """Format value as percentage."""
    if pd.isna(value):
        return "N/A"
    return f"{value:.1%}"


def format_dataframe_currency(df: pd.DataFrame, currency_cols: list) -> pd.DataFrame:
    """Format currency columns in DataFrame for display."""
    df_display = df.copy()
    for col in currency_cols:
        if col in df_display.columns:
            df_display[col] = df_display[col].apply(lambda x: format_currency(x) if pd.notna(x) else "N/A")
    return df_display


def format_dataframe_percentage(df: pd.DataFrame, pct_cols: list) -> pd.DataFrame:
    """Format percentage columns in DataFrame for display."""
    df_display = df.copy()
    for col in pct_cols:
        if col in df_display.columns:
            df_display[col] = df_display[col].apply(lambda x: format_percentage(x) if pd.notna(x) else "N/A")
    return df_display
