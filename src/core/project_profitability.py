"""
Project Profitability Analysis - Data adapter, drivers, and actions.
Deterministic verdict: "This project is bad because X — and the fix is Y."
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple


# Thresholds
TARGET_MARGIN_PERCENT = 0.20  # 20%
LABOR_SHARE_HIGH_THRESHOLD = 0.55  # 55%
OVERHEAD_SHARE_HIGH_THRESHOLD = 0.20  # 20%
COST_OVERRUN_THRESHOLD = 0.10  # 10%


def normalize_project_profitability(
    project_row: pd.Series,
    project_details: Optional[pd.DataFrame] = None,
    time_entries: Optional[pd.DataFrame] = None
) -> Dict:
    """
    Normalize project data into a view model for UI.
    
    Args:
        project_row: Row from compute_project_metrics (overall, not monthly)
        project_details: Row from projects.csv (optional, for metadata)
        time_entries: Time entries for the project (optional, for hours breakdown)
    
    Returns:
        ProjectProfitabilityViewModel dict with:
            - id, name, client
            - revenue, totalCost, marginValue, marginPercent
            - costBreakdown: {laborCost, overheadCost, otherCost}
            - status: "Healthy" | "At Risk" | "Loss-making"
            - dataCompleteness: % and missingFields list
            - hours: {billable, total}
    """
    # Basic fields
    project_id = project_row.get("project_id", "Unknown")
    revenue = project_row.get("revenue", 0)
    labor_cost = project_row.get("labor_cost", 0)
    allocated_expenses = project_row.get("allocated_expenses", 0)
    gross_profit = project_row.get("gross_profit", 0)
    gross_margin_pct = project_row.get("gross_margin_pct", np.nan)
    billable_hours = project_row.get("billable_hours", 0)
    total_hours = project_row.get("total_hours", 0)
    effective_hourly_rate = project_row.get("effective_hourly_rate", np.nan)
    
    # Total cost
    total_cost = labor_cost + allocated_expenses
    
    # Cost breakdown (labor = labor_cost, overhead = allocated_expenses, other = 0)
    cost_breakdown = {
        "laborCost": labor_cost,
        "overheadCost": allocated_expenses,
        "otherCost": 0
    }
    
    # Data completeness
    required_fields = ["revenue", "labor_cost", "allocated_expenses", "billable_hours"]
    missing_fields = []
    for field in required_fields:
        value = project_row.get(field, 0)
        if pd.isna(value) or value == 0:
            missing_fields.append(field)
    
    completeness_percent = 1.0 - (len(missing_fields) / len(required_fields))
    
    # Status determination
    if pd.isna(gross_margin_pct):
        status = "Unknown"
    elif gross_margin_pct < 0:
        status = "Loss-making"
    elif gross_margin_pct < TARGET_MARGIN_PERCENT:
        status = "At Risk"
    else:
        status = "Healthy"
    
    # Get project name and client from project_details if available
    project_name = project_id
    client_name = "Unknown"
    if project_details is not None and len(project_details) > 0:
        project_name = project_details.get("project_name", project_id)
        client_name = project_details.get("client_name", "Unknown")
    
    return {
        "id": project_id,
        "name": project_name,
        "client": client_name,
        "revenue": revenue,
        "totalCost": total_cost,
        "marginValue": gross_profit,
        "marginPercent": gross_margin_pct if not pd.isna(gross_margin_pct) else None,
        "costBreakdown": cost_breakdown,
        "status": status,
        "dataCompleteness": completeness_percent,
        "missingFields": missing_fields,
        "hours": {
            "billable": billable_hours,
            "total": total_hours
        },
        "effectiveHourlyRate": effective_hourly_rate if not pd.isna(effective_hourly_rate) else None
    }


def detect_drivers(vm: Dict) -> List[Dict]:
    """
    Detect top 3 drivers explaining project profitability.
    
    Args:
        vm: ProjectProfitabilityViewModel
    
    Returns:
        List of driver dicts with:
            - title: str
            - evidence: str (metric values)
            - explanation: str
            - score: float (for ranking)
    """
    drivers = []
    
    revenue = vm["revenue"]
    total_cost = vm["totalCost"]
    labor_cost = vm["costBreakdown"]["laborCost"]
    overhead_cost = vm["costBreakdown"]["overheadCost"]
    margin_percent = vm["marginPercent"]
    billable_hours = vm["hours"]["billable"]
    effective_rate = vm["effectiveHourlyRate"]
    
    # Driver 1: High labor share
    if revenue > 0 and labor_cost > 0:
        labor_share = labor_cost / revenue
        if labor_share >= LABOR_SHARE_HIGH_THRESHOLD:
            drivers.append({
                "title": "High Labor Cost Share",
                "evidence": f"Labor cost is {labor_share:.1%} of revenue (€{labor_cost:,.0f} / €{revenue:,.0f})",
                "explanation": "Labor costs are consuming most of the revenue, leaving little margin for overhead and profit.",
                "score": labor_share
            })
    
    # Driver 2: High overhead share
    if revenue > 0 and overhead_cost > 0:
        overhead_share = overhead_cost / revenue
        if overhead_share >= OVERHEAD_SHARE_HIGH_THRESHOLD:
            drivers.append({
                "title": "High Overhead Allocation",
                "evidence": f"Overhead is {overhead_share:.1%} of revenue (€{overhead_cost:,.0f} / €{revenue:,.0f})",
                "explanation": "Overhead expenses (allocated expenses) are high relative to project revenue.",
                "score": overhead_share
            })
    
    # Driver 3: Low effective rate
    if effective_rate is not None and effective_rate > 0:
        # Estimate blended cost rate if we have labor cost and hours
        if billable_hours > 0 and labor_cost > 0:
            blended_cost_rate = labor_cost / billable_hours
            min_desired_rate = blended_cost_rate * 1.2  # Should be at least 20% above cost
            
            if effective_rate < min_desired_rate:
                drivers.append({
                    "title": "Low Effective Hourly Rate",
                    "evidence": f"Effective rate is €{effective_rate:.2f}/hr (cost rate: €{blended_cost_rate:.2f}/hr)",
                    "explanation": "Revenue per billable hour is too close to cost, providing insufficient margin.",
                    "score": (min_desired_rate - effective_rate) / min_desired_rate
                })
    
    # Driver 4: Low margin vs target
    if margin_percent is not None:
        gap = TARGET_MARGIN_PERCENT - margin_percent
        if gap > 0.05:  # More than 5% below target
            drivers.append({
                "title": "Margin Below Target",
                "evidence": f"Margin is {margin_percent:.1%} (target: {TARGET_MARGIN_PERCENT:.1%}, gap: {gap:.1%})",
                "explanation": f"Project margin is significantly below the target of {TARGET_MARGIN_PERCENT:.0%}.",
                "score": gap
            })
    
    # Driver 5: Total cost too high (fallback if no specific breakdown)
    if revenue > 0 and total_cost > 0 and len(drivers) < 2:
        cost_ratio = total_cost / revenue
        if cost_ratio >= 0.80:  # Costs >= 80% of revenue
            drivers.append({
                "title": "High Total Cost",
                "evidence": f"Total costs are {cost_ratio:.1%} of revenue (€{total_cost:,.0f} / €{revenue:,.0f})",
                "explanation": "Overall project costs are consuming most of the revenue.",
                "score": cost_ratio
            })
    
    # Sort by score descending and return top 3
    drivers_sorted = sorted(drivers, key=lambda x: x["score"], reverse=True)
    return drivers_sorted[:3]


def generate_actions(vm: Dict, drivers: List[Dict]) -> List[Dict]:
    """
    Generate top 3 recommended actions based on drivers.
    
    Args:
        vm: ProjectProfitabilityViewModel
        drivers: List of detected drivers
    
    Returns:
        List of action dicts with:
            - title: str
            - why: str (1 sentence)
            - what: str (1 sentence)
            - impact: "High" | "Medium" | "Low"
    """
    actions = []
    driver_titles = [d["title"] for d in drivers]
    
    # Map drivers to actions
    if "High Labor Cost Share" in driver_titles:
        actions.append({
            "title": "Rebalance Team Mix",
            "why": "Labor costs are too high relative to revenue, reducing margin.",
            "what": "Reduce senior allocation or tighten scope to lower unbillable hours.",
            "impact": "High"
        })
    
    if "High Overhead Allocation" in driver_titles:
        actions.append({
            "title": "Review Overhead Allocation",
            "why": "Allocated overhead expenses are consuming too much of the project's revenue.",
            "what": "Revisit allocation methodology or negotiate overhead structure with finance.",
            "impact": "Medium"
        })
    
    if "Low Effective Hourly Rate" in driver_titles:
        actions.append({
            "title": "Increase Effective Rate",
            "why": "Revenue per hour is too close to cost, leaving insufficient margin.",
            "what": "Reprice the project upward or increase billable utilization to boost effective rate.",
            "impact": "High"
        })
    
    if "Margin Below Target" in driver_titles:
        actions.append({
            "title": "Improve Delivery Efficiency",
            "why": "Margin is below target, indicating costs or pricing need adjustment.",
            "what": "Reduce delivery cost through better scoping or negotiate rate increase with client.",
            "impact": "High"
        })
    
    if "High Total Cost" in driver_titles:
        actions.append({
            "title": "Reduce Overall Costs",
            "why": "Total project costs are consuming most of the revenue.",
            "what": "Review all cost categories and identify areas for reduction or renegotiation.",
            "impact": "Medium"
        })
    
    # If healthy, suggest continuous improvement
    if vm["status"] == "Healthy" and len(actions) == 0:
        margin = vm["marginPercent"]
        if margin is not None and margin < 0.30:  # Room for improvement
            actions.append({
                "title": "Optimize for Higher Margin",
                "why": "Project is healthy but margin could be improved further.",
                "what": "Identify efficiency gains or pricing opportunities to increase margin above 30%.",
                "impact": "Medium"
            })
        actions.append({
            "title": "Document Best Practices",
            "why": "This project is performing well and provides a good model.",
            "what": "Capture what's working (team mix, pricing, scope management) for reuse.",
                "impact": "Low"
        })
        actions.append({
            "title": "Monitor Continuously",
            "why": "Maintain current performance to prevent margin erosion.",
            "what": "Set up monthly reviews to catch early warning signs of scope creep or cost overruns.",
            "impact": "Low"
        })
    
    # Return top 3
    return actions[:3]


def generate_verdict_sentence(vm: Dict, drivers: List[Dict], actions: List[Dict]) -> str:
    """
    Generate the verdict sentence: "This project is bad/good because X — and the fix is Y."
    
    Args:
        vm: ProjectProfitabilityViewModel
        drivers: List of drivers
        actions: List of actions
    
    Returns:
        Verdict sentence
    """
    status = vm["status"]
    margin = vm["marginPercent"]
    
    if status == "Loss-making":
        # Bad project
        if drivers:
            driver_summary = drivers[0]["title"].lower()
            x = f"{driver_summary}"
        else:
            x = "costs exceed revenue"
        
        if actions:
            action_summary = actions[0]["title"].lower()
            y = f"{action_summary}"
        else:
            y = "reduce costs or increase pricing"
        
        margin_text = f"{margin:.1%}" if margin is not None else "negative"
        return f"This project is **loss-making** (margin: {margin_text}) because {x} — and the fix is {y}."
    
    elif status == "At Risk":
        # Risky project
        if drivers:
            driver_summary = drivers[0]["title"].lower()
            x = f"{driver_summary}"
        else:
            x = "margin is below target"
        
        if actions:
            action_summary = actions[0]["title"].lower()
            y = f"{action_summary}"
        else:
            y = "improve pricing or reduce costs"
        
        margin_text = f"{margin:.1%}" if margin is not None else "low"
        return f"This project is **at risk** (margin: {margin_text}) because {x} — and the fix is {y}."
    
    elif status == "Healthy":
        # Good project
        if drivers and drivers[0]["score"] > 0.3:
            # Has some issues even if healthy
            driver_summary = drivers[0]["title"].lower()
            x = f"margin is good despite {driver_summary}"
        else:
            x = "costs are well-controlled and pricing is adequate"
        
        if actions:
            action_summary = actions[0]["title"].lower()
            y = f"{action_summary}"
        else:
            y = "maintain current performance"
        
        margin_text = f"{margin:.1%}" if margin is not None else "positive"
        return f"This project is **healthy** (margin: {margin_text}) because {x} — and the next best improvement is {y}."
    
    else:
        return "This project has **insufficient data** for a verdict — add missing metrics to analyze profitability."


def get_data_confidence(vm: Dict) -> Tuple[str, str]:
    """
    Get data confidence level and message.
    
    Returns:
        (level, message) where level is "High" | "Medium" | "Low"
    """
    completeness = vm["dataCompleteness"]
    missing_fields = vm["missingFields"]
    
    if completeness >= 0.75 and vm["revenue"] > 0 and vm["totalCost"] > 0:
        return ("High", "All key metrics are available.")
    elif completeness >= 0.50:
        return ("Medium", f"Some metrics are missing: {', '.join(missing_fields)}.")
    else:
        return ("Low", f"Critical metrics are missing: {', '.join(missing_fields)}. Add these inputs to make the verdict reliable.")
