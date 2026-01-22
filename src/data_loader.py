"""
Data loading and validation module.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
from .config import SCHEMAS, DTYPES, INTERNAL_PROJECT_ID


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


def load_csv(file_path: Path) -> pd.DataFrame:
    """Load a CSV file."""
    return pd.read_csv(file_path)


def validate_schema(df: pd.DataFrame, expected_cols: List[str], file_name: str) -> List[str]:
    """Validate that DataFrame has all required columns."""
    errors = []
    missing = set(expected_cols) - set(df.columns)
    if missing:
        errors.append(f"{file_name}: Missing columns: {', '.join(missing)}")
    return errors


def validate_types(df: pd.DataFrame, dtypes: Dict[str, str], file_name: str) -> List[str]:
    """Validate and coerce data types."""
    errors = []
    warnings = []
    
    for col, dtype in dtypes.items():
        if col not in df.columns:
            continue
            
        try:
            if dtype == "datetime64[ns]":
                df[col] = pd.to_datetime(df[col], errors="coerce")
                if df[col].isna().any():
                    warnings.append(f"{file_name}: {col} has unparseable dates")
            elif dtype == "float64":
                df[col] = pd.to_numeric(df[col], errors="coerce")
                if df[col].isna().any():
                    warnings.append(f"{file_name}: {col} has non-numeric values")
            elif dtype == "string":
                df[col] = df[col].astype(str)
        except Exception as e:
            errors.append(f"{file_name}: Error converting {col} to {dtype}: {str(e)}")
    
    return errors, warnings


def validate_relationships(
    projects: pd.DataFrame,
    employees: pd.DataFrame,
    time_entries: pd.DataFrame,
    invoices: pd.DataFrame,
    expenses: pd.DataFrame
) -> Tuple[List[str], List[str]]:
    """Validate key relationships between tables."""
    errors = []
    warnings = []
    
    # projects.project_id is unique
    if projects["project_id"].duplicated().any():
        errors.append("projects: project_id must be unique")
    
    # employees.employee_id is unique
    if employees["employee_id"].duplicated().any():
        errors.append("employees: employee_id must be unique")
    
    # time_entries.employee_id must exist in employees
    missing_employees = set(time_entries["employee_id"].unique()) - set(employees["employee_id"].unique())
    if missing_employees:
        errors.append(f"time_entries: employee_id values not in employees: {', '.join(list(missing_employees)[:5])}")
    
    # time_entries.project_id can be INTERNAL or valid project_id
    valid_projects = set(projects["project_id"].unique()) | {INTERNAL_PROJECT_ID}
    invalid_projects = set(time_entries["project_id"].unique()) - valid_projects
    if invalid_projects:
        errors.append(f"time_entries: Invalid project_id values: {', '.join(list(invalid_projects)[:5])}")
    
    # invoices.project_id must exist in projects
    missing_projects = set(invoices["project_id"].unique()) - set(projects["project_id"].unique())
    if missing_projects:
        errors.append(f"invoices: project_id values not in projects: {', '.join(list(missing_projects)[:5])}")
    
    # expenses.allocated_project_id can be blank OR valid project_id
    expenses_with_allocation = expenses[expenses["allocated_project_id"].notna() & (expenses["allocated_project_id"] != "")]
    if len(expenses_with_allocation) > 0:
        valid_expense_projects = set(projects["project_id"].unique())
        invalid_expense_projects = set(expenses_with_allocation["allocated_project_id"].unique()) - valid_expense_projects
        if invalid_expense_projects:
            warnings.append(f"expenses: allocated_project_id values not in projects: {', '.join(list(invalid_expense_projects)[:5])}")
    
    return errors, warnings


def load_and_validate_data(data_dir: Path) -> Tuple[Dict[str, pd.DataFrame], Dict[str, List[str]]]:
    """
    Load all CSVs and validate them.
    
    Returns:
        Tuple of (dataframes_dict, validation_results)
        validation_results contains 'errors' and 'warnings' lists
    """
    data = {}
    all_errors = []
    all_warnings = []
    
    # Load each CSV
    for file_name, expected_cols in SCHEMAS.items():
        file_path = data_dir / f"{file_name}.csv"
        
        if not file_path.exists():
            all_errors.append(f"{file_name}.csv not found")
            continue
        
        try:
            df = load_csv(file_path)
            data[file_name] = df
            
            # Validate schema
            schema_errors = validate_schema(df, expected_cols, file_name)
            all_errors.extend(schema_errors)
            
            # Validate types
            if file_name in DTYPES:
                type_errors, type_warnings = validate_types(df, DTYPES[file_name], file_name)
                all_errors.extend(type_errors)
                all_warnings.extend(type_warnings)
                
        except Exception as e:
            all_errors.append(f"{file_name}: Error loading file: {str(e)}")
    
    # Validate relationships if all files loaded
    if len(data) == len(SCHEMAS):
        rel_errors, rel_warnings = validate_relationships(
            data.get("projects", pd.DataFrame()),
            data.get("employees", pd.DataFrame()),
            data.get("time_entries", pd.DataFrame()),
            data.get("invoices", pd.DataFrame()),
            data.get("expenses", pd.DataFrame())
        )
        all_errors.extend(rel_errors)
        all_warnings.extend(rel_warnings)
    
    validation_results = {
        "errors": all_errors,
        "warnings": all_warnings
    }
    
    return data, validation_results


def get_data_summary(data: Dict[str, pd.DataFrame]) -> Dict[str, Dict]:
    """Get summary statistics for each dataset."""
    summary = {}
    
    for name, df in data.items():
        summary[name] = {
            "row_count": len(df),
            "columns": list(df.columns),
            "date_range": {}
        }
        
        # Find date columns and their ranges
        date_cols = ["date", "invoice_date", "payment_date", "start_date", "end_date"]
        for col in date_cols:
            if col in df.columns:
                if df[col].notna().any():
                    summary[name]["date_range"][col] = {
                        "min": df[col].min(),
                        "max": df[col].max()
                    }
    
    return summary
