# Decision Infrastructure

Decision Infrastructure is a Streamlit-based decision-support prototype for SMEs. It ingests canonical CSV files and computes project profitability, utilization, income statement, cashflow, and runway metrics. The deterministic calculations are the source of truth; the AI layer only explains computed facts and summarizes insights.

## Current App Surface

The app currently opens in demo mode with:

- Overview Dashboard
- Projects
- Insights & Explanations

The following pages are implemented but hidden while `DEMO_MODE = True` in `app.py`:

- People & Utilization
- Financial Statements
- Weekly Brief
- Data Quality

## Data Inputs

The app expects CSV files in `data/sample/`:

- `projects.csv`
- `employees.csv`
- `time_entries.csv`
- `invoices.csv`
- `expenses.csv`

## Setup

### Prerequisites

- Python 3.11+
- pip

### Create a virtual environment

PowerShell:

```powershell
python -m venv .venv
```

Activate it:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

If you prefer not to activate, you can run commands directly with:

```powershell
.\.venv\Scripts\python.exe
```

### Install dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Run the app

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

The app should be available at `http://localhost:8501`.

## Trust Model

- Deterministic metrics and validation are the source of truth.
- AI output must stay grounded in computed facts.
- AI can rephrase, summarize, and suggest next questions, but it must not invent numbers or unsupported certainty.

## Key Calculations

### Project Profitability

- Billable hours are hours where `activity_type == "billable"` and `project_id != "INTERNAL"`
- Labor cost is `hours_logged * hourly_cost_eur`
- Allocated expenses come from rows with `allocated_project_id == project_id`
- Gross profit is revenue minus labor cost minus allocated expenses
- Gross margin is gross profit divided by revenue
- Effective hourly rate is revenue divided by billable hours

### Employee Utilization

- Monthly capacity is `weekly_capacity_hours * 52 / 12`
- Utilization is billable hours divided by capacity
- Internal hours are hours where `project_id == "INTERNAL"`

### Income Statement

- Revenue is bucketed by `invoice_date`
- COGS is direct labor cost plus direct allocated expenses
- EBITDA is gross profit minus operating expenses

### Cashflow Statement

- Cash in is bucketed by `payment_date`
- Cash out includes payroll and expenses
- Ending cash is starting cash plus cumulative net cashflow
- Runway uses average monthly burn over the last 3 months

## Notes

- All monetary values are in EUR.
- Dates are bucketed by month.
- `INTERNAL` is used for non-billable internal work.
- The app is intentionally deterministic-first.

