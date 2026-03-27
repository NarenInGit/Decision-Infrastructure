"""
Metrics engine - single source of truth for all calculations.
"""

from typing import Dict, Optional

import numpy as np
import pandas as pd

from .config import DEFAULT_STARTING_CASH, INTERNAL_PROJECT_ID


def _copy_frame(df: pd.DataFrame) -> pd.DataFrame:
    return df.copy() if df is not None else pd.DataFrame()


def _normalize_period_series(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series).dt.to_period("M")


def _stable_cache_key(
    data: Dict[str, pd.DataFrame],
    starting_cash: float,
    start_date: Optional[pd.Timestamp],
    end_date: Optional[pd.Timestamp],
    as_of_date: Optional[pd.Timestamp],
) -> str:
    parts = [
        f"starting_cash={starting_cash:.2f}",
        f"start={start_date.isoformat() if start_date is not None else 'none'}",
        f"end={end_date.isoformat() if end_date is not None else 'none'}",
        f"as_of={as_of_date.isoformat() if as_of_date is not None else 'none'}",
    ]
    for name in sorted(data.keys()):
        df = data[name]
        parts.append(f"{name}:{len(df)}")
    return "|".join(parts)


def compute_daily_time_cost(time_entries: pd.DataFrame) -> pd.DataFrame:
    """
    Compute daily time cost table.
    """
    df = _copy_frame(time_entries)
    if df.empty:
        return df

    df["labor_cost_eur"] = df["hours_logged"] * df["hourly_cost_eur"]
    billable_mask = (df["activity_type"] == "billable") & (df["project_id"] != INTERNAL_PROJECT_ID)
    df["billable_hours"] = np.where(billable_mask, df["hours_logged"], 0.0)
    df["non_billable_hours"] = np.where(billable_mask, 0.0, df["hours_logged"])
    df["is_internal"] = df["project_id"] == INTERNAL_PROJECT_ID
    return df


def compute_project_metrics(
    time_entries: pd.DataFrame,
    invoices: pd.DataFrame,
    expenses: pd.DataFrame,
    by_month: bool = False,
) -> pd.DataFrame:
    """
    Compute project-level profitability metrics.
    """
    daily_cost = compute_daily_time_cost(time_entries)
    invoices_df = _copy_frame(invoices)
    expenses_df = _copy_frame(expenses)

    if by_month:
        daily_cost["month"] = _normalize_period_series(daily_cost["date"])
        project_time = (
            daily_cost.groupby(["project_id", "month"], dropna=False)[["billable_hours", "hours_logged", "labor_cost_eur"]]
            .sum()
            .reset_index()
            .rename(columns={"hours_logged": "total_hours", "labor_cost_eur": "labor_cost"})
        )

        invoices_df["month"] = _normalize_period_series(invoices_df["invoice_date"])
        revenue = (
            invoices_df.groupby(["project_id", "month"], dropna=False)["amount_eur"]
            .sum()
            .reset_index()
            .rename(columns={"amount_eur": "revenue"})
        )

        expenses_with_allocation = expenses_df[expenses_df["allocated_project_id"].notna()].copy()
        expenses_with_allocation["month"] = _normalize_period_series(expenses_with_allocation["date"])
        allocated_exp = (
            expenses_with_allocation.groupby(["allocated_project_id", "month"], dropna=False)["amount_eur"]
            .sum()
            .reset_index()
            .rename(columns={"allocated_project_id": "project_id", "amount_eur": "allocated_expenses"})
        )

        result = project_time.merge(revenue, on=["project_id", "month"], how="outer")
        result = result.merge(allocated_exp, on=["project_id", "month"], how="outer")
    else:
        project_time = (
            daily_cost.groupby("project_id", dropna=False)[["billable_hours", "hours_logged", "labor_cost_eur"]]
            .sum()
            .reset_index()
            .rename(columns={"hours_logged": "total_hours", "labor_cost_eur": "labor_cost"})
        )
        revenue = (
            invoices_df.groupby("project_id", dropna=False)["amount_eur"]
            .sum()
            .reset_index()
            .rename(columns={"amount_eur": "revenue"})
        )
        expenses_with_allocation = expenses_df[expenses_df["allocated_project_id"].notna()].copy()
        allocated_exp = (
            expenses_with_allocation.groupby("allocated_project_id", dropna=False)["amount_eur"]
            .sum()
            .reset_index()
            .rename(columns={"allocated_project_id": "project_id", "amount_eur": "allocated_expenses"})
        )

        result = project_time.merge(revenue, on="project_id", how="outer")
        result = result.merge(allocated_exp, on="project_id", how="outer")

    for col in ["allocated_expenses", "revenue", "labor_cost", "billable_hours", "total_hours"]:
        if col not in result.columns:
            result[col] = 0.0
    result[["allocated_expenses", "revenue", "labor_cost", "billable_hours", "total_hours"]] = result[
        ["allocated_expenses", "revenue", "labor_cost", "billable_hours", "total_hours"]
    ].fillna(0.0)

    result["gross_profit"] = result["revenue"] - result["labor_cost"] - result["allocated_expenses"]
    result["gross_margin_pct"] = np.where(result["revenue"] > 0, result["gross_profit"] / result["revenue"], np.nan)
    result["effective_hourly_rate"] = np.where(
        result["billable_hours"] > 0, result["revenue"] / result["billable_hours"], np.nan
    )
    return result


