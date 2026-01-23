"""
Deterministic Insights Engine.
Generates rule-based insights from metrics outputs WITHOUT creating new data.
"""

import pandas as pd
from typing import Dict, List, Optional
from ..config import UNDERUTILIZED_THRESHOLD, OVERUTILIZED_THRESHOLD


def generate_insights(
    projects_metrics: pd.DataFrame,
    projects_metrics_monthly: Optional[pd.DataFrame] = None,
    employee_utilization: Optional[pd.DataFrame] = None,
    income_statement_monthly: Optional[pd.DataFrame] = None,
    cashflow_monthly: Optional[pd.DataFrame] = None,
    invoices: Optional[pd.DataFrame] = None,
    low_margin_threshold: float = 0.1,
    margin_decline_months: int = 3
) -> List[Dict]:
    """
    Generate deterministic insights from metrics outputs.
    
    Args:
        projects_metrics: Overall project metrics (project_id, revenue, gross_margin_pct, etc.)
        projects_metrics_monthly: Monthly project metrics (optional, for trend analysis)
        employee_utilization: Employee utilization metrics (optional)
        income_statement_monthly: Monthly income statement (optional)
        cashflow_monthly: Monthly cashflow (optional)
        invoices: Invoices DataFrame (optional, for overdue analysis)
        low_margin_threshold: Threshold for low margin flag (default 10%)
        margin_decline_months: Number of months to check for margin decline (default 3)
    
    Returns:
        List of insight dicts, each with:
            - type: str (e.g., "project_margin_issue", "employee_underutilized")
            - severity: str ("info", "warning", "critical")
            - entity: str (project_id, employee_id, or "company")
            - message: str (short factual statement)
            - drivers: List[str] (reasons for the insight)
    """
    insights = []
    
    # Project-level insights
    if projects_metrics is not None and len(projects_metrics) > 0:
        insights.extend(_analyze_project_margins(projects_metrics, low_margin_threshold))
        insights.extend(_analyze_project_rates(projects_metrics))
        
        if projects_metrics_monthly is not None and len(projects_metrics_monthly) > 0:
            insights.extend(_analyze_margin_trends(projects_metrics_monthly, margin_decline_months))
    
    # Employee-level insights
    if employee_utilization is not None and len(employee_utilization) > 0:
        insights.extend(_analyze_employee_utilization(employee_utilization))
    
    # Company-level insights
    if income_statement_monthly is not None and len(income_statement_monthly) > 0:
        insights.extend(_analyze_company_financials(income_statement_monthly))
    
    if cashflow_monthly is not None and len(cashflow_monthly) > 0:
        insights.extend(_analyze_cashflow(cashflow_monthly))
    
    # Invoice-level insights
    if invoices is not None and len(invoices) > 0:
        insights.extend(_analyze_overdue_invoices(invoices))
    
    return insights


def _analyze_project_margins(projects_metrics: pd.DataFrame, low_margin_threshold: float) -> List[Dict]:
    """Analyze project margins for issues."""
    insights = []
    
    # Negative margin projects
    negative_margin = projects_metrics[projects_metrics["gross_margin_pct"] < 0]
    for _, row in negative_margin.iterrows():
        insights.append({
            "type": "project_margin_issue",
            "severity": "critical",
            "entity": row["project_id"],
            "message": f"Project {row['project_id']} has negative gross margin ({row['gross_margin_pct']:.1f}%)",
            "drivers": [
                f"Revenue: €{row['revenue']:,.0f}",
                f"Total costs: €{row['labor_cost'] + row.get('allocated_expenses', 0):,.0f}",
                f"Gross profit: €{row['gross_profit']:,.0f}"
            ]
        })
    
    # Low margin projects
    low_margin = projects_metrics[
        (projects_metrics["gross_margin_pct"] >= 0) & 
        (projects_metrics["gross_margin_pct"] < low_margin_threshold) &
        (projects_metrics["revenue"] > 0)
    ]
    for _, row in low_margin.iterrows():
        insights.append({
            "type": "project_margin_issue",
            "severity": "warning",
            "entity": row["project_id"],
            "message": f"Project {row['project_id']} has low gross margin ({row['gross_margin_pct']:.1f}%)",
            "drivers": [
                f"Margin below {low_margin_threshold*100:.0f}% threshold",
                f"Revenue: €{row['revenue']:,.0f}",
                f"Gross profit: €{row['gross_profit']:,.0f}"
            ]
        })
    
    return insights


