"""
Decision Infrastructure - Streamlit App
Main entry point for the B2B service prototype.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
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


def _render_data_quality_banner(data: dict, validation_results: dict, metrics_outputs: dict | None = None):
    """Render a compact, explicit trust banner above computed outputs."""
    if not data or not validation_results:
        return

    as_of_date = None
    if metrics_outputs is not None:
        as_of_date = metrics_outputs.get("filters", {}).get("as_of_date")

    overview = get_data_quality_overview(data, validation_results, as_of_date=as_of_date)
    status = overview["status"]

    if status == "blocked":
        st.error(overview["message"])
    elif status == "caution":
        st.warning(overview["message"])
    else:
        st.success(overview["message"])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Blocking Errors", overview["blocking_error_count"])
    with col2:
        st.metric("Warnings", overview["warning_count"])
    with col3:
        as_of_display = overview["as_of_date"].date().isoformat() if overview["as_of_date"] is not None else "N/A"
        st.metric("As-of Date", as_of_display)
    with col4:
        if overview["coverage_start"] is not None and overview["coverage_end"] is not None:
            coverage_display = (
                f"{pd.to_datetime(overview['coverage_start']).date()} -> "
                f"{pd.to_datetime(overview['coverage_end']).date()}"
            )
        else:
            coverage_display = "N/A"
        st.metric("Coverage", coverage_display)

    with st.expander("Dataset Coverage & Freshness", expanded=False):
        coverage_rows = []
        for dataset in overview["datasets"]:
            coverage_rows.append(
                {
                    "Dataset": dataset["dataset"],
                    "Rows": dataset["row_count"],
                    "Coverage Start": dataset["coverage_start"].date().isoformat() if dataset["coverage_start"] is not None else "N/A",
                    "Coverage End": dataset["coverage_end"].date().isoformat() if dataset["coverage_end"] is not None else "N/A",
                    "Freshness vs As-of (days)": dataset["freshness_days"] if dataset["freshness_days"] is not None else "N/A",
                }
            )
        st.dataframe(pd.DataFrame(coverage_rows), use_container_width=True, hide_index=True)
        st.caption("Deterministic outputs are only as trustworthy as the loaded CSV coverage and validation status.")


# Load data on first run
if st.session_state.data is None:
    load_data()


def page_overview():
    """Overview Dashboard page."""
    st.title("📊 Overview Dashboard")
    
    if st.session_state.data is None:
        st.error("No data loaded. Please check Data Quality page.")
        return
    
    data = st.session_state.data
    
    min_date, max_date = _get_data_date_bounds(data)
    if min_date is not None and max_date is not None:
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", value=min_date.date())
        with col2:
            end_date = st.date_input("End Date", value=max_date.date())
        
        start_date_ts = pd.Timestamp(start_date)
        end_date_ts = pd.Timestamp(end_date)
    else:
        start_date_ts = None
        end_date_ts = None

    metrics_outputs = _build_metrics_outputs(data, start_date_ts, end_date_ts)
    _render_data_quality_banner(data, st.session_state.validation_results, metrics_outputs)
    income_stmt = metrics_outputs["income_statement_monthly"]
    cashflow_stmt = metrics_outputs["cashflow_monthly"]
    project_metrics = metrics_outputs["projects_metrics"]
    
    # KPI Cards
    st.subheader("Key Metrics")
    monthly_income = income_stmt[income_stmt["month"] != "Total"]
    monthly_cashflow = cashflow_stmt[cashflow_stmt["month"] != "Total"]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_revenue = income_stmt[income_stmt["month"] == "Total"]["revenue"].iloc[0]
        st.metric("Total Revenue (Accrual)", f"€{total_revenue:,.0f}")
    with col2:
        total_gross_profit = income_stmt[income_stmt["month"] == "Total"]["gross_profit"].iloc[0]
        gross_margin = (total_gross_profit / total_revenue * 100) if total_revenue > 0 else 0
        st.metric("Gross Profit", f"€{total_gross_profit:,.0f}", f"{gross_margin:.1f}%")
    with col3:
        ebitda = income_stmt[income_stmt["month"] == "Total"]["ebitda"].iloc[0]
        st.metric("EBITDA", f"€{ebitda:,.0f}")
    with col4:
        cash_collected = cashflow_stmt[cashflow_stmt["month"] == "Total"]["cash_in"].iloc[0]
        st.metric("Cash Collected", f"€{cash_collected:,.0f}")
    
    col1, col2 = st.columns(2)
    with col1:
        ending_cash = monthly_cashflow["ending_cash"].iloc[-1] if len(monthly_cashflow) > 0 else st.session_state.starting_cash
        st.metric("Ending Cash Balance", f"€{ending_cash:,.0f}")
    with col2:
        runway = compute_runway(cashflow_stmt, st.session_state.starting_cash)
        runway_display = f"{runway:.1f}" if runway != float('inf') else "∞"
        st.metric("Runway (months)", runway_display)
    
    # Charts
    st.subheader("Financial Trends")
    
    # Revenue vs COGS vs EBITDA
    monthly_income_display = monthly_income.copy()
    monthly_income_display["month"] = monthly_income_display["month"].astype(str)
    
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=monthly_income_display["month"], y=monthly_income_display["revenue"],
                              mode='lines+markers', name='Revenue', line=dict(color='green')))
    fig1.add_trace(go.Scatter(x=monthly_income_display["month"], y=monthly_income_display["cogs"],
                              mode='lines+markers', name='COGS', line=dict(color='red')))
    fig1.add_trace(go.Scatter(x=monthly_income_display["month"], y=monthly_income_display["ebitda"],
                              mode='lines+markers', name='EBITDA', line=dict(color='blue')))
    fig1.update_layout(title="Revenue vs COGS vs EBITDA", xaxis_title="Month", yaxis_title="EUR",
                      hovermode='x unified')
    st.plotly_chart(fig1, use_container_width=True)
    
    # Cashflow chart
    monthly_cashflow_display = monthly_cashflow.copy()
    monthly_cashflow_display["month"] = monthly_cashflow_display["month"].astype(str)
    
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=monthly_cashflow_display["month"], y=monthly_cashflow_display["cash_in"],
                         name='Cash In', marker_color='green'))
    fig2.add_trace(go.Bar(x=monthly_cashflow_display["month"], y=-monthly_cashflow_display["cash_out_total"],
                         name='Cash Out', marker_color='red'))
    fig2.add_trace(go.Scatter(x=monthly_cashflow_display["month"], y=monthly_cashflow_display["ending_cash"],
                             mode='lines+markers', name='Ending Cash', line=dict(color='blue', width=3)))
    fig2.update_layout(title="Cashflow: In vs Out + Ending Cash", xaxis_title="Month", yaxis_title="EUR",
                      barmode='group', hovermode='x unified')
    st.plotly_chart(fig2, use_container_width=True)
    
    # Top/Bottom Projects
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top 10 Projects by Gross Profit")
        top_projects = project_metrics.nlargest(10, "gross_profit")[
            ["project_id", "revenue", "gross_profit", "gross_margin_pct"]
        ]
        st.dataframe(top_projects.style.format({
            "revenue": "€{:,.0f}",
            "gross_profit": "€{:,.0f}",
            "gross_margin_pct": "{:.1%}"
        }), use_container_width=True)
    
    with col2:
        st.subheader("Bottom 10 Projects by Gross Margin %")
        bottom_projects = project_metrics.nsmallest(10, "gross_margin_pct")[
            ["project_id", "revenue", "gross_profit", "gross_margin_pct"]
        ]
        st.dataframe(bottom_projects.style.format({
            "revenue": "€{:,.0f}",
            "gross_profit": "€{:,.0f}",
            "gross_margin_pct": "{:.1%}"
        }), use_container_width=True)


def page_projects():
    """Projects page - Refactored for decision-oriented UX."""
    if st.session_state.data is None:
        st.error("No data loaded.")
        return
    
    data = st.session_state.data
    metrics_outputs = _build_metrics_outputs(data)
    _render_data_quality_banner(data, st.session_state.validation_results, metrics_outputs)
    projects_metrics = metrics_outputs["projects_metrics"]
    
    # Render the refactored projects page
    render_projects_page(data, projects_metrics)


def page_people():
    """People/Utilization page."""
    st.title("👥 People & Utilization")
    
    if st.session_state.data is None:
        st.error("No data loaded.")
        return
    
    data = st.session_state.data
    employees = data["employees"]
    time_entries = data["time_entries"]
    metrics_outputs = _build_metrics_outputs(data)
    _render_data_quality_banner(data, st.session_state.validation_results, metrics_outputs)
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
            marker_color=['red', 'green', 'orange']
        )])
        fig2.update_layout(title="Utilization Status", yaxis_title="Number of Employees")
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
                             name='Billable', marker_color='green'))
        fig3.add_trace(go.Bar(x=monthly_agg["month"], y=monthly_agg["non_billable_hours"],
                             name='Non-billable', marker_color='red'))
        fig3.update_layout(title="Billable vs Non-billable Hours by Month",
                          xaxis_title="Month", yaxis_title="Hours",
                          barmode='stack')
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
    st.title("💰 Financial Statements")
    
    if st.session_state.data is None:
        st.error("No data loaded.")
        return
    
    data = st.session_state.data
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
    st.title("🔍 Data Quality")
    
    validation_results = st.session_state.validation_results
    data = st.session_state.data
    
    if validation_results is None:
        st.warning("No validation results available.")
        return

    overview = get_data_quality_overview(data or {}, validation_results)
    _render_data_quality_banner(data or {}, validation_results)

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
    st.write(
        f"As-of date: **{overview['as_of_date'].date().isoformat() if overview['as_of_date'] is not None else 'N/A'}**"
    )
    if overview["coverage_start"] is not None and overview["coverage_end"] is not None:
        st.write(
            "Overall coverage: "
            f"**{pd.to_datetime(overview['coverage_start']).date().isoformat()} -> "
            f"{pd.to_datetime(overview['coverage_end']).date().isoformat()}**"
        )

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
        metrics_outputs = _build_metrics_outputs(data)
        _render_data_quality_banner(data, st.session_state.validation_results, metrics_outputs)
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
        metrics_outputs = _build_metrics_outputs(data)
        _render_data_quality_banner(data, st.session_state.validation_results, metrics_outputs)
        render_insights_tab(metrics_outputs, data, st.session_state.starting_cash)
        
    except Exception as e:
        st.error(f"Error computing metrics: {str(e)}")
        st.exception(e)


# Main app
def main():
    """Main app function."""
    # Sidebar navigation
    st.sidebar.title("Navigation")
    st.sidebar.caption("Deterministic metrics are the source of truth. AI only explains computed facts.")
    st.session_state.starting_cash = st.sidebar.number_input(
        "Starting Cash (EUR)",
        min_value=0.0,
        value=st.session_state.starting_cash,
        step=1000.0,
    )
    
    # Demo mode: show only selected pages
    if DEMO_MODE:
        available_pages = ["Overview Dashboard", "Projects", "Insights & Explanations"]
    else:
        available_pages = ["Overview Dashboard", "Projects", "People", "Financial Statements", "Weekly Brief", "Insights & Explanations", "Data Quality"]
    
    page = st.sidebar.radio(
        "Go to",
        available_pages
    )
    
    # Route to page
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
