import pytest
import pandas as pd

from src.metrics import (
    compute_cashflow_statement,
    compute_employee_utilization,
    compute_income_statement,
    compute_project_metrics,
    compute_runway,
)


def test_project_and_utilization_metrics(base_data_frames):
    employees = base_data_frames["employees"].copy()
    time_entries = base_data_frames["time_entries"].copy()
    invoices = base_data_frames["invoices"].copy()
    expenses = base_data_frames["expenses"].copy()

    project_metrics = compute_project_metrics(time_entries, invoices, expenses)
    row = project_metrics[project_metrics["project_id"] == "P001"].iloc[0]
    assert row["project_id"] == "P001"
    assert row["revenue"] == 1000
    assert row["billable_hours"] == 10
    assert row["total_hours"] == 10
    assert row["labor_cost"] == 500
    assert row["allocated_expenses"] == 200
    assert row["gross_profit"] == 300
    assert row["gross_margin_pct"] == 0.3
    assert row["effective_hourly_rate"] == 100

    monthly = compute_project_metrics(time_entries, invoices, expenses, by_month=True)
    feb = monthly[(monthly["project_id"] == "P001") & (monthly["month"].astype(str) == "2026-02")].iloc[0]
    mar = monthly[(monthly["project_id"] == "P001") & (monthly["month"].astype(str) == "2026-03")].iloc[0]

    assert feb["revenue"] == 1000
    assert feb["billable_hours"] == 6
    assert feb["labor_cost"] == 300
    assert feb["allocated_expenses"] == 200
    assert feb["gross_profit"] == 500
    assert feb["effective_hourly_rate"] == pytest.approx(166.6666667)
    assert mar["revenue"] == 0
    assert mar["billable_hours"] == 4
    assert mar["labor_cost"] == 200
    assert mar["gross_profit"] == -200
    assert mar["effective_hourly_rate"] == 0

    utilization = compute_employee_utilization(time_entries, employees)
    util_row = utilization.iloc[0]
    assert util_row["employee_id"] == "E001"
    assert util_row["billable_hours"] == 10
    assert util_row["internal_hours"] == 2
    assert util_row["non_billable_hours"] == 2
    assert util_row["cost_of_time"] == 600
    assert util_row["utilization_pct"] == pytest.approx(10 / (40 * 52 / 12))

    monthly_util = compute_employee_utilization(time_entries, employees, by_month=True)
    feb_util = monthly_util[monthly_util["month"].astype(str) == "2026-02"].iloc[0]
    mar_util = monthly_util[monthly_util["month"].astype(str) == "2026-03"].iloc[0]
    assert feb_util["billable_hours"] == 6
    assert feb_util["internal_hours"] == 2
    assert feb_util["prorated_capacity"] == pytest.approx((40 * 52 / 12) * (19 / 28))
    assert mar_util["billable_hours"] == 4
    assert mar_util["internal_hours"] == 0
    assert mar_util["prorated_capacity"] == pytest.approx(40 * 52 / 12)


def test_income_statement_cashflow_and_runway(base_data_frames):
    employees = base_data_frames["employees"].copy()
    time_entries = base_data_frames["time_entries"].copy()
    invoices = base_data_frames["invoices"].copy()
    expenses = base_data_frames["expenses"].copy()

    income_stmt = compute_income_statement(invoices, time_entries, expenses)
    total = income_stmt[income_stmt["month"] == "Total"].iloc[0]
    assert total["revenue"] == 1000
    assert total["direct_labor_cost"] == 500
    assert total["direct_allocated_expenses"] == 200
    assert total["cogs"] == 700
    assert total["gross_profit"] == 300
    assert total["overhead_labor_cost"] == 100
    assert total["overhead_expenses"] == 100
    assert total["operating_expenses"] == 200
    assert total["ebitda"] == 100

    cashflow = compute_cashflow_statement(invoices, expenses, employees, starting_cash=50000)
    total_cash = cashflow[cashflow["month"] == "Total"].iloc[0]
    assert total_cash["cash_in"] == 1000
    assert total_cash["cash_out_expenses"] == 300
    assert total_cash["cash_out_payroll"] == pytest.approx(8392.857142857143)
    assert total_cash["cash_out_total"] == pytest.approx(8692.857142857143)
    assert total_cash["net_cashflow"] == pytest.approx(-7692.857142857143)
    assert total_cash["ending_cash"] == pytest.approx(42307.142857142855)

    runway = compute_runway(cashflow, starting_cash=50000)
    expected_runway = 42307.142857142855 / ((3592.857142857143 + 4100) / 2)
    assert runway == pytest.approx(expected_runway)
