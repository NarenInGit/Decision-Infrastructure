"""
Data loading and validation module.
"""

from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

from .config import (
    DATE_ORDER_RULES,
    DTYPES,
    ENUM_FIELDS,
    INTERNAL_PROJECT_ID,
    NON_NEGATIVE_FIELDS,
    PRIMARY_KEYS,
    REQUIRED_FIELDS,
    SCHEMAS,
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


def _add_detail(details: List[Dict[str, str]], level: str, message: str) -> None:
    details.append({"level": level, "message": message})


def _compute_trust_score(
    blocking_error_count: int,
    warning_count: int,
    dataset_rows: List[Dict[str, object]],
) -> int:
    """Score trust deterministically from validation severity and freshness."""
    score = 100
    score -= min(75, blocking_error_count * 35)
    score -= min(18, warning_count * 6)

    freshness_values = [
        int(row["freshness_days"])
        for row in dataset_rows
        if row.get("freshness_days") is not None
    ]
    max_freshness_days = max(freshness_values, default=0)

    if max_freshness_days > 90:
        score -= 18
    elif max_freshness_days > 30:
        score -= 12
    elif max_freshness_days > 7:
        score -= 6

    if dataset_rows and all(row.get("coverage_end") is None for row in dataset_rows):
        score -= 10

    return max(10, min(100, int(score)))


def load_and_validate_data(data_dir: Path) -> Tuple[Dict[str, pd.DataFrame], Dict[str, List[str]]]:
    """
    Load all CSVs and validate them.

    Returns:
        Tuple of (dataframes_dict, validation_results)
    """
    data: Dict[str, pd.DataFrame] = {}
    all_errors: List[str] = []
    all_warnings: List[str] = []
    details: List[Dict[str, str]] = []

    for file_name, expected_cols in SCHEMAS.items():
        file_path = data_dir / f"{file_name}.csv"

        if not file_path.exists():
            message = f"{file_name}.csv not found"
            all_errors.append(message)
            _add_detail(details, "error", message)
            continue

        try:
            df = load_csv(file_path)
            data[file_name] = df

            schema_errors = validate_schema(df, expected_cols, file_name)
            all_errors.extend(schema_errors)
            for message in schema_errors:
                _add_detail(details, "error", message)

            if file_name in DTYPES:
                type_errors, type_warnings = validate_types(df, DTYPES[file_name], file_name)
                all_errors.extend(type_errors)
                all_warnings.extend(type_warnings)
                for message in type_errors:
                    _add_detail(details, "error", message)
                for message in type_warnings:
                    _add_detail(details, "warning", message)

            required_errors = validate_required_values(df, REQUIRED_FIELDS.get(file_name, []), file_name)
            enum_errors = validate_enum_values(df, ENUM_FIELDS.get(file_name, {}), file_name)
            numeric_errors = validate_numeric_rules(df, NON_NEGATIVE_FIELDS.get(file_name, []), file_name)

            for message in required_errors + enum_errors + numeric_errors:
                all_errors.append(message)
                _add_detail(details, "error", message)

            primary_key = PRIMARY_KEYS.get(file_name)
            if primary_key and primary_key in df.columns:
                duplicate_count = int(df[primary_key].dropna().duplicated().sum())
                if duplicate_count:
                    message = f"{file_name}: {primary_key} has {duplicate_count} duplicate value(s)"
                    all_errors.append(message)
                    _add_detail(details, "error", message)
        except Exception as exc:
            message = f"{file_name}: Error loading file: {exc}"
            all_errors.append(message)
            _add_detail(details, "error", message)

    if len(data) == len(SCHEMAS):
        for message in validate_date_rules(data):
            all_errors.append(message)
            _add_detail(details, "error", message)

        rel_errors, rel_warnings = validate_relationships(
            data["projects"],
            data["employees"],
            data["time_entries"],
            data["invoices"],
            data["expenses"],
        )
        all_errors.extend(rel_errors)
        all_warnings.extend(rel_warnings)
        for message in rel_errors:
            _add_detail(details, "error", message)
        for message in rel_warnings:
            _add_detail(details, "warning", message)

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


def get_data_quality_overview(
    data: Dict[str, pd.DataFrame],
    validation_results: Dict[str, List[str]],
    as_of_date: pd.Timestamp | None = None,
) -> Dict:
    """Build a compact data-quality overview for the UI."""
    summary = get_data_summary(data)
    date_coverage = []
    dataset_rows = []

    for dataset_name, info in summary.items():
        dataset_start = None
        dataset_end = None
        if info["date_range"]:
            mins = [pd.to_datetime(item["min"]) for item in info["date_range"].values()]
            maxes = [pd.to_datetime(item["max"]) for item in info["date_range"].values()]
            dataset_start = min(mins)
            dataset_end = max(maxes)
            date_coverage.append((dataset_start, dataset_end))

        dataset_rows.append(
            {
                "dataset": dataset_name,
                "row_count": info["row_count"],
                "coverage_start": dataset_start,
                "coverage_end": dataset_end,
            }
        )

    inferred_as_of = pd.to_datetime(as_of_date) if as_of_date is not None else None
    if inferred_as_of is None and date_coverage:
        inferred_as_of = max(end for _, end in date_coverage)

    for row in dataset_rows:
        coverage_end = row["coverage_end"]
        if inferred_as_of is not None and coverage_end is not None:
            row["freshness_days"] = int((inferred_as_of.normalize() - pd.to_datetime(coverage_end).normalize()).days)
        else:
            row["freshness_days"] = None

    blocking_error_count = validation_results.get("error_count", len(validation_results.get("errors", [])))
    warning_count = validation_results.get("warning_count", len(validation_results.get("warnings", [])))

    if blocking_error_count > 0:
        status = "blocked"
        trust_label = "Lower Trust"
        message = "Outputs are based on data with blocking validation errors. Numbers may be incomplete or unreliable."
    elif warning_count > 0:
        status = "caution"
        trust_label = "Caution"
        message = "Outputs are computed, but the input data has warnings that may reduce confidence."
    else:
        status = "ready"
        trust_label = "Standard"
        message = "No blocking validation issues detected. Outputs are based on the current validated data."

    overall_start = min((start for start, _ in date_coverage), default=None)
    overall_end = max((end for _, end in date_coverage), default=None)
    trust_score = _compute_trust_score(blocking_error_count, warning_count, dataset_rows)

    return {
        "status": status,
        "trust_label": trust_label,
        "trust_score": trust_score,
        "message": message,
        "blocking_error_count": blocking_error_count,
        "warning_count": warning_count,
        "as_of_date": inferred_as_of,
        "coverage_start": overall_start,
        "coverage_end": overall_end,
        "datasets": dataset_rows,
    }
