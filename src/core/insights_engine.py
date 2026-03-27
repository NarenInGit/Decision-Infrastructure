"""
Deterministic Insights Engine.
Generates rule-based insights from metrics outputs without creating new data.
"""

from typing import Dict, List, Optional

import pandas as pd

from ..config import OVERUTILIZED_THRESHOLD, UNDERUTILIZED_THRESHOLD


def generate_insights(
    projects_metrics: pd.DataFrame,
    projects_metrics_monthly: Optional[pd.DataFrame] = None,
    employee_utilization: Optional[pd.DataFrame] = None,
    income_statement_monthly: Optional[pd.DataFrame] = None,
    cashflow_monthly: Optional[pd.DataFrame] = None,
    invoices: Optional[pd.DataFrame] = None,
    as_of_date: Optional[pd.Timestamp] = None,
    low_margin_threshold: float = 0.1,
    margin_decline_months: int = 3,
) -> List[Dict]:
    """Generate deterministic insights from metrics outputs."""
    insights: List[Dict] = []

    if projects_metrics is not None and len(projects_metrics) > 0:
        insights.extend(_analyze_project_margins(projects_metrics, low_margin_threshold))
        insights.extend(_analyze_project_rates(projects_metrics))
        if projects_metrics_monthly is not None and len(projects_metrics_monthly) > 0:
            insights.extend(_analyze_margin_trends(projects_metrics_monthly, margin_decline_months))

    if employee_utilization is not None and len(employee_utilization) > 0:
        insights.extend(_analyze_employee_utilization(employee_utilization))

    if income_statement_monthly is not None and len(income_statement_monthly) > 0:
        insights.extend(_analyze_company_financials(income_statement_monthly))

    if cashflow_monthly is not None and len(cashflow_monthly) > 0:
        insights.extend(_analyze_cashflow(cashflow_monthly))

    if invoices is not None and len(invoices) > 0:
        insights.extend(_analyze_overdue_invoices(invoices, as_of_date=as_of_date))

    return insights


def _analyze_project_margins(projects_metrics: pd.DataFrame, low_margin_threshold: float) -> List[Dict]:
    insights: List[Dict] = []

    negative_margin = projects_metrics[projects_metrics["gross_margin_pct"] < 0]
    for _, row in negative_margin.iterrows():
        insights.append(
            {
                "type": "project_margin_issue",
                "severity": "critical",
                "entity": row["project_id"],
                "message": f"Project {row['project_id']} has negative gross margin ({row['gross_margin_pct']:.1%})",
                "drivers": [
                    f"Revenue: EUR {row['revenue']:,.0f}",
                    f"Total costs: EUR {row['labor_cost'] + row.get('allocated_expenses', 0):,.0f}",
                    f"Gross profit: EUR {row['gross_profit']:,.0f}",
                ],
            }
        )

    low_margin = projects_metrics[
        (projects_metrics["gross_margin_pct"] >= 0)
        & (projects_metrics["gross_margin_pct"] < low_margin_threshold)
        & (projects_metrics["revenue"] > 0)
    ]
    for _, row in low_margin.iterrows():
        insights.append(
            {
                "type": "project_margin_issue",
                "severity": "warning",
                "entity": row["project_id"],
                "message": f"Project {row['project_id']} has low gross margin ({row['gross_margin_pct']:.1%})",
                "drivers": [
                    f"Margin below {low_margin_threshold * 100:.0f}% threshold",
                    f"Revenue: EUR {row['revenue']:,.0f}",
                    f"Gross profit: EUR {row['gross_profit']:,.0f}",
                ],
            }
        )

    return insights


def _analyze_project_rates(projects_metrics: pd.DataFrame) -> List[Dict]:
    insights: List[Dict] = []
    low_rate = projects_metrics[
        (projects_metrics["effective_hourly_rate"] > 0)
        & (projects_metrics["effective_hourly_rate"] < 50)
        & (projects_metrics["billable_hours"] > 0)
    ]
    for _, row in low_rate.iterrows():
        insights.append(
            {
                "type": "project_rate_issue",
                "severity": "warning",
                "entity": row["project_id"],
                "message": f"Project {row['project_id']} has low effective hourly rate (EUR {row['effective_hourly_rate']:.2f}/hr)",
                "drivers": [
                    f"Revenue: EUR {row['revenue']:,.0f}",
                    f"Billable hours: {row['billable_hours']:.1f}",
                    "Effective rate below typical threshold (EUR 50/hr)",
                ],
            }
        )
    return insights


