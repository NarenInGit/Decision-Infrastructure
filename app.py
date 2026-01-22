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

from src.data_loader import load_and_validate_data, get_data_summary
from src.metrics import (
    compute_project_metrics,
    compute_employee_utilization,
    compute_income_statement,
    compute_cashflow_statement,
    compute_runway
)
from src.config import DEFAULT_STARTING_CASH, UNDERUTILIZED_THRESHOLD, OVERUTILIZED_THRESHOLD

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
    
    # Date range selector
    time_entries = data["time_entries"]
    invoices = data["invoices"]
    
    if len(time_entries) > 0 and len(invoices) > 0:
        min_date = min(
            pd.to_datetime(time_entries["date"]).min(),
            pd.to_datetime(invoices["invoice_date"]).min()
        )
        max_date = max(
            pd.to_datetime(time_entries["date"]).max(),
            pd.to_datetime(invoices["invoice_date"]).max()
        )
        
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
    
    # Starting cash input
    st.session_state.starting_cash = st.sidebar.number_input(
        "Starting Cash (EUR)",
        min_value=0.0,
        value=st.session_state.starting_cash,
        step=1000.0
    )
    
    # Compute metrics
    income_stmt = compute_income_statement(
        invoices, time_entries, data["expenses"], start_date_ts, end_date_ts
    )
    cashflow_stmt = compute_cashflow_statement(
        invoices, data["expenses"], data["employees"],
        st.session_state.starting_cash, start_date_ts, end_date_ts
    )
    project_metrics = compute_project_metrics(time_entries, invoices, data["expenses"])
    
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
    """Projects page."""
    st.title("📁 Projects")
    
    if st.session_state.data is None:
        st.error("No data loaded.")
        return
    
    data = st.session_state.data
    projects = data["projects"]
    time_entries = data["time_entries"]
    invoices = data["invoices"]
    expenses = data["expenses"]
    
    # Filters
    st.sidebar.subheader("Filters")
    
    clients = ["All"] + sorted(projects["client_name"].unique().tolist())
    selected_client = st.sidebar.selectbox("Client", clients)
    
    statuses = ["All"] + sorted(projects["status"].unique().tolist())
    selected_status = st.sidebar.selectbox("Status", statuses)
    
    billing_models = ["All"] + sorted(projects["billing_model"].unique().tolist())
    selected_billing = st.sidebar.selectbox("Billing Model", billing_models)
    
    countries = ["All"] + sorted(projects["country"].unique().tolist())
    selected_country = st.sidebar.selectbox("Country", countries)
    
    industries = ["All"] + sorted(projects["industry"].unique().tolist())
    selected_industry = st.sidebar.selectbox("Industry", industries)
    
    # Filter projects
    filtered_projects = projects.copy()
    if selected_client != "All":
        filtered_projects = filtered_projects[filtered_projects["client_name"] == selected_client]
    if selected_status != "All":
        filtered_projects = filtered_projects[filtered_projects["status"] == selected_status]
    if selected_billing != "All":
        filtered_projects = filtered_projects[filtered_projects["billing_model"] == selected_billing]
    if selected_country != "All":
        filtered_projects = filtered_projects[filtered_projects["country"] == selected_country]
    if selected_industry != "All":
        filtered_projects = filtered_projects[filtered_projects["industry"] == selected_industry]
    
    # Compute project metrics
    project_metrics = compute_project_metrics(time_entries, invoices, expenses)
    
    # Merge with project details
    project_display = filtered_projects.merge(project_metrics, on="project_id", how="left")
    
    # Display table
    st.subheader("Projects")
    display_cols = ["project_id", "client_name", "project_name", "status", "billing_model",
                    "revenue", "labor_cost", "allocated_expenses", "gross_profit", "gross_margin_pct",
                    "billable_hours", "effective_hourly_rate"]
    
    available_cols = [col for col in display_cols if col in project_display.columns]
    st.dataframe(
        project_display[available_cols].style.format({
            "revenue": "€{:,.0f}",
            "labor_cost": "€{:,.0f}",
            "allocated_expenses": "€{:,.0f}",
            "gross_profit": "€{:,.0f}",
            "gross_margin_pct": "{:.1%}",
            "billable_hours": "{:.1f}",
            "effective_hourly_rate": "€{:.2f}"
        }),
        use_container_width=True,
        height=400
    )
    
    # Project detail view
    st.subheader("Project Detail")
    project_ids = ["Select a project"] + sorted(filtered_projects["project_id"].unique().tolist())
    selected_project_id = st.selectbox("Select Project", project_ids)
    
    if selected_project_id != "Select a project":
        # Monthly trend
        project_monthly = compute_project_metrics(time_entries, invoices, expenses, by_month=True)
        project_monthly = project_monthly[project_monthly["project_id"] == selected_project_id]
        
        if len(project_monthly) > 0:
            st.write(f"**Monthly Trend for {selected_project_id}**")
            project_monthly_display = project_monthly.copy()
            project_monthly_display["month"] = project_monthly_display["month"].astype(str)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=project_monthly_display["month"], y=project_monthly_display["revenue"],
                                    mode='lines+markers', name='Revenue', line=dict(color='green')))
            fig.add_trace(go.Scatter(x=project_monthly_display["month"], y=project_monthly_display["labor_cost"],
                                    mode='lines+markers', name='Labor Cost', line=dict(color='red')))
            fig.add_trace(go.Scatter(x=project_monthly_display["month"], y=project_monthly_display["allocated_expenses"],
                                    mode='lines+markers', name='Allocated Expenses', line=dict(color='orange')))
            fig.add_trace(go.Scatter(x=project_monthly_display["month"], y=project_monthly_display["gross_profit"],
                                    mode='lines+markers', name='Gross Profit', line=dict(color='blue')))
            fig.update_layout(title=f"Monthly Trend: {selected_project_id}", xaxis_title="Month", yaxis_title="EUR",
                            hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)
            
            # Team contribution
            st.write("**Team Contribution**")
            project_time = time_entries[time_entries["project_id"] == selected_project_id]
            if len(project_time) > 0:
                team_contrib = project_time.groupby("employee_id").agg({
                    "hours_logged": "sum",
                    "labor_cost_eur": lambda x: (x * project_time.loc[x.index, "hours_logged"]).sum()
                }).reset_index()
                team_contrib.columns = ["employee_id", "hours", "cost"]
                
                # Merge with employees
                employees = data["employees"]
                team_contrib = team_contrib.merge(
                    employees[["employee_id", "job_title", "department"]],
                    on="employee_id",
                    how="left"
                )
                
                st.dataframe(
                    team_contrib.style.format({
                        "hours": "{:.1f}",
                        "cost": "€{:,.0f}"
                    }),
                    use_container_width=True
                )


