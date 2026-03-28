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

# Trust-scoring model
DATASET_TRUST_WEIGHTS = {
    "invoices": 30,
    "time_entries": 30,
    "employees": 20,
    "expenses": 15,
    "projects": 5,
}

FIELD_IMPORTANCE = {
    "projects": {
        "project_id": "critical",
        "billing_model": "important",
        "start_date": "important",
        "status": "important",
        "currency": "important",
        "client_name": "supporting",
        "project_name": "supporting",
    },
    "employees": {
        "employee_id": "critical",
        "monthly_salary_eur": "critical",
        "employment_type": "important",
        "employer_cost_multiplier": "critical",
        "weekly_capacity_hours": "critical",
        "start_date": "important",
        "job_title": "supporting",
        "department": "supporting",
    },
    "time_entries": {
        "date": "critical",
        "employee_id": "critical",
        "project_id": "critical",
        "hours_logged": "critical",
        "activity_type": "important",
        "hourly_cost_eur": "critical",
        "task": "supporting",
    },
    "invoices": {
        "invoice_id": "critical",
        "project_id": "critical",
        "invoice_date": "critical",
        "amount_eur": "critical",
        "status": "critical",
        "payment_date": "important",
        "due_date": "important",
        "client_name": "supporting",
    },
    "expenses": {
        "expense_id": "critical",
        "date": "critical",
        "amount_eur": "critical",
        "allocated_project_id": "critical",
        "fixed_or_variable": "important",
        "category": "supporting",
        "vendor": "supporting",
    },
}

TRUST_IMPORTANCE_WEIGHTS = {
    "critical": 3.0,
    "important": 2.0,
    "supporting": 1.0,
}

TRUST_VALIDATION_BASE_PENALTIES = {
    "error": 12.0,
    "warning": 4.0,
}

TRUST_RULE_MULTIPLIERS = {
    "missing_file": 2.0,
    "missing_column": 1.5,
    "missing_required": 1.0,
    "duplicate_key": 2.0,
    "relationship": 2.0,
    "date_order": 1.25,
    "invalid_enum": 1.25,
    "negative_value": 1.25,
    "non_numeric": 1.0,
    "unparseable_date": 1.0,
    "type_conversion_error": 1.0,
    "consistency_warning": 0.75,
}

TRUST_FRESHNESS_RULES = {
    "projects": {
        "date_fields": [],
        "target_days": 90,
        "max_penalty": 0,
    },
    "employees": {
        "date_fields": ["start_date"],
        "target_days": 45,
        "max_penalty": 5,
    },
    "time_entries": {
        "date_fields": ["date"],
        "target_days": 7,
        "max_penalty": 20,
    },
    "invoices": {
        "date_fields": ["payment_date", "invoice_date"],
        "target_days": 14,
        "max_penalty": 20,
    },
    "expenses": {
        "date_fields": ["date"],
        "target_days": 21,
        "max_penalty": 15,
    },
}
