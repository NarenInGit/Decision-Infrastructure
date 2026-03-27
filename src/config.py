"""
Configuration constants, schemas, and validation rules.
"""

from typing import Dict, List, Tuple

# Expected CSV schemas
SCHEMAS = {
    "projects": [
        "project_id",
        "client_name",
        "project_name",
        "project_type",
        "billing_model",
        "contract_value_eur",
        "start_date",
        "end_date",
        "status",
        "currency",
        "country",
        "industry",
    ],
    "employees": [
        "employee_id",
        "job_title",
        "department",
        "monthly_salary_eur",
        "employment_type",
        "country_payroll",
        "employer_cost_multiplier",
        "weekly_capacity_hours",
        "start_date",
    ],
    "time_entries": [
        "date",
        "employee_id",
        "project_id",
        "hours_logged",
        "activity_type",
        "task",
        "hourly_cost_eur",
    ],
    "invoices": [
        "invoice_id",
        "client_name",
        "project_id",
        "invoice_date",
        "amount_eur",
        "status",
        "payment_date",
        "due_date",
    ],
    "expenses": [
        "expense_id",
        "date",
        "category",
        "vendor",
        "amount_eur",
        "fixed_or_variable",
        "allocated_project_id",
    ],
}

# Data types for validation
DTYPES = {
    "projects": {
        "project_id": "string",
        "client_name": "string",
        "project_name": "string",
        "project_type": "string",
        "billing_model": "string",
        "contract_value_eur": "float64",
        "start_date": "datetime64[ns]",
        "end_date": "datetime64[ns]",
        "status": "string",
        "currency": "string",
        "country": "string",
        "industry": "string",
    },
    "employees": {
        "employee_id": "string",
        "job_title": "string",
        "department": "string",
        "monthly_salary_eur": "float64",
        "employment_type": "string",
        "country_payroll": "string",
        "employer_cost_multiplier": "float64",
        "weekly_capacity_hours": "float64",
        "start_date": "datetime64[ns]",
    },
    "time_entries": {
        "date": "datetime64[ns]",
        "employee_id": "string",
        "project_id": "string",
        "hours_logged": "float64",
        "activity_type": "string",
        "task": "string",
        "hourly_cost_eur": "float64",
    },
    "invoices": {
        "invoice_id": "string",
        "client_name": "string",
        "project_id": "string",
        "invoice_date": "datetime64[ns]",
        "amount_eur": "float64",
        "status": "string",
        "payment_date": "datetime64[ns]",
        "due_date": "datetime64[ns]",
    },
    "expenses": {
        "expense_id": "string",
        "date": "datetime64[ns]",
        "category": "string",
        "vendor": "string",
        "amount_eur": "float64",
        "fixed_or_variable": "string",
        "allocated_project_id": "string",
    },
}

REQUIRED_FIELDS = {
    "projects": [
        "project_id",
        "client_name",
        "project_name",
        "billing_model",
        "start_date",
        "status",
        "currency",
    ],
    "employees": [
        "employee_id",
        "job_title",
        "department",
        "monthly_salary_eur",
        "employment_type",
        "employer_cost_multiplier",
        "weekly_capacity_hours",
        "start_date",
    ],
    "time_entries": [
        "date",
        "employee_id",
        "project_id",
        "hours_logged",
        "activity_type",
        "hourly_cost_eur",
    ],
    "invoices": [
        "invoice_id",
        "client_name",
        "project_id",
        "invoice_date",
        "amount_eur",
        "status",
        "due_date",
    ],
    "expenses": [
        "expense_id",
        "date",
        "category",
        "vendor",
        "amount_eur",
        "fixed_or_variable",
    ],
}

ENUM_FIELDS = {
    "projects": {
        "billing_model": {"fixed_price", "monthly_retainer", "time_and_materials"},
        "status": {"active", "completed", "paused", "cancelled"},
        "currency": {"EUR"},
    },
    "employees": {
        "employment_type": {"full_time", "part_time", "contractor"},
    },
    "time_entries": {
        "activity_type": {"billable", "non_billable"},
    },
    "invoices": {
        "status": {"draft", "sent", "paid", "overdue", "cancelled"},
    },
    "expenses": {
        "fixed_or_variable": {"fixed", "variable"},
    },
}

NON_NEGATIVE_FIELDS = {
    "projects": ["contract_value_eur"],
    "employees": ["monthly_salary_eur", "employer_cost_multiplier", "weekly_capacity_hours"],
    "time_entries": ["hours_logged", "hourly_cost_eur"],
    "invoices": ["amount_eur"],
    "expenses": ["amount_eur"],
}

PRIMARY_KEYS = {
    "projects": "project_id",
    "employees": "employee_id",
    "invoices": "invoice_id",
    "expenses": "expense_id",
}

DATE_ORDER_RULES: List[Tuple[str, str, str, str]] = [
    ("projects", "start_date", "end_date", "projects: end_date must be on or after start_date"),
    ("invoices", "invoice_date", "due_date", "invoices: due_date must be on or after invoice_date"),
]

# Constants
INTERNAL_PROJECT_ID = "INTERNAL"
DEFAULT_STARTING_CASH = 50000.0
UNDERUTILIZED_THRESHOLD = 0.60
OVERUTILIZED_THRESHOLD = 0.85
