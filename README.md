# Decision Infrastructure

A B2B service prototype for ingesting CSVs and computing project profitability + company financial statements (Income Statement, Cashflow, Runway).

## Features

- **Data Ingestion & Validation**: Load and validate CSV files with schema checking and relationship validation
- **Project Profitability**: Compute revenue, costs, margins, and effective hourly rates by project
- **Employee Utilization**: Track billable vs non-billable hours, utilization %, and capacity
- **Financial Statements**: 
  - Income Statement (accrual basis by invoice_date)
  - Cashflow Statement (cash basis by payment_date)
  - Runway calculation
- **Interactive Dashboard**: Clean Streamlit UI with filters, charts, and tables

## Quick Start

### Prerequisites

- Python 3.11+
- pip

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Decision-Infrastructure
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app**:
   ```bash
   streamlit run app.py
   ```

The app will open in your browser at `http://localhost:8501`.

## Data Requirements

The app expects CSV files in `./data/sample/`:

- **projects.csv**: project_id, client_name, project_name, project_type, billing_model, contract_value_eur, start_date, end_date, status, currency, country, industry
- **employees.csv**: employee_id, job_title, department, monthly_salary_eur, employment_type, country_payroll, employer_cost_multiplier, weekly_capacity_hours, start_date
- **time_entries.csv**: date, employee_id, project_id, hours_logged, activity_type, task, hourly_cost_eur
- **invoices.csv**: invoice_id, client_name, project_id, invoice_date, amount_eur, status, payment_date, due_date
- **expenses.csv**: expense_id, date, category, vendor, amount_eur, fixed_or_variable, allocated_project_id

## Pages

### 1. Overview Dashboard
- Date range selector
- KPI cards: Revenue, Gross Profit, EBITDA, Cash Collected, Ending Cash, Runway
- Charts: Revenue vs COGS vs EBITDA, Cashflow trends
- Top/Bottom projects tables

### 2. Projects
- Filter by client, status, billing_model, country, industry
- Projects table with profitability metrics
- Project detail view with monthly trends and team contribution

### 3. People & Utilization
- Employee utilization table
- Utilization distribution charts
- Billable vs non-billable hours over time
- Underutilized/overutilized employee alerts

### 4. Financial Statements
- Income Statement (accrual basis)
- Cashflow Statement (cash basis)
- CSV export for both statements

### 5. Data Quality
- Validation errors and warnings
- Row counts per file
- Date coverage information

## Key Calculations

### Project Profitability
- **Billable hours**: Sum of hours where `activity_type == "billable"` AND `project_id != "INTERNAL"`
- **Labor cost**: Sum of `hours_logged * hourly_cost_eur` for the project
- **Allocated expenses**: Sum of expenses where `allocated_project_id == project_id`
- **Gross profit**: Revenue - Labor cost - Allocated expenses
- **Gross margin %**: Gross profit / Revenue
- **Effective hourly rate**: Revenue / Billable hours

### Employee Utilization
- **Monthly capacity**: `weekly_capacity_hours * 52 / 12` (prorated for start month)
- **Utilization %**: Billable hours / Monthly capacity
- **Internal hours**: Hours where `project_id == "INTERNAL"`

### Income Statement (Accrual)
- **Revenue**: Sum of invoices by `invoice_date` month
- **COGS**: Direct labor cost + Direct allocated expenses
- **Gross profit**: Revenue - COGS
- **Operating expenses**: Overhead labor + Overhead expenses
- **EBITDA**: Gross profit - Operating expenses

### Cashflow Statement (Cash)
- **Cash In**: Sum of invoices with `payment_date` by payment month
- **Cash Out (Payroll)**: `monthly_salary_eur * employer_cost_multiplier` for active employees
- **Cash Out (Expenses)**: Sum of expenses by date month
- **Net cashflow**: Cash In - Cash Out
- **Ending cash**: Starting cash + cumulative net cashflow
- **Runway**: Ending cash / Average monthly burn (last 3 months)

## Project Structure

```
Decision-Infrastructure/
├── app.py                 # Main Streamlit app
├── src/
│   ├── config.py         # Schemas and constants
│   ├── data_loader.py    # CSV loading and validation
│   ├── metrics.py        # All calculations
│   └── ui_components.py  # UI helpers
├── data/
│   └── sample/           # CSV files
├── requirements.txt
└── README.md
```

## Configuration

- **Starting Cash**: Set in sidebar (default: €50,000)
- **Underutilized threshold**: < 60% utilization
- **Overutilized threshold**: > 85% utilization

## Notes

- All monetary values are in EUR
- Dates are bucketed by month (YYYY-MM format)
- Empty months are handled gracefully
- The app is data-driven (no hard-coded project IDs)
- INTERNAL project_id is used for non-billable/internal work

## License

[Add your license here]
