"""
Build compact scenario summaries for LLM consumption.
Only sends small, structured summaries - never raw tables or CSVs.
"""

import pandas as pd
from typing import Dict, List


def build_scenario_summary(
    baseline_outputs: Dict,
    scenario_outputs: Dict,
    scenario_input: Dict
) -> Dict:
    """
    Build a compact JSON-serializable summary for LLM.
    
    Args:
        baseline_outputs: Baseline metrics outputs
        scenario_outputs: Scenario metrics outputs (from apply_scenario)
        scenario_input: Original scenario input dict
    
    Returns:
        Dictionary with:
            - scenario_name, start_month, changes
            - headline_kpis: before/after/delta for revenue_total, ebitda_total, ending_cash, runway_months
            - top_winners: top 5 projects by gross_profit improvement
            - top_losers: top 5 projects by gross_profit deterioration
            - high_risk_projects: top 5 projects with gross_margin_pct < 0 in scenario
            - key_drivers: list of deterministic computed drivers
    """
    baseline_projects = baseline_outputs["projects_metrics_monthly"]
    scenario_projects = scenario_outputs["scenario_projects_monthly"]
    deltas = scenario_outputs["deltas"]
    
    # Headline KPIs
    baseline_income = baseline_outputs["income_statement_monthly"]
    scenario_income = scenario_outputs["scenario_income_statement_monthly"]
    baseline_cashflow = baseline_outputs["cashflow_monthly"]
    scenario_cashflow = scenario_outputs["scenario_cashflow_monthly"]
    
    baseline_revenue = baseline_income[baseline_income["month"] == "Total"]["revenue"].iloc[0] if len(baseline_income[baseline_income["month"] == "Total"]) > 0 else baseline_income["revenue"].sum()
    scenario_revenue = scenario_income[scenario_income["month"] == "Total"]["revenue"].iloc[0] if len(scenario_income[scenario_income["month"] == "Total"]) > 0 else scenario_income["revenue"].sum()
    
    baseline_ebitda = baseline_income[baseline_income["month"] == "Total"]["ebitda"].iloc[0] if len(baseline_income[baseline_income["month"] == "Total"]) > 0 else baseline_income["ebitda"].sum()
    scenario_ebitda = scenario_income[scenario_income["month"] == "Total"]["ebitda"].iloc[0] if len(scenario_income[scenario_income["month"] == "Total"]) > 0 else scenario_income["ebitda"].sum()
    
    baseline_monthly_cf = baseline_cashflow[baseline_cashflow["month"] != "Total"]
    scenario_monthly_cf = scenario_cashflow[scenario_cashflow["month"] != "Total"]
    baseline_ending_cash = baseline_monthly_cf["ending_cash"].iloc[-1] if len(baseline_monthly_cf) > 0 else 0
    scenario_ending_cash = scenario_monthly_cf["ending_cash"].iloc[-1] if len(scenario_monthly_cf) > 0 else 0
    
    from ..metrics import compute_runway
    baseline_runway = compute_runway(baseline_cashflow, 0)
    scenario_runway = compute_runway(scenario_cashflow, 0)
    
    # Top winners/losers by gross profit delta
    baseline_projects_agg = baseline_projects.groupby("project_id")["gross_profit"].sum().reset_index()
    baseline_projects_agg.columns = ["project_id", "baseline_gross_profit"]
    
    scenario_projects_agg = scenario_projects.groupby("project_id")["gross_profit"].sum().reset_index()
    scenario_projects_agg.columns = ["project_id", "scenario_gross_profit"]
    
    comparison = baseline_projects_agg.merge(scenario_projects_agg, on="project_id", how="outer")
    comparison = comparison.fillna(0)
    comparison["gross_profit_delta"] = comparison["scenario_gross_profit"] - comparison["baseline_gross_profit"]
    
    top_winners = comparison.nlargest(5, "gross_profit_delta")[
        ["project_id", "baseline_gross_profit", "scenario_gross_profit", "gross_profit_delta"]
    ].to_dict("records")
    
    top_losers = comparison.nsmallest(5, "gross_profit_delta")[
        ["project_id", "baseline_gross_profit", "scenario_gross_profit", "gross_profit_delta"]
    ].to_dict("records")
    
    # High risk projects (negative margin in scenario)
    scenario_projects_agg_margin = scenario_projects.groupby("project_id")["gross_margin_pct"].mean().reset_index()
    high_risk = scenario_projects_agg_margin[
        scenario_projects_agg_margin["gross_margin_pct"] < 0
    ].nsmallest(5, "gross_margin_pct")[
        ["project_id", "gross_margin_pct"]
    ].to_dict("records")
    
    # Key drivers (deterministic)
    key_drivers = []
    for change in scenario_input["changes"]:
        if change["type"] == "price_uplift_pct":
            key_drivers.append(f"Revenue increased by {change['pct']:.0%} for project {change['project_id']} starting {scenario_input['start_month']}")
        elif change["type"] == "hours_reduction_pct":
            key_drivers.append(f"Labor cost decreased by {change['pct']:.0%} for project {change['project_id']} starting {scenario_input['start_month']}")
        elif change["type"] == "overhead_cut_eur":
            key_drivers.append(f"Overhead expenses reduced by €{change['amount_eur']:,.0f} starting {scenario_input['start_month']}")
        elif change["type"] == "hire":
            key_drivers.append(f"New hire added with monthly cost of €{change['monthly_fully_loaded_cost_eur']:,.0f} starting {scenario_input['start_month']}")
    
    return {
        "scenario_name": scenario_input["name"],
        "start_month": scenario_input["start_month"],
        "changes": scenario_input["changes"],
        "headline_kpis": {
            "revenue_total": {
                "before": float(baseline_revenue),
                "after": float(scenario_revenue),
                "delta": float(deltas["delta_revenue_total"])
            },
            "ebitda_total": {
                "before": float(baseline_ebitda),
                "after": float(scenario_ebitda),
                "delta": float(deltas["delta_ebitda"])
            },
            "ending_cash": {
                "before": float(baseline_ending_cash),
                "after": float(scenario_ending_cash),
                "delta": float(deltas["delta_ending_cash"])
            },
            "runway_months": {
                "before": float(baseline_runway) if baseline_runway != float('inf') else None,
                "after": float(scenario_runway) if scenario_runway != float('inf') else None,
                "delta": float(deltas["delta_runway_months"]) if deltas["delta_runway_months"] != float('inf') else None
            }
        },
        "top_winners": top_winners,
        "top_losers": top_losers,
        "high_risk_projects": high_risk,
        "key_drivers": key_drivers
    }
