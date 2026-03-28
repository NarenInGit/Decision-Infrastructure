"""
Decision Infrastructure - Streamlit App
Main entry point for the B2B service prototype.
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from html import escape
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.data_loader import load_and_validate_data, get_data_quality_overview, get_data_summary
from src.metrics import (
    compute_metrics_bundle,
    compute_project_metrics,
    compute_employee_utilization,
    compute_income_statement,
    compute_cashflow_statement,
    compute_runway
)
from src.config import DEFAULT_STARTING_CASH, UNDERUTILIZED_THRESHOLD, OVERUTILIZED_THRESHOLD
from src.core.insights_engine import generate_insights
from src.ui.insights_tab import render_insights_tab
from src.ui.projects_page import render_projects_page
from src.ui.briefs_tab import render_briefs_tab

# ============================================================
# DEMO MODE: Temporarily hide some pages for expert demo
# To revert and show all pages: Set DEMO_MODE = False
# ============================================================
DEMO_MODE = True

# Page config
st.set_page_config(
    page_title="Decision Infrastructure",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "data" not in st.session_state:
    st.session_state.data = None
if "validation_results" not in st.session_state:
    st.session_state.validation_results = None
if "starting_cash" not in st.session_state:
    st.session_state.starting_cash = DEFAULT_STARTING_CASH
if "current_page" not in st.session_state:
    st.session_state.current_page = "Overview Dashboard"


PAGE_COPY = {
    "Overview Dashboard": (
        "SME Decision Support",
        "Overview Dashboard",
        "A deterministic operating view of revenue, margin, cash, and runway. Built to earn trust before it adds interpretation.",
    ),
    "Projects": (
        "Project Profitability",
        "Project Performance",
        "Margin, delivery economics, and pressure points across the current portfolio.",
    ),
    "People": (
        "Capacity and Delivery",
        "People and Utilization",
        "Team utilization, staffing pressure, and billable capacity based on the loaded operating data.",
    ),
    "Financial Statements": (
        "Financial Reporting",
        "Financial Statements",
        "Accrual and cash-based views grounded in the same validated source data.",
    ),
    "Weekly Brief": (
        "Executive Narrative",
        "Weekly Brief",
        "Guardrailed narrative summaries built on deterministic metrics and explicit data quality.",
    ),
    "Insights & Explanations": (
        "Decision Support",
        "Insights and Explanations",
        "Explainable operating signals, grounded in computed facts rather than invented certainty.",
    ),
    "Data Quality": (
        "Data Contract",
        "Data Quality",
        "Coverage, freshness, and validation status for the datasets behind every visible output.",
    ),
}


def _inject_app_theme():
    """Apply a premium dark product shell with custom navigation and surfaces."""
    st.markdown(
        """
        <style>
        :root {
            --bg: #06080d;
            --bg-soft: #0d1118;
            --surface: rgba(17, 22, 30, 0.9);
            --surface-elevated: rgba(20, 26, 35, 0.94);
            --surface-strong: rgba(11, 15, 22, 0.98);
            --card-surface: rgba(255, 255, 255, 0.028);
            --border: rgba(255, 255, 255, 0.08);
            --border-strong: rgba(255, 255, 255, 0.14);
            --text: #ffffff;
            --muted: #a3acb8;
            --muted-strong: #f2f5f8;
            --accent: #f3c86d;
            --accent-soft: rgba(243, 200, 109, 0.18);
            --good: #36d39b;
            --warn: #f3b35f;
            --danger: #ff7d6d;
            --chart-green: #36d39b;
            --chart-rose: #ff7d6d;
            --chart-sand: #f3c86d;
            --chart-slate: #85baff;
            --shadow: 0 28px 60px rgba(0, 0, 0, 0.38);
            --shadow-soft: 0 16px 34px rgba(0, 0, 0, 0.24);
            --radius-lg: 24px;
            --radius-md: 18px;
            --radius-sm: 14px;
            --control-radius: 14px;
            --control-height: 48px;
            --dropdown-inline-padding: 0.95rem;
            --dropdown-icon-gap: 0.9rem;
            --dropdown-arrow-size: 1rem;
            --dropdown-text-offset: calc(var(--dropdown-inline-padding) + var(--dropdown-arrow-size) + var(--dropdown-icon-gap));
            --accordion-duration: 500ms;
            --accordion-ease: cubic-bezier(0.4, 0, 0.2, 1);
            --shell-ease: cubic-bezier(0.22, 1, 0.36, 1);
            --sidebar-control-height: 50px;
            --space-content: 1.1rem;
            --space-section: 1.6rem;
            --font-sans: "IBM Plex Sans", "Segoe UI Variable Text", "Segoe UI", sans-serif;
            --font-display: "IBM Plex Sans", "Segoe UI Variable Text", "Segoe UI", sans-serif;
        }
        .stApp {
            background:
                radial-gradient(72rem 28rem at 10% -12%, rgba(255, 255, 255, 0.04), transparent 58%),
                radial-gradient(44rem 24rem at 92% 2%, rgba(54, 211, 155, 0.03), transparent 60%),
                linear-gradient(180deg, #020304 0%, #05070b 45%, #020304 100%);
            color: var(--text);
            font-family: var(--font-sans);
        }
        .stApp::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            background:
                linear-gradient(110deg, transparent 0%, transparent 26%, rgba(255, 255, 255, 0.045) 36%, transparent 50%),
                linear-gradient(96deg, transparent 54%, rgba(255, 255, 255, 0.02) 64%, transparent 75%);
            opacity: 0.34;
        }
        [data-testid="stAppViewContainer"] > .main { position: relative; z-index: 1; }
        [data-testid="stAppViewContainer"] .main [data-testid="stVerticalBlock"] { gap: 1rem; }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.75rem; }
        [data-testid="stHeader"] {
            background: linear-gradient(180deg, rgba(8, 11, 17, 0.96), rgba(8, 11, 17, 0.88)) !important;
            backdrop-filter: blur(14px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
            height: 3.35rem !important;
            min-height: 3.35rem !important;
            z-index: 1000 !important;
        }
        [data-testid="stToolbar"] {
            position: fixed !important;
            right: 0.8rem !important;
            top: 0.58rem !important;
            z-index: 1002 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: flex-end !important;
            background: transparent !important;
        }
        [data-testid="stToolbar"] button,
        [data-testid="stToolbar"] [role="button"] {
            border-radius: 14px !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            background: linear-gradient(180deg, rgba(28, 33, 42, 0.96), rgba(18, 22, 28, 0.96)) !important;
            color: var(--text) !important;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.2) !important;
            transition: all 0.32s ease !important;
        }
        [data-testid="stToolbar"] button:hover,
        [data-testid="stToolbar"] [role="button"]:hover {
            transform: scale(1.03);
            border-color: rgba(255, 255, 255, 0.14) !important;
            background: rgba(255, 255, 255, 0.04) !important;
            box-shadow: 12px 17px 42px rgba(0, 0, 0, 0.22), 0 0 20px rgba(255, 255, 255, 0.05) !important;
        }
        [data-testid="stToolbar"] button:active,
        [data-testid="stToolbar"] [role="button"]:active {
            transform: scale(0.95) rotateZ(1.7deg);
        }
        [data-testid="collapsedControl"] {
            position: fixed !important;
            left: 0.8rem !important;
            top: 0.58rem !important;
            z-index: 1002 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        [data-testid="collapsedControl"] button {
            width: 42px !important;
            height: 42px !important;
            min-width: 42px !important;
            min-height: 42px !important;
            padding: 0 !important;
            border-radius: 14px !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            background: linear-gradient(180deg, rgba(28, 33, 42, 0.96), rgba(18, 22, 28, 0.96)) !important;
            color: var(--text) !important;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.2) !important;
            transition: all 0.32s ease !important;
        }
        [data-testid="collapsedControl"] button:hover {
            transform: scale(1.03);
            border-color: rgba(255, 255, 255, 0.14) !important;
            background: rgba(255, 255, 255, 0.04) !important;
            box-shadow: 12px 17px 42px rgba(0, 0, 0, 0.22), 0 0 20px rgba(255, 255, 255, 0.05) !important;
        }
        [data-testid="collapsedControl"] button:active {
            transform: scale(0.95) rotateZ(1.7deg);
        }
        [data-testid="collapsedControl"] svg {
            width: 1rem !important;
            height: 1rem !important;
        }
        [data-testid="stSidebar"] { display: block !important; }
        .di-shell-toggle-label {
            position: relative;
            top: 0;
            left: 0;
        }
        .di-shell-toggle-note {
            color: rgba(255, 255, 255, 0.62);
            font-size: 0.72rem;
            line-height: 1.2;
            margin-top: 0.35rem;
        }
        .di-custom-sidebar,
        .di-sidebar-rail {
            position: sticky;
            top: 1rem;
        }
        .di-custom-sidebar {
            padding-right: 0.35rem;
        }
        .di-custom-sidebar .di-sidebar-brand,
        .di-custom-sidebar .di-sidebar-trust {
            margin-left: 0;
            margin-right: 0;
        }
        .di-sidebar-toggle-wrap {
            margin-bottom: 0.75rem;
        }
        [data-testid="stSidebar"] {
            background: var(--card-surface);
            border-right: 1px solid var(--border);
            min-width: 305px !important;
            max-width: 305px !important;
            box-shadow: 26px 0 60px rgba(0, 0, 0, 0.24);
            backdrop-filter: blur(22px);
            transition:
                transform 380ms var(--shell-ease),
                opacity 260ms ease,
                box-shadow 280ms var(--shell-ease);
        }
        [data-testid="stSidebar"] * { color: var(--text); }
        [data-testid="stSidebar"] .block-container {
            padding-top: 1.25rem;
            padding-bottom: 1.45rem;
        }
        .block-container {
            padding-top: 4rem;
            padding-bottom: 3rem;
            padding-left: 1rem;
            padding-right: 1rem;
            max-width: 1700px;
        }
        h1, h2, h3, h4 {
            color: var(--text);
            letter-spacing: -0.035em;
            font-family: var(--font-display);
        }
        h1 { display: none; }
        p, li, label, [data-testid="stMarkdownContainer"], .stCaption {
            font-family: var(--font-sans);
        }
        body, p, li {
            font-size: 0.94rem;
            line-height: 1.55;
        }
        h2 {
            font-size: 1.36rem;
            font-weight: 600;
        }
        h3 {
            font-size: 1.04rem;
            font-weight: 600;
        }
        .di-sidebar-brand {
            margin-bottom: 1.2rem;
            padding: 1.15rem 1rem 1rem 1rem;
            border-radius: var(--radius-md);
            border: 1px solid var(--border);
            background: var(--card-surface);
            box-shadow: var(--shadow-soft);
        }
        .di-sidebar-eyebrow {
            text-transform: uppercase;
            letter-spacing: 0.16em;
            font-size: 0.68rem;
            color: var(--muted);
            margin-bottom: 0.55rem;
        }
        .di-sidebar-title {
            font-family: var(--font-display);
            font-size: 1.02rem;
            font-weight: 600;
            letter-spacing: -0.02em;
            color: var(--text);
            margin-bottom: 0.35rem;
        }
        .di-sidebar-copy {
            color: rgba(255, 255, 255, 0.72);
            font-size: 0.83rem;
            line-height: 1.5;
        }
        .di-sidebar-section {
            margin: 1.15rem 0 0.55rem 0;
            color: var(--text);
            text-transform: uppercase;
            letter-spacing: 0.16em;
            font-size: 0.68rem;
        }
        .di-sidebar-field-label {
            color: var(--text);
            font-size: 0.78rem;
            margin-bottom: 0.55rem;
        }
        .di-sidebar-note {
            color: rgba(255, 255, 255, 0.68);
            font-size: 0.76rem;
            line-height: 1.45;
            margin-top: 0.2rem;
        }
        [data-testid="stSidebar"] .stNumberInput label,
        [data-testid="stSidebar"] .stButton button p {
            font-family: var(--font-sans);
        }
        [data-testid="stSidebar"] .stNumberInput {
            margin-top: 0.2rem;
            margin-bottom: 0.3rem;
            min-height: var(--sidebar-control-height);
            padding: 0 0.92rem;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            background: var(--card-surface);
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.18);
            display: flex;
            align-items: center;
        }
        [data-testid="stSidebar"] .stNumberInput > div[data-baseweb="input"] {
            min-height: 36px;
            border-radius: var(--radius-sm) !important;
            border: 0 !important;
            background: transparent !important;
            padding: 0 !important;
            box-shadow: none !important;
        }
        [data-testid="stSidebar"] .stNumberInput [data-baseweb="input"] > div,
        [data-testid="stSidebar"] .stNumberInput [data-baseweb="base-input"] {
            border: 0 !important;
            box-shadow: none !important;
            background: transparent !important;
            align-items: center;
            justify-content: center;
            min-height: 36px;
        }
        [data-testid="stSidebar"] .stNumberInput input {
            background: transparent !important;
            color: var(--text) !important;
            font-size: 1.02rem;
            font-weight: 600;
            text-align: center;
            line-height: 1.2;
            min-height: 36px !important;
            padding: 0 !important;
        }
        [data-testid="stSidebar"] .stNumberInput button {
            min-height: 28px !important;
            min-width: 32px !important;
            align-self: center !important;
            border: 0 !important;
            background: transparent !important;
            color: var(--muted-strong) !important;
            box-shadow: none !important;
        }
        [data-testid="stSidebar"] .stNumberInput button:hover {
            color: var(--text) !important;
            background: rgba(255, 255, 255, 0.04) !important;
            border-radius: 10px !important;
        }
        [data-testid="stSidebar"] .stNumberInput [data-testid="InputInstructions"] {
            display: none !important;
        }
        [data-testid="stSidebar"] .stButton > button {
            width: 100%;
            min-height: var(--sidebar-control-height);
            justify-content: flex-start;
            padding: 0 0.92rem;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.07) !important;
            background: var(--card-surface) !important;
            color: var(--text) !important;
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.14) !important;
            font-weight: 500;
            cursor: pointer;
            user-select: none;
            transition: all 0.32s ease !important;
            align-items: center;
        }
        [data-testid="stSidebar"] .stButton > button:hover {
            transform: scale(1.03);
            border-color: rgba(255, 255, 255, 0.14) !important;
            background: rgba(255, 255, 255, 0.04) !important;
            box-shadow: 12px 17px 42px rgba(0, 0, 0, 0.22), 0 0 20px rgba(255, 255, 255, 0.05) !important;
        }
        [data-testid="stSidebar"] .stButton > button[kind="primary"] {
            background: var(--card-surface) !important;
            border-color: rgba(255, 255, 255, 0.18) !important;
            color: var(--text) !important;
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.05),
                0 10px 22px rgba(0, 0, 0, 0.24),
                0 0 28px rgba(255, 255, 255, 0.1),
                0 0 12px rgba(255, 255, 255, 0.08) !important;
        }
        [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
            border-color: rgba(255, 255, 255, 0.22) !important;
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.06),
                0 12px 24px rgba(0, 0, 0, 0.24),
                0 0 34px rgba(255, 255, 255, 0.13),
                0 0 16px rgba(255, 255, 255, 0.09) !important;
        }
        [data-testid="stSidebar"] .stButton > button:active {
            transform: scale(0.95) rotateZ(1.7deg);
        }
        .di-sidebar-trust {
            margin: 1.05rem 0 1.2rem 0;
            padding: 0.95rem;
            border-radius: var(--radius-sm);
            border: 1px solid var(--border);
            background: var(--card-surface);
        }
        .di-sidebar-trust-top {
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            gap: 0.5rem;
            margin-bottom: 0.45rem;
        }
        .di-sidebar-trust-score {
            font-family: var(--font-display);
            font-size: 1.55rem;
            font-weight: 600;
            letter-spacing: -0.04em;
        }
        .di-sidebar-trust-label {
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: var(--muted);
        }
        .di-meter-track {
            width: 100%;
            height: 0.4rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.08);
            overflow: hidden;
        }
        .di-meter-fill {
            height: 100%;
            border-radius: 999px;
            background: #f3b35f;
        }
        .di-meter-fill.ready,
        .di-meter-fill.caution,
        .di-meter-fill.blocked { background: #f3b35f; }
        .di-sidebar-trust-copy {
            margin-top: 0.55rem;
            color: rgba(255, 255, 255, 0.72);
            font-size: 0.8rem;
            line-height: 1.45;
        }
        .di-hero {
            padding: 0.15rem 0 0 0;
            margin-bottom: 0;
            border: 0;
            border-radius: 0;
            background: transparent;
            box-shadow: none;
            backdrop-filter: none;
        }
        .di-title {
            font-family: var(--font-display);
            font-size: clamp(4rem, 6.2vw, 6rem);
            font-weight: 700;
            line-height: 0.92;
            margin: 0;
            color: var(--text);
            max-width: 72rem;
            text-shadow: 0 0 22px rgba(255, 255, 255, 0.07);
        }
        .di-page-title {
            font-size: clamp(3.35rem, 5.45vw, 4.8rem) !important;
            font-weight: 520 !important;
            line-height: 0.94 !important;
            letter-spacing: -0.05em !important;
            margin: 0 !important;
        }
        .di-subtitle {
            margin-top: 0.8rem;
            color: rgba(255, 255, 255, 0.82);
            max-width: 58rem;
            font-size: 0.88rem;
            line-height: 1.55;
        }
        .di-hero-rule {
            margin-top: 1.15rem;
            width: 100%;
            height: 1px;
            background:
                linear-gradient(
                    90deg,
                    rgba(255, 255, 255, 0),
                    rgba(255, 255, 255, 0.26) 18%,
                    rgba(255, 255, 255, 0.1) 62%,
                    rgba(255, 255, 255, 0)
                );
            box-shadow: 0 0 18px rgba(255, 255, 255, 0.045);
        }
        .di-section-label {
            margin: var(--space-section) 0 0.6rem 0;
            color: var(--text);
            text-transform: uppercase;
            letter-spacing: 0.16em;
            font-size: 0.68rem;
        }
        .di-section-gap {
            height: var(--space-section);
        }
        .di-content-gap {
            height: var(--space-content);
        }
        .di-kpi-card {
            min-height: 186px;
            height: 100%;
            padding: 1.08rem 1.08rem 1rem 1.08rem;
            margin-bottom: 0;
            border-radius: var(--radius-md);
            border: 1px solid rgba(255, 255, 255, 0.09);
            background: var(--card-surface);
            box-shadow: var(--shadow-soft);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            overflow: hidden;
            cursor: pointer;
            user-select: none;
            transition: all 0.32s ease;
        }
        .di-kpi-card:hover {
            transform: scale(1.03);
            border-color: rgba(255, 255, 255, 0.14);
            box-shadow: 12px 17px 42px rgba(0, 0, 0, 0.22), 0 0 24px rgba(255, 255, 255, 0.05);
        }
        .di-kpi-card:active {
            transform: scale(0.95) rotateZ(1.7deg);
        }
        .di-kpi-label {
            color: var(--muted-strong);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            font-size: 0.72rem;
            margin-bottom: 0.8rem;
        }
        .di-kpi-value {
            font-family: var(--font-display);
            font-size: 1.78rem;
            font-weight: 600;
            letter-spacing: -0.04em;
            color: var(--text);
            margin-bottom: 0.55rem;
            line-height: 1.05;
            min-height: 2.1rem;
        }
        .di-kpi-detail {
            color: var(--muted-strong);
            font-size: 0.88rem;
            line-height: 1.45;
            min-height: 3.95rem;
            max-height: 3.95rem;
            overflow: hidden;
            word-break: break-word;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
        }
        [data-testid="column"] .di-kpi-card,
        [data-testid="column"] .di-insight-card {
            height: 100%;
        }
        .di-kpi-tone-bar {
            width: 2.65rem;
            height: 0.22rem;
            border-radius: 999px;
            margin-top: 0.95rem;
            background: rgba(255, 255, 255, 0.12);
        }
        .di-kpi-card.good .di-kpi-tone-bar { background: var(--good); }
        .di-kpi-card.caution .di-kpi-tone-bar { background: var(--warn); }
        .di-kpi-card.danger .di-kpi-tone-bar { background: var(--danger); }
        .di-kpi-card.accent .di-kpi-tone-bar { background: var(--accent); }
        .di-trust-banner {
            margin: 0;
            padding: 1.25rem;
            border-radius: var(--radius-lg);
            border: 1px solid rgba(255, 255, 255, 0.09);
            background: var(--card-surface);
            box-shadow: var(--shadow);
            backdrop-filter: blur(12px);
        }
        .di-trust-layout {
            display: grid;
            grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.9fr);
            gap: 1rem;
            align-items: start;
        }
        .di-trust-score-row {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            flex-wrap: wrap;
            margin-bottom: 0.8rem;
        }
        .di-trust-score {
            font-family: var(--font-display);
            font-size: 2.8rem;
            font-weight: 620;
            letter-spacing: -0.05em;
            line-height: 1;
            color: var(--text);
        }
        .di-pill {
            display: inline-flex;
            align-items: center;
            padding: 0.35rem 0.8rem;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            border: 1px solid rgba(255, 255, 255, 0.08);
            background: rgba(255, 255, 255, 0.04);
        }
        .di-pill.ready { color: var(--good); }
        .di-pill.caution { color: var(--warn); }
        .di-pill.blocked { color: var(--danger); }
        .di-trust-message {
            color: rgba(255, 255, 255, 0.82);
            line-height: 1.6;
            font-size: 0.95rem;
            margin-top: 0.9rem;
            max-width: 42rem;
        }
        .di-trust-stats {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.7rem;
        }
        .di-stat-card {
            min-height: 104px;
            padding: 0.9rem 0.95rem;
            border-radius: 18px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            background: var(--card-surface);
            cursor: pointer;
            user-select: none;
            transition: all 0.32s ease;
        }
        .di-stat-card:hover {
            transform: scale(1.03);
            border-color: rgba(255, 255, 255, 0.14);
            box-shadow: 12px 17px 42px rgba(0, 0, 0, 0.22), 0 0 22px rgba(255, 255, 255, 0.045);
        }
        .di-stat-card:active {
            transform: scale(0.95) rotateZ(1.7deg);
        }
        .di-stat-label {
            color: var(--muted-strong);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            font-size: 0.68rem;
            margin-bottom: 0.5rem;
        }
        .di-stat-value {
            color: var(--text);
            font-family: var(--font-display);
            font-size: 1.2rem;
            line-height: 1.2;
            letter-spacing: -0.03em;
        }
        .di-stat-detail {
            color: rgba(255, 255, 255, 0.68);
            font-size: 0.78rem;
            line-height: 1.45;
            margin-top: 0.45rem;
        }
        .di-stat-issues {
            margin: 0.55rem 0 0 0;
            padding-left: 1rem;
            color: rgba(255, 255, 255, 0.84);
            font-size: 0.78rem;
            line-height: 1.45;
        }
        .di-stat-issues li {
            margin-bottom: 0.34rem;
        }
        .di-stat-issues li:last-child {
            margin-bottom: 0;
        }
        .di-stat-empty {
            margin-top: 0.55rem;
            color: rgba(255, 255, 255, 0.58);
            font-size: 0.78rem;
            line-height: 1.45;
        }
        .di-trust-meta {
            margin-top: 0.9rem;
            padding: 0.8rem 0.9rem;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            background: var(--card-surface);
        }
        .di-trust-meta-title {
            color: var(--muted-strong);
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-size: 0.68rem;
            margin-bottom: 0.45rem;
        }
        .di-trust-meta-copy {
            color: rgba(255, 255, 255, 0.82);
            font-size: 0.84rem;
            line-height: 1.5;
        }
        .di-trust-driver-list {
            margin: 0.55rem 0 0 0;
            padding-left: 1rem;
            color: rgba(255, 255, 255, 0.82);
            font-size: 0.82rem;
            line-height: 1.5;
        }
        .di-trust-driver-list li {
            margin-bottom: 0.32rem;
        }
        .di-trust-driver-list li:last-child {
            margin-bottom: 0;
        }
        .di-surface {
            padding: 1.15rem 1.15rem 0.5rem 1.15rem;
            margin-bottom: 0;
            border-radius: var(--radius-lg);
            border: 1px solid rgba(255, 255, 255, 0.09);
            background: var(--card-surface);
            box-shadow: var(--shadow-soft);
            backdrop-filter: blur(10px);
        }
        .di-surface-head {
            margin-bottom: 0.85rem;
            padding: 0 0.05rem;
        }
        .di-surface-title {
            font-family: var(--font-display);
            font-size: 1.08rem;
            font-weight: 600;
            color: var(--text);
            margin-bottom: 0.25rem;
        }
        .di-surface-copy {
            color: rgba(255, 255, 255, 0.72);
            font-size: 0.88rem;
            line-height: 1.5;
        }
        .di-insight-card {
            height: 100%;
            min-height: 152px;
            padding: 1rem 1rem 0.9rem 1rem;
            margin-bottom: 0;
            border-radius: 18px;
            border: 1px solid rgba(255, 255, 255, 0.09);
            background: var(--card-surface);
            display: flex;
            flex-direction: column;
            cursor: pointer;
            user-select: none;
            transition: all 0.32s ease;
        }
        .di-card-row-gap {
            height: var(--space-content);
        }
        .di-insight-card:hover {
            transform: scale(1.03);
            border-color: rgba(255, 255, 255, 0.14);
            box-shadow: 12px 17px 42px rgba(0, 0, 0, 0.22), 0 0 24px rgba(255, 255, 255, 0.045);
        }
        .di-insight-card:active {
            transform: scale(0.95) rotateZ(1.7deg);
        }
        .di-insight-topline {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.6rem;
            margin-bottom: 0.7rem;
        }
        .di-insight-entity {
            color: var(--muted-strong);
            font-size: 0.74rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }
        .di-severity-pill {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 0.2rem 0.56rem;
            font-size: 0.68rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            background: rgba(255, 255, 255, 0.04);
        }
        .di-severity-pill.critical { color: var(--danger); }
        .di-severity-pill.warning { color: var(--warn); }
        .di-severity-pill.info { color: var(--good); }
        .di-insight-message {
            color: var(--text);
            font-size: 0.95rem;
            line-height: 1.55;
            margin-bottom: 0.7rem;
        }
        .di-insight-driver {
            color: rgba(255, 255, 255, 0.68);
            font-size: 0.8rem;
            line-height: 1.5;
        }
        .di-table-shell {
            border-radius: 18px;
            border: 1px solid rgba(255, 255, 255, 0.09);
            background: var(--card-surface);
            overflow: hidden;
            box-shadow: 0 10px 22px rgba(0, 0, 0, 0.16);
            transition: transform 220ms ease, border-color 220ms ease, box-shadow 260ms ease;
        }
        .di-table-shell:hover {
            transform: translateY(-1px);
            border-color: rgba(255, 255, 255, 0.14);
            box-shadow: 0 16px 34px rgba(0, 0, 0, 0.24), 0 0 20px rgba(255, 255, 255, 0.025);
        }
        .di-table-wrap {
            overflow-x: auto;
        }
        .di-table {
            width: 100%;
            border-collapse: collapse;
        }
        .di-table thead th {
            background: rgba(255, 255, 255, 0.03);
            color: var(--muted-strong);
            text-align: left;
            font-size: 0.7rem;
            font-weight: 600;
            letter-spacing: 0.09em;
            text-transform: uppercase;
            padding: 0.82rem 0.92rem;
            border-bottom: 1px solid var(--border);
            white-space: nowrap;
        }
        .di-table tbody td {
            color: var(--text);
            font-size: 0.9rem;
            line-height: 1.5;
            padding: 0.86rem 0.92rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.045);
        }
        .di-table tbody tr:last-child td {
            border-bottom: 0;
        }
        .di-table tbody tr:nth-child(even) td {
            background: rgba(255, 255, 255, 0.012);
        }
        .di-table tbody tr:hover td {
            background: rgba(255, 255, 255, 0.028);
        }
        [data-testid="stExpander"] {
            border: 1px solid var(--border);
            border-radius: var(--control-radius);
            background: var(--card-surface);
            overflow: hidden;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.2);
            cursor: pointer;
            user-select: none;
            transition: all var(--accordion-duration) var(--accordion-ease);
        }
        [data-testid="stExpander"]:has(> details[open]) {
            border-radius: 18px;
        }
        [data-testid="stExpander"] > details {
            display: grid !important;
            grid-template-rows: minmax(var(--control-height), auto) 0fr;
            border: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
            border-radius: inherit !important;
            position: relative !important;
            transition: grid-template-rows var(--accordion-duration) var(--accordion-ease);
        }
        [data-testid="stExpander"] > details::before {
            content: "";
            position: absolute;
            left: var(--dropdown-inline-padding);
            top: calc(var(--control-height) / 2);
            width: var(--dropdown-arrow-size);
            height: var(--dropdown-arrow-size);
            transform: translateY(-50%) rotate(180deg);
            transform-origin: center center;
            background-color: rgba(255, 255, 255, 0.72);
            mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='none'%3E%3Cpath d='M6 12l4-4 4 4' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") center / contain no-repeat;
            -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='none'%3E%3Cpath d='M6 12l4-4 4 4' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") center / contain no-repeat;
            transition:
                transform var(--accordion-duration) var(--accordion-ease),
                background-color var(--accordion-duration) var(--accordion-ease);
            pointer-events: none;
            z-index: 2;
        }
        [data-testid="stExpander"] > details[open] {
            grid-template-rows: minmax(var(--control-height), auto) 1fr;
        }
        [data-testid="stExpander"] > details[open]::before {
            transform: translateY(-50%) rotate(0deg);
            background-color: var(--text);
        }
        [data-testid="stExpander"] > details.di-expander-closing::before {
            transform: translateY(-50%) rotate(180deg);
            background-color: rgba(255, 255, 255, 0.72);
        }
        [data-testid="stExpander"] > details[open] > summary {
            border-bottom: 1px solid var(--border) !important;
            border-bottom-left-radius: 0 !important;
            border-bottom-right-radius: 0 !important;
        }
        [data-testid="stExpander"] > details > div {
            min-height: 0;
            overflow: hidden !important;
            opacity: 0;
            transform: translateY(0.4rem);
            transform-origin: top center;
            transition:
                opacity var(--accordion-duration) var(--accordion-ease),
                transform var(--accordion-duration) var(--accordion-ease);
        }
        [data-testid="stExpander"] > details[open] > div {
            opacity: 1;
            transform: translateY(0);
            border-radius: 0 0 18px 18px;
            overflow: visible !important;
        }
        [data-testid="stExpander"] > details > div > div {
            opacity: 0;
            transform: translateY(0.9rem);
            transition:
                opacity var(--accordion-duration) var(--accordion-ease),
                transform var(--accordion-duration) var(--accordion-ease);
        }
        [data-testid="stExpander"] > details[open] > div > div {
            opacity: 1;
            transform: translateY(0);
            transition-delay: 75ms;
        }
        [data-testid="stExpander"] > details > summary {
            border: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
            min-height: var(--control-height);
            padding: 0 var(--dropdown-inline-padding) 0 var(--dropdown-text-offset) !important;
            display: flex !important;
            align-items: center !important;
            gap: 0 !important;
            border-radius: inherit !important;
            position: relative !important;
            transition:
                background var(--accordion-duration) var(--accordion-ease),
                color var(--accordion-duration) var(--accordion-ease);
        }
        [data-testid="stExpander"] > details > summary::marker,
        [data-testid="stExpander"] > details > summary::-webkit-details-marker {
            display: none !important;
        }
        [data-testid="stExpander"] > details > summary::before {
            display: none !important;
            content: none !important;
        }
        [data-testid="stExpander"] > details > summary::after {
            display: none !important;
            content: none !important;
        }
        [data-testid="stExpander"] > details > summary p,
        [data-testid="stExpander"] > details > summary span,
        [data-testid="stExpander"] > details > summary div {
            color: var(--text) !important;
            line-height: 1.2 !important;
            transition:
                color var(--accordion-duration) var(--accordion-ease),
                opacity var(--accordion-duration) var(--accordion-ease),
                transform var(--accordion-duration) var(--accordion-ease);
        }
        [data-testid="stExpander"] > details > summary > span {
            display: flex !important;
            align-items: center !important;
            gap: 0 !important;
            width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        [data-testid="stExpander"] > details > summary > span > div,
        [data-testid="stExpander"] > details > summary > span > p {
            margin: 0 !important;
            padding: 0 !important;
        }
        [data-testid="stExpander"] > details > summary svg {
            display: none !important;
        }
        [data-testid="stExpander"] > details [data-testid^="stExpanderIcon"] {
            display: none !important;
        }
        [data-testid="stExpander"] > details > summary > span > :first-child {
            display: none !important;
        }
        .di-dropdown-shell details {
            display: grid;
            grid-template-rows: minmax(var(--control-height), auto) 0fr;
            border: 1px solid var(--border);
            border-radius: var(--control-radius);
            background: var(--card-surface);
            overflow: hidden;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.2);
            transition: all var(--accordion-duration) var(--accordion-ease);
        }
        .di-dropdown-shell details[open] {
            grid-template-rows: minmax(var(--control-height), auto) 1fr;
            border-radius: 18px;
        }
        .di-dropdown-shell summary {
            list-style: none;
            border: 0;
            background: transparent;
            box-shadow: none;
            min-height: var(--control-height);
            padding: 0 var(--dropdown-inline-padding) 0 var(--dropdown-text-offset);
            display: flex;
            align-items: center;
            gap: 0;
            border-radius: inherit;
            position: relative;
            cursor: pointer;
            color: var(--text);
            transition:
                background var(--accordion-duration) var(--accordion-ease),
                color var(--accordion-duration) var(--accordion-ease);
        }
        .di-dropdown-shell summary::marker,
        .di-dropdown-shell summary::-webkit-details-marker {
            display: none;
        }
        .di-dropdown-shell summary::before {
            content: "";
            position: absolute;
            left: var(--dropdown-inline-padding);
            top: 50%;
            width: var(--dropdown-arrow-size);
            height: var(--dropdown-arrow-size);
            transform: translateY(-50%) rotate(180deg);
            transform-origin: center center;
            background-color: rgba(255, 255, 255, 0.72);
            mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='none'%3E%3Cpath d='M6 12l4-4 4 4' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") center / contain no-repeat;
            -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='none'%3E%3Cpath d='M6 12l4-4 4 4' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") center / contain no-repeat;
            transition:
                transform var(--accordion-duration) var(--accordion-ease),
                background-color var(--accordion-duration) var(--accordion-ease);
            pointer-events: none;
        }
        .di-dropdown-shell details[open] > summary {
            border-bottom: 1px solid var(--border);
            border-bottom-left-radius: 0;
            border-bottom-right-radius: 0;
        }
        .di-dropdown-shell details[open] > summary::before {
            transform: translateY(-50%) rotate(0deg);
            background-color: var(--text);
        }
        .di-dropdown-shell details > div {
            min-height: 0;
            overflow: hidden;
            opacity: 0;
            transform: translateY(0.4rem);
            transform-origin: top center;
            transition:
                opacity var(--accordion-duration) var(--accordion-ease),
                transform var(--accordion-duration) var(--accordion-ease);
        }
        .di-dropdown-shell details[open] > div {
            opacity: 1;
            transform: translateY(0);
            border-radius: 0 0 18px 18px;
            overflow: visible;
        }
        .di-dropdown-shell details > div > div {
            opacity: 0;
            transform: translateY(0.9rem);
            transition:
                opacity var(--accordion-duration) var(--accordion-ease),
                transform var(--accordion-duration) var(--accordion-ease);
        }
        .di-dropdown-shell details[open] > div > div {
            opacity: 1;
            transform: translateY(0);
            transition-delay: 75ms;
        }
        .di-dropdown-caption {
            color: rgba(255, 255, 255, 0.72);
            font-size: 0.82rem;
            line-height: 1.45;
            margin-top: 0.7rem;
        }
        .di-dropdown-meta-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.7rem;
            margin-bottom: 0.8rem;
        }
        .di-dropdown-meta-card {
            padding: 0.8rem 0.9rem;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            background: var(--card-surface);
        }
        .di-dropdown-meta-label {
            color: var(--muted-strong);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            font-size: 0.66rem;
            margin-bottom: 0.4rem;
        }
        .di-dropdown-meta-value {
            color: var(--text);
            font-family: var(--font-display);
            font-size: 1rem;
            letter-spacing: -0.02em;
            line-height: 1.25;
        }
        .di-dropdown-meta-copy {
            margin-top: 0.35rem;
            color: rgba(255, 255, 255, 0.72);
            font-size: 0.78rem;
            line-height: 1.45;
        }
        .di-dropdown-list {
            list-style: disc;
            margin: 0.55rem 0 0 1.15rem;
            padding: 0;
            color: var(--text);
        }
        .di-dropdown-list li {
            margin: 0 0 0.38rem 0;
            line-height: 1.5;
        }
        .di-dropdown-list li:last-child {
            margin-bottom: 0;
        }
        .stDateInput > div,
        .stSelectbox > div,
        .stMultiSelect > div,
        .stTextInput > div,
        .stNumberInput > div {
            border: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
        }
        .stSelectbox div[data-baseweb="select"] > div,
        .stMultiSelect div[data-baseweb="select"] > div,
        .stTextInput [data-baseweb="base-input"],
        .stNumberInput [data-baseweb="base-input"],
        .stDateInput [data-baseweb="input"] {
            background: var(--card-surface) !important;
            border: 1px solid var(--border-strong) !important;
            border-radius: var(--control-radius) !important;
            color: var(--text) !important;
            box-shadow: none !important;
            min-height: var(--control-height) !important;
            transition: all var(--accordion-duration) var(--accordion-ease) !important;
        }
        .stSelectbox div[data-baseweb="select"] > div,
        .stMultiSelect div[data-baseweb="select"] > div {
            display: flex !important;
            align-items: center !important;
            padding: 0 var(--dropdown-inline-padding) 0 var(--dropdown-text-offset) !important;
            gap: 0 !important;
            position: relative !important;
        }
        .stSelectbox div[data-baseweb="select"] > div:has([aria-expanded="true"]),
        .stMultiSelect div[data-baseweb="select"] > div:has([aria-expanded="true"]),
        .stDateInput [data-baseweb="input"]:focus-within {
            border-radius: 18px !important;
        }
        .stSelectbox div[data-baseweb="select"] > div:has([aria-expanded="true"]),
        .stMultiSelect div[data-baseweb="select"] > div:has([aria-expanded="true"]) {
            border-bottom-left-radius: 0 !important;
            border-bottom-right-radius: 0 !important;
            border-bottom-color: transparent !important;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.2) !important;
        }
        .stSelectbox div[data-baseweb="select"] > div > div:first-child,
        .stMultiSelect div[data-baseweb="select"] > div > div:first-child {
            order: initial !important;
            display: flex !important;
            align-items: center !important;
            flex: 1 1 auto;
            min-width: 0;
            margin: 0 !important;
            padding: 0 !important;
        }
        .stSelectbox div[data-baseweb="select"] > div > div:last-child,
        .stMultiSelect div[data-baseweb="select"] > div > div:last-child {
            display: none !important;
        }
        .stSelectbox div[data-baseweb="select"] > div::before,
        .stMultiSelect div[data-baseweb="select"] > div::before {
            content: "";
            position: absolute;
            left: var(--dropdown-inline-padding);
            top: 50%;
            width: var(--dropdown-arrow-size);
            height: var(--dropdown-arrow-size);
            transform: translateY(-50%) rotate(180deg);
            transform-origin: center center;
            background-color: rgba(255, 255, 255, 0.72);
            mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='none'%3E%3Cpath d='M6 12l4-4 4 4' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") center / contain no-repeat;
            -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='none'%3E%3Cpath d='M6 12l4-4 4 4' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") center / contain no-repeat;
            transition:
                transform var(--accordion-duration) var(--accordion-ease),
                background-color var(--accordion-duration) var(--accordion-ease) !important;
            pointer-events: none;
        }
        .stSelectbox div[data-baseweb="select"] > div svg,
        .stMultiSelect div[data-baseweb="select"] > div svg {
            display: none !important;
        }
        .stSelectbox div[data-baseweb="select"] > div:has([aria-expanded="true"])::before,
        .stMultiSelect div[data-baseweb="select"] > div:has([aria-expanded="true"])::before {
            transform: translateY(-50%) rotate(0deg);
            background-color: var(--text);
        }
        .stSelectbox div[data-baseweb="select"] [data-baseweb="select"] > div,
        .stMultiSelect div[data-baseweb="select"] [data-baseweb="select"] > div,
        .stDateInput div[data-baseweb="input"] [data-baseweb="input"] > div,
        .stDateInput div[data-baseweb="input"] [data-baseweb="base-input"],
        .stDateInput div[data-baseweb="input"] input,
        .stSelectbox div[data-baseweb="select"] [role="combobox"],
        .stMultiSelect div[data-baseweb="select"] [role="combobox"] {
            border: 0 !important;
            outline: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
            border-radius: 0 !important;
        }
        .stDateInput [data-baseweb="input"] > div,
        .stTextInput [data-baseweb="base-input"] > div,
        .stNumberInput [data-baseweb="base-input"] > div,
        .stSelectbox div[data-baseweb="select"] > div > div,
        .stMultiSelect div[data-baseweb="select"] > div > div,
        .stDateInput [data-baseweb="base-input"] {
            border: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
        }
        .stDateInput input,
        .stSelectbox div[data-baseweb="select"] [role="combobox"],
        .stMultiSelect div[data-baseweb="select"] [role="combobox"],
        [data-testid="stExpander"] > details > summary {
            min-height: var(--control-height) !important;
        }
        .stSelectbox div[data-baseweb="select"] [role="combobox"],
        .stMultiSelect div[data-baseweb="select"] [role="combobox"] {
            display: flex !important;
            align-items: center !important;
            justify-content: flex-start !important;
            line-height: 1.2 !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
            margin: 0 !important;
            text-align: left !important;
        }
        .stSelectbox div[data-baseweb="select"] [role="combobox"] > div,
        .stMultiSelect div[data-baseweb="select"] [role="combobox"] > div {
            margin: 0 !important;
            padding: 0 !important;
        }
        [data-testid="stSidebar"] .stNumberInput > div,
        [data-testid="stSidebar"] .stNumberInput > div[data-baseweb="input"],
        [data-testid="stSidebar"] .stNumberInput [data-baseweb="input"],
        [data-testid="stSidebar"] .stNumberInput [data-baseweb="base-input"],
        [data-testid="stSidebar"] .stNumberInput [data-baseweb="base-input"] > div {
            border: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
        }
        [data-testid="stSidebar"] .stNumberInput [data-baseweb="base-input"] {
            justify-content: center !important;
            gap: 0.18rem !important;
        }
        label[data-testid="stWidgetLabel"] p {
            color: var(--text) !important;
            letter-spacing: 0.01em;
        }
        h3 {
            margin: 0 0 0.65rem 0 !important;
        }
        .stCaption {
            color: rgba(255, 255, 255, 0.72) !important;
            margin-top: 0.35rem !important;
        }
        .stButton > button, .stDownloadButton > button {
            border-radius: 14px !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            background: linear-gradient(180deg, rgba(28, 33, 42, 0.96), rgba(18, 22, 28, 0.96)) !important;
            color: var(--text) !important;
            cursor: pointer;
            user-select: none;
            transition: all 0.32s ease !important;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.2);
        }
        .stButton > button:hover, .stDownloadButton > button:hover {
            transform: scale(1.03);
            border-color: rgba(255, 255, 255, 0.14) !important;
            box-shadow: 12px 17px 42px rgba(0, 0, 0, 0.22), 0 0 18px rgba(255, 255, 255, 0.04);
        }
        .stButton > button:active, .stDownloadButton > button:active {
            transform: scale(0.95) rotateZ(1.7deg);
        }
        [data-testid="stDataFrame"], [data-testid="stTable"] {
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid var(--border);
            box-shadow: 0 8px 18px rgba(0, 0, 0, 0.14);
        }
        [data-testid="stDataFrame"] [role="grid"],
        [data-testid="stTable"] table {
            background: var(--card-surface);
        }
        [data-testid="stDataFrame"] [role="columnheader"],
        [data-testid="stTable"] th {
            background: rgba(255, 255, 255, 0.035) !important;
            color: var(--muted-strong) !important;
            font-size: 0.72rem !important;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            border-bottom: 1px solid var(--border) !important;
        }
        [data-testid="stDataFrame"] [role="gridcell"],
        [data-testid="stTable"] td {
            color: var(--text) !important;
            border-top: 1px solid rgba(255, 255, 255, 0.04) !important;
            background: rgba(0, 0, 0, 0) !important;
        }
        [data-testid="stPlotlyChart"] {
            border-radius: 18px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.09);
            background: var(--card-surface);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.14);
            padding: 0.18rem;
            transition: transform 220ms ease, border-color 220ms ease, box-shadow 260ms ease;
        }
        [data-testid="stPlotlyChart"]:hover {
            transform: translateY(-1px);
            border-color: rgba(255, 255, 255, 0.14);
            box-shadow: 0 16px 30px rgba(0, 0, 0, 0.22), 0 0 18px rgba(255, 255, 255, 0.025);
        }
        [data-testid="stChatInput"] {
            border: 1px solid var(--border);
            border-radius: 18px;
            background: rgba(16, 20, 27, 0.92);
            padding: 0.25rem 0.45rem;
            overflow-anchor: none;
        }
        [data-testid="stChatInput"] textarea {
            font-size: 0.95rem !important;
        }
        [data-testid="stChatMessage"] {
            overflow-anchor: none;
        }
        [data-baseweb="popover"] [role="listbox"],
        [data-baseweb="popover"] [data-baseweb="menu"] {
            animation: di-dropdown-panel-in var(--accordion-duration) var(--accordion-ease);
            transform-origin: top center;
            overflow: hidden;
            margin-top: 0 !important;
            border: 1px solid var(--border-strong);
            border-top: 0;
            border-radius: 0 0 18px 18px;
            background: var(--card-surface) !important;
            box-shadow: 0 16px 34px rgba(0, 0, 0, 0.26);
            padding-top: 0.2rem;
        }
        [data-baseweb="popover"] [data-baseweb="calendar"] {
            background: var(--card-surface) !important;
            border: 1px solid var(--border-strong) !important;
            border-radius: 18px !important;
            box-shadow: 0 16px 34px rgba(0, 0, 0, 0.26) !important;
            backdrop-filter: blur(18px);
            color: var(--text) !important;
            overflow: hidden !important;
        }
        [data-baseweb="popover"] [data-baseweb="calendar"] *,
        [data-baseweb="popover"] [data-baseweb="calendar"] button,
        [data-baseweb="popover"] [data-baseweb="calendar"] span,
        [data-baseweb="popover"] [data-baseweb="calendar"] div {
            color: var(--text) !important;
        }
        [data-baseweb="popover"] [data-baseweb="calendar"] button {
            border-radius: 12px !important;
            transition: background-color 180ms ease, color 180ms ease, box-shadow 180ms ease !important;
        }
        [data-baseweb="popover"] [data-baseweb="calendar"] button:hover {
            background: rgba(255, 255, 255, 0.055) !important;
        }
        [data-baseweb="popover"] [data-baseweb="calendar"] [aria-selected="true"],
        [data-baseweb="popover"] [data-baseweb="calendar"] [data-highlighted="true"] {
            background: rgba(255, 255, 255, 0.085) !important;
            box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08) !important;
        }
        [data-baseweb="popover"] [data-baseweb="calendar"] [aria-disabled="true"] {
            color: rgba(255, 255, 255, 0.36) !important;
        }
        [data-baseweb="popover"] [role="option"],
        [data-baseweb="popover"] [data-baseweb="menu"] > * {
            opacity: 1;
            transform: none;
            animation: none !important;
            background: transparent !important;
        }
        .stSelectbox div[data-baseweb="select"] > div:focus-within,
        .stMultiSelect div[data-baseweb="select"] > div:focus-within,
        .stDateInput [data-baseweb="input"]:focus-within {
            border-color: rgba(255, 255, 255, 0.12) !important;
            box-shadow: none !important;
        }
        .stTextInput [data-baseweb="base-input"]:focus-within,
        .stNumberInput [data-baseweb="base-input"]:focus-within {
            border-color: rgba(243, 200, 109, 0.44) !important;
            box-shadow: 0 0 0 1px rgba(243, 200, 109, 0.2);
        }
        @keyframes di-dropdown-panel-in {
            from {
                opacity: 0;
                transform: translateY(0.4rem);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        hr {
            border-color: rgba(255, 255, 255, 0.08);
            margin: var(--space-section) 0 !important;
        }
        @media (max-width: 1080px) {
            .di-trust-layout { grid-template-columns: 1fr; }
            .di-dropdown-meta-grid { grid-template-columns: 1fr; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_page_intro(title: str, subtitle: str):
    """Render a premium page hero."""
    st.markdown(
        f"""
        <div class="di-hero">
            <div class="di-title di-page-title">{title}</div>
            <div class="di-subtitle">{subtitle}</div>
            <div class="di-hero-rule"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_page_shell(page_name: str):
    _, title, subtitle = PAGE_COPY[page_name]
    _render_page_intro(title, subtitle)
    _render_layout_gap("section")


def _render_section_label(label: str):
    st.markdown(f'<div class="di-section-label">{label}</div>', unsafe_allow_html=True)


def _render_layout_gap(size: str = "section"):
    css_class = "di-section-gap" if size == "section" else "di-content-gap"
    st.markdown(f'<div class="{css_class}"></div>', unsafe_allow_html=True)


def _open_surface():
    return None


def _close_surface():
    return None


def _render_surface_header(title: str, subtitle: str | None = None):
    subtitle_markup = f'<div class="di-surface-copy">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="di-surface-head">
            <div class="di-surface-title">{title}</div>
            {subtitle_markup}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _format_display_date(value) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return pd.to_datetime(value).strftime("%b %d, %Y")


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[index:index + 2], 16) for index in (0, 2, 4))


def _interpolate_hex(start: str, end: str, ratio: float) -> str:
    ratio = max(0.0, min(1.0, ratio))
    start_rgb = _hex_to_rgb(start)
    end_rgb = _hex_to_rgb(end)
    blended = tuple(round(start_component + (end_component - start_component) * ratio) for start_component, end_component in zip(start_rgb, end_rgb))
    return "#" + "".join(f"{component:02x}" for component in blended)


def _blend_hex(color: str, target: str, ratio: float) -> str:
    return _interpolate_hex(color, target, ratio)


def _trust_score_color(score: float) -> str:
    score = max(0.0, min(100.0, float(score)))
    if score <= 50:
        return _interpolate_hex("#ff7d6d", "#f3b35f", score / 50 if score else 0.0)
    return _interpolate_hex("#f3b35f", "#36d39b", (score - 50) / 50 if score < 100 else 1.0)


def _trust_meter_fill_style(score: float) -> str:
    score = max(0.0, min(100.0, float(score)))
    background_size = 100 if score <= 0 else (100 / score) * 100
    return (
        "background: linear-gradient(90deg, #ff7d6d 0%, #f3b35f 50%, #36d39b 100%); "
        f"background-size: {background_size:.2f}% 100%; "
        "background-position: left top; "
        "background-repeat: no-repeat;"
    )


def _format_coverage_window(start_value, end_value) -> str:
    if start_value is None and end_value is None:
        return "No dated records"
    if start_value is None:
        return f"Through {_format_display_date(end_value)}"
    if end_value is None:
        return f"From {_format_display_date(start_value)}"
    start_text = _format_display_date(start_value)
    end_text = _format_display_date(end_value)
    return start_text if start_text == end_text else f"{start_text} - {end_text}"


def _render_kpi_card(label: str, value: str, detail: str, tone: str = "accent"):
    card_markup = (
        f'<div class="di-kpi-card {escape(str(tone))}">'
        f'<div class="di-kpi-label">{escape(str(label))}</div>'
        f'<div class="di-kpi-value">{escape(str(value))}</div>'
        f'<div class="di-kpi-detail">{escape(str(detail))}</div>'
        f'<div class="di-kpi-tone-bar"></div>'
        f'</div>'
    )
    st.markdown(card_markup, unsafe_allow_html=True)


def _render_kpi_grid(cards: list[tuple[str, str, str, str]]):
    for start_index in range(0, len(cards), 3):
        if start_index > 0:
            st.markdown('<div class="di-card-row-gap"></div>', unsafe_allow_html=True)
        columns = st.columns(3, gap="large")
        for column, card in zip(columns, cards[start_index:start_index + 3]):
            with column:
                _render_kpi_card(*card)


def _render_insight_grid(insights: list[dict]):
    for start_index in range(0, len(insights), 3):
        if start_index > 0:
            st.markdown('<div class="di-card-row-gap"></div>', unsafe_allow_html=True)
        columns = st.columns(3, gap="large")
        for column, insight in zip(columns, insights[start_index:start_index + 3]):
            with column:
                _render_insight_card(insight)


def _format_table_cell(value, formatter=None) -> str:
    if formatter is not None:
        return formatter(value)
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


def _build_modern_table_markup(dataframe: pd.DataFrame, formatters: dict[str, object] | None = None) -> str:
    formatters = formatters or {}
    headers = "".join(f"<th>{escape(str(column))}</th>" for column in dataframe.columns)
    body_rows = []
    for row in dataframe.itertuples(index=False, name=None):
        cells = []
        for column, value in zip(dataframe.columns, row):
            formatted_value = _format_table_cell(value, formatters.get(column))
            cells.append(f"<td>{escape(formatted_value)}</td>")
        body_rows.append(f"<tr>{''.join(cells)}</tr>")

    return (
        f'<div class="di-table-shell"><div class="di-table-wrap"><table class="di-table">'
        f'<thead><tr>{headers}</tr></thead><tbody>{"".join(body_rows)}</tbody></table></div></div>'
    )


def _render_modern_table(dataframe: pd.DataFrame, formatters: dict[str, object] | None = None):
    st.markdown(_build_modern_table_markup(dataframe, formatters=formatters), unsafe_allow_html=True)


def _build_issue_list_markup(messages: list[str], empty_message: str, max_items: int = 3) -> str:
    if not messages:
        return f'<div class="di-stat-empty">{escape(empty_message)}</div>'

    visible = messages[:max_items]
    items_markup = "".join(f"<li>{escape(message)}</li>" for message in visible)
    remainder = len(messages) - len(visible)
    if remainder > 0:
        items_markup += f"<li>+ {remainder} more issue(s)</li>"
    return f'<ul class="di-stat-issues">{items_markup}</ul>'


def _apply_chart_theme(fig: go.Figure):
    """Apply a consistent dark premium chart theme."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.028)",
        font=dict(color="#e7e9ec", family="IBM Plex Sans, Segoe UI Variable Text, Segoe UI, sans-serif", size=12),
        title_font=dict(size=18, color="#f5f5f6"),
        margin=dict(l=8, r=8, t=28, b=8),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11, color="#b9c0ca"),
        ),
        xaxis=dict(showgrid=False, zeroline=False, linecolor="rgba(255,255,255,0.08)", color="#c1c8d2", tickfont=dict(size=10)),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", zeroline=False, color="#c1c8d2", tickfont=dict(size=10)),
        hoverlabel=dict(bgcolor="#11161f", bordercolor="rgba(243,200,109,0.2)", font_color="#f5f5f6"),
    )
    return fig


def _inject_expander_close_sync():
    """Force native expander chevrons to start closing immediately on click."""
    components.html(
        """
        <script>
        const parentDoc = window.parent && window.parent.document ? window.parent.document : document;
        const CLOSING_CLASS = "di-expander-closing";
        const DURATION_MS = 560;

        function bindExpanders() {
          parentDoc
            .querySelectorAll('[data-testid="stExpander"] > details > summary')
            .forEach((summary) => {
              if (summary.dataset.diCloseSyncBound === "1") return;
              summary.dataset.diCloseSyncBound = "1";

              summary.addEventListener("click", () => {
                const details = summary.parentElement;
                if (!details) return;

                if (details.hasAttribute("open")) {
                  details.classList.add(CLOSING_CLASS);
                  window.setTimeout(() => {
                    details.classList.remove(CLOSING_CLASS);
                  }, DURATION_MS);
                } else {
                  details.classList.remove(CLOSING_CLASS);
                }
              });
            });
        }

        bindExpanders();
        const observer = new MutationObserver(() => bindExpanders());
        observer.observe(parentDoc.body, { childList: true, subtree: true });
        </script>
        """,
        height=0,
        width=0,
    )


def _inject_select_toggle_fix():
    """Make clicking an already-open BaseWeb select close it cleanly."""
    components.html(
        """
        <script>
        const parentDoc = window.parent && window.parent.document ? window.parent.document : document;
        const SELECT_TRIGGER = [
          '.stSelectbox div[data-baseweb="select"] > div',
          '.stMultiSelect div[data-baseweb="select"] > div'
        ].join(', ');

        function getTrigger(target) {
          return target && target.closest ? target.closest(SELECT_TRIGGER) : null;
        }

        function getCombobox(trigger) {
          return trigger ? trigger.querySelector('[role="combobox"]') : null;
        }

        if (!parentDoc.__diSelectToggleFixBound) {
          parentDoc.__diSelectToggleFixBound = true;

          function closeIfExpanded(event) {
            const trigger = getTrigger(event.target);
            if (!trigger) return false;

            const combobox = getCombobox(trigger);
            if (!combobox || combobox.getAttribute("aria-expanded") !== "true") {
              return false;
            }

            trigger.dataset.diForceClose = "1";
            event.preventDefault();
            event.stopPropagation();

            combobox.dispatchEvent(
              new KeyboardEvent("keydown", {
                key: "Escape",
                code: "Escape",
                keyCode: 27,
                which: 27,
                bubbles: true,
              })
            );
            combobox.blur();

            window.setTimeout(() => {
              delete trigger.dataset.diForceClose;
            }, 140);
            return true;
          }

          parentDoc.addEventListener(
            "pointerdown",
            (event) => {
              closeIfExpanded(event);
            },
            true
          );

          parentDoc.addEventListener(
            "click",
            (event) => {
              const trigger = getTrigger(event.target);
              if (!trigger) return;

              if (trigger.dataset.diForceClose === "1" || closeIfExpanded(event)) {
                event.preventDefault();
                event.stopPropagation();
              }
            },
            true
          );
        }
        </script>
        """,
        height=0,
        width=0,
    )


_inject_app_theme()


def load_data():
    """Load and validate data."""
    data_dir = Path(__file__).parent / "data" / "sample"
    data, validation_results = load_and_validate_data(data_dir)
    st.session_state.data = data
    st.session_state.validation_results = validation_results


def _get_data_date_bounds(data: dict):
    """Find the earliest and latest meaningful dates in the loaded data."""
    candidates = []
    for table_name, column_name in [
        ("time_entries", "date"),
        ("invoices", "invoice_date"),
        ("invoices", "payment_date"),
        ("expenses", "date"),
    ]:
        df = data.get(table_name)
        if df is not None and column_name in df.columns and df[column_name].notna().any():
            candidates.append(pd.to_datetime(df[column_name]).min())
            candidates.append(pd.to_datetime(df[column_name]).max())

    if not candidates:
        return None, None
    return min(candidates), max(candidates)


def _build_metrics_outputs(data: dict, start_date_ts=None, end_date_ts=None):
    """Compute the canonical metrics bundle for the current view."""
    return compute_metrics_bundle(
        data,
        st.session_state.starting_cash,
        as_of_date=end_date_ts,
        date_window={"start_date": start_date_ts, "end_date": end_date_ts},
    )


def _render_sidebar_shell(available_pages: list[str]):
    """Render the native Streamlit sidebar and return the active page plus main container."""
    if st.session_state.current_page not in available_pages:
        st.session_state.current_page = available_pages[0]

    with st.sidebar:
        st.markdown(
            """
            <div class="di-sidebar-brand">
                <div class="di-sidebar-eyebrow">Decision Infrastructure</div>
                <div class="di-sidebar-title">Validated operating metrics</div>
                <div class="di-sidebar-copy">
                    Revenue, margin, cash, runway, and explanation surfaces grounded in validated source data.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="di-sidebar-section">Navigation</div>',
            unsafe_allow_html=True,
        )
        for page_name in available_pages:
            button_type = "primary" if st.session_state.current_page == page_name else "secondary"
            if st.button(page_name, key=f"nav_{page_name}", type=button_type, use_container_width=True):
                st.session_state.current_page = page_name
                st.rerun()

        st.markdown('<div class="di-sidebar-section">Financial Context</div>', unsafe_allow_html=True)
        st.markdown('<div class="di-sidebar-field-label">Starting cash baseline</div>', unsafe_allow_html=True)
        st.session_state.starting_cash = st.number_input(
            "Starting Cash (EUR)",
            min_value=0.0,
            value=st.session_state.starting_cash,
            step=1000.0,
            label_visibility="collapsed",
            key="starting_cash_sidebar",
        )
        st.markdown(
            '<div class="di-sidebar-note">Used for deterministic runway and ending-cash calculations.</div>',
            unsafe_allow_html=True,
        )

        if st.session_state.data is not None and st.session_state.validation_results is not None:
            sidebar_overview = get_data_quality_overview(st.session_state.data, st.session_state.validation_results)
            status_class = "ready" if sidebar_overview["status"] == "ready" else ("caution" if sidebar_overview["status"] == "caution" else "blocked")
            sidebar_trust_color = _trust_score_color(sidebar_overview["trust_score"])
            sidebar_meter_style = _trust_meter_fill_style(sidebar_overview["trust_score"])
            st.markdown(
                f"""
                <div class="di-sidebar-trust">
                    <div class="di-sidebar-section" style="margin-top:0; margin-bottom:0.45rem;">Trust Snapshot</div>
                    <div class="di-sidebar-trust-top">
                        <div class="di-sidebar-trust-score" style="color:{sidebar_trust_color};">{sidebar_overview['trust_score']}%</div>
                        <div class="di-sidebar-trust-label" style="color:{sidebar_trust_color};">{sidebar_overview['trust_label']}</div>
                    </div>
                    <div class="di-meter-track">
                        <div class="di-meter-fill {status_class}" style="width:{sidebar_overview['trust_score']}%; {sidebar_meter_style}"></div>
                    </div>
                    <div class="di-sidebar-trust-copy">
                        As of {_format_display_date(sidebar_overview['as_of_date'])}<br/>
                        Coverage {_format_coverage_window(sidebar_overview['coverage_start'], sidebar_overview['coverage_end'])}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.caption("Validated inputs, deterministic calculations, and explicit caveats set the trust level for every output.")

    return st.session_state.current_page, st.container()


def _render_data_quality_banner(data: dict, validation_results: dict, metrics_outputs: dict | None = None):
    """Render a premium trust banner above computed outputs."""
    if not data or not validation_results:
        return

    as_of_date = None
    if metrics_outputs is not None:
        as_of_date = metrics_outputs.get("filters", {}).get("as_of_date")

    overview = get_data_quality_overview(data, validation_results, as_of_date=as_of_date)
    status = overview["status"]

    status_class = "ready" if status == "ready" else ("caution" if status == "caution" else "blocked")
    trust_color = _trust_score_color(overview["trust_score"])
    meter_fill_style = _trust_meter_fill_style(overview["trust_score"])
    as_of_display = _format_display_date(overview["as_of_date"])
    coverage_display = _format_coverage_window(overview["coverage_start"], overview["coverage_end"])
    freshness_days = [row["freshness_days"] for row in overview["datasets"] if row["freshness_days"] is not None]
    freshness_display = f"{max(freshness_days)} day lag" if freshness_days else "Fully current"
    blocking_issue_markup = _build_issue_list_markup(
        overview.get("blocking_error_messages", []),
        "No blocking errors are currently reducing trust.",
    )
    warning_issue_markup = _build_issue_list_markup(
        overview.get("warning_messages", []),
        "No warnings are currently reducing trust.",
    )
    trust_driver_markup = _build_issue_list_markup(
        overview.get("main_factors", []),
        "No material trust deductions were detected.",
        max_items=4,
    )
    trust_meta_markup = ""
    if overview.get("cap_reason"):
        trust_meta_markup = (
            '<div class="di-trust-meta">'
            '<div class="di-trust-meta-title">Why the displayed trust is capped</div>'
            f'<div class="di-trust-meta-copy">Underlying weighted data quality is {overview.get("uncapped_trust_score", overview["trust_score"])}%. '
            f'{escape(str(overview["cap_reason"]))}</div>'
            "</div>"
        )

    _render_surface_header(
        "Data Trust",
        f'Trust score {overview["trust_score"]}%. Deterministic outputs remain visible, but should be read in light of the current validation, coverage, and freshness status.',
    )
    st.markdown(
        f"""
        <div class="di-trust-banner">
            <div class="di-trust-layout">
                <div>
                    <div class="di-kpi-label">Trust Score</div>
                    <div class="di-trust-score-row">
                        <div class="di-trust-score" style="color:{trust_color};">{overview['trust_score']}%</div>
                        <div class="di-pill {status_class}" style="color:{trust_color}; border-color:{trust_color}33;">{overview['trust_label']}</div>
                    </div>
                    <div class="di-meter-track">
                        <div class="di-meter-fill {status_class}" style="width:{overview['trust_score']}%; {meter_fill_style}"></div>
                    </div>
                    <div class="di-trust-message">
                        {overview["message"]} Deterministic calculations remain visible, but they should be read in light of the current validation, coverage, and freshness status.
                    </div>
                    {trust_meta_markup}
                </div>
                <div class="di-trust-stats">
                    <div class="di-stat-card">
                        <div class="di-stat-label">Blocking Errors</div>
                        <div class="di-stat-value">{overview['blocking_error_count']}</div>
                        <div class="di-stat-detail">Issues that can make outputs incomplete or unreliable.</div>
                        {blocking_issue_markup}
                    </div>
                    <div class="di-stat-card">
                        <div class="di-stat-label">Warnings</div>
                        <div class="di-stat-value">{overview['warning_count']}</div>
                        <div class="di-stat-detail">Inputs worth reviewing before using outputs with confidence.</div>
                        {warning_issue_markup}
                    </div>
                    <div class="di-stat-card">
                        <div class="di-stat-label">As-of Date</div>
                        <div class="di-stat-value">{as_of_display}</div>
                        <div class="di-stat-detail">Deterministic statements are computed against this effective date.</div>
                    </div>
                    <div class="di-stat-card">
                        <div class="di-stat-label">Coverage Window</div>
                        <div class="di-stat-value">{coverage_display}</div>
                        <div class="di-stat-detail">{freshness_display} across the dated input tables.</div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_layout_gap("content")
    coverage_rows = []
    for dataset in overview["datasets"]:
        coverage_rows.append(
            {
                "Dataset": dataset["dataset"].replace("_", " ").title(),
                "Weight": f"{dataset.get('weight', 0)}%",
                "Dataset Trust": f"{dataset.get('dataset_score', 0)}%",
                "Rows": dataset["row_count"],
                "Coverage": _format_coverage_window(dataset["coverage_start"], dataset["coverage_end"]),
                "Freshness Lag": dataset["freshness_days"] if dataset["freshness_days"] is not None else "N/A",
                "Freshness Target": (
                    f"{dataset['freshness_target_days']} days"
                    if dataset.get("freshness_target_days") is not None
                    else "N/A"
                ),
                "Completeness Penalty": f"{dataset.get('completeness_penalty', 0):.0f}",
                "Validity Penalty": f"{dataset.get('validity_penalty', 0):.0f}",
                "Freshness Penalty": f"{dataset.get('freshness_penalty', 0):.0f}",
                "Primary Driver": dataset.get("top_factor", "No material trust deductions."),
            }
        )
    coverage_table_markup = _build_modern_table_markup(pd.DataFrame(coverage_rows))
    st.markdown(
        f"""
        <div class="di-dropdown-shell">
            <details>
                <summary>Dataset Coverage &amp; Freshness</summary>
                <div>
                    <div>
                        <div class="di-dropdown-meta-grid">
                            <div class="di-dropdown-meta-card">
                                <div class="di-dropdown-meta-label">Displayed Trust</div>
                                <div class="di-dropdown-meta-value">{overview['trust_score']}%</div>
                                <div class="di-dropdown-meta-copy">{escape(str(overview['trust_label']))}. {escape(str(overview['message']))}</div>
                            </div>
                            <div class="di-dropdown-meta-card">
                                <div class="di-dropdown-meta-label">Underlying Dataset Quality</div>
                                <div class="di-dropdown-meta-value">{overview.get('uncapped_trust_score', overview['trust_score'])}%</div>
                                <div class="di-dropdown-meta-copy">{escape(str(overview.get('cap_reason') or 'No validation cap is currently applied.'))}</div>
                            </div>
                        </div>
                        <div class="di-dropdown-meta-card" style="margin-bottom:0.8rem;">
                            <div class="di-dropdown-meta-label">Main Trust Drivers</div>
                            {trust_driver_markup}
                        </div>
                        {coverage_table_markup}
                        <div class="di-dropdown-caption">
                            Deterministic outputs are only as trustworthy as the loaded CSV coverage, validation status, and freshness of the transactional datasets. Each dataset score above feeds the weighted trust model directly.
                        </div>
                    </div>
                </div>
            </details>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return overview


def _get_cached_insights(metrics_outputs: dict, data: dict):
    """Build deterministic insights once per metrics bundle."""
    cache_key = metrics_outputs.get("cache_key", "default")
    if st.session_state.get("overview_insights_cache_key") != cache_key:
        st.session_state.overview_insights = generate_insights(
            projects_metrics=metrics_outputs.get("projects_metrics"),
            projects_metrics_monthly=metrics_outputs.get("projects_metrics_monthly"),
            employee_utilization=metrics_outputs.get("employee_utilization"),
            income_statement_monthly=metrics_outputs.get("income_statement_monthly"),
            cashflow_monthly=metrics_outputs.get("cashflow_monthly"),
            invoices=data.get("invoices"),
            as_of_date=metrics_outputs.get("filters", {}).get("as_of_date"),
        )
        st.session_state.overview_insights_cache_key = cache_key
    return st.session_state.get("overview_insights", [])


def _render_insight_card(insight: dict):
    severity = escape(str(insight.get("severity", "info")))
    drivers = insight.get("drivers", [])
    driver_text = " ".join(drivers[:2]) if drivers else "Derived directly from the current deterministic metrics bundle."
    card_markup = (
        f'<div class="di-insight-card">'
        f'<div class="di-insight-topline">'
        f'<div class="di-insight-entity">{escape(str(insight.get("entity", "Company")))}</div>'
        f'<div class="di-severity-pill {severity}">{severity}</div>'
        f'</div>'
        f'<div class="di-insight-message">{escape(str(insight.get("message", "No insight available.")))}</div>'
        f'<div class="di-insight-driver">{escape(driver_text)}</div>'
        f'</div>'
    )
    st.markdown(card_markup, unsafe_allow_html=True)


def _render_overview_page():
    """Render the refined overview page."""
    if st.session_state.data is None:
        st.error("No data loaded. Please check Data Quality page.")
        return

    data = st.session_state.data
    _render_page_shell("Overview Dashboard")

    min_date, max_date = _get_data_date_bounds(data)
    if min_date is not None and max_date is not None:
        _open_surface()
        _render_surface_header("Reporting window", "Select the deterministic period used for the operating view below.")
        col1, col2 = st.columns(2, gap="large")
        with col1:
            start_date = st.date_input("Start Date", value=min_date.date())
        with col2:
            end_date = st.date_input("End Date", value=max_date.date())
        _close_surface()
        start_date_ts = pd.Timestamp(start_date)
        end_date_ts = pd.Timestamp(end_date)
    else:
        start_date_ts = None
        end_date_ts = None

    _render_layout_gap("section")
    metrics_outputs = _build_metrics_outputs(data, start_date_ts, end_date_ts)
    overview = _render_data_quality_banner(data, st.session_state.validation_results, metrics_outputs)
    _render_layout_gap("section")
    insights_list = _get_cached_insights(metrics_outputs, data)

    income_stmt = metrics_outputs["income_statement_monthly"]
    cashflow_stmt = metrics_outputs["cashflow_monthly"]
    project_metrics = metrics_outputs["projects_metrics"]
    monthly_income = income_stmt[income_stmt["month"] != "Total"]
    monthly_cashflow = cashflow_stmt[cashflow_stmt["month"] != "Total"]

    total_revenue = income_stmt[income_stmt["month"] == "Total"]["revenue"].iloc[0]
    total_gross_profit = income_stmt[income_stmt["month"] == "Total"]["gross_profit"].iloc[0]
    gross_margin = (total_gross_profit / total_revenue * 100) if total_revenue > 0 else 0
    ebitda = income_stmt[income_stmt["month"] == "Total"]["ebitda"].iloc[0]
    cash_collected = cashflow_stmt[cashflow_stmt["month"] == "Total"]["cash_in"].iloc[0]
    ending_cash = monthly_cashflow["ending_cash"].iloc[-1] if len(monthly_cashflow) > 0 else st.session_state.starting_cash
    runway = compute_runway(cashflow_stmt, st.session_state.starting_cash)
    runway_display = f"{runway:.1f} months" if runway != float("inf") else "Sustained"

    _open_surface()
    _render_surface_header(
        "Current operating picture",
        f"Trust score {overview['trust_score']}%. All figures below are deterministic and aligned to the selected reporting window.",
    )
    kpi_cards = [
        ("Total Revenue", f"EUR {total_revenue:,.0f}", "Accrual-basis revenue across the selected window.", "accent"),
        ("Gross Profit", f"EUR {total_gross_profit:,.0f}", f"{gross_margin:.1f}% gross margin.", "good" if gross_margin >= 30 else "caution"),
        ("EBITDA", f"EUR {ebitda:,.0f}", "Operating profit after overhead, before financing and taxes.", "good" if ebitda >= 0 else "danger"),
        ("Cash Collected", f"EUR {cash_collected:,.0f}", "Cash received over the selected reporting window.", "accent"),
        ("Ending Cash Balance", f"EUR {ending_cash:,.0f}", f"Starting from EUR {st.session_state.starting_cash:,.0f}.", "good" if ending_cash >= 0 else "danger"),
        ("Runway", runway_display, "Months of remaining runway at the current net cash profile.", "accent" if runway == float('inf') or runway >= 6 else "caution"),
    ]
    _render_kpi_grid(kpi_cards)
    _close_surface()

    _render_layout_gap("section")
    _open_surface()
    _render_surface_header(
        "Short insights summary",
        "Highest-priority deterministic signals from the current projects, people, company, and invoice data.",
    )
    if insights_list:
        ranked_insights = sorted(
            insights_list,
            key=lambda item: {"critical": 0, "warning": 1, "info": 2}.get(item.get("severity"), 3),
        )[:3]
        _render_insight_grid(ranked_insights)
    else:
        st.info("No material deterministic insights were generated for the current reporting window.")
    _close_surface()

    _render_layout_gap("section")
    monthly_income_display = monthly_income.copy()
    monthly_income_display["month"] = monthly_income_display["month"].astype(str)

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=monthly_income_display["month"], y=monthly_income_display["revenue"], mode="lines", name="Revenue", line=dict(color="#36d39b", width=1.9)))
    fig1.add_trace(go.Scatter(x=monthly_income_display["month"], y=monthly_income_display["cogs"], mode="lines", name="COGS", line=dict(color="#ff7d6d", width=1.8)))
    fig1.add_trace(go.Scatter(x=monthly_income_display["month"], y=monthly_income_display["ebitda"], mode="lines", name="EBITDA", line=dict(color="#f3c86d", width=1.95)))
    fig1.update_layout(xaxis_title="Month", yaxis_title="EUR", hovermode="x unified")
    _apply_chart_theme(fig1)

    monthly_cashflow_display = monthly_cashflow.copy()
    monthly_cashflow_display["month"] = monthly_cashflow_display["month"].astype(str)
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=monthly_cashflow_display["month"], y=monthly_cashflow_display["cash_in"], name="Cash In", marker_color="#36d39b"))
    fig2.add_trace(go.Bar(x=monthly_cashflow_display["month"], y=-monthly_cashflow_display["cash_out_total"], name="Cash Out", marker_color="#ff8f73"))
    fig2.add_trace(go.Scatter(x=monthly_cashflow_display["month"], y=monthly_cashflow_display["ending_cash"], mode="lines", name="Ending Cash", line=dict(color="#85baff", width=1.95)))
    fig2.update_layout(xaxis_title="Month", yaxis_title="EUR", barmode="group", bargap=0.26, hovermode="x unified")
    _apply_chart_theme(fig2)

    chart_col1, chart_col2 = st.columns([1.08, 0.92], gap="large")
    with chart_col1:
        _open_surface()
        _render_surface_header("Revenue, COGS, and EBITDA", "Accrual performance across the current reporting window.")
        st.plotly_chart(fig1, use_container_width=True)
        _close_surface()
    with chart_col2:
        _open_surface()
        _render_surface_header("Cash movement and ending balance", "Cash receipts, cash outflows, and ending cash over time.")
        st.plotly_chart(fig2, use_container_width=True)
        _close_surface()

    _render_layout_gap("section")
    table_col1, table_col2 = st.columns(2, gap="large")
    with table_col1:
        _open_surface()
        _render_surface_header("Top projects by gross profit", "Projects contributing the most gross profit in the selected period.")
        top_projects = (
            project_metrics.nlargest(10, "gross_profit")[["project_id", "revenue", "gross_profit", "gross_margin_pct"]]
            .rename(columns={"project_id": "Project", "revenue": "Revenue", "gross_profit": "Gross Profit", "gross_margin_pct": "Gross Margin"})
        )
        _render_modern_table(
            top_projects,
            formatters={
                "Revenue": lambda value: f"EUR {value:,.0f}",
                "Gross Profit": lambda value: f"EUR {value:,.0f}",
                "Gross Margin": lambda value: f"{value:.1%}",
            },
        )
        _close_surface()
    with table_col2:
        _open_surface()
        _render_surface_header("Bottom projects by gross margin", "The weakest-margin projects that deserve immediate review.")
        bottom_projects = (
            project_metrics.nsmallest(10, "gross_margin_pct")[["project_id", "revenue", "gross_profit", "gross_margin_pct"]]
            .rename(columns={"project_id": "Project", "revenue": "Revenue", "gross_profit": "Gross Profit", "gross_margin_pct": "Gross Margin"})
        )
        _render_modern_table(
            bottom_projects,
            formatters={
                "Revenue": lambda value: f"EUR {value:,.0f}",
                "Gross Profit": lambda value: f"EUR {value:,.0f}",
                "Gross Margin": lambda value: f"{value:.1%}",
            },
        )
        _close_surface()


