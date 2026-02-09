"""
Context Builder - Build compact, JSON-serializable context packages for AI.
Never sends raw full tables or CSVs - only small, structured snippets.
"""

import pandas as pd
from typing import Dict, List, Optional


def build_context(
    intent: Dict,
    metrics_outputs: Dict,
    insights_list: List[Dict],
    max_rows: int = 5
) -> Dict:
    """
    Build compact context package for AI based on query intent.
    
    Args:
        intent: Intent dict with type, entity_id, keywords
        metrics_outputs: Full metrics outputs from metrics engine
        insights_list: List of all insights
        max_rows: Maximum table rows to include (default 5)
    
    Returns:
        Compact context dict with only relevant snippets:
        {
            "kpis": {<key metrics as scalars>},
            "insights": [<relevant insight dicts>],
            "table_snippets": {<top N rows only>},
            "trends": {<optional trend data>}
        }
    """
    intent_type = intent["intent"]
    entity_id = intent["entity_id"]
    
    # Route to specific context builder
    if intent_type == "project":
        return _build_project_context(entity_id, metrics_outputs, insights_list, max_rows)
    elif intent_type == "employee":
        return _build_employee_context(entity_id, metrics_outputs, insights_list, max_rows)
    elif intent_type == "invoices":
        return _build_invoices_context(metrics_outputs, insights_list)
    elif intent_type == "cashflow":
        return _build_cashflow_context(metrics_outputs, insights_list)
    elif intent_type == "utilization":
        return _build_utilization_context(metrics_outputs, insights_list, max_rows)
    elif intent_type == "company":
        return _build_company_context(metrics_outputs, insights_list)
    else:
        return _build_generic_context(metrics_outputs, insights_list, max_rows)


def _build_project_context(
    project_id: Optional[str],
    metrics_outputs: Dict,
    insights_list: List[Dict],
    max_rows: int
) -> Dict:
    """Build compact context for project queries."""
    context = {
        "kpis": {},
        "insights": [],
        "table_snippets": {},
        "trends": {}
    }
    
    projects_metrics = metrics_outputs.get("projects_metrics")
    
    # Get relevant insights (project-specific or all project insights)
    if project_id:
        context["insights"] = [i for i in insights_list if i["entity"] == project_id]
    else:
        context["insights"] = [i for i in insights_list if i["type"].startswith("project")]
        context["insights"] = sorted(
            context["insights"],
            key=lambda x: {"critical": 0, "warning": 1, "info": 2}.get(x["severity"], 3)
        )[:max_rows]
    
    # Get KPIs (scalars only, no dataframes)
    if projects_metrics is not None and len(projects_metrics) > 0:
        if project_id:
            # Specific project KPIs
            proj_row = projects_metrics[projects_metrics["project_id"] == project_id]
            if len(proj_row) > 0:
                row = proj_row.iloc[0]
                context["kpis"] = {
                    "project_id": project_id,
                    "revenue": float(row.get("revenue", 0)),
                    "gross_profit": float(row.get("gross_profit", 0)),
                    "gross_margin_pct": float(row.get("gross_margin_pct", 0)),
                    "labor_cost": float(row.get("labor_cost", 0)),
                    "billable_hours": float(row.get("billable_hours", 0))
                }
        else:
            # Worst projects (top 5 by margin)
            sorted_projects = projects_metrics.sort_values("gross_margin_pct").head(max_rows)
            context["table_snippets"]["worst_projects"] = sorted_projects[[
                "project_id", "revenue", "gross_margin_pct", "gross_profit"
            ]].to_dict("records")
    
    return context


def _build_employee_context(
    employee_id: Optional[str],
    metrics_outputs: Dict,
    insights_list: List[Dict],
    max_rows: int
) -> Dict:
    """Build compact context for employee queries."""
    context = {
        "kpis": {},
        "insights": [],
        "table_snippets": {},
        "trends": {}
    }
    
    employee_util = metrics_outputs.get("employee_utilization")
    
    # Get relevant insights
    if employee_id:
        context["insights"] = [i for i in insights_list if i["entity"] == employee_id]
    else:
        context["insights"] = [i for i in insights_list if i["type"].startswith("employee")]
        context["insights"] = sorted(
            context["insights"],
            key=lambda x: {"critical": 0, "warning": 1, "info": 2}.get(x["severity"], 3)
        )[:max_rows]
    
    # Get KPIs
    if employee_util is not None and len(employee_util) > 0:
        if employee_id:
            emp_row = employee_util[employee_util["employee_id"] == employee_id]
            if len(emp_row) > 0:
                row = emp_row.iloc[0]
                context["kpis"] = {
                    "employee_id": employee_id,
                    "utilization_pct": float(row.get("utilization_pct", 0)),
                    "billable_hours": float(row.get("billable_hours", 0)),
                    "monthly_capacity_hours": float(row.get("monthly_capacity_hours", 0))
                }
        else:
            # Underutilized and overutilized (top 5 each)
            underutil = employee_util[employee_util["utilization_pct"] < 0.6].head(max_rows)
            overutil = employee_util[employee_util["utilization_pct"] > 0.85].head(max_rows)
            
            context["table_snippets"]["underutilized"] = underutil[[
                "employee_id", "utilization_pct", "billable_hours"
            ]].to_dict("records") if len(underutil) > 0 else []
            
            context["table_snippets"]["overutilized"] = overutil[[
                "employee_id", "utilization_pct", "billable_hours"
            ]].to_dict("records") if len(overutil) > 0 else []
    
    return context