def _analyze_margin_trends(projects_metrics_monthly: pd.DataFrame, months: int) -> List[Dict]:
    insights: List[Dict] = []
    df = projects_metrics_monthly.copy()
    if "month" in df.columns:
        df["month"] = df["month"].astype(str)
        df = df[df["month"] != "Total"]

    for project_id in df["project_id"].unique():
        project_data = df[df["project_id"] == project_id].sort_values("month")
        if len(project_data) < months:
            continue

        recent = project_data.tail(months)
        first_margin = recent.iloc[0]["gross_margin_pct"]
        last_margin = recent.iloc[-1]["gross_margin_pct"]
        if first_margin > 0 and last_margin < first_margin and (first_margin - last_margin) > 0.05:
            insights.append(
                {
                    "type": "project_margin_decline",
                    "severity": "warning",
                    "entity": project_id,
                    "message": f"Project {project_id} shows declining margin over last {months} months",
                    "drivers": [
                        f"Margin dropped from {first_margin:.1%} to {last_margin:.1%}",
                        f"Change: {(first_margin - last_margin) * 100:.1f} percentage points",
                    ],
                }
            )
    return insights


def _analyze_employee_utilization(employee_utilization: pd.DataFrame) -> List[Dict]:
    insights: List[Dict] = []

    underutilized = employee_utilization[employee_utilization["utilization_pct"] < UNDERUTILIZED_THRESHOLD]
    for _, row in underutilized.iterrows():
        insights.append(
            {
                "type": "employee_underutilized",
                "severity": "warning",
                "entity": row["employee_id"],
                "message": f"Employee {row['employee_id']} is underutilized ({row['utilization_pct']:.1%})",
                "drivers": [
                    f"Billable hours: {row.get('billable_hours', 0):.1f}",
                    f"Capacity: {row.get('monthly_capacity_hours', row.get('prorated_capacity', 0)):.1f}",
                    f"Below {UNDERUTILIZED_THRESHOLD * 100:.0f}% threshold",
                ],
            }
        )

    overutilized = employee_utilization[employee_utilization["utilization_pct"] > OVERUTILIZED_THRESHOLD]
    for _, row in overutilized.iterrows():
        insights.append(
            {
                "type": "employee_overutilized",
                "severity": "warning",
                "entity": row["employee_id"],
                "message": f"Employee {row['employee_id']} is overutilized ({row['utilization_pct']:.1%})",
                "drivers": [
                    f"Billable hours: {row.get('billable_hours', 0):.1f}",
                    f"Capacity: {row.get('monthly_capacity_hours', row.get('prorated_capacity', 0)):.1f}",
                    f"Above {OVERUTILIZED_THRESHOLD * 100:.0f}% threshold",
                ],
            }
        )

    return insights


def _analyze_company_financials(income_statement_monthly: pd.DataFrame) -> List[Dict]:
    insights: List[Dict] = []
    df = income_statement_monthly.copy()
    if "month" in df.columns:
        df["month"] = df["month"].astype(str)
        df = df[df["month"] != "Total"]

    if df.empty:
        return insights

    negative_ebitda = df[df["ebitda"] < 0]
    if not negative_ebitda.empty:
        months = negative_ebitda["month"].tolist()
        total_negative = negative_ebitda["ebitda"].sum()
        insights.append(
            {
                "type": "company_negative_ebitda",
                "severity": "critical",
                "entity": "company",
                "message": f"Company has negative EBITDA in {len(negative_ebitda)} month(s)",
                "drivers": [
                    f"Months: {', '.join(months[:5])}" + ("..." if len(months) > 5 else ""),
                    f"Total negative EBITDA: EUR {total_negative:,.0f}",
                ],
            }
        )

    if len(df) >= 3:
        recent = df.tail(3).sort_values("month")
        first_revenue = recent.iloc[0]["revenue"]
        last_revenue = recent.iloc[-1]["revenue"]
        if first_revenue > 0 and last_revenue < first_revenue * 0.9:
            insights.append(
                {
                    "type": "company_revenue_decline",
                    "severity": "warning",
                    "entity": "company",
                    "message": "Company revenue shows declining trend over last 3 months",
                    "drivers": [
                        f"Revenue dropped from EUR {first_revenue:,.0f} to EUR {last_revenue:,.0f}",
                        f"Change: {((last_revenue - first_revenue) / first_revenue * 100):.1f}%",
                    ],
                }
            )

    return insights


