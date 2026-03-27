from pathlib import Path

import pandas as pd

from src.config import DTYPES, INTERNAL_PROJECT_ID, SCHEMAS
from src.data_loader import (
    get_data_quality_overview,
    get_data_summary,
    load_and_validate_data,
    validate_relationships,
    validate_schema,
    validate_types,
)


def test_validate_schema_and_types_report_issues():
    df = pd.DataFrame(
        {
            "project_id": ["P001"],
            "contract_value_eur": ["not-a-number"],
            "start_date": ["not-a-date"],
            "end_date": ["2026-03-01"],
        }
    )

    errors = validate_schema(df, SCHEMAS["projects"], "projects")
    assert any("Missing columns" in error for error in errors)

    type_errors, warnings = validate_types(df, DTYPES["projects"], "projects")
    assert type_errors == []
    assert any("contract_value_eur has 1 non-numeric value(s)" in warning for warning in warnings)
    assert any("start_date has 1 unparseable date value(s)" in warning for warning in warnings)
    assert pd.isna(df.loc[0, "contract_value_eur"])
    assert pd.isna(df.loc[0, "start_date"])


def test_validate_relationships_reports_errors_and_warnings():
    projects = pd.DataFrame({"project_id": ["P001"]})
    employees = pd.DataFrame({"employee_id": ["E001"]})
    time_entries = pd.DataFrame(
        [
            {"employee_id": "E002", "project_id": "P999", "hours_logged": 1, "activity_type": "billable", "hourly_cost_eur": 1},
            {"employee_id": "E001", "project_id": INTERNAL_PROJECT_ID, "hours_logged": 1, "activity_type": "billable", "hourly_cost_eur": 1},
        ]
    )
    invoices = pd.DataFrame(
        [
            {
                "invoice_id": "I404",
                "project_id": "P404",
                "status": "paid",
                "payment_date": None,
                "due_date": "2026-03-01",
            }
        ]
    )
    expenses = pd.DataFrame(
        [
            {"allocated_project_id": "P404"},
            {"allocated_project_id": ""},
        ]
    )

    errors, warnings = validate_relationships(projects, employees, time_entries, invoices, expenses)
    assert any("employee_id values not in employees" in error for error in errors)
    assert any("Invalid project_id values" in error for error in errors)
    assert any("project_id values not in projects" in error for error in errors)
    assert any("allocated_project_id values not in projects" in error for error in errors)


def test_load_and_validate_data_reads_valid_bundle(tmp_path: Path, base_data_frames):
    for name, df in base_data_frames.items():
        df.to_csv(tmp_path / f"{name}.csv", index=False)

    data, validation_results = load_and_validate_data(tmp_path)

    assert set(data.keys()) == set(SCHEMAS.keys())
    assert validation_results["errors"] == []
    assert validation_results["warnings"] == []
    summary = get_data_summary(data)
    assert summary["projects"]["row_count"] == 1
    assert summary["invoices"]["row_count"] == 1


def test_data_quality_overview_reports_status_and_freshness(base_data_frames):
    validation_results = {
        "errors": ["projects: missing required value"],
        "warnings": ["invoices: payment_date warning"],
        "error_count": 1,
        "warning_count": 1,
    }

    overview = get_data_quality_overview(
        base_data_frames,
        validation_results,
        as_of_date=pd.Timestamp("2026-03-15"),
    )

    assert overview["status"] == "blocked"
    assert "blocking validation errors" in overview["message"].lower()
    assert overview["blocking_error_count"] == 1
    assert overview["warning_count"] == 1
    assert overview["as_of_date"] == pd.Timestamp("2026-03-15")

    invoices_row = next(row for row in overview["datasets"] if row["dataset"] == "invoices")
    assert invoices_row["coverage_end"] == pd.Timestamp("2026-03-15")
    assert invoices_row["freshness_days"] == 0
