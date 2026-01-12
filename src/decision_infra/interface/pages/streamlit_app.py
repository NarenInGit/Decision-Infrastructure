"""
Streamlit interface for internal decision visibility.
This is a demo and internal tool, not a customer-facing SaaS.
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(src_path))

from decision_infra.logic.profitability import compute_project_profitability
from decision_infra.logic.cashflow import compute_runway


def main():
    st.title("Decision Infrastructure Dashboard")
    
    # Get the project root (file is at src/decision_infra/interface/pages/streamlit_app.py)
    # Go up 4 levels: pages -> interface -> decision_infra -> src -> project root
    project_root = Path(__file__).parent.parent.parent.parent.parent
    data_dir = project_root / "data" / "sample"
    
    # Load sample CSVs
    try:
        revenue_df = pd.read_csv(data_dir / "revenue.csv")
        cost_df = pd.read_csv(data_dir / "costs.csv")
    except FileNotFoundError:
        st.warning("Sample CSV files not found. Using generated sample data.")
        # Generate sample data
        revenue_df = pd.DataFrame({
            'project_id': ['P001', 'P002', 'P003'],
            'client_name': ['Client A', 'Client B', 'Client A'],
            'amount': [10000, 15000, 8000]
        })
        cost_df = pd.DataFrame({
            'project_id': ['P001', 'P002', 'P003'],
            'client_name': ['Client A', 'Client B', 'Client A'],
            'amount': [7000, 12000, 9000]
        })
    
    # Profitability section
    st.header("Project Profitability")
    profitability_df = compute_project_profitability(revenue_df, cost_df)
    st.dataframe(profitability_df)
    
    # Cashflow section
    st.header("Cashflow Runway")
    
    # Sample cashflow inputs
    starting_cash = 500000
    monthly_inflow = 50000
    monthly_outflow = 80000
    
    runway_months, net_burn = compute_runway(starting_cash, monthly_inflow, monthly_outflow)
    
    cashflow_data = {
        'Metric': ['Starting Cash', 'Monthly Inflow', 'Monthly Outflow', 'Net Burn', 'Runway (months)'],
        'Value': [
            f"€{starting_cash:,.0f}",
            f"€{monthly_inflow:,.0f}",
            f"€{monthly_outflow:,.0f}",
            f"€{net_burn:,.0f}",
            f"{runway_months:.1f}" if runway_months != float('inf') else "∞"
        ]
    }
    cashflow_df = pd.DataFrame(cashflow_data)
    st.dataframe(cashflow_df)


if __name__ == "__main__":
    main()