def _analyze_cashflow(cashflow_monthly: pd.DataFrame) -> List[Dict]:
    insights: List[Dict] = []
    df = cashflow_monthly.copy()
    if "month" in df.columns:
        df["month"] = df["month"].astype(str)
        df = df[df["month"] != "Total"]

    if df.empty:
        return insights

    if len(df) >= 3:
        recent = df.tail(3).sort_values("month")
        first_cash = recent.iloc[0]["ending_cash"]
        last_cash = recent.iloc[-1]["ending_cash"]
        if first_cash > 0 and last_cash < first_cash * 0.8:
            insights.append(
                {
                    "type": "cashflow_stress",
                    "severity": "warning",
                    "entity": "company",
                    "message": "Ending cash balance declining over last 3 months",
                    "drivers": [
                        f"Cash dropped from EUR {first_cash:,.0f} to EUR {last_cash:,.0f}",
                        f"Change: {((last_cash - first_cash) / first_cash * 100):.1f}%",
                    ],
                }
            )

    negative_cashflow = df[df["net_cashflow"] < 0]
    if not negative_cashflow.empty:
        months = negative_cashflow["month"].tolist()
        total_negative = negative_cashflow["net_cashflow"].sum()
        insights.append(
            {
                "type": "cashflow_negative",
                "severity": "warning",
                "entity": "company",
                "message": f"Negative net cashflow in {len(negative_cashflow)} month(s)",
                "drivers": [
                    f"Months: {', '.join(months[:5])}" + ("..." if len(months) > 5 else ""),
                    f"Total negative cashflow: EUR {total_negative:,.0f}",
                ],
            }
        )
    return insights


def _analyze_overdue_invoices(
    invoices: pd.DataFrame,
    as_of_date: Optional[pd.Timestamp] = None,
) -> List[Dict]:
    insights: List[Dict] = []
    if "payment_date" not in invoices.columns or "due_date" not in invoices.columns:
        return insights

    df = invoices.copy()
    df["due_date_ts"] = pd.to_datetime(df["due_date"], errors="coerce")
    df["payment_date_ts"] = pd.to_datetime(df["payment_date"], errors="coerce")

    if as_of_date is None:
        candidates = []
        for col in ["payment_date_ts", "due_date_ts"]:
            if df[col].notna().any():
                candidates.append(df[col].max())
        as_of_date = max(candidates) if candidates else pd.Timestamp("today").normalize()

    overdue = df[
        ((df["payment_date_ts"].isna()) & (df["due_date_ts"] < as_of_date))
        | ((df["payment_date_ts"].notna()) & (df["payment_date_ts"] > df["due_date_ts"]))
    ]

    if not overdue.empty:
        total_overdue = overdue["amount_eur"].sum()
        average_days_overdue = (pd.Timestamp(as_of_date) - overdue["due_date_ts"]).dt.days.mean()
        insights.append(
            {
                "type": "invoices_overdue",
                "severity": "warning",
                "entity": "company",
                "message": f"{len(overdue)} invoice(s) are overdue",
                "drivers": [
                    f"Total overdue amount: EUR {total_overdue:,.0f}",
                    f"As of date: {pd.Timestamp(as_of_date).date()}",
                    f"Average days overdue: {average_days_overdue:.0f}",
                ],
            }
        )
    return insights
