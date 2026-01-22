"""
Scenarios & Copilot tab for Streamlit.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, Optional

from ..core.scenario_engine import apply_scenario
from ..ai.summary_builder import build_scenario_summary
from ..ai.local_llm import generate_scenario_memo


def render_scenario_tab(baseline_outputs: Dict, starting_cash: float):
    """
    Render the Scenarios & Copilot tab.
    
    Args:
        baseline_outputs: Dictionary with baseline metrics outputs:
            - projects_metrics_monthly
            - income_statement_monthly
            - cashflow_monthly
        starting_cash: Starting cash balance
    """
    st.title("🔮 Scenarios & Copilot")
    
    # Check if we have required data
    required_keys = ["projects_metrics_monthly", "income_statement_monthly", "cashflow_monthly"]
    missing_keys = [key for key in required_keys if key not in baseline_outputs]
    
    if missing_keys:
        st.error(f"Missing required baseline outputs: {', '.join(missing_keys)}. Please visit other tabs first.")
        return
    
    # Get available months
    projects_monthly = baseline_outputs["projects_metrics_monthly"]
    if "month" in projects_monthly.columns:
        available_months = sorted(projects_monthly["month"].unique().astype(str))
    else:
        st.error("Projects metrics must have monthly breakdown. Please ensure by_month=True.")
        return
    
    # Sidebar inputs
    st.sidebar.subheader("Scenario Configuration")
    
    scenario_name = st.sidebar.text_input("Scenario Name", value="Scenario 1")
    start_month = st.sidebar.selectbox("Start Month", available_months)
    
    # Starting cash input
    scenario_starting_cash = st.sidebar.number_input(
        "Starting Cash (EUR)",
        min_value=0.0,
        value=starting_cash,
        step=1000.0
    )
    
    # Scenario levers
    st.sidebar.subheader("Scenario Levers")
    
    # Price uplift
    st.sidebar.write("**Price Uplift**")
    price_uplift_project = st.sidebar.selectbox(
        "Project ID",
        ["None"] + sorted(projects_monthly["project_id"].unique().tolist()),
        key="price_project"
    )
    price_uplift_pct = st.sidebar.number_input(
        "Uplift (0.0 = 0%, 1.0 = 100%)",
        min_value=0.0,
        max_value=1.0,
        value=0.0,
        step=0.05,
        format="%.2f",
        key="price_pct"
    )
    
    # Hours reduction
    st.sidebar.write("**Hours Reduction**")
    hours_reduction_project = st.sidebar.selectbox(
        "Project ID",
        ["None"] + sorted(projects_monthly["project_id"].unique().tolist()),
        key="hours_project"
    )
    hours_reduction_pct = st.sidebar.number_input(
        "Reduction (0.0 = 0%, 1.0 = 100%)",
        min_value=0.0,
        max_value=1.0,
        value=0.0,
        step=0.05,
        format="%.2f",
        key="hours_pct"
    )
    
    # Overhead cut
    st.sidebar.write("**Overhead Cut**")
    overhead_cut_eur = st.sidebar.number_input(
        "Monthly Reduction (EUR)",
        min_value=0.0,
        value=0.0,
        step=100.0,
        key="overhead_cut"
    )
    
    # Hire
    st.sidebar.write("**Hire**")
    hire_monthly_cost = st.sidebar.number_input(
        "Monthly Fully Loaded Cost (EUR)",
        min_value=0.0,
        value=0.0,
        step=500.0,
        key="hire_cost"
    )
    
    # Build scenario dict
    changes = []
    if price_uplift_project != "None" and price_uplift_pct > 0:
        changes.append({
            "type": "price_uplift_pct",
            "project_id": price_uplift_project,
            "pct": price_uplift_pct
        })
    
    if hours_reduction_project != "None" and hours_reduction_pct > 0:
        changes.append({
            "type": "hours_reduction_pct",
            "project_id": hours_reduction_project,
            "pct": hours_reduction_pct
        })
    
    if overhead_cut_eur > 0:
        changes.append({
            "type": "overhead_cut_eur",
            "amount_eur": overhead_cut_eur
        })
    
    if hire_monthly_cost > 0:
        changes.append({
            "type": "hire",
            "monthly_fully_loaded_cost_eur": hire_monthly_cost
        })
    
    scenario_input = {
        "name": scenario_name,
        "start_month": start_month,
        "changes": changes
    }
    
    # Buttons
    col1, col2 = st.columns(2)
    
    with col1:
        run_scenario = st.button("Run Scenario", type="primary", use_container_width=True)
    
    with col2:
        generate_memo = st.button("Generate AI Memo", type="secondary", use_container_width=True)
    
    # Run scenario
    if run_scenario:
        if len(changes) == 0:
            st.warning("⚠️ Please configure at least one scenario lever.")
        else:
            with st.spinner("Computing scenario..."):
                try:
                    scenario_outputs = apply_scenario(
                        baseline_outputs,
                        scenario_input,
                        scenario_starting_cash
                    )
                    
                    # Store in session state
                    st.session_state.scenario_outputs = scenario_outputs
                    st.session_state.scenario_input = scenario_input
                    st.session_state.scenario_summary = build_scenario_summary(
                        baseline_outputs,
                        scenario_outputs,
                        scenario_input
                    )
                    
                    st.success("✅ Scenario computed successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error computing scenario: {str(e)}")
                    st.exception(e)
    
    # Display results if scenario has been run
    if "scenario_outputs" in st.session_state:
        scenario_outputs = st.session_state.scenario_outputs
        scenario_input = st.session_state.scenario_input
        deltas = scenario_outputs["deltas"]
        
        # KPI Cards
        st.subheader("Baseline vs Scenario")
        
        baseline_income = baseline_outputs["income_statement_monthly"]
        scenario_income = scenario_outputs["scenario_income_statement_monthly"]
        
        baseline_revenue = baseline_income[baseline_income["month"] == "Total"]["revenue"].iloc[0] if len(baseline_income[baseline_income["month"] == "Total"]) > 0 else baseline_income["revenue"].sum()
        scenario_revenue = scenario_income[scenario_income["month"] == "Total"]["revenue"].iloc[0] if len(scenario_income[scenario_income["month"] == "Total"]) > 0 else scenario_income["revenue"].sum()
        
        baseline_ebitda = baseline_income[baseline_income["month"] == "Total"]["ebitda"].iloc[0] if len(baseline_income[baseline_income["month"] == "Total"]) > 0 else baseline_income["ebitda"].sum()
        scenario_ebitda = scenario_income[scenario_income["month"] == "Total"]["ebitda"].iloc[0] if len(scenario_income[scenario_income["month"] == "Total"]) > 0 else scenario_income["ebitda"].sum()
        
        baseline_cashflow = baseline_outputs["cashflow_monthly"]
        scenario_cashflow = scenario_outputs["scenario_cashflow_monthly"]
        
        baseline_monthly_cf = baseline_cashflow[baseline_cashflow["month"] != "Total"]
        scenario_monthly_cf = scenario_cashflow[scenario_cashflow["month"] != "Total"]
        baseline_ending_cash = baseline_monthly_cf["ending_cash"].iloc[-1] if len(baseline_monthly_cf) > 0 else scenario_starting_cash
        scenario_ending_cash = scenario_monthly_cf["ending_cash"].iloc[-1] if len(scenario_monthly_cf) > 0 else scenario_starting_cash
        
        from ..metrics import compute_runway
        baseline_runway = compute_runway(baseline_cashflow, scenario_starting_cash)
        scenario_runway = compute_runway(scenario_cashflow, scenario_starting_cash)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Revenue",
                f"€{scenario_revenue:,.0f}",
                delta=f"€{deltas['delta_revenue_total']:+,.0f}"
            )
        
        with col2:
            st.metric(
                "EBITDA",
                f"€{scenario_ebitda:,.0f}",
                delta=f"€{deltas['delta_ebitda']:+,.0f}"
            )
        
        with col3:
            st.metric(
                "Ending Cash",
                f"€{scenario_ending_cash:,.0f}",
                delta=f"€{deltas['delta_ending_cash']:+,.0f}"
            )
        
        with col4:
            runway_display = f"{scenario_runway:.1f}" if scenario_runway != float('inf') else "∞"
            runway_delta = deltas['delta_runway_months']
            delta_display = f"{runway_delta:+.1f}" if runway_delta != float('inf') else "N/A"
            st.metric(
                "Runway (months)",
                runway_display,
                delta=delta_display
            )
        
        # Charts
        st.subheader("Financial Trends")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # EBITDA by month
            baseline_monthly = baseline_income[baseline_income["month"] != "Total"]
            scenario_monthly = scenario_income[scenario_income["month"] != "Total"]
            
            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(
                x=baseline_monthly["month"].astype(str),
                y=baseline_monthly["ebitda"],
                mode='lines+markers',
                name='Baseline EBITDA',
                line=dict(color='blue')
            ))
            fig1.add_trace(go.Scatter(
                x=scenario_monthly["month"].astype(str),
                y=scenario_monthly["ebitda"],
                mode='lines+markers',
                name='Scenario EBITDA',
                line=dict(color='green')
            ))
            fig1.update_layout(
                title="EBITDA by Month",
                xaxis_title="Month",
                yaxis_title="EUR",
                hovermode='x unified'
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Ending cash by month
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=baseline_monthly_cf["month"].astype(str),
                y=baseline_monthly_cf["ending_cash"],
                mode='lines+markers',
                name='Baseline Ending Cash',
                line=dict(color='blue')
            ))
            fig2.add_trace(go.Scatter(
                x=scenario_monthly_cf["month"].astype(str),
                y=scenario_monthly_cf["ending_cash"],
                mode='lines+markers',
                name='Scenario Ending Cash',
                line=dict(color='green')
            ))
            fig2.update_layout(
                title="Ending Cash Balance by Month",
                xaxis_title="Month",
                yaxis_title="EUR",
                hovermode='x unified'
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        # Project impacts table
        st.subheader("Project Impacts")
        
        baseline_projects_agg = baseline_outputs["projects_metrics_monthly"].groupby("project_id").agg({
            "revenue": "sum",
            "gross_profit": "sum",
            "gross_margin_pct": "mean"
        }).reset_index()
        baseline_projects_agg.columns = ["project_id", "baseline_revenue", "baseline_gross_profit", "baseline_margin_pct"]
        
        scenario_projects_agg = scenario_outputs["scenario_projects_monthly"].groupby("project_id").agg({
            "revenue": "sum",
            "gross_profit": "sum",
            "gross_margin_pct": "mean"
        }).reset_index()
        scenario_projects_agg.columns = ["project_id", "scenario_revenue", "scenario_gross_profit", "scenario_margin_pct"]
        
        project_impacts = baseline_projects_agg.merge(scenario_projects_agg, on="project_id")
        project_impacts["revenue_delta"] = project_impacts["scenario_revenue"] - project_impacts["baseline_revenue"]
        project_impacts["gross_profit_delta"] = project_impacts["scenario_gross_profit"] - project_impacts["baseline_gross_profit"]
        project_impacts["margin_delta"] = project_impacts["scenario_margin_pct"] - project_impacts["baseline_margin_pct"]
        
        display_cols = ["project_id", "revenue_delta", "gross_profit_delta", "margin_delta", "scenario_margin_pct"]
        st.dataframe(
            project_impacts[display_cols].style.format({
                "revenue_delta": "€{:+,.0f}",
                "gross_profit_delta": "€{:+,.0f}",
                "margin_delta": "{:+.1%}",
                "scenario_margin_pct": "{:.1%}"
            }),
            use_container_width=True
        )
        
        # High-risk projects
        st.subheader("High-Risk Projects (Scenario)")
        high_risk = scenario_outputs["scenario_projects_monthly"][
            scenario_outputs["scenario_projects_monthly"]["gross_margin_pct"] < 0
        ].groupby("project_id").agg({
            "gross_margin_pct": "mean",
            "gross_profit": "sum",
            "revenue": "sum"
        }).reset_index()
        
        if len(high_risk) > 0:
            st.dataframe(
                high_risk.style.format({
                    "gross_margin_pct": "{:.1%}",
                    "gross_profit": "€{:,.0f}",
                    "revenue": "€{:,.0f}"
                }),
                use_container_width=True
            )
        else:
            st.info("No projects with negative margins in scenario.")
        
        # AI Memo section
        st.divider()
        st.subheader("AI-Generated Memo")
        
        if generate_memo or "scenario_memo" in st.session_state:
            if generate_memo:
                if "scenario_summary" not in st.session_state:
                    st.error("Please run a scenario first before generating a memo.")
                else:
                    with st.spinner("Generating memo..."):
                        summary = st.session_state.scenario_summary
                        memo = generate_scenario_memo(summary)
                        st.session_state.scenario_memo = memo
            
            if "scenario_memo" in st.session_state:
                st.markdown(st.session_state.scenario_memo)
                st.caption("**Disclaimer:** Generated narrative. Numbers are deterministic.")
        else:
            st.info("Click 'Generate AI Memo' to create a narrative summary of the scenario.")
