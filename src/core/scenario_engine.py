"""
Deterministic Scenario Engine.
Applies scenario changes to baseline metrics outputs.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional


def apply_scenario(baseline: Dict, scenario: Dict, starting_cash: float) -> Dict:
    """
    Apply scenario changes to baseline metrics outputs.
    
    Args:
        baseline: Dictionary with keys:
            - projects_metrics_monthly: DataFrame with project_id, month, revenue, labor_cost, 
              allocated_expenses, gross_profit, gross_margin_pct, billable_hours
            - income_statement_monthly: DataFrame with month, revenue, cogs, gross_profit, 
              operating_expenses, ebitda
            - cashflow_monthly: DataFrame with month, cash_in, cash_out_payroll, 
              cash_out_expenses, cash_out_total, net_cashflow, ending_cash
        scenario: Dictionary with:
            - name: str
            - start_month: str (YYYY-MM)
            - changes: List of change dicts
        starting_cash: Starting cash balance
    
    Returns:
        Dictionary with:
            - scenario_projects_monthly: DataFrame
            - scenario_income_statement_monthly: DataFrame
            - scenario_cashflow_monthly: DataFrame
            - deltas: Dictionary with KPI deltas
    """
    projects_monthly = baseline["projects_metrics_monthly"].copy()
    income_stmt = baseline["income_statement_monthly"].copy()
    cashflow = baseline["cashflow_monthly"].copy()
    
    start_month = scenario["start_month"]
    changes = scenario["changes"]
    
    # Ensure month is string type for consistent operations
    projects_monthly = projects_monthly.copy()
    projects_monthly["month"] = projects_monthly["month"].astype(str)
    
    # Apply project-level changes
    for change in changes:
        change_type = change["type"]
        
        if change_type == "price_uplift_pct":
            project_id = change["project_id"]
            pct = change["pct"]
            
            # Apply revenue uplift from start_month onwards
            mask = (projects_monthly["project_id"] == project_id) & (
                projects_monthly["month"] >= start_month
            )
            projects_monthly.loc[mask, "revenue"] *= (1 + pct)
        
        elif change_type == "hours_reduction_pct":
            project_id = change["project_id"]
            pct = change["pct"]
            
            # Apply labor cost and billable hours reduction from start_month onwards
            mask = (projects_monthly["project_id"] == project_id) & (
                projects_monthly["month"] >= start_month
            )
            projects_monthly.loc[mask, "labor_cost"] *= (1 - pct)
            projects_monthly.loc[mask, "billable_hours"] *= (1 - pct)
    
    # Recalculate project-level metrics after changes
    projects_monthly["gross_profit"] = (
        projects_monthly["revenue"] - 
        projects_monthly["labor_cost"] - 
        projects_monthly["allocated_expenses"]
    )
    projects_monthly["gross_margin_pct"] = projects_monthly.apply(
        lambda row: (row["gross_profit"] / row["revenue"]) if row["revenue"] > 0 else np.nan,
        axis=1
    )
    
    # Rebuild income statement from projects monthly
    scenario_income = rebuild_income_statement(projects_monthly, income_stmt, changes, start_month)
    
    # Rebuild cashflow
    scenario_cashflow = rebuild_cashflow(
        cashflow, projects_monthly, baseline["projects_metrics_monthly"], 
        changes, start_month, starting_cash
    )
    
    # Calculate deltas
    deltas = calculate_deltas(baseline, {
        "projects_metrics_monthly": projects_monthly,
        "income_statement_monthly": scenario_income,
        "cashflow_monthly": scenario_cashflow
    })
    
    return {
        "scenario_projects_monthly": projects_monthly,
        "scenario_income_statement_monthly": scenario_income,
        "scenario_cashflow_monthly": scenario_cashflow,
        "deltas": deltas
    }


def rebuild_income_statement(
    projects_monthly: pd.DataFrame,
    baseline_income: pd.DataFrame,
    changes: List[Dict],
    start_month: str
) -> pd.DataFrame:
    """
    Rebuild income statement from scenario projects monthly.
    
    Revenue = sum(project revenue by month)
    COGS = sum(project labor_cost + allocated_expenses by month)
    OpEx = baseline OpEx +/- scenario changes
    """
    # Aggregate revenue and COGS by month from projects
    # Month should already be string from apply_scenario, but ensure it
    projects_monthly = projects_monthly.copy()
    projects_monthly["month"] = projects_monthly["month"].astype(str)
    
    monthly_revenue = projects_monthly.groupby("month", as_index=False)["revenue"].sum()
    monthly_revenue.columns = ["month", "revenue"]
    
    monthly_cogs = projects_monthly.groupby("month", as_index=False).agg({
        "labor_cost": "sum",
        "allocated_expenses": "sum"
    })
    monthly_cogs["cogs"] = monthly_cogs["labor_cost"] + monthly_cogs["allocated_expenses"]
    monthly_cogs = monthly_cogs[["month", "cogs"]]
    
    # Start with baseline income statement structure
    scenario_income = baseline_income.copy()
    
    # Ensure month is string type in scenario_income for consistent merging
    scenario_income["month"] = scenario_income["month"].astype(str)
    
    # Update revenue and COGS from projects
    scenario_income = scenario_income.merge(monthly_revenue, on="month", how="left", suffixes=("", "_new"))
    scenario_income["revenue"] = scenario_income["revenue_new"].fillna(scenario_income["revenue"])
    scenario_income = scenario_income.drop(columns=["revenue_new"], errors="ignore")
    
    scenario_income = scenario_income.merge(monthly_cogs, on="month", how="left", suffixes=("", "_new"))
    scenario_income["cogs"] = scenario_income["cogs_new"].fillna(scenario_income["cogs"])
    scenario_income = scenario_income.drop(columns=["cogs_new"], errors="ignore")
    
    # Recalculate gross profit
    scenario_income["gross_profit"] = scenario_income["revenue"] - scenario_income["cogs"]
    
    # Apply overhead and hire changes to operating expenses
    # Ensure month is string for comparison
    scenario_income["month"] = scenario_income["month"].astype(str)
    
    for change in changes:
        change_type = change["type"]
        
        if change_type == "overhead_cut_eur":
            amount = change["amount_eur"]
            mask = scenario_income["month"] >= start_month
            # Update overhead_expenses
            if "overhead_expenses" in scenario_income.columns:
                scenario_income.loc[mask, "overhead_expenses"] -= amount
            # Recalculate operating_expenses
            if "overhead_labor_cost" in scenario_income.columns and "overhead_expenses" in scenario_income.columns:
                scenario_income.loc[mask, "operating_expenses"] = (
                    scenario_income.loc[mask, "overhead_labor_cost"] + 
                    scenario_income.loc[mask, "overhead_expenses"]
                )
            else:
                scenario_income.loc[mask, "operating_expenses"] -= amount
        
        elif change_type == "hire":
            monthly_cost = change["monthly_fully_loaded_cost_eur"]
            mask = scenario_income["month"] >= start_month
            # Update overhead_labor_cost
            if "overhead_labor_cost" in scenario_income.columns:
                scenario_income.loc[mask, "overhead_labor_cost"] += monthly_cost
            # Recalculate operating_expenses
            if "overhead_labor_cost" in scenario_income.columns and "overhead_expenses" in scenario_income.columns:
                scenario_income.loc[mask, "operating_expenses"] = (
                    scenario_income.loc[mask, "overhead_labor_cost"] + 
                    scenario_income.loc[mask, "overhead_expenses"]
                )
            else:
                scenario_income.loc[mask, "operating_expenses"] += monthly_cost
    
    # Recalculate EBITDA
    scenario_income["ebitda"] = scenario_income["gross_profit"] - scenario_income["operating_expenses"]
    
    # Update totals row if present
    if "Total" in scenario_income["month"].values:
        totals_mask = scenario_income["month"] == "Total"
        scenario_income.loc[totals_mask, "revenue"] = scenario_income[scenario_income["month"] != "Total"]["revenue"].sum()
        scenario_income.loc[totals_mask, "cogs"] = scenario_income[scenario_income["month"] != "Total"]["cogs"].sum()
        scenario_income.loc[totals_mask, "gross_profit"] = scenario_income[scenario_income["month"] != "Total"]["gross_profit"].sum()
        scenario_income.loc[totals_mask, "operating_expenses"] = scenario_income[scenario_income["month"] != "Total"]["operating_expenses"].sum()
        scenario_income.loc[totals_mask, "ebitda"] = scenario_income[scenario_income["month"] != "Total"]["ebitda"].sum()
    
    return scenario_income


def rebuild_cashflow(
    baseline_cashflow: pd.DataFrame,
    scenario_projects: pd.DataFrame,
    baseline_projects: pd.DataFrame,
    changes: List[Dict],
    start_month: str,
    starting_cash: float
) -> pd.DataFrame:
    """
    Rebuild cashflow statement with scenario changes.
    
    Cash In: Scale baseline cash_in by revenue uplift proportion (simple approximation)
    Cash Out: Apply overhead cuts and hires
    """
    scenario_cashflow = baseline_cashflow.copy()
    
    # Exclude totals row for calculations
    monthly_cashflow = scenario_cashflow[scenario_cashflow["month"] != "Total"].copy()
    monthly_cashflow["month"] = monthly_cashflow["month"].astype(str)
    
    # Calculate revenue uplift factor for affected projects
    revenue_uplift_factor = 1.0
    for change in changes:
        if change["type"] == "price_uplift_pct":
            project_id = change["project_id"]
            pct = change["pct"]
            
            # Calculate baseline and scenario revenue for this project after start_month
            # Ensure month is string for comparison
            baseline_projects = baseline_projects.copy()
            baseline_projects["month"] = baseline_projects["month"].astype(str)
            scenario_projects = scenario_projects.copy()
            scenario_projects["month"] = scenario_projects["month"].astype(str)
            
            baseline_rev = baseline_projects[
                (baseline_projects["project_id"] == project_id) &
                (baseline_projects["month"] >= start_month)
            ]["revenue"].sum()
            
            scenario_rev = scenario_projects[
                (scenario_projects["project_id"] == project_id) &
                (scenario_projects["month"] >= start_month)
            ]["revenue"].sum()
            
            if baseline_rev > 0:
                # Simple approximation: scale cash_in proportionally
                project_uplift = scenario_rev / baseline_rev
                # Weight by project's share of total revenue (simplified)
                revenue_uplift_factor = max(revenue_uplift_factor, project_uplift)
    
    # Apply revenue uplift to cash_in (simple approximation)
    mask = monthly_cashflow["month"] >= start_month
    monthly_cashflow.loc[mask, "cash_in"] *= revenue_uplift_factor
    
    # Apply overhead cuts and hires to cash_out
    for change in changes:
        change_type = change["type"]
        
        if change_type == "overhead_cut_eur":
            amount = change["amount_eur"]
            mask = monthly_cashflow["month"] >= start_month
            monthly_cashflow.loc[mask, "cash_out_expenses"] -= amount
        
        elif change_type == "hire":
            monthly_cost = change["monthly_fully_loaded_cost_eur"]
            mask = monthly_cashflow["month"] >= start_month
            monthly_cashflow.loc[mask, "cash_out_payroll"] += monthly_cost
    
    # Recalculate totals
    monthly_cashflow["cash_out_total"] = (
        monthly_cashflow["cash_out_payroll"] + 
        monthly_cashflow["cash_out_expenses"]
    )
    monthly_cashflow["net_cashflow"] = (
        monthly_cashflow["cash_in"] - 
        monthly_cashflow["cash_out_total"]
    )
    
    # Recalculate ending cash cumulatively
    monthly_cashflow = monthly_cashflow.sort_values("month")
    monthly_cashflow["ending_cash"] = starting_cash + monthly_cashflow["net_cashflow"].cumsum()
    
    # Add totals row
    totals = pd.DataFrame([{
        "month": "Total",
        "cash_in": monthly_cashflow["cash_in"].sum(),
        "cash_out_payroll": monthly_cashflow["cash_out_payroll"].sum(),
        "cash_out_expenses": monthly_cashflow["cash_out_expenses"].sum(),
        "cash_out_total": monthly_cashflow["cash_out_total"].sum(),
        "net_cashflow": monthly_cashflow["net_cashflow"].sum(),
        "ending_cash": monthly_cashflow["ending_cash"].iloc[-1] if len(monthly_cashflow) > 0 else starting_cash
    }])
    
    scenario_cashflow = pd.concat([monthly_cashflow, totals], ignore_index=True)
    
    return scenario_cashflow


def calculate_deltas(baseline: Dict, scenario: Dict) -> Dict:
    """
    Calculate KPI deltas between baseline and scenario.
    
    Returns dictionary with:
        - delta_revenue_total
        - delta_revenue_by_month (dict)
        - delta_gross_profit
        - delta_ebitda
        - delta_ending_cash
        - delta_runway_months
    """
    baseline_income = baseline["income_statement_monthly"]
    scenario_income = scenario["income_statement_monthly"]
    baseline_cashflow = baseline["cashflow_monthly"]
    scenario_cashflow = scenario["cashflow_monthly"]
    
    # Total revenue delta
    baseline_revenue_total = baseline_income[baseline_income["month"] == "Total"]["revenue"].iloc[0] if len(baseline_income[baseline_income["month"] == "Total"]) > 0 else baseline_income["revenue"].sum()
    scenario_revenue_total = scenario_income[scenario_income["month"] == "Total"]["revenue"].iloc[0] if len(scenario_income[scenario_income["month"] == "Total"]) > 0 else scenario_income["revenue"].sum()
    delta_revenue_total = scenario_revenue_total - baseline_revenue_total
    
    # Revenue by month
    baseline_monthly = baseline_income[baseline_income["month"] != "Total"]
    scenario_monthly = scenario_income[scenario_income["month"] != "Total"]
    delta_revenue_by_month = {}
    for month in baseline_monthly["month"].unique():
        baseline_rev = baseline_monthly[baseline_monthly["month"] == month]["revenue"].iloc[0] if len(baseline_monthly[baseline_monthly["month"] == month]) > 0 else 0
        scenario_rev = scenario_monthly[scenario_monthly["month"] == month]["revenue"].iloc[0] if len(scenario_monthly[scenario_monthly["month"] == month]) > 0 else 0
        delta_revenue_by_month[str(month)] = scenario_rev - baseline_rev
    
    # Gross profit delta
    baseline_gp = baseline_income[baseline_income["month"] == "Total"]["gross_profit"].iloc[0] if len(baseline_income[baseline_income["month"] == "Total"]) > 0 else baseline_income["gross_profit"].sum()
    scenario_gp = scenario_income[scenario_income["month"] == "Total"]["gross_profit"].iloc[0] if len(scenario_income[scenario_income["month"] == "Total"]) > 0 else scenario_income["gross_profit"].sum()
    delta_gross_profit = scenario_gp - baseline_gp
    
    # EBITDA delta
    baseline_ebitda = baseline_income[baseline_income["month"] == "Total"]["ebitda"].iloc[0] if len(baseline_income[baseline_income["month"] == "Total"]) > 0 else baseline_income["ebitda"].sum()
    scenario_ebitda = scenario_income[scenario_income["month"] == "Total"]["ebitda"].iloc[0] if len(scenario_income[scenario_income["month"] == "Total"]) > 0 else scenario_income["ebitda"].sum()
    delta_ebitda = scenario_ebitda - baseline_ebitda
    
    # Ending cash delta
    baseline_monthly_cf = baseline_cashflow[baseline_cashflow["month"] != "Total"]
    scenario_monthly_cf = scenario_cashflow[scenario_cashflow["month"] != "Total"]
    baseline_ending_cash = baseline_monthly_cf["ending_cash"].iloc[-1] if len(baseline_monthly_cf) > 0 else 0
    scenario_ending_cash = scenario_monthly_cf["ending_cash"].iloc[-1] if len(scenario_monthly_cf) > 0 else 0
    delta_ending_cash = scenario_ending_cash - baseline_ending_cash
    
    # Runway delta (using last 3 months average burn)
    from ..metrics import compute_runway
    baseline_runway = compute_runway(baseline_cashflow, 0)  # starting_cash doesn't matter for delta
    scenario_runway = compute_runway(scenario_cashflow, 0)
    delta_runway_months = scenario_runway - baseline_runway
    
    return {
        "delta_revenue_total": delta_revenue_total,
        "delta_revenue_by_month": delta_revenue_by_month,
        "delta_gross_profit": delta_gross_profit,
        "delta_ebitda": delta_ebitda,
        "delta_ending_cash": delta_ending_cash,
        "delta_runway_months": delta_runway_months
    }