# Load data on first run
if st.session_state.data is None:
    load_data()


def page_overview():
    """Overview Dashboard page."""
    _render_overview_page()
    return
    """
    st.title("📊 Overview Dashboard")
    
    if st.session_state.data is None:
        st.error("No data loaded. Please check Data Quality page.")
        return
    
    data = st.session_state.data
    _render_page_shell("Overview Dashboard")
    
    min_date, max_date = _get_data_date_bounds(data)
    if min_date is not None and max_date is not None:
        _render_section_label("Analysis Window")
        _open_surface()
        _render_surface_header(
            "Reporting window",
            "Select the deterministic period used for the operating view below.",
        )
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", value=min_date.date())
        with col2:
            end_date = st.date_input("End Date", value=max_date.date())
        _close_surface()
        
        start_date_ts = pd.Timestamp(start_date)
        end_date_ts = pd.Timestamp(end_date)
    else:
        start_date_ts = None
        end_date_ts = None

    metrics_outputs = _build_metrics_outputs(data, start_date_ts, end_date_ts)
    overview = _render_data_quality_banner(data, st.session_state.validation_results, metrics_outputs)
    st.markdown("<style>[data-testid='stMetric'] { display: none; }</style>", unsafe_allow_html=True)
    income_stmt = metrics_outputs["income_statement_monthly"]
    cashflow_stmt = metrics_outputs["cashflow_monthly"]
    project_metrics = metrics_outputs["projects_metrics"]
    
    _render_section_label("Operating Snapshot")
    monthly_income = income_stmt[income_stmt["month"] != "Total"]
    monthly_cashflow = cashflow_stmt[cashflow_stmt["month"] != "Total"]
    total_revenue = income_stmt[income_stmt["month"] == "Total"]["revenue"].iloc[0]
    total_gross_profit = income_stmt[income_stmt["month"] == "Total"]["gross_profit"].iloc[0]
    gross_margin = (total_gross_profit / total_revenue * 100) if total_revenue > 0 else 0
    ebitda = income_stmt[income_stmt["month"] == "Total"]["ebitda"].iloc[0]
    cash_collected = cashflow_stmt[cashflow_stmt["month"] == "Total"]["cash_in"].iloc[0]
    ending_cash = monthly_cashflow["ending_cash"].iloc[-1] if len(monthly_cashflow) > 0 else st.session_state.starting_cash
    runway = compute_runway(cashflow_stmt, st.session_state.starting_cash)
    runway_display = f"{runway:.1f} months" if runway != float("inf") else "Sustained"
    
    _open_surface()
    _render_surface_header(
        "Current operating picture",
        f"Trust score {overview['trust_score']}%. The outputs below remain deterministic even when trust is lowered by validation or coverage issues.",
    )
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        _render_kpi_card("Total Revenue", f"EUR {total_revenue:,.0f}", "Accrual-basis revenue across the selected window.", tone="accent")
        total_revenue = income_stmt[income_stmt["month"] == "Total"]["revenue"].iloc[0]
        st.metric("Total Revenue (Accrual)", f"€{total_revenue:,.0f}")
    with col2:
        _render_kpi_card("Gross Profit", f"EUR {total_gross_profit:,.0f}", f"{gross_margin:.1f}% gross margin.", tone="good" if gross_margin >= 30 else "caution")
        total_gross_profit = income_stmt[income_stmt["month"] == "Total"]["gross_profit"].iloc[0]
        gross_margin = (total_gross_profit / total_revenue * 100) if total_revenue > 0 else 0
        st.metric("Gross Profit", f"€{total_gross_profit:,.0f}", f"{gross_margin:.1f}%")
    with col3:
        _render_kpi_card("EBITDA", f"EUR {ebitda:,.0f}", "Operating profit after overhead, before financing and taxes.", tone="good" if ebitda >= 0 else "danger")
        ebitda = income_stmt[income_stmt["month"] == "Total"]["ebitda"].iloc[0]
        st.metric("EBITDA", f"€{ebitda:,.0f}")
    with col4:
        _render_kpi_card("Cash Collected", f"EUR {cash_collected:,.0f}", "Cash received over the selected reporting window.", tone="accent")
        cash_collected = cashflow_stmt[cashflow_stmt["month"] == "Total"]["cash_in"].iloc[0]
        st.metric("Cash Collected", f"€{cash_collected:,.0f}")
    
    col1, col2 = st.columns(2)
    with col1:
        _render_kpi_card("Ending Cash Balance", f"EUR {ending_cash:,.0f}", f"Starting from EUR {st.session_state.starting_cash:,.0f}.", tone="good" if ending_cash >= 0 else "danger")
        ending_cash = monthly_cashflow["ending_cash"].iloc[-1] if len(monthly_cashflow) > 0 else st.session_state.starting_cash
        st.metric("Ending Cash Balance", f"€{ending_cash:,.0f}")
    with col2:
        _render_kpi_card("Runway", runway_display, "Months of remaining runway at the current net cash profile.", tone="accent" if runway == float("inf") or runway >= 6 else "caution")
        runway = compute_runway(cashflow_stmt, st.session_state.starting_cash)
        runway_display = f"{runway:.1f}" if runway != float('inf') else "∞"
        st.metric("Runway (months)", runway_display)
    
    _close_surface()

    _render_section_label("Financial Trends")
    monthly_income_display = monthly_income.copy()
    monthly_income_display["month"] = monthly_income_display["month"].astype(str)
    
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=monthly_income_display["month"], y=monthly_income_display["revenue"],
                              mode='lines+markers', name='Revenue', line=dict(color='#7ec6a4', width=2.8)))
    fig1.add_trace(go.Scatter(x=monthly_income_display["month"], y=monthly_income_display["cogs"],
                              mode='lines+markers', name='COGS', line=dict(color='#d77a7a', width=2.6)))
    fig1.add_trace(go.Scatter(x=monthly_income_display["month"], y=monthly_income_display["ebitda"],
                              mode='lines+markers', name='EBITDA', line=dict(color='#d9c7a2', width=2.8)))
    fig1.update_layout(xaxis_title="Month", yaxis_title="EUR",
                      hovermode='x unified')
    _apply_chart_theme(fig1)

    monthly_cashflow_display = monthly_cashflow.copy()
    monthly_cashflow_display["month"] = monthly_cashflow_display["month"].astype(str)
    
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=monthly_cashflow_display["month"], y=monthly_cashflow_display["cash_in"],
                         name='Cash In', marker_color='#7ec6a4'))
    fig2.add_trace(go.Bar(x=monthly_cashflow_display["month"], y=-monthly_cashflow_display["cash_out_total"],
                         name='Cash Out', marker_color='#d77a7a'))
    fig2.add_trace(go.Scatter(x=monthly_cashflow_display["month"], y=monthly_cashflow_display["ending_cash"],
                             mode='lines+markers', name='Ending Cash', line=dict(color='#b7bcc6', width=3)))
    fig2.update_layout(xaxis_title="Month", yaxis_title="EUR",
                      barmode='group', hovermode='x unified')
    _apply_chart_theme(fig2)

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        _open_surface()
        _render_surface_header("Revenue, COGS, and EBITDA", "Accrual performance across the current reporting window.")
        st.plotly_chart(fig1, use_container_width=True)
        _close_surface()
    with chart_col2:
        _open_surface()
        _render_surface_header("Cash movement and ending balance", "Cash receipts, cash outflows, and ending cash over time.")
        st.plotly_chart(fig2, use_container_width=True)
        _close_surface()

    _render_section_label("Project Distribution")
    col1, col2 = st.columns(2)
    with col1:
        _render_surface_header("Top projects by gross profit", "Projects contributing the most gross profit in the selected period.")
        top_projects = project_metrics.nlargest(10, "gross_profit")[
            ["project_id", "revenue", "gross_profit", "gross_margin_pct"]
        ]
        st.dataframe(top_projects.style.format({
            "revenue": "€{:,.0f}",
            "gross_profit": "€{:,.0f}",
            "gross_margin_pct": "{:.1%}"
        }), use_container_width=True)
    
    with col2:
        _render_surface_header("Bottom projects by gross margin", "The weakest-margin projects that deserve immediate review.")
        bottom_projects = project_metrics.nsmallest(10, "gross_margin_pct")[
            ["project_id", "revenue", "gross_profit", "gross_margin_pct"]
        ]
        st.dataframe(bottom_projects.style.format({
            "revenue": "€{:,.0f}",
            "gross_profit": "€{:,.0f}",
            "gross_margin_pct": "{:.1%}"
        }), use_container_width=True)
    """