def page_people():
    """People/Utilization page."""
    st.title("👥 People & Utilization")
    
    if st.session_state.data is None:
        st.error("No data loaded.")
        return
    
    data = st.session_state.data
    employees = data["employees"]
    time_entries = data["time_entries"]
    
    # Compute utilization
    emp_utilization = compute_employee_utilization(time_entries, employees)
    
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
    
    # Date range
    if len(time_entries) > 0 and len(invoices) > 0:
        min_date = min(
            pd.to_datetime(time_entries["date"]).min(),
            pd.to_datetime(invoices["invoice_date"]).min()
        )
        max_date = max(
            pd.to_datetime(time_entries["date"]).max(),
            pd.to_datetime(invoices["invoice_date"]).max()
        )
        
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
    
    with tab1:
        st.subheader("Income Statement (Accrual Basis)")
        income_stmt = compute_income_statement(invoices, time_entries, expenses, start_date_ts, end_date_ts)
        
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
        cashflow_stmt = compute_cashflow_statement(
            invoices, expenses, employees,
            st.session_state.starting_cash, start_date_ts, end_date_ts
        )
        
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
    
    # Errors and Warnings
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Errors")
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


# Main app
def main():
    """Main app function."""
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["Overview Dashboard", "Projects", "People", "Financial Statements", "Data Quality"]
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
    elif page == "Data Quality":
        page_data_quality()


if __name__ == "__main__":
    main()
