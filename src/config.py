"""
Configuration constants and schemas.
"""

from typing import Dict, List

# Expected CSV schemas
SCHEMAS = {
    "projects": ["project_id", "client_name", "project_name", "project_type", "billing_model", 
                 "contract_value_eur", "start_date", "end_date", "status", "currency", "country", "industry"],
    "employees": ["employee_id", "job_title", "department", "monthly_salary_eur", "employment_type",
                  "country_payroll", "employer_cost_multiplier", "weekly_capacity_hours", "start_date"],
    "time_entries": ["date", "employee_id", "project_id", "hours_logged", "activity_type", "task", "hourly_cost_eur"],
    "invoices": ["invoice_id", "client_name", "project_id", "invoice_date", "amount_eur", "status", "payment_date", "due_date"],
    "expenses": ["expense_id", "date", "category", "vendor", "amount_eur", "fixed_or_variable", "allocated_project_id"]
}

# Data types for validation
DTYPES = {
    "projects": {
        "project_id": "string",
        "contract_value_eur": "float64",
        "start_date": "datetime64[ns]",
        "end_date": "datetime64[ns]"
    },
    "employees": {
        "employee_id": "string",
        "monthly_salary_eur": "float64",
        "employer_cost_multiplier": "float64",
        "weekly_capacity_hours": "float64",
        "start_date": "datetime64[ns]"
    },
    "time_entries": {
        "date": "datetime64[ns]",
        "employee_id": "string",
        "project_id": "string",
        "hours_logged": "float64",
        "hourly_cost_eur": "float64"
    },
    "invoices": {
        "invoice_id": "string",
        "project_id": "string",
        "invoice_date": "datetime64[ns]",
        "amount_eur": "float64",
        "payment_date": "datetime64[ns]",
        "due_date": "datetime64[ns]"
    },
    "expenses": {
        "expense_id": "string",
        "date": "datetime64[ns]",
        "amount_eur": "float64",
        "allocated_project_id": "string"
    }
}

# Constants
INTERNAL_PROJECT_ID = "INTERNAL"
DEFAULT_STARTING_CASH = 50000.0
UNDERUTILIZED_THRESHOLD = 0.60
OVERUTILIZED_THRESHOLD = 0.85