def page_projects():
    """Projects page - Refactored for decision-oriented UX."""
    if st.session_state.data is None:
        st.error("No data loaded.")
        return
    
    data = st.session_state.data
    _render_page_shell("Projects")
    metrics_outputs = _build_metrics_outputs(data)
    _render_data_quality_banner(data, st.session_state.validation_results, metrics_outputs)
    _render_layout_gap("section")
    projects_metrics = metrics_outputs["projects_metrics"]
    
    # Render the refactored projects page
    render_projects_page(data, projects_metrics)


def page_people():
    """People/Utilization page."""
    if st.session_state.data is None:
        st.error("No data loaded.")
        return
    
    data = st.session_state.data
    _render_page_shell("People")
    employees = data["employees"]
    time_entries = data["time_entries"]
    metrics_outputs = _build_metrics_outputs(data)
    _render_data_quality_banner(data, st.session_state.validation_results, metrics_outputs)
    _render_layout_gap("section")
    emp_utilization = metrics_outputs["employee_utilization"]
    
    # Merge with employee details
    emp_display = employees.merge(emp_utilization, on="employee_id", how="left")
    
    # Display table
    st.subheader("Employee Utilization")
    display_cols = ["employee_id", "job_title", "department", "utilization_pct",
                    "billable_hours", "internal_hours", "cost_of_time"]
    
    available_cols = [col for col in display_cols if col in emp_display.columns]
    st.dataframe(
        emp_display[available_cols].style.format({
            "utilization_pct": "{:.1%}",
            "billable_hours": "{:.1f}",
            "internal_hours": "{:.1f}",
            "cost_of_time": "€{:,.0f}"
        }),
        use_container_width=True,
        height=400
    )
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Utilization Distribution")
        fig1 = px.histogram(emp_display, x="utilization_pct", nbins=20,
                           title="Distribution of Utilization %",
                           labels={"utilization_pct": "Utilization %", "count": "Number of Employees"})
        fig1.update_traces(marker_color="#f3c86d")
        _apply_chart_theme(fig1)
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        st.subheader("Utilization Status")
        underutilized = len(emp_display[emp_display["utilization_pct"] < UNDERUTILIZED_THRESHOLD])
        optimal = len(emp_display[
            (emp_display["utilization_pct"] >= UNDERUTILIZED_THRESHOLD) &
            (emp_display["utilization_pct"] <= OVERUTILIZED_THRESHOLD)
        ])
        overutilized = len(emp_display[emp_display["utilization_pct"] > OVERUTILIZED_THRESHOLD])
        
        fig2 = go.Figure(data=[go.Bar(
            x=["Underutilized (<60%)", "Optimal (60-85%)", "Overutilized (>85%)"],
            y=[underutilized, optimal, overutilized],
            marker_color=['#ff7d6d', '#36d39b', '#f3c86d']
        )])
        fig2.update_layout(title="Utilization Status", yaxis_title="Number of Employees")
        _apply_chart_theme(fig2)
        st.plotly_chart(fig2, use_container_width=True)
    
    # Billable vs Non-billable over time
    st.subheader("Billable vs Non-billable Hours Over Time")
    emp_monthly = compute_employee_utilization(time_entries, employees, by_month=True)
    
    if len(emp_monthly) > 0:
        monthly_agg = emp_monthly.groupby("month").agg({
            "billable_hours": "sum",
            "non_billable_hours": "sum"
        }).reset_index()
        monthly_agg["month"] = monthly_agg["month"].astype(str)
        
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(x=monthly_agg["month"], y=monthly_agg["billable_hours"],
                             name='Billable', marker_color='#36d39b'))
        fig3.add_trace(go.Bar(x=monthly_agg["month"], y=monthly_agg["non_billable_hours"],
                             name='Non-billable', marker_color='#ff7d6d'))
        fig3.update_layout(title="Billable vs Non-billable Hours by Month",
                          xaxis_title="Month", yaxis_title="Hours",
                          barmode='stack')
        _apply_chart_theme(fig3)
        st.plotly_chart(fig3, use_container_width=True)
    
    # Identify underutilized and overutilized
    st.subheader("Utilization Alerts")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Underutilized Employees (<60%)**")
        underutilized_emps = emp_display[emp_display["utilization_pct"] < UNDERUTILIZED_THRESHOLD][
            ["employee_id", "job_title", "department", "utilization_pct", "billable_hours"]
        ]
        if len(underutilized_emps) > 0:
            st.dataframe(
                underutilized_emps.style.format({
                    "utilization_pct": "{:.1%}",
                    "billable_hours": "{:.1f}"
                }),
                use_container_width=True
            )
        else:
            st.info("No underutilized employees.")
    
    with col2:
        st.write("**Overutilized Employees (>85%)**")
        overutilized_emps = emp_display[emp_display["utilization_pct"] > OVERUTILIZED_THRESHOLD][
            ["employee_id", "job_title", "department", "utilization_pct", "billable_hours"]
        ]
        if len(overutilized_emps) > 0:
            st.dataframe(
                overutilized_emps.style.format({
                    "utilization_pct": "{:.1%}",
                    "billable_hours": "{:.1f}"
                }),
                use_container_width=True
            )
        else:
            st.info("No overutilized employees.")