def _analyze_project_rates(projects_metrics: pd.DataFrame) -> List[Dict]:
    """Analyze effective hourly rates."""
    insights = []
    
    # Projects with very low effective hourly rate
    low_rate = projects_metrics[
        (projects_metrics["effective_hourly_rate"] > 0) &
        (projects_metrics["effective_hourly_rate"] < 50) &
        (projects_metrics["billable_hours"] > 0)
    ]
    for _, row in low_rate.iterrows():
        insights.append({
            "type": "project_rate_issue",
            "severity": "warning",
            "entity": row["project_id"],
            "message": f"Project {row['project_id']} has low effective hourly rate (€{row['effective_hourly_rate']:.2f}/hr)",
            "drivers": [
                f"Revenue: €{row['revenue']:,.0f}",
                f"Billable hours: {row['billable_hours']:.1f}",
                f"Effective rate below typical threshold (€50/hr)"
            ]
        })
    
    return insights


def _analyze_margin_trends(projects_metrics_monthly: pd.DataFrame, months: int) -> List[Dict]:
    """Analyze margin trends over time."""
    insights = []
    
    # Convert month to string for consistent comparison
    if "month" in projects_metrics_monthly.columns:
        projects_metrics_monthly = projects_metrics_monthly.copy()
        projects_metrics_monthly["month"] = projects_metrics_monthly["month"].astype(str)
        # Filter out "Total" row
        projects_metrics_monthly = projects_metrics_monthly[projects_metrics_monthly["month"] != "Total"]
    
    # Group by project and get last N months
    for project_id in projects_metrics_monthly["project_id"].unique():
        project_data = projects_metrics_monthly[
            projects_metrics_monthly["project_id"] == project_id
        ].sort_values("month")
        
        if len(project_data) < months:
            continue
        
        # Get last N months
        recent = project_data.tail(months)
        
        # Check for declining margin
        if len(recent) >= 2:
            first_margin = recent.iloc[0]["gross_margin_pct"]
            last_margin = recent.iloc[-1]["gross_margin_pct"]
            
            if first_margin > 0 and last_margin < first_margin and (first_margin - last_margin) > 0.05:
                insights.append({
                    "type": "project_margin_decline",
                    "severity": "warning",
                    "entity": project_id,
                    "message": f"Project {project_id} shows declining margin over last {months} months",
                    "drivers": [
                        f"Margin dropped from {first_margin:.1f}% to {last_margin:.1f}%",
                        f"Change: {first_margin - last_margin:.1f} percentage points"
                    ]
                })
    
    return insights


def _analyze_employee_utilization(employee_utilization: pd.DataFrame) -> List[Dict]:
    """Analyze employee utilization."""
    insights = []
    
    # Underutilized employees
    underutilized = employee_utilization[
        employee_utilization["utilization_pct"] < UNDERUTILIZED_THRESHOLD
    ]
    for _, row in underutilized.iterrows():
        insights.append({
            "type": "employee_underutilized",
            "severity": "warning",
            "entity": row["employee_id"],
            "message": f"Employee {row['employee_id']} is underutilized ({row['utilization_pct']:.1f}%)",
            "drivers": [
                f"Billable hours: {row.get('billable_hours', 0):.1f}",
                f"Capacity: {row.get('monthly_capacity_hours', 0):.1f}",
                f"Below {UNDERUTILIZED_THRESHOLD*100:.0f}% threshold"
            ]
        })
    
    # Overutilized employees
    overutilized = employee_utilization[
        employee_utilization["utilization_pct"] > OVERUTILIZED_THRESHOLD
    ]
    for _, row in overutilized.iterrows():
        insights.append({
            "type": "employee_overutilized",
            "severity": "warning",
            "entity": row["employee_id"],
            "message": f"Employee {row['employee_id']} is overutilized ({row['utilization_pct']:.1f}%)",
            "drivers": [
                f"Billable hours: {row.get('billable_hours', 0):.1f}",
                f"Capacity: {row.get('monthly_capacity_hours', 0):.1f}",
                f"Above {OVERUTILIZED_THRESHOLD*100:.0f}% threshold"
            ]
        })
    
    return insights


