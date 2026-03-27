import pandas as pd
import pytest


@pytest.fixture
def base_data_frames():
    projects = pd.DataFrame(
        [
            {
                "project_id": "P001",
                "client_name": "Acme",
                "project_name": "Website Build",
                "project_type": "delivery",
                "billing_model": "fixed_price",
                "contract_value_eur": 12000,
                "start_date": "2026-02-01",
                "end_date": "2026-04-30",
                "status": "active",
                "currency": "EUR",
                "country": "AT",
                "industry": "SaaS",
            }
        ]
    )

    employees = pd.DataFrame(
        [
            {
                "employee_id": "E001",
                "job_title": "Consultant",
                "department": "Delivery",
                "monthly_salary_eur": 4000,
                "employment_type": "full_time",
                "country_payroll": "AT",
                "employer_cost_multiplier": 1.25,
                "weekly_capacity_hours": 40,
                "start_date": "2026-02-10",
            }
        ]
    )

    time_entries = pd.DataFrame(
        [
            {
                "date": "2026-02-10",
                "employee_id": "E001",
                "project_id": "P001",
                "hours_logged": 6,
                "activity_type": "billable",
                "task": "Build",
                "hourly_cost_eur": 50,
            },
            {
                "date": "2026-02-11",
                "employee_id": "E001",
                "project_id": "INTERNAL",
                "hours_logged": 2,
                "activity_type": "non_billable",
                "task": "Internal admin",
                "hourly_cost_eur": 50,
            },
            {
                "date": "2026-03-05",
                "employee_id": "E001",
                "project_id": "P001",
                "hours_logged": 4,
                "activity_type": "billable",
                "task": "Delivery",
                "hourly_cost_eur": 50,
            },
        ]
    )

    invoices = pd.DataFrame(
        [
            {
                "invoice_id": "I001",
                "client_name": "Acme",
                "project_id": "P001",
                "invoice_date": "2026-02-28",
                "amount_eur": 1000,
                "status": "paid",
                "payment_date": "2026-03-15",
                "due_date": "2026-03-01",
            }
        ]
    )

    expenses = pd.DataFrame(
        [
            {
                "expense_id": "X001",
                "date": "2026-02-15",
                "category": "software",
                "vendor": "Tools Co",
                "amount_eur": 200,
                "fixed_or_variable": "fixed",
                "allocated_project_id": "P001",
            },
            {
                "expense_id": "X002",
                "date": "2026-03-01",
                "category": "overhead",
                "vendor": "Rent Co",
                "amount_eur": 100,
                "fixed_or_variable": "fixed",
                "allocated_project_id": None,
            },
        ]
    )

    return {
        "projects": projects,
        "employees": employees,
        "time_entries": time_entries,
        "invoices": invoices,
        "expenses": expenses,
    }