def compute_employee_utilization(
    time_entries: pd.DataFrame,
    employees: pd.DataFrame,
    by_month: bool = False,
) -> pd.DataFrame:
    """
    Compute employee utilization metrics.
    """
    daily_cost = compute_daily_time_cost(time_entries)
    employees_df = _copy_frame(employees)
    if employees_df.empty:
        return pd.DataFrame()

    employees_df["monthly_capacity_hours"] = employees_df["weekly_capacity_hours"] * 52 / 12

    if by_month:
        daily_cost["month"] = _normalize_period_series(daily_cost["date"])
        employees_df["start_month"] = _normalize_period_series(employees_df["start_date"])

        emp_time = (
            daily_cost.groupby(["employee_id", "month"], dropna=False)[["billable_hours", "hours_logged", "labor_cost_eur"]]
            .sum()
            .reset_index()
        )
        emp_time["non_billable_hours"] = emp_time["hours_logged"] - emp_time["billable_hours"]

        internal_hours = (
            daily_cost[daily_cost["project_id"] == INTERNAL_PROJECT_ID]
            .groupby(["employee_id", "month"], dropna=False)["hours_logged"]
            .sum()
            .reset_index()
            .rename(columns={"hours_logged": "internal_hours"})
        )

        result = emp_time.merge(
            employees_df[["employee_id", "monthly_capacity_hours", "start_month", "start_date"]],
            on="employee_id",
            how="left",
        )
        result["prorated_capacity"] = result.apply(
            lambda row: (
                row["monthly_capacity_hours"]
                * (row["month"].days_in_month - pd.to_datetime(row["start_date"]).day + 1)
                / row["month"].days_in_month
                if row["month"] == row["start_month"]
                else row["monthly_capacity_hours"]
            ),
            axis=1,
        )
        result = result.merge(internal_hours, on=["employee_id", "month"], how="left")
        result["internal_hours"] = result["internal_hours"].fillna(0.0)
    else:
        emp_time = (
            daily_cost.groupby("employee_id", dropna=False)[["billable_hours", "hours_logged", "labor_cost_eur"]]
            .sum()
            .reset_index()
        )
        internal_hours = (
            daily_cost[daily_cost["project_id"] == INTERNAL_PROJECT_ID]
            .groupby("employee_id", dropna=False)["hours_logged"]
            .sum()
            .reset_index()
            .rename(columns={"hours_logged": "internal_hours"})
        )

        result = emp_time.merge(employees_df[["employee_id", "monthly_capacity_hours"]], on="employee_id", how="left")
        result = result.merge(internal_hours, on="employee_id", how="left")
        result["internal_hours"] = result["internal_hours"].fillna(0.0)
        result["prorated_capacity"] = result["monthly_capacity_hours"]
        result["non_billable_hours"] = result["hours_logged"] - result["billable_hours"]

    result["utilization_pct"] = np.where(
        result["prorated_capacity"] > 0, result["billable_hours"] / result["prorated_capacity"], np.nan
    )
    result["cost_of_time"] = result["labor_cost_eur"]
    return result


def compute_income_statement(
    invoices: pd.DataFrame,
    time_entries: pd.DataFrame,
    expenses: pd.DataFrame,
    start_date: Optional[pd.Timestamp] = None,
    end_date: Optional[pd.Timestamp] = None,
) -> pd.DataFrame:
    """
    Compute monthly Income Statement (accrual basis).
    """
    invoices_df = _copy_frame(invoices)
    daily_cost = compute_daily_time_cost(time_entries)
    expenses_df = _copy_frame(expenses)

    if start_date is not None:
        invoices_df = invoices_df[pd.to_datetime(invoices_df["invoice_date"]) >= start_date].copy()
        daily_cost = daily_cost[pd.to_datetime(daily_cost["date"]) >= start_date].copy()
        expenses_df = expenses_df[pd.to_datetime(expenses_df["date"]) >= start_date].copy()
    if end_date is not None:
        invoices_df = invoices_df[pd.to_datetime(invoices_df["invoice_date"]) <= end_date].copy()
        daily_cost = daily_cost[pd.to_datetime(daily_cost["date"]) <= end_date].copy()
        expenses_df = expenses_df[pd.to_datetime(expenses_df["date"]) <= end_date].copy()

    invoices_df["month"] = _normalize_period_series(invoices_df["invoice_date"])
    revenue = (
        invoices_df.groupby("month", dropna=False)["amount_eur"].sum().reset_index().rename(columns={"amount_eur": "revenue"})
    )

    daily_cost["month"] = _normalize_period_series(daily_cost["date"])
    direct_labor = (
        daily_cost[daily_cost["billable_hours"] > 0]
        .groupby("month", dropna=False)["labor_cost_eur"]
        .sum()
        .reset_index()
        .rename(columns={"labor_cost_eur": "direct_labor_cost"})
    )

    expenses_with_allocation = expenses_df[expenses_df["allocated_project_id"].notna()].copy()
    expenses_with_allocation["month"] = _normalize_period_series(expenses_with_allocation["date"])
    direct_exp = (
        expenses_with_allocation.groupby("month", dropna=False)["amount_eur"]
        .sum()
        .reset_index()
        .rename(columns={"amount_eur": "direct_allocated_expenses"})
    )

    overhead_labor = (
        daily_cost[daily_cost["billable_hours"] == 0]
        .groupby("month", dropna=False)["labor_cost_eur"]
        .sum()
        .reset_index()
        .rename(columns={"labor_cost_eur": "overhead_labor_cost"})
    )

    overhead_exp = expenses_df[expenses_df["allocated_project_id"].isna()].copy()
    overhead_exp["month"] = _normalize_period_series(overhead_exp["date"])
    overhead_exp = (
        overhead_exp.groupby("month", dropna=False)["amount_eur"]
        .sum()
        .reset_index()
        .rename(columns={"amount_eur": "overhead_expenses"})
    )

    result = revenue.merge(direct_labor, on="month", how="outer")
    result = result.merge(direct_exp, on="month", how="outer")
    result = result.merge(overhead_labor, on="month", how="outer")
    result = result.merge(overhead_exp, on="month", how="outer")
    result = result.fillna(0.0).sort_values("month")

    result["cogs"] = result["direct_labor_cost"] + result["direct_allocated_expenses"]
    result["gross_profit"] = result["revenue"] - result["cogs"]
    result["operating_expenses"] = result["overhead_labor_cost"] + result["overhead_expenses"]
    result["ebitda"] = result["gross_profit"] - result["operating_expenses"]

    totals = pd.DataFrame(
        [
            {
                "month": "Total",
                "revenue": result["revenue"].sum(),
                "direct_labor_cost": result["direct_labor_cost"].sum(),
                "direct_allocated_expenses": result["direct_allocated_expenses"].sum(),
                "cogs": result["cogs"].sum(),
                "gross_profit": result["gross_profit"].sum(),
                "overhead_labor_cost": result["overhead_labor_cost"].sum(),
                "overhead_expenses": result["overhead_expenses"].sum(),
                "operating_expenses": result["operating_expenses"].sum(),
                "ebitda": result["ebitda"].sum(),
            }
        ]
    )
    return pd.concat([result, totals], ignore_index=True)


def compute_cashflow_statement(
    invoices: pd.DataFrame,
    expenses: pd.DataFrame,
    employees: pd.DataFrame,
    starting_cash: float = DEFAULT_STARTING_CASH,
    start_date: Optional[pd.Timestamp] = None,
    end_date: Optional[pd.Timestamp] = None,
) -> pd.DataFrame:
    """
    Compute monthly Cashflow Statement (cash basis).
    """
    invoices_df = _copy_frame(invoices)
    expenses_df = _copy_frame(expenses)
    employees_df = _copy_frame(employees)

    invoices_with_payment = invoices_df[invoices_df["payment_date"].notna()].copy()
    if start_date is not None:
        invoices_with_payment = invoices_with_payment[pd.to_datetime(invoices_with_payment["payment_date"]) >= start_date].copy()
        expenses_df = expenses_df[pd.to_datetime(expenses_df["date"]) >= start_date].copy()
    if end_date is not None:
        invoices_with_payment = invoices_with_payment[pd.to_datetime(invoices_with_payment["payment_date"]) <= end_date].copy()
        expenses_df = expenses_df[pd.to_datetime(expenses_df["date"]) <= end_date].copy()

    invoices_with_payment["month"] = _normalize_period_series(invoices_with_payment["payment_date"])
    cash_in = (
        invoices_with_payment.groupby("month", dropna=False)["amount_eur"]
        .sum()
        .reset_index()
        .rename(columns={"amount_eur": "cash_in"})
    )

    expenses_df["month"] = _normalize_period_series(expenses_df["date"])
    cash_out_exp = (
        expenses_df.groupby("month", dropna=False)["amount_eur"]
        .sum()
        .reset_index()
        .rename(columns={"amount_eur": "cash_out_expenses"})
    )

    employees_df["start_month"] = _normalize_period_series(employees_df["start_date"])
    employees_df["monthly_payroll_cost"] = employees_df["monthly_salary_eur"] * employees_df["employer_cost_multiplier"]

    all_months = set(cash_in["month"].unique()) | set(cash_out_exp["month"].unique())
    if not all_months:
        if not employees_df.empty:
            min_month = employees_df["start_month"].min()
            max_month = min_month
            all_months = pd.period_range(min_month, max_month, freq="M")
        else:
            all_months = []

    payroll_by_month = []
    for month in sorted(all_months):
        month_ts = month.to_timestamp() if isinstance(month, pd.Period) else pd.to_datetime(month)
        active_employees = employees_df[employees_df["start_month"] <= month]
        payroll_cost = 0.0
        for _, emp in active_employees.iterrows():
            if emp["start_month"] == month:
                start_day = pd.to_datetime(emp["start_date"]).day
                prorate_factor = (month.days_in_month - start_day + 1) / month.days_in_month
                payroll_cost += emp["monthly_payroll_cost"] * prorate_factor
            else:
                payroll_cost += emp["monthly_payroll_cost"]
        payroll_by_month.append({"month": month, "cash_out_payroll": payroll_cost})

    cash_out_payroll = pd.DataFrame(payroll_by_month)
    result = cash_in.merge(cash_out_exp, on="month", how="outer")
    result = result.merge(cash_out_payroll, on="month", how="outer")
    result = result.fillna(0.0).sort_values("month")

    result["cash_out_total"] = result["cash_out_payroll"] + result["cash_out_expenses"]
    result["net_cashflow"] = result["cash_in"] - result["cash_out_total"]
    result["ending_cash"] = starting_cash + result["net_cashflow"].cumsum()

    totals = pd.DataFrame(
        [
            {
                "month": "Total",
                "cash_in": result["cash_in"].sum(),
                "cash_out_payroll": result["cash_out_payroll"].sum(),
                "cash_out_expenses": result["cash_out_expenses"].sum(),
                "cash_out_total": result["cash_out_total"].sum(),
                "net_cashflow": result["net_cashflow"].sum(),
                "ending_cash": result["ending_cash"].iloc[-1] if not result.empty else starting_cash,
            }
        ]
    )
    return pd.concat([result, totals], ignore_index=True)