def page_financial_statements():
    """Financial Statements page."""
    if st.session_state.data is None:
        st.error("No data loaded.")
        return
    
    data = st.session_state.data
    _render_page_shell("Financial Statements")
    time_entries = data["time_entries"]
    invoices = data["invoices"]
    expenses = data["expenses"]
    employees = data["employees"]
    
    min_date, max_date = _get_data_date_bounds(data)
    if min_date is not None and max_date is not None:
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", value=min_date.date(), key="fs_start")
        with col2:
            end_date = st.date_input("End Date", value=max_date.date(), key="fs_end")
        
        start_date_ts = pd.Timestamp(start_date)
        end_date_ts = pd.Timestamp(end_date)
    else:
        start_date_ts = None
        end_date_ts = None
    
    # Tabs
    tab1, tab2 = st.tabs(["Income Statement", "Cashflow Statement"])
    metrics_outputs = _build_metrics_outputs(data, start_date_ts, end_date_ts)
    _render_data_quality_banner(data, st.session_state.validation_results, metrics_outputs)
    _render_layout_gap("section")
    
    with tab1:
        st.subheader("Income Statement (Accrual Basis)")
        income_stmt = metrics_outputs["income_statement_monthly"]
        
        st.dataframe(
            income_stmt.style.format({
                "revenue": "€{:,.0f}",
                "direct_labor_cost": "€{:,.0f}",
                "direct_allocated_expenses": "€{:,.0f}",
                "cogs": "€{:,.0f}",
                "gross_profit": "€{:,.0f}",
                "overhead_labor_cost": "€{:,.0f}",
                "overhead_expenses": "€{:,.0f}",
                "operating_expenses": "€{:,.0f}",
                "ebitda": "€{:,.0f}"
            }),
            use_container_width=True
        )
        
        # Download button
        csv = income_stmt.to_csv(index=False)
        st.download_button(
            label="Download Income Statement as CSV",
            data=csv,
            file_name="income_statement.csv",
            mime="text/csv"
        )
    
    with tab2:
        st.subheader("Cashflow Statement (Cash Basis)")
        cashflow_stmt = metrics_outputs["cashflow_monthly"]
        
        st.dataframe(
            cashflow_stmt.style.format({
                "cash_in": "€{:,.0f}",
                "cash_out_payroll": "€{:,.0f}",
                "cash_out_expenses": "€{:,.0f}",
                "cash_out_total": "€{:,.0f}",
                "net_cashflow": "€{:,.0f}",
                "ending_cash": "€{:,.0f}"
            }),
            use_container_width=True
        )
        
        # Download button
        csv = cashflow_stmt.to_csv(index=False)
        st.download_button(
            label="Download Cashflow Statement as CSV",
            data=csv,
            file_name="cashflow_statement.csv",
            mime="text/csv"
        )


