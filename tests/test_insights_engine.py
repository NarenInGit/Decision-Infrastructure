import pandas as pd

from src.core.insights_engine import generate_insights


def test_overdue_invoice_insights_are_deterministic_for_a_fixed_clock(monkeypatch):
    invoices = pd.DataFrame(
        [
            {
                "invoice_id": "I001",
                "client_name": "Acme",
                "project_id": "P001",
                "invoice_date": "2026-02-01",
                "amount_eur": 100,
                "status": "open",
                "payment_date": None,
                "due_date": "2026-02-10",
            },
            {
                "invoice_id": "I002",
                "client_name": "Acme",
                "project_id": "P001",
                "invoice_date": "2026-02-01",
                "amount_eur": 50,
                "status": "paid",
                "payment_date": "2026-02-20",
                "due_date": "2026-02-15",
            },
            {
                "invoice_id": "I003",
                "client_name": "Acme",
                "project_id": "P001",
                "invoice_date": "2026-02-01",
                "amount_eur": 75,
                "status": "open",
                "payment_date": None,
                "due_date": "2026-04-01",
            },
        ]
    )

    fixed_now = pd.Timestamp("2026-03-01")
    monkeypatch.setattr(pd.Timestamp, "now", lambda *args, **kwargs: fixed_now)

    first = generate_insights(projects_metrics=pd.DataFrame(), invoices=invoices)
    second = generate_insights(projects_metrics=pd.DataFrame(), invoices=invoices)

    assert first == second
    overdue = [insight for insight in first if insight["type"] == "invoices_overdue"]
    assert len(overdue) == 1
    assert overdue[0]["message"] == "2 invoice(s) are overdue"
    assert "Total overdue amount: EUR 150" in overdue[0]["drivers"][0]