def _analyze_company_financials(income_statement_monthly: pd.DataFrame) -> List[Dict]:
    """Analyze company-level financials."""
    insights = []
    
    # Filter out "Total" row
    df = income_statement_monthly.copy()
    if "month" in df.columns:
        df["month"] = df["month"].astype(str)
        df = df[df["month"] != "Total"]
    
    if len(df) == 0:
        return insights
    
    # Check for negative EBITDA
    negative_ebitda = df[df["ebitda"] < 0]
    if len(negative_ebitda) > 0:
        months = negative_ebitda["month"].tolist()
        total_negative = negative_ebitda["ebitda"].sum()
        insights.append({
            "type": "company_negative_ebitda",
            "severity": "critical",
            "entity": "company",
            "message": f"Company has negative EBITDA in {len(negative_ebitda)} month(s)",
            "drivers": [
                f"Months: {', '.join(months[:5])}" + ("..." if len(months) > 5 else ""),
                f"Total negative EBITDA: €{total_negative:,.0f}"
            ]
        })
    
    # Check for declining revenue trend
    if len(df) >= 3:
        recent = df.tail(3).sort_values("month")
        if len(recent) >= 2:
            first_revenue = recent.iloc[0]["revenue"]
            last_revenue = recent.iloc[-1]["revenue"]
            if first_revenue > 0 and last_revenue < first_revenue * 0.9:
                insights.append({
                    "type": "company_revenue_decline",
                    "severity": "warning",
                    "entity": "company",
                    "message": "Company revenue shows declining trend over last 3 months",
                    "drivers": [
                        f"Revenue dropped from €{first_revenue:,.0f} to €{last_revenue:,.0f}",
                        f"Change: {((last_revenue - first_revenue) / first_revenue * 100):.1f}%"
                    ]
                })
    
    return insights


def _analyze_cashflow(cashflow_monthly: pd.DataFrame) -> List[Dict]:
    """Analyze cashflow for stress signals."""
    insights = []
    
    # Filter out "Total" row
    df = cashflow_monthly.copy()
    if "month" in df.columns:
        df["month"] = df["month"].astype(str)
        df = df[df["month"] != "Total"]
    
    if len(df) == 0:
        return insights
    
    # Check for declining ending cash
    if len(df) >= 3:
        recent = df.tail(3).sort_values("month")
        if len(recent) >= 2:
            first_cash = recent.iloc[0]["ending_cash"]
            last_cash = recent.iloc[-1]["ending_cash"]
            if first_cash > 0 and last_cash < first_cash * 0.8:
                insights.append({
                    "type": "cashflow_stress",
                    "severity": "warning",
                    "entity": "company",
                    "message": "Ending cash balance declining over last 3 months",
                    "drivers": [
                        f"Cash dropped from €{first_cash:,.0f} to €{last_cash:,.0f}",
                        f"Change: {((last_cash - first_cash) / first_cash * 100):.1f}%"
                    ]
                })
    
    # Check for negative net cashflow
    negative_cashflow = df[df["net_cashflow"] < 0]
    if len(negative_cashflow) > 0:
        months = negative_cashflow["month"].tolist()
        total_negative = negative_cashflow["net_cashflow"].sum()
        insights.append({
            "type": "cashflow_negative",
            "severity": "warning",
            "entity": "company",
            "message": f"Negative net cashflow in {len(negative_cashflow)} month(s)",
            "drivers": [
                f"Months: {', '.join(months[:5])}" + ("..." if len(months) > 5 else ""),
                f"Total negative cashflow: €{total_negative:,.0f}"
            ]
        })
    
    return insights


def _analyze_overdue_invoices(invoices: pd.DataFrame) -> List[Dict]:
    """Analyze overdue invoices."""
    insights = []
    
    if "payment_date" not in invoices.columns or "due_date" not in invoices.columns:
        return insights
    
    # Convert dates
    invoices = invoices.copy()
    invoices["due_date_ts"] = pd.to_datetime(invoices["due_date"], errors="coerce")
    invoices["payment_date_ts"] = pd.to_datetime(invoices["payment_date"], errors="coerce")
    
    # Find overdue invoices (payment_date > due_date or payment_date is null and due_date is past)
    now = pd.Timestamp.now()
    overdue = invoices[
        (
            (invoices["payment_date_ts"].isna()) & (invoices["due_date_ts"] < now)
        ) | (
            (invoices["payment_date_ts"].notna()) & 
            (invoices["payment_date_ts"] > invoices["due_date_ts"])
        )
    ]
    
    if len(overdue) > 0:
        total_overdue = overdue["amount_eur"].sum()
        insights.append({
            "type": "invoices_overdue",
            "severity": "warning",
            "entity": "company",
            "message": f"{len(overdue)} invoice(s) are overdue",
            "drivers": [
                f"Total overdue amount: €{total_overdue:,.0f}",
                f"Average days overdue: {(now - overdue['due_date_ts']).dt.days.mean():.0f}"
            ]
        })
    
    return insights
