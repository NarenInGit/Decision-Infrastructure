"""
Data loading and validation module.
"""

from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

from .config import (
    DATASET_TRUST_WEIGHTS,
    DATE_ORDER_RULES,
    DTYPES,
    ENUM_FIELDS,
    FIELD_IMPORTANCE,
    INTERNAL_PROJECT_ID,
    NON_NEGATIVE_FIELDS,
    PRIMARY_KEYS,
    REQUIRED_FIELDS,
    SCHEMAS,
    TRUST_FRESHNESS_RULES,
    TRUST_IMPORTANCE_WEIGHTS,
    TRUST_RULE_MULTIPLIERS,
    TRUST_VALIDATION_BASE_PENALTIES,
)


class ValidationError(Exception):
    """Custom exception for validation errors."""


def load_csv(file_path: Path) -> pd.DataFrame:
    """Load a CSV file while preserving blanks as nulls."""
    return pd.read_csv(file_path, keep_default_na=True, na_values=["", " "])


def validate_schema(df: pd.DataFrame, expected_cols: List[str], file_name: str) -> List[str]:
    """Validate that DataFrame has all required columns."""
    missing = sorted(set(expected_cols) - set(df.columns))
    if not missing:
        return []
    return [f"{file_name}: Missing columns: {', '.join(missing)}"]


def validate_types(df: pd.DataFrame, dtypes: Dict[str, str], file_name: str) -> Tuple[List[str], List[str]]:
    """Validate and coerce data types."""
    errors: List[str] = []
    warnings: List[str] = []

    for col, dtype in dtypes.items():
        if col not in df.columns:
            continue

        original = df[col].copy()

        try:
            if dtype == "datetime64[ns]":
                df[col] = pd.to_datetime(df[col], errors="coerce")
                invalid_mask = original.notna() & df[col].isna()
                if invalid_mask.any():
                    warnings.append(f"{file_name}: {col} has {int(invalid_mask.sum())} unparseable date value(s)")
            elif dtype == "float64":
                df[col] = pd.to_numeric(df[col], errors="coerce")
                invalid_mask = original.notna() & df[col].isna()
                if invalid_mask.any():
                    warnings.append(f"{file_name}: {col} has {int(invalid_mask.sum())} non-numeric value(s)")
            elif dtype == "string":
                series = original.astype("string").str.strip()
                df[col] = series.replace("", pd.NA)
        except Exception as exc:
            errors.append(f"{file_name}: Error converting {col} to {dtype}: {exc}")

    return errors, warnings


def validate_required_values(df: pd.DataFrame, required_cols: List[str], file_name: str) -> List[str]:
    """Validate required columns have values."""
    errors: List[str] = []
    for col in required_cols:
        if col not in df.columns:
            continue
        missing_count = int(df[col].isna().sum())
        if missing_count:
            errors.append(f"{file_name}: {col} has {missing_count} missing required value(s)")
    return errors


def validate_enum_values(df: pd.DataFrame, enums: Dict[str, set], file_name: str) -> List[str]:
    """Validate enum-like fields."""
    errors: List[str] = []
    for col, allowed in enums.items():
        if col not in df.columns:
            continue
        invalid = df[col].dropna()
        invalid = invalid[~invalid.isin(allowed)]
        if not invalid.empty:
            sample = ", ".join(sorted(set(str(value) for value in invalid.head(5).tolist())))
            errors.append(f"{file_name}: {col} has invalid value(s): {sample}")
    return errors


def validate_numeric_rules(df: pd.DataFrame, numeric_cols: List[str], file_name: str) -> List[str]:
    """Validate numeric columns that must be non-negative."""
    errors: List[str] = []
    for col in numeric_cols:
        if col not in df.columns:
            continue
        invalid_count = int((df[col].dropna() < 0).sum())
        if invalid_count:
            errors.append(f"{file_name}: {col} has {invalid_count} negative value(s)")
    return errors


def validate_date_rules(data: Dict[str, pd.DataFrame]) -> List[str]:
    """Validate date ordering rules."""
    errors: List[str] = []
    for file_name, start_col, end_col, message in DATE_ORDER_RULES:
        df = data.get(file_name)
        if df is None or start_col not in df.columns or end_col not in df.columns:
            continue
        comparable = df[start_col].notna() & df[end_col].notna()
        if comparable.any() and (df.loc[comparable, end_col] < df.loc[comparable, start_col]).any():
            errors.append(message)
    return errors


def validate_relationships(
    projects: pd.DataFrame,
    employees: pd.DataFrame,
    time_entries: pd.DataFrame,
    invoices: pd.DataFrame,
    expenses: pd.DataFrame,
) -> Tuple[List[str], List[str]]:
    """Validate key relationships between tables."""
    errors: List[str] = []
    warnings: List[str] = []

    if projects["project_id"].duplicated().any():
        errors.append("projects: project_id must be unique")

    if employees["employee_id"].duplicated().any():
        errors.append("employees: employee_id must be unique")

    missing_employees = sorted(set(time_entries["employee_id"].dropna().unique()) - set(employees["employee_id"].dropna().unique()))
    if missing_employees:
        errors.append(f"time_entries: employee_id values not in employees: {', '.join(missing_employees[:5])}")

    valid_projects = set(projects["project_id"].dropna().unique()) | {INTERNAL_PROJECT_ID}
    invalid_projects = sorted(set(time_entries["project_id"].dropna().unique()) - valid_projects)
    if invalid_projects:
        errors.append(f"time_entries: Invalid project_id values: {', '.join(invalid_projects[:5])}")

    missing_projects = sorted(set(invoices["project_id"].dropna().unique()) - set(projects["project_id"].dropna().unique()))
    if missing_projects:
        errors.append(f"invoices: project_id values not in projects: {', '.join(missing_projects[:5])}")

    expenses_with_allocation = expenses[expenses["allocated_project_id"].notna()]
    if not expenses_with_allocation.empty:
        invalid_expense_projects = sorted(
            set(expenses_with_allocation["allocated_project_id"].unique()) - set(projects["project_id"].dropna().unique())
        )
        if invalid_expense_projects:
            errors.append(
                "expenses: allocated_project_id values not in projects: "
                + ", ".join(invalid_expense_projects[:5])
            )

    paid_without_payment_date = invoices[(invoices["status"] == "paid") & invoices["payment_date"].isna()]
    if not paid_without_payment_date.empty:
        errors.append("invoices: paid invoices must have payment_date")

    unpaid_with_payment_date = invoices[(invoices["status"] != "paid") & invoices["payment_date"].notna()]
    if not unpaid_with_payment_date.empty:
        warnings.append("invoices: non-paid invoices have payment_date values")

    return errors, warnings


def _field_importance(dataset_name: str, field_name: str | None) -> str:
    if field_name is None:
        return "critical"
    return FIELD_IMPORTANCE.get(dataset_name, {}).get(field_name, "supporting")


def _build_detail(
    *,
    level: str,
    dataset: str,
    message: str,
    field: str | None = None,
    rule: str,
    count: int | None = None,
    row_count: int | None = None,
    importance: str | None = None,
) -> Dict[str, object]:
    safe_count = int(count) if count is not None else None
    safe_row_count = int(row_count) if row_count is not None else None
    affected_share = None

    if safe_count is not None and safe_row_count and safe_row_count > 0:
        affected_share = min(1.0, safe_count / safe_row_count)
    elif rule in {"missing_file", "missing_column"}:
        affected_share = 1.0

    resolved_importance = importance or _field_importance(dataset, field)
    return {
        "level": level,
        "dataset": dataset,
        "field": field,
        "rule": rule,
        "message": message,
        "count": safe_count,
        "row_count": safe_row_count,
        "affected_share": affected_share,
        "importance": resolved_importance,
    }


def _validate_schema_details(df: pd.DataFrame, expected_cols: List[str], file_name: str) -> List[Dict[str, object]]:
    missing = sorted(set(expected_cols) - set(df.columns))
    row_count = max(len(df), 1)
    return [
        _build_detail(
            level="error",
            dataset=file_name,
            field=column_name,
            rule="missing_column",
            message=f"{file_name}: Missing column: {column_name}",
            count=row_count,
            row_count=row_count,
        )
        for column_name in missing
    ]


def _validate_types_details(df: pd.DataFrame, dtypes: Dict[str, str], file_name: str) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    errors: List[Dict[str, object]] = []
    warnings: List[Dict[str, object]] = []
    row_count = len(df)

    for col, dtype in dtypes.items():
        if col not in df.columns:
            continue

        original = df[col].copy()

        try:
            if dtype == "datetime64[ns]":
                df[col] = pd.to_datetime(df[col], errors="coerce")
                invalid_mask = original.notna() & df[col].isna()
                invalid_count = int(invalid_mask.sum())
                if invalid_count:
                    warnings.append(
                        _build_detail(
                            level="warning",
                            dataset=file_name,
                            field=col,
                            rule="unparseable_date",
                            message=f"{file_name}: {col} has {invalid_count} unparseable date value(s)",
                            count=invalid_count,
                            row_count=row_count,
                        )
                    )
            elif dtype == "float64":
                df[col] = pd.to_numeric(df[col], errors="coerce")
                invalid_mask = original.notna() & df[col].isna()
                invalid_count = int(invalid_mask.sum())
                if invalid_count:
                    warnings.append(
                        _build_detail(
                            level="warning",
                            dataset=file_name,
                            field=col,
                            rule="non_numeric",
                            message=f"{file_name}: {col} has {invalid_count} non-numeric value(s)",
                            count=invalid_count,
                            row_count=row_count,
                        )
                    )
            elif dtype == "string":
                series = original.astype("string").str.strip()
                df[col] = series.replace("", pd.NA)
        except Exception as exc:
            errors.append(
                _build_detail(
                    level="error",
                    dataset=file_name,
                    field=col,
                    rule="type_conversion_error",
                    message=f"{file_name}: Error converting {col} to {dtype}: {exc}",
                    count=1,
                    row_count=max(row_count, 1),
                )
            )

    return errors, warnings


def _validate_required_values_details(df: pd.DataFrame, required_cols: List[str], file_name: str) -> List[Dict[str, object]]:
    errors: List[Dict[str, object]] = []
    row_count = len(df)
    for col in required_cols:
        if col not in df.columns:
            continue
        missing_count = int(df[col].isna().sum())
        if missing_count:
            errors.append(
                _build_detail(
                    level="error",
                    dataset=file_name,
                    field=col,
                    rule="missing_required",
                    message=f"{file_name}: {col} has {missing_count} missing required value(s)",
                    count=missing_count,
                    row_count=row_count,
                )
            )
    return errors


def _validate_enum_values_details(df: pd.DataFrame, enums: Dict[str, set], file_name: str) -> List[Dict[str, object]]:
    errors: List[Dict[str, object]] = []
    row_count = len(df)
    for col, allowed in enums.items():
        if col not in df.columns:
            continue
        invalid = df[col].dropna()
        invalid = invalid[~invalid.isin(allowed)]
        if not invalid.empty:
            sample = ", ".join(sorted(set(str(value) for value in invalid.head(5).tolist())))
            errors.append(
                _build_detail(
                    level="error",
                    dataset=file_name,
                    field=col,
                    rule="invalid_enum",
                    message=f"{file_name}: {col} has invalid value(s): {sample}",
                    count=int(len(invalid)),
                    row_count=row_count,
                )
            )
    return errors


def _validate_numeric_rules_details(df: pd.DataFrame, numeric_cols: List[str], file_name: str) -> List[Dict[str, object]]:
    errors: List[Dict[str, object]] = []
    row_count = len(df)
    for col in numeric_cols:
        if col not in df.columns:
            continue
        invalid_count = int((df[col].dropna() < 0).sum())
        if invalid_count:
            errors.append(
                _build_detail(
                    level="error",
                    dataset=file_name,
                    field=col,
                    rule="negative_value",
                    message=f"{file_name}: {col} has {invalid_count} negative value(s)",
                    count=invalid_count,
                    row_count=row_count,
                )
            )
    return errors


def _validate_date_rule_details(data: Dict[str, pd.DataFrame]) -> List[Dict[str, object]]:
    errors: List[Dict[str, object]] = []
    for file_name, start_col, end_col, message in DATE_ORDER_RULES:
        df = data.get(file_name)
        if df is None or start_col not in df.columns or end_col not in df.columns:
            continue
        comparable = df[start_col].notna() & df[end_col].notna()
        invalid_count = int((df.loc[comparable, end_col] < df.loc[comparable, start_col]).sum()) if comparable.any() else 0
        if invalid_count:
            errors.append(
                _build_detail(
                    level="error",
                    dataset=file_name,
                    field=end_col,
                    rule="date_order",
                    message=message,
                    count=invalid_count,
                    row_count=int(comparable.sum()),
                )
            )
    return errors