def _build_invoices_context(
    metrics_outputs: Dict,
    insights_list: List[Dict]
) -> Dict:
    """Build compact context for invoice queries."""
    context = {
        "kpis": {},
        "insights": [],
        "table_snippets": {},
        "trends": {}
    }
    
    # Get invoice insights
    context["insights"] = [i for i in insights_list if i["type"].startswith("invoices")]
    
    context["kpis"]["invoice_insights_count"] = len(context["insights"])
    
    return context


def _build_cashflow_context(
    metrics_outputs: Dict,
    insights_list: List[Dict]
) -> Dict:
    """Build compact context for cashflow queries."""
    context = {
        "kpis": {},
        "insights": [],
        "table_snippets": {},
        "trends": {}
    }
    
    cashflow_monthly = metrics_outputs.get("cashflow_monthly")
    
    # Get cashflow insights
    context["insights"] = [i for i in insights_list if i["type"].startswith("cashflow")]
    
    # Get KPIs
    if cashflow_monthly is not None and len(cashflow_monthly) > 0:
        df = cashflow_monthly.copy()
        if "month" in df.columns:
            df["month"] = df["month"].astype(str)
            df = df[df["month"] != "Total"]
        
        if len(df) > 0:
            context["kpis"] = {
                "ending_cash": float(df["ending_cash"].iloc[-1]),
                "runway_months": float(metrics_outputs.get("runway_months", 0)),
                "negative_cashflow_months": int(len(df[df["net_cashflow"] < 0]))
            }
            
            # Last 3 months as snippet
            recent = df.tail(3)
            context["table_snippets"]["recent_months"] = recent[[
                "month", "cash_in", "cash_out_total", "net_cashflow", "ending_cash"
            ]].to_dict("records")
    
    return context


def _build_utilization_context(
    metrics_outputs: Dict,
    insights_list: List[Dict],
    max_rows: int
) -> Dict:
    """Build compact context for utilization queries."""
    return _build_employee_context(None, metrics_outputs, insights_list, max_rows)


def _build_company_context(
    metrics_outputs: Dict,
    insights_list: List[Dict]
) -> Dict:
    """Build compact context for company queries."""
    context = {
        "kpis": {},
        "insights": [],
        "table_snippets": {},
        "trends": {}
    }
    
    income_monthly = metrics_outputs.get("income_statement_monthly")
    
    # Get company insights
    context["insights"] = [i for i in insights_list if i["entity"] == "company"]
    
    # Get KPIs
    if income_monthly is not None and len(income_monthly) > 0:
        df = income_monthly.copy()
        if "month" in df.columns:
            df["month"] = df["month"].astype(str)
            df = df[df["month"] != "Total"]
        
        if len(df) > 0:
            context["kpis"] = {
                "total_revenue": float(df["revenue"].sum()),
                "total_ebitda": float(df["ebitda"].sum()),
                "negative_ebitda_months": int(len(df[df["ebitda"] < 0]))
            }
            
            # Last 3 months
            recent = df.tail(3)
            context["table_snippets"]["recent_months"] = recent[[
                "month", "revenue", "ebitda"
            ]].to_dict("records")
    
    return context


def _build_generic_context(
    metrics_outputs: Dict,
    insights_list: List[Dict],
    max_rows: int
) -> Dict:
    """Build generic context (top insights)."""
    context = {
        "kpis": {},
        "insights": [],
        "table_snippets": {},
        "trends": {}
    }
    
    # Top insights by severity
    sorted_insights = sorted(
        insights_list,
        key=lambda x: {"critical": 0, "warning": 1, "info": 2}.get(x["severity"], 3)
    )
    context["insights"] = sorted_insights[:max_rows]
    
    return context