def page_data_quality():
    """Data Quality page."""
    validation_results = st.session_state.validation_results
    data = st.session_state.data
    
    _render_page_shell("Data Quality")
    if validation_results is None:
        st.warning("No validation results available.")
        return

    overview = get_data_quality_overview(data or {}, validation_results)
    _render_data_quality_banner(data or {}, validation_results)
    _render_layout_gap("section")

    st.subheader("Validation Status")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Blocking Errors")
        errors = validation_results.get("errors", [])
        if errors:
            st.error(f"**{len(errors)} error(s) found:**")
            for error in errors:
                st.write(f"- {error}")
        else:
            st.success("✅ No errors found!")
    
    with col2:
        st.subheader("Warnings")
        warnings = validation_results.get("warnings", [])
        if warnings:
            st.warning(f"**{len(warnings)} warning(s) found:**")
            for warning in warnings:
                st.write(f"- {warning}")
        else:
            st.info("ℹ️ No warnings.")
    
    st.subheader("Coverage Summary")
    st.write(f"As-of date: **{_format_display_date(overview['as_of_date'])}**")
    st.write(f"Overall coverage: **{_format_coverage_window(overview['coverage_start'], overview['coverage_end'])}**")

    # Data Summary
    if data:
        st.subheader("Data Summary")
        summary = get_data_summary(data)
        
        for name, info in summary.items():
            with st.expander(f"{name.upper()} ({info['row_count']} rows)"):
                st.write(f"**Columns:** {', '.join(info['columns'])}")
                if info['date_range']:
                    st.write("**Date Ranges:**")
                    for col, date_range in info['date_range'].items():
                        st.write(f"- {col}: {date_range['min']} to {date_range['max']}")
    
    # Reload button
    if st.button("Reload Data"):
        load_data()
        st.rerun()