def _validate_relationship_details(
    projects: pd.DataFrame,
    employees: pd.DataFrame,
    time_entries: pd.DataFrame,
    invoices: pd.DataFrame,
    expenses: pd.DataFrame,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    errors: List[Dict[str, object]] = []
    warnings: List[Dict[str, object]] = []

    if "project_id" in projects.columns and projects["project_id"].duplicated().any():
        duplicate_count = int(projects["project_id"].dropna().duplicated().sum())
        errors.append(
            _build_detail(
                level="error",
                dataset="projects",
                field="project_id",
                rule="duplicate_key",
                message="projects: project_id must be unique",
                count=duplicate_count,
                row_count=len(projects),
            )
        )

    if "employee_id" in employees.columns and employees["employee_id"].duplicated().any():
        duplicate_count = int(employees["employee_id"].dropna().duplicated().sum())
        errors.append(
            _build_detail(
                level="error",
                dataset="employees",
                field="employee_id",
                rule="duplicate_key",
                message="employees: employee_id must be unique",
                count=duplicate_count,
                row_count=len(employees),
            )
        )

    if {"employee_id"}.issubset(time_entries.columns) and {"employee_id"}.issubset(employees.columns):
        valid_employees = set(employees["employee_id"].dropna().unique())
        invalid_employee_mask = time_entries["employee_id"].dropna().map(lambda value: value not in valid_employees)
        invalid_employee_rows = int(invalid_employee_mask.sum())
        if invalid_employee_rows:
            missing_employees = sorted(set(time_entries.loc[invalid_employee_mask, "employee_id"].astype(str).tolist()))
            errors.append(
                _build_detail(
                    level="error",
                    dataset="time_entries",
                    field="employee_id",
                    rule="relationship",
                    message=f"time_entries: employee_id values not in employees: {', '.join(missing_employees[:5])}",
                    count=invalid_employee_rows,
                    row_count=len(time_entries),
                )
            )

    if {"project_id"}.issubset(time_entries.columns) and {"project_id"}.issubset(projects.columns):
        valid_projects = set(projects["project_id"].dropna().unique()) | {INTERNAL_PROJECT_ID}
        invalid_project_mask = time_entries["project_id"].dropna().map(lambda value: value not in valid_projects)
        invalid_project_rows = int(invalid_project_mask.sum())
        if invalid_project_rows:
            invalid_projects = sorted(set(time_entries.loc[invalid_project_mask, "project_id"].astype(str).tolist()))
            errors.append(
                _build_detail(
                    level="error",
                    dataset="time_entries",
                    field="project_id",
                    rule="relationship",
                    message=f"time_entries: Invalid project_id values: {', '.join(invalid_projects[:5])}",
                    count=invalid_project_rows,
                    row_count=len(time_entries),
                )
            )

    if {"project_id"}.issubset(invoices.columns) and {"project_id"}.issubset(projects.columns):
        valid_projects = set(projects["project_id"].dropna().unique())
        missing_project_mask = invoices["project_id"].dropna().map(lambda value: value not in valid_projects)
        missing_project_rows = int(missing_project_mask.sum())
        if missing_project_rows:
            missing_projects = sorted(set(invoices.loc[missing_project_mask, "project_id"].astype(str).tolist()))
            errors.append(
                _build_detail(
                    level="error",
                    dataset="invoices",
                    field="project_id",
                    rule="relationship",
                    message=f"invoices: project_id values not in projects: {', '.join(missing_projects[:5])}",
                    count=missing_project_rows,
                    row_count=len(invoices),
                )
            )

    if {"allocated_project_id"}.issubset(expenses.columns) and {"project_id"}.issubset(projects.columns):
        expenses_with_allocation = expenses[expenses["allocated_project_id"].notna()]
        if not expenses_with_allocation.empty:
            valid_projects = set(projects["project_id"].dropna().unique())
            invalid_expense_mask = expenses_with_allocation["allocated_project_id"].map(lambda value: value not in valid_projects)
            invalid_expense_rows = int(invalid_expense_mask.sum())
            if invalid_expense_rows:
                invalid_expense_projects = sorted(
                    set(expenses_with_allocation.loc[invalid_expense_mask, "allocated_project_id"].astype(str).tolist())
                )
                errors.append(
                    _build_detail(
                        level="error",
                        dataset="expenses",
                        field="allocated_project_id",
                        rule="relationship",
                        message="expenses: allocated_project_id values not in projects: "
                        + ", ".join(invalid_expense_projects[:5]),
                        count=invalid_expense_rows,
                        row_count=len(expenses),
                    )
                )

    if {"status", "payment_date"}.issubset(invoices.columns):
        paid_without_payment_date = invoices[(invoices["status"] == "paid") & invoices["payment_date"].isna()]
        if not paid_without_payment_date.empty:
            errors.append(
                _build_detail(
                    level="error",
                    dataset="invoices",
                    field="payment_date",
                    rule="relationship",
                    message="invoices: paid invoices must have payment_date",
                    count=len(paid_without_payment_date),
                    row_count=len(invoices),
                )
            )

        unpaid_with_payment_date = invoices[(invoices["status"] != "paid") & invoices["payment_date"].notna()]
        if not unpaid_with_payment_date.empty:
            warnings.append(
                _build_detail(
                    level="warning",
                    dataset="invoices",
                    field="payment_date",
                    rule="consistency_warning",
                    message="invoices: non-paid invoices have payment_date values",
                    count=len(unpaid_with_payment_date),
                    row_count=len(invoices),
                )
            )

    return errors, warnings


def _messages_for_level(details: List[Dict[str, object]], level: str) -> List[str]:
    return [detail["message"] for detail in details if detail["level"] == level]


def load_and_validate_data(data_dir: Path) -> Tuple[Dict[str, pd.DataFrame], Dict[str, List[str]]]:
    """
    Load all CSVs and validate them.

    Returns:
        Tuple of (dataframes_dict, validation_results)
    """
    data: Dict[str, pd.DataFrame] = {}
    all_errors: List[str] = []
    all_warnings: List[str] = []
    details: List[Dict[str, object]] = []

    for file_name, expected_cols in SCHEMAS.items():
        file_path = data_dir / f"{file_name}.csv"

        if not file_path.exists():
            message = f"{file_name}.csv not found"
            all_errors.append(message)
            details.append(
                _build_detail(
                    level="error",
                    dataset=file_name,
                    field=None,
                    rule="missing_file",
                    message=message,
                    count=1,
                    row_count=1,
                )
            )
            continue

        try:
            df = load_csv(file_path)
            data[file_name] = df

            schema_errors = validate_schema(df, expected_cols, file_name)
            schema_details = _validate_schema_details(df, expected_cols, file_name)
            all_errors.extend(schema_errors)
            details.extend(schema_details)

            if file_name in DTYPES:
                type_error_details, type_warning_details = _validate_types_details(df, DTYPES[file_name], file_name)
                all_errors.extend(_messages_for_level(type_error_details, "error"))
                all_warnings.extend(_messages_for_level(type_warning_details, "warning"))
                details.extend(type_error_details)
                details.extend(type_warning_details)

            required_details = _validate_required_values_details(df, REQUIRED_FIELDS.get(file_name, []), file_name)
            enum_details = _validate_enum_values_details(df, ENUM_FIELDS.get(file_name, {}), file_name)
            numeric_details = _validate_numeric_rules_details(df, NON_NEGATIVE_FIELDS.get(file_name, []), file_name)
            for issue_details in (required_details, enum_details, numeric_details):
                all_errors.extend(_messages_for_level(issue_details, "error"))
                details.extend(issue_details)

            primary_key = PRIMARY_KEYS.get(file_name)
            if primary_key and primary_key in df.columns:
                duplicate_count = int(df[primary_key].dropna().duplicated().sum())
                if duplicate_count:
                    message = f"{file_name}: {primary_key} has {duplicate_count} duplicate value(s)"
                    all_errors.append(message)
                    details.append(
                        _build_detail(
                            level="error",
                            dataset=file_name,
                            field=primary_key,
                            rule="duplicate_key",
                            message=message,
                            count=duplicate_count,
                            row_count=len(df),
                        )
                    )
        except Exception as exc:
            message = f"{file_name}: Error loading file: {exc}"
            all_errors.append(message)
            details.append(
                _build_detail(
                    level="error",
                    dataset=file_name,
                    field=None,
                    rule="type_conversion_error",
                    message=message,
                    count=1,
                    row_count=max(len(data.get(file_name, [])), 1),
                )
            )

    if len(data) == len(SCHEMAS):
        date_rule_details = _validate_date_rule_details(data)
        all_errors.extend(_messages_for_level(date_rule_details, "error"))
        details.extend(date_rule_details)

        rel_error_details, rel_warning_details = _validate_relationship_details(
            data["projects"],
            data["employees"],
            data["time_entries"],
            data["invoices"],
            data["expenses"],
        )
        all_errors.extend(_messages_for_level(rel_error_details, "error"))
        all_warnings.extend(_messages_for_level(rel_warning_details, "warning"))
        details.extend(rel_error_details)
        details.extend(rel_warning_details)

    validation_results = {
        "errors": all_errors,
        "warnings": all_warnings,
        "details": details,
        "error_count": len(all_errors),
        "warning_count": len(all_warnings),
    }

    return data, validation_results


def get_data_summary(data: Dict[str, pd.DataFrame]) -> Dict[str, Dict]:
    """Get summary statistics for each dataset."""
    summary = {}

    for name, df in data.items():
        summary[name] = {
            "row_count": len(df),
            "columns": list(df.columns),
            "date_range": {},
        }

        for col in ["date", "invoice_date", "payment_date", "start_date", "end_date", "due_date"]:
            if col in df.columns and df[col].notna().any():
                summary[name]["date_range"][col] = {
                    "min": df[col].min(),
                    "max": df[col].max(),
                }

    return summary


def _freshness_reference_end(df: pd.DataFrame, dataset_name: str):
    rule = TRUST_FRESHNESS_RULES.get(dataset_name, {})
    candidate_dates = []
    for column_name in rule.get("date_fields", []):
        if column_name in df.columns and df[column_name].notna().any():
            candidate_dates.append(pd.to_datetime(df[column_name]).max())
    return max(candidate_dates) if candidate_dates else None


def _completeness_penalty(df: pd.DataFrame, dataset_name: str) -> tuple[float, list[dict]]:
    required_fields = REQUIRED_FIELDS.get(dataset_name, [])
    row_count = len(df)
    if not required_fields:
        return 0.0, []

    if row_count == 0:
        return 40.0, [
            {
                "impact": 40.0,
                "message": f"{dataset_name} has no rows, so required-field completeness is unproven.",
            }
        ]

    field_weights = {
        field_name: TRUST_IMPORTANCE_WEIGHTS[_field_importance(dataset_name, field_name)]
        for field_name in required_fields
    }
    total_weight = sum(field_weights.values())
    weighted_completion = 0.0
    factors: list[dict] = []

    for field_name in required_fields:
        weight = field_weights[field_name]

        if field_name not in df.columns:
            completion_ratio = 0.0
            missing_count = row_count
        else:
            non_null_count = int(df[field_name].notna().sum())
            completion_ratio = non_null_count / row_count if row_count else 0.0
            missing_count = row_count - non_null_count

        weighted_completion += weight * completion_ratio
        if missing_count:
            field_penalty = 40.0 * (weight / total_weight) * (1 - completion_ratio)
            factors.append(
                {
                    "impact": field_penalty,
                    "message": f"{dataset_name}.{field_name} is missing in {missing_count} of {row_count} row(s).",
                }
            )

    completeness_ratio = weighted_completion / total_weight if total_weight else 1.0
    return round(40.0 * (1 - completeness_ratio), 2), factors


def _extent_multiplier(affected_share: float | None) -> float:
    if affected_share is None:
        return 1.0
    if affected_share >= 0.20:
        return 1.0
    if affected_share >= 0.05:
        return 0.7
    return 0.4


def _detail_penalty(detail: Dict[str, object]) -> float:
    if detail["rule"] in {"missing_file", "missing_column", "missing_required"}:
        return 0.0

    severity_base = TRUST_VALIDATION_BASE_PENALTIES.get(str(detail["level"]), 4.0)
    rule_multiplier = TRUST_RULE_MULTIPLIERS.get(str(detail["rule"]), 1.0)
    importance_weight = TRUST_IMPORTANCE_WEIGHTS.get(str(detail.get("importance", "supporting")), 1.0)
    field_multiplier = {
        3.0: 1.0,
        2.0: 0.7,
        1.0: 0.4,
    }.get(importance_weight, 0.4)
    return round(severity_base * rule_multiplier * field_multiplier * _extent_multiplier(detail.get("affected_share")), 2)


def _validity_penalty(details: List[Dict[str, object]], dataset_name: str) -> tuple[float, list[dict]]:
    factors: list[dict] = []
    total_penalty = 0.0

    for detail in details:
        if detail.get("dataset") != dataset_name:
            continue
        penalty = _detail_penalty(detail)
        if penalty <= 0:
            continue
        total_penalty += penalty
        factors.append({"impact": penalty, "message": str(detail["message"])})

    return min(40.0, round(total_penalty, 2)), factors


def _freshness_penalty(row: Dict[str, object]) -> tuple[float, list[dict]]:
    dataset_name = str(row["dataset"])
    rule = TRUST_FRESHNESS_RULES.get(dataset_name, {})
    max_penalty = float(rule.get("max_penalty", 0))
    if max_penalty <= 0:
        return 0.0, []

    freshness_days = row.get("freshness_days")
    if freshness_days is None:
        return max_penalty, [
            {
                "impact": max_penalty,
                "message": f"{dataset_name} has no usable freshness date for trust scoring.",
            }
        ]

    freshness_days = max(0, int(freshness_days))
    target_days = int(rule.get("target_days", 30))
    if freshness_days <= target_days:
        return 0.0, []
    if freshness_days <= target_days * 2:
        penalty = max_penalty * 0.25
    elif freshness_days <= target_days * 4:
        penalty = max_penalty * 0.5
    else:
        penalty = max_penalty

    return round(penalty, 2), [
        {
            "impact": round(penalty, 2),
            "message": f"{dataset_name} is {freshness_days} day(s) behind the as-of date against a {target_days}-day target.",
        }
    ]


def _score_dataset(row: Dict[str, object], df: pd.DataFrame, validation_details: List[Dict[str, object]]) -> Dict[str, object]:
    completeness_penalty, completeness_factors = _completeness_penalty(df, row["dataset"])
    validity_penalty, validity_factors = _validity_penalty(validation_details, row["dataset"])
    freshness_penalty, freshness_factors = _freshness_penalty(row)

    dataset_score = max(0, round(100 - completeness_penalty - validity_penalty - freshness_penalty))
    factors = sorted(
        completeness_factors + validity_factors + freshness_factors,
        key=lambda item: item["impact"],
        reverse=True,
    )

    return {
        "score": int(dataset_score),
        "completeness_penalty": round(completeness_penalty, 2),
        "validity_penalty": round(validity_penalty, 2),
        "freshness_penalty": round(freshness_penalty, 2),
        "factors": factors[:3],
    }


def _unique_messages(messages: List[str]) -> List[str]:
    seen = set()
    unique = []
    for message in messages:
        if message in seen:
            continue
        seen.add(message)
        unique.append(message)
    return unique


def _issue_messages(validation_results: Dict[str, List[str]], level: str) -> List[str]:
    detail_level = "error" if level == "error" else "warning"
    detail_messages = [
        str(detail.get("message", ""))
        for detail in validation_results.get("details", [])
        if detail.get("level") == detail_level and detail.get("message")
    ]
    fallback_messages = validation_results.get("errors" if level == "error" else "warnings", [])
    return _unique_messages(detail_messages or list(fallback_messages))


def get_data_quality_overview(
    data: Dict[str, pd.DataFrame],
    validation_results: Dict[str, List[str]],
    as_of_date: pd.Timestamp | None = None,
) -> Dict:
    """Build a compact data-quality overview for the UI."""
    summary = get_data_summary(data)
    date_coverage = []
    dataset_rows = []
    validation_details = validation_results.get("details", [])

    for dataset_name, info in summary.items():
        dataset_start = None
        dataset_end = None
        if info["date_range"]:
            mins = [pd.to_datetime(item["min"]) for item in info["date_range"].values()]
            maxes = [pd.to_datetime(item["max"]) for item in info["date_range"].values()]
            dataset_start = min(mins)
            dataset_end = max(maxes)
            date_coverage.append((dataset_start, dataset_end))

        freshness_end = _freshness_reference_end(data[dataset_name], dataset_name)

        dataset_rows.append(
            {
                "dataset": dataset_name,
                "row_count": info["row_count"],
                "coverage_start": dataset_start,
                "coverage_end": dataset_end,
                "freshness_reference_end": freshness_end,
                "weight": DATASET_TRUST_WEIGHTS.get(dataset_name, 0),
            }
        )

    inferred_as_of = pd.to_datetime(as_of_date) if as_of_date is not None else None
    if inferred_as_of is None:
        freshness_candidates = [row["freshness_reference_end"] for row in dataset_rows if row["freshness_reference_end"] is not None]
        if freshness_candidates:
            inferred_as_of = max(freshness_candidates)
        elif date_coverage:
            inferred_as_of = max(end for _, end in date_coverage)

    for row in dataset_rows:
        reference_end = row["freshness_reference_end"]
        if inferred_as_of is not None and reference_end is not None:
            lag = int((inferred_as_of.normalize() - pd.to_datetime(reference_end).normalize()).days)
            row["freshness_days"] = max(0, lag)
        else:
            row["freshness_days"] = None

    blocking_error_count = validation_results.get("error_count", len(validation_results.get("errors", [])))
    warning_count = validation_results.get("warning_count", len(validation_results.get("warnings", [])))

    overall_start = min((start for start, _ in date_coverage), default=None)
    overall_end = max((end for _, end in date_coverage), default=None)
    dataset_scores = {}
    dataset_factors = []
    weighted_score = 0.0

    for row in dataset_rows:
        dataset_name = row["dataset"]
        dataset_result = _score_dataset(row, data[dataset_name], validation_details)
        row["dataset_score"] = dataset_result["score"]
        row["completeness_penalty"] = dataset_result["completeness_penalty"]
        row["validity_penalty"] = dataset_result["validity_penalty"]
        row["freshness_penalty"] = dataset_result["freshness_penalty"]
        row["freshness_target_days"] = TRUST_FRESHNESS_RULES.get(dataset_name, {}).get("target_days")
        row["top_factor"] = dataset_result["factors"][0]["message"] if dataset_result["factors"] else "No material trust deductions."
        dataset_scores[dataset_name] = dataset_result["score"]
        weighted_score += (row["weight"] / 100) * dataset_result["score"]
        dataset_factors.extend(dataset_result["factors"])

    uncapped_trust_score = int(round(weighted_score)) if dataset_rows else 0
    trust_score = uncapped_trust_score
    cap_reason = None

    if blocking_error_count > 0:
        trust_score = min(trust_score, 69)
        cap_reason = "Blocking validation errors cap the displayed trust score at 69 until those issues are fixed."
    elif warning_count > 0:
        trust_score = min(trust_score, 89)
        cap_reason = "Warnings cap the displayed trust score at 89 until the affected records are reviewed."

    main_factors = [factor["message"] for factor in sorted(dataset_factors, key=lambda item: item["impact"], reverse=True)[:3]]
    blocking_error_messages = _issue_messages(validation_results, "error")
    warning_messages = _issue_messages(validation_results, "warning")

    if trust_score < 70:
        status = "blocked"
        trust_label = "Lower Trust"
        if blocking_error_count > 0:
            message = "Blocking validation errors cap the final trust score until those issues are resolved, even if most datasets are otherwise strong."
        else:
            message = "Trust is reduced because weak core datasets materially affect the reliability of outputs."
    elif trust_score < 90:
        status = "caution"
        trust_label = "Caution"
        if warning_count > 0:
            message = "Warnings cap the final trust score below Standard until the affected records are reviewed."
        else:
            message = "Outputs remain deterministic, but trust is reduced by dataset gaps or stale transactional data."
    else:
        status = "ready"
        trust_label = "Standard"
        message = "Core datasets are complete, validated, and fresh enough for standard operating use."

    return {
        "status": status,
        "trust_label": trust_label,
        "trust_score": trust_score,
        "message": message,
        "trust_explanation": (
            "Weighted average of dataset trust across invoices (30%), time entries (30%), "
            "employees (20%), expenses (15%), and projects (5%). "
            "Each dataset loses trust from required-field completeness gaps, validation issues, and staleness. "
            "If blocking errors exist, the final score is capped at 69. If only warnings exist, it is capped at 89."
        ),
        "uncapped_trust_score": uncapped_trust_score,
        "cap_reason": cap_reason,
        "main_factors": main_factors,
        "blocking_error_messages": blocking_error_messages,
        "warning_messages": warning_messages,
        "dataset_scores": dataset_scores,
        "blocking_error_count": blocking_error_count,
        "warning_count": warning_count,
        "as_of_date": inferred_as_of,
        "coverage_start": overall_start,
        "coverage_end": overall_end,
        "datasets": dataset_rows,
    }
