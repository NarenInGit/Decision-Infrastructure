Decision Infrastructure — Sample Dataset (A–E)
Time range: 2025-10-01 to 2026-03-31 (time entries), invoices mainly Oct 2025–Mar 2026 (plus milestone invoices outside range).

Files:
A) projects.csv         — Project/client master data
B) time_entries.csv     — Time tracking lines (billable/non-billable + hourly cost)
C) employees.csv        — Payroll + employer cost multiplier + capacity
D) invoices.csv         — Revenue & collections (paid/unpaid/overdue + payment dates)
E) expenses.csv         — OpEx lines (fixed/variable + optional project allocation)

Notes:
- time_entries.project_id can be a real project_id or "INTERNAL" for overhead/non-client work.
- invoices.amount_eur for T&M is derived from billable hours * employee-specific bill rates.
- expenses.allocated_project_id is blank for overhead; sometimes populated for project-linked costs.