"""
Metrics engine - single source of truth for all calculations.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from .config import INTERNAL_PROJECT_ID, DEFAULT_STARTING_CASH


def compute_daily_time_cost(time_entries: pd.DataFrame) -> pd.DataFrame:
    """
    Compute daily time cost table.
    
    Returns DataFrame with:
    - date, employee_id, project_id, hours_logged, hourly_cost_eur
    - labor_cost_eur = hours_logged * hourly_cost_eur
    - billable_hours = hours_logged where activity_type == "billable" AND project_id != INTERNAL
    - non_billable_hours = hours_logged where activity_type == "non_billable" OR project_id == INTERNAL
    """
    df = time_entries.copy()
    df["labor_cost_eur"] = df["hours_logged"] * df["hourly_cost_eur"]
    df["billable_hours"] = df.apply(
        lambda row: row["hours_logged"] if (row["activity_type"] == "billable" and row["project_id"] != INTERNAL_PROJECT_ID) else 0,
        axis=1
    )
    df["non_billable_hours"] = df.apply(
        lambda row: row["hours_logged"] if (row["activity_type"] == "non_billable" or row["project_id"] == INTERNAL_PROJECT_ID) else 0,
        axis=1
    )
    return df


def compute_project_metrics(
    time_entries: pd.DataFrame,
    invoices: pd.DataFrame,
    expenses: pd.DataFrame,
    by_month: bool = False
) -> pd.DataFrame:
    """
    Compute project-level profitability metrics.
    
    Returns DataFrame with columns:
    - project_id, revenue, billable_hours, total_hours, labor_cost, allocated_expenses,
      gross_profit, gross_margin_pct, effective_hourly_rate
    """
    daily_cost = compute_daily_time_cost(time_entries)
    
    # Project-level aggregations
    project_time = daily_cost.groupby("project_id").agg({
        "billable_hours": "sum",
        "hours_logged": "sum",
        "labor_cost_eur": "sum"
    }).reset_index()
    project_time.columns = ["project_id", "billable_hours", "total_hours", "labor_cost"]
    
    # Revenue by project (and optionally by month)
    if by_month:
        invoices["month"] = pd.to_datetime(invoices["invoice_date"]).dt.to_period("M")
        revenue = invoices.groupby(["project_id", "month"])["amount_eur"].sum().reset_index()
        revenue.columns = ["project_id", "month", "revenue"]
    else:
        revenue = invoices.groupby("project_id")["amount_eur"].sum().reset_index()
        revenue.columns = ["project_id", "revenue"]
    
    # Allocated expenses
    expenses_with_allocation = expenses[
        expenses["allocated_project_id"].notna() & (expenses["allocated_project_id"] != "")
    ]
    if by_month:
        expenses_with_allocation["month"] = pd.to_datetime(expenses_with_allocation["date"]).dt.to_period("M")
        allocated_exp = expenses_with_allocation.groupby(["allocated_project_id", "month"])["amount_eur"].sum().reset_index()
        allocated_exp.columns = ["project_id", "month", "allocated_expenses"]
    else:
        allocated_exp = expenses_with_allocation.groupby("allocated_project_id")["amount_eur"].sum().reset_index()
        allocated_exp.columns = ["project_id", "allocated_expenses"]
    
    # Merge
    if by_month:
        result = project_time.merge(revenue, on="project_id", how="outer")
        result = result.merge(allocated_exp, on=["project_id", "month"], how="outer")
        result["allocated_expenses"] = result["allocated_expenses"].fillna(0)
        result["revenue"] = result["revenue"].fillna(0)
    else:
        result = project_time.merge(revenue, on="project_id", how="outer")
        result = result.merge(allocated_exp, on="project_id", how="outer")
        result["allocated_expenses"] = result["allocated_expenses"].fillna(0)
        result["revenue"] = result["revenue"].fillna(0)
    
    # Calculate metrics
    result["gross_profit"] = result["revenue"] - result["labor_cost"] - result["allocated_expenses"]
    result["gross_margin_pct"] = result.apply(
        lambda row: (row["gross_profit"] / row["revenue"]) if row["revenue"] > 0 else np.nan,
        axis=1
    )
    result["effective_hourly_rate"] = result.apply(
        lambda row: (row["revenue"] / row["billable_hours"]) if row["billable_hours"] > 0 else np.nan,
        axis=1
    )
    
    return result


def compute_employee_utilization(
    time_entries: pd.DataFrame,
    employees: pd.DataFrame,
    by_month: bool = False
) -> pd.DataFrame:
    """
    Compute employee utilization metrics.
    
    Returns DataFrame with:
    - employee_id, month (if by_month), monthly_capacity_hours, billable_hours,
      utilization_pct, cost_of_time, internal_hours
    """
    daily_cost = compute_daily_time_cost(time_entries)
    
    # Calculate monthly capacity
    employees = employees.copy()
    employees["monthly_capacity_hours"] = employees["weekly_capacity_hours"] * 52 / 12
    
    if by_month:
        daily_cost["month"] = pd.to_datetime(daily_cost["date"]).dt.to_period("M")
        employees["start_month"] = pd.to_datetime(employees["start_date"]).dt.to_period("M")
        
        # Aggregate by employee and month
        emp_time = daily_cost.groupby(["employee_id", "month"]).agg({
            "billable_hours": "sum",
            "hours_logged": "sum",
            "labor_cost_eur": "sum"
        }).reset_index()
        emp_time["non_billable_hours"] = emp_time["hours_logged"] - emp_time["billable_hours"]
        
        # Filter for INTERNAL hours
        internal_hours = daily_cost[daily_cost["project_id"] == INTERNAL_PROJECT_ID].groupby(
            ["employee_id", "month"]
        )["hours_logged"].sum().reset_index()
        internal_hours.columns = ["employee_id", "month", "internal_hours"]
        
        # Merge with employees
        result = emp_time.merge(employees[["employee_id", "monthly_capacity_hours", "start_month"]], on="employee_id")
        
        # Prorate capacity for start month
        result["prorated_capacity"] = result.apply(
            lambda row: (
                row["monthly_capacity_hours"] * (pd.Period(row["month"]).days_in_month - row["start_month"].to_timestamp().day + 1) / pd.Period(row["month"]).days_in_month
                if row["month"] == row["start_month"] else row["monthly_capacity_hours"]
            ),
            axis=1
        )
        
        result = result.merge(internal_hours, on=["employee_id", "month"], how="left")
        result["internal_hours"] = result["internal_hours"].fillna(0)
    else:
        emp_time = daily_cost.groupby("employee_id").agg({
            "billable_hours": "sum",
            "hours_logged": "sum",
            "labor_cost_eur": "sum"
        }).reset_index()
        
        internal_hours = daily_cost[daily_cost["project_id"] == INTERNAL_PROJECT_ID].groupby("employee_id")["hours_logged"].sum().reset_index()
        internal_hours.columns = ["employee_id", "internal_hours"]
        
        result = emp_time.merge(employees[["employee_id", "monthly_capacity_hours"]], on="employee_id")
        result = result.merge(internal_hours, on="employee_id", how="left")
        result["internal_hours"] = result["internal_hours"].fillna(0)
        result["prorated_capacity"] = result["monthly_capacity_hours"]
        result["non_billable_hours"] = result["hours_logged"] - result["billable_hours"]
    
    result["utilization_pct"] = result.apply(
        lambda row: (row["billable_hours"] / row["prorated_capacity"]) if row["prorated_capacity"] > 0 else np.nan,
        axis=1
    )
    result["cost_of_time"] = result["labor_cost_eur"]
    
    return result


def compute_income_statement(
    invoices: pd.DataFrame,
    time_entries: pd.DataFrame,
    expenses: pd.DataFrame,
    start_date: Optional[pd.Timestamp] = None,
    end_date: Optional[pd.Timestamp] = None
) -> pd.DataFrame:
    """
    Compute monthly Income Statement (accrual basis).
    
    Returns DataFrame with columns:
    - month, revenue, direct_labor_cost, direct_allocated_expenses, cogs, gross_profit,
      overhead_labor_cost, overhead_expenses, operating_expenses, ebitda
    """
    daily_cost = compute_daily_time_cost(time_entries)
    
    # Filter by date range
    if start_date:
        invoices = invoices[pd.to_datetime(invoices["invoice_date"]) >= start_date]
        daily_cost = daily_cost[pd.to_datetime(daily_cost["date"]) >= start_date]
        expenses = expenses[pd.to_datetime(expenses["date"]) >= start_date]
    if end_date:
        invoices = invoices[pd.to_datetime(invoices["invoice_date"]) <= end_date]
        daily_cost = daily_cost[pd.to_datetime(daily_cost["date"]) <= end_date]
        expenses = expenses[pd.to_datetime(expenses["date"]) <= end_date]
    
    # Revenue by month (accrual - invoice_date)
    invoices["month"] = pd.to_datetime(invoices["invoice_date"]).dt.to_period("M")
    revenue = invoices.groupby("month")["amount_eur"].sum().reset_index()
    revenue.columns = ["month", "revenue"]
    
    # Direct labor cost (project_id != INTERNAL and not empty)
    daily_cost["month"] = pd.to_datetime(daily_cost["date"]).dt.to_period("M")
    direct_labor = daily_cost[
        (daily_cost["project_id"] != INTERNAL_PROJECT_ID) & (daily_cost["project_id"] != "")
    ].groupby("month")["labor_cost_eur"].sum().reset_index()
    direct_labor.columns = ["month", "direct_labor_cost"]
    
    # Direct allocated expenses
    expenses_with_allocation = expenses[
        expenses["allocated_project_id"].notna() & (expenses["allocated_project_id"] != "")
    ]
    expenses_with_allocation["month"] = pd.to_datetime(expenses_with_allocation["date"]).dt.to_period("M")
    direct_exp = expenses_with_allocation.groupby("month")["amount_eur"].sum().reset_index()
    direct_exp.columns = ["month", "direct_allocated_expenses"]
    
    # Overhead labor (INTERNAL or non-billable with INTERNAL)
    overhead_labor = daily_cost[
        (daily_cost["project_id"] == INTERNAL_PROJECT_ID) | 
        ((daily_cost["project_id"] == INTERNAL_PROJECT_ID) & (daily_cost["activity_type"] == "non_billable"))
    ].groupby("month")["labor_cost_eur"].sum().reset_index()
    overhead_labor.columns = ["month", "overhead_labor_cost"]
    
    # Overhead expenses (no allocation)
    overhead_exp = expenses[
        expenses["allocated_project_id"].isna() | (expenses["allocated_project_id"] == "")
    ]
    overhead_exp["month"] = pd.to_datetime(overhead_exp["date"]).dt.to_period("M")
    overhead_exp = overhead_exp.groupby("month")["amount_eur"].sum().reset_index()
    overhead_exp.columns = ["month", "overhead_expenses"]
    
    # Merge all
    result = revenue.merge(direct_labor, on="month", how="outer")
    result = result.merge(direct_exp, on="month", how="outer")
    result = result.merge(overhead_labor, on="month", how="outer")
    result = result.merge(overhead_exp, on="month", how="outer")
    
    # Fill NaNs with 0
    result = result.fillna(0)
    
    # Calculate derived metrics
    result["cogs"] = result["direct_labor_cost"] + result["direct_allocated_expenses"]
    result["gross_profit"] = result["revenue"] - result["cogs"]
    result["operating_expenses"] = result["overhead_labor_cost"] + result["overhead_expenses"]
    result["ebitda"] = result["gross_profit"] - result["operating_expenses"]
    
    # Add totals row
    totals = pd.DataFrame([{
        "month": "Total",
        "revenue": result["revenue"].sum(),
        "direct_labor_cost": result["direct_labor_cost"].sum(),
        "direct_allocated_expenses": result["direct_allocated_expenses"].sum(),
        "cogs": result["cogs"].sum(),
        "gross_profit": result["gross_profit"].sum(),
        "overhead_labor_cost": result["overhead_labor_cost"].sum(),
        "overhead_expenses": result["overhead_expenses"].sum(),
        "operating_expenses": result["operating_expenses"].sum(),
        "ebitda": result["ebitda"].sum()
    }])
    
    result = pd.concat([result, totals], ignore_index=True)
    
    return result


def compute_cashflow_statement(
    invoices: pd.DataFrame,
    expenses: pd.DataFrame,
    employees: pd.DataFrame,
    starting_cash: float = DEFAULT_STARTING_CASH,
    start_date: Optional[pd.Timestamp] = None,
    end_date: Optional[pd.Timestamp] = None
) -> pd.DataFrame:
    """
    Compute monthly Cashflow Statement (cash basis).
    
    Returns DataFrame with columns:
    - month, cash_in, cash_out_payroll, cash_out_expenses, cash_out_total, net_cashflow, ending_cash
    """
    # Filter by date range
    if start_date:
        invoices = invoices[pd.to_datetime(invoices["invoice_date"]) >= start_date]
        expenses = expenses[pd.to_datetime(expenses["date"]) >= start_date]
    if end_date:
        invoices = invoices[pd.to_datetime(invoices["invoice_date"]) <= end_date]
        expenses = expenses[pd.to_datetime(expenses["date"]) <= end_date]
    
    # Cash In: invoices with payment_date (bucket by payment_date month)
    invoices_with_payment = invoices[invoices["payment_date"].notna()]
    invoices_with_payment["month"] = pd.to_datetime(invoices_with_payment["payment_date"]).dt.to_period("M")
    cash_in = invoices_with_payment.groupby("month")["amount_eur"].sum().reset_index()
    cash_in.columns = ["month", "cash_in"]
    
    # Cash Out: Expenses by month
    expenses["month"] = pd.to_datetime(expenses["date"]).dt.to_period("M")
    cash_out_exp = expenses.groupby("month")["amount_eur"].sum().reset_index()
    cash_out_exp.columns = ["month", "cash_out_expenses"]
    
    # Cash Out: Payroll proxy
    employees = employees.copy()
    employees["start_month"] = pd.to_datetime(employees["start_date"]).dt.to_period("M")
    employees["start_month_ts"] = employees["start_month"].apply(lambda x: x.to_timestamp() if isinstance(x, pd.Period) else pd.to_datetime(x))
    employees["monthly_payroll_cost"] = employees["monthly_salary_eur"] * employees["employer_cost_multiplier"]
    
    # Generate month range
    all_months = set(cash_in["month"].unique()) | set(cash_out_exp["month"].unique())
    if len(all_months) == 0:
        # Use employee start dates to determine range
        if len(employees) > 0:
            min_month = employees["start_month"].min()
            max_month = pd.Period.now()
            all_months = pd.period_range(min_month, max_month, freq="M")
        else:
            all_months = []
    
    payroll_by_month = []
    for month in sorted(all_months):
        # Active employees in this month
        # Convert Period to timestamp for comparison
        if isinstance(month, pd.Period):
            month_ts = month.to_timestamp()
        else:
            month_ts = pd.to_datetime(month)
        
        active_employees = employees[employees["start_month_ts"] <= month_ts]
        
        if len(active_employees) > 0:
            # Prorate for start month
            payroll_cost = 0
            for _, emp in active_employees.iterrows():
                if emp["start_month"] == month:
                    # Prorate by days
                    days_in_month = pd.Period(month).days_in_month
                    start_day = pd.to_datetime(emp["start_date"]).day
                    prorate_factor = (days_in_month - start_day + 1) / days_in_month
                    payroll_cost += emp["monthly_payroll_cost"] * prorate_factor
                else:
                    payroll_cost += emp["monthly_payroll_cost"]
            
            payroll_by_month.append({"month": month, "cash_out_payroll": payroll_cost})
    
    cash_out_payroll = pd.DataFrame(payroll_by_month)
    
    # Merge all
    result = cash_in.merge(cash_out_exp, on="month", how="outer")
    result = result.merge(cash_out_payroll, on="month", how="outer")
    result = result.fillna(0)
    
    # Calculate totals
    result["cash_out_total"] = result["cash_out_payroll"] + result["cash_out_expenses"]
    result["net_cashflow"] = result["cash_in"] - result["cash_out_total"]
    
    # Calculate ending cash (cumulative)
    result = result.sort_values("month")
    result["ending_cash"] = starting_cash + result["net_cashflow"].cumsum()
    
    # Add totals row
    totals = pd.DataFrame([{
        "month": "Total",
        "cash_in": result["cash_in"].sum(),
        "cash_out_payroll": result["cash_out_payroll"].sum(),
        "cash_out_expenses": result["cash_out_expenses"].sum(),
        "cash_out_total": result["cash_out_total"].sum(),
        "net_cashflow": result["net_cashflow"].sum(),
        "ending_cash": result["ending_cash"].iloc[-1] if len(result) > 0 else starting_cash
    }])
    
    result = pd.concat([result, totals], ignore_index=True)
    
    return result


def compute_runway(cashflow_df: pd.DataFrame, starting_cash: float) -> float:
    """
    Compute runway in months.
    
    Uses average monthly burn over last 3 months.
    """
    # Exclude totals row
    monthly_data = cashflow_df[cashflow_df["month"] != "Total"]
    
    if len(monthly_data) == 0:
        return np.inf
    
    # Get last 3 months
    last_3 = monthly_data.tail(3)
    
    # Calculate average burn (cash_out - cash_in)
    avg_burn = (last_3["cash_out_total"] - last_3["cash_in"]).mean()
    
    if avg_burn <= 0:
        return np.inf
    
    # Current ending cash
    current_cash = monthly_data["ending_cash"].iloc[-1] if len(monthly_data) > 0 else starting_cash
    
    runway_months = current_cash / avg_burn
    
    return runway_months