def compute_runway(cashflow_df: pd.DataFrame, starting_cash: float) -> float:
    """
    Compute runway in months using the average monthly burn over the last 3 months.
    """
    monthly_data = cashflow_df[cashflow_df["month"] != "Total"]
    if monthly_data.empty:
        return np.inf

    last_3 = monthly_data.tail(3)
    avg_burn = (last_3["cash_out_total"] - last_3["cash_in"]).mean()
    if avg_burn <= 0:
        return np.inf

    current_cash = monthly_data["ending_cash"].iloc[-1] if not monthly_data.empty else starting_cash
    return current_cash / avg_burn


def compute_metrics_bundle(
    data: Dict[str, pd.DataFrame],
    starting_cash: float,
    as_of_date: Optional[pd.Timestamp] = None,
    date_window: Optional[Dict[str, Optional[pd.Timestamp]]] = None,
) -> Dict:
    """
    Build the canonical metrics bundle used by the UI and AI layers.
    """
    date_window = date_window or {}
    start_date = date_window.get("start_date")
    end_date = date_window.get("end_date")
    inferred_as_of = as_of_date or end_date
    if inferred_as_of is None:
        candidate_dates = []
        for table_name, column_name in [
            ("time_entries", "date"),
            ("invoices", "payment_date"),
            ("invoices", "invoice_date"),
            ("invoices", "due_date"),
            ("expenses", "date"),
        ]:
            df = data.get(table_name)
            if df is not None and column_name in df.columns and df[column_name].notna().any():
                candidate_dates.append(pd.to_datetime(df[column_name]).max())
        inferred_as_of = max(candidate_dates) if candidate_dates else None

    invoices = data["invoices"]
    time_entries = data["time_entries"]
    expenses = data["expenses"]
    employees = data["employees"]

    income_statement_monthly = compute_income_statement(invoices, time_entries, expenses, start_date, end_date)
    cashflow_monthly = compute_cashflow_statement(invoices, expenses, employees, starting_cash, start_date, end_date)
    projects_metrics = compute_project_metrics(time_entries, invoices, expenses, by_month=False)
    projects_metrics_monthly = compute_project_metrics(time_entries, invoices, expenses, by_month=True)
    employee_utilization = compute_employee_utilization(time_entries, employees, by_month=False)
    runway_months = compute_runway(cashflow_monthly, starting_cash)

    return {
        "filters": {
            "start_date": start_date,
            "end_date": end_date,
            "starting_cash": starting_cash,
            "as_of_date": inferred_as_of,
        },
        "projects_metrics": projects_metrics,
        "projects_metrics_monthly": projects_metrics_monthly,
        "employee_utilization": employee_utilization,
        "income_statement_monthly": income_statement_monthly,
        "cashflow_monthly": cashflow_monthly,
        "runway_months": runway_months,
        "cache_key": _stable_cache_key(data, starting_cash, start_date, end_date, inferred_as_of),
    }