def page_briefs():
    """Weekly Brief page."""
    if st.session_state.data is None:
        st.warning("⚠️ Please upload data on the Data Quality page first.")
        return
    
    data = st.session_state.data
    
    try:
        _render_page_shell("Weekly Brief")
        metrics_outputs = _build_metrics_outputs(data)
        _render_data_quality_banner(data, st.session_state.validation_results, metrics_outputs)
        _render_layout_gap("section")
        render_briefs_tab(metrics_outputs, data, st.session_state.starting_cash)
        
    except Exception as e:
        st.error(f"Error computing metrics: {str(e)}")
        st.exception(e)


def page_insights():
    """Insights & Explanations page."""
    if st.session_state.data is None:
        st.warning("⚠️ Please upload data on the Data Quality page first.")
        return
    
    data = st.session_state.data
    try:
        _render_page_shell("Insights & Explanations")
        metrics_outputs = _build_metrics_outputs(data)
        _render_data_quality_banner(data, st.session_state.validation_results, metrics_outputs)
        _render_layout_gap("section")
        render_insights_tab(metrics_outputs, data, st.session_state.starting_cash)
        
    except Exception as e:
        st.error(f"Error computing metrics: {str(e)}")
        st.exception(e)


# Main app
def main():
    """Main app function."""
    if DEMO_MODE:
        available_pages = ["Overview Dashboard", "Projects", "Insights & Explanations"]
    else:
        available_pages = ["Overview Dashboard", "Projects", "People", "Financial Statements", "Weekly Brief", "Insights & Explanations", "Data Quality"]

    page, main_container = _render_sidebar_shell(available_pages)

    with main_container:
        if page == "Overview Dashboard":
            page_overview()
        elif page == "Projects":
            page_projects()
        elif page == "People":
            page_people()
        elif page == "Financial Statements":
            page_financial_statements()
        elif page == "Weekly Brief":
            page_briefs()
        elif page == "Insights & Explanations":
            page_insights()
        elif page == "Data Quality":
            page_data_quality()


if __name__ == "__main__":
    main()
