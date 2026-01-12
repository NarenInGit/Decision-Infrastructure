"""
This module computes project- and client-level profitability.

Inputs:
- DataFrame of project revenue
- DataFrame of allocated delivery costs

Outputs:
- DataFrame with revenue, cost, margin (€), margin (%)
- Flags for negative or risky margins

This logic must be deterministic and independent of any UI.
"""

import pandas as pd


def compute_project_profitability(revenue_df, cost_df):
    """
    Compute project-level profitability by aggregating revenue and costs.
    
    Args:
        revenue_df: DataFrame with columns project_id, client_name, amount
        cost_df: DataFrame with columns project_id, client_name, amount
    
    Returns:
        DataFrame with columns: project_id, client_name, revenue, cost, margin, margin_pct
    """
    # Aggregate revenue by project_id
    revenue_agg = revenue_df.groupby('project_id').agg({
        'amount': 'sum',
        'client_name': 'first'  # Take first client_name per project (assuming consistent)
    }).rename(columns={'amount': 'revenue'})
    
    # Aggregate costs by project_id
    cost_agg = cost_df.groupby('project_id').agg({
        'amount': 'sum'
    }).rename(columns={'amount': 'cost'})
    
    # Merge revenue and costs
    result = revenue_agg.merge(cost_agg, left_index=True, right_index=True, how='outer')
    
    # Fill missing values with 0 (projects with only revenue or only costs)
    result['revenue'] = result['revenue'].fillna(0)
    result['cost'] = result['cost'].fillna(0)
    
    # Calculate margin and margin percentage
    result['margin'] = result['revenue'] - result['cost']
    result['margin_pct'] = result['margin'] / result['revenue'].replace(0, pd.NA)
    
    # Reset index to make project_id a column
    result = result.reset_index()
    
    # Select and order output columns
    result = result[['project_id', 'client_name', 'revenue', 'cost', 'margin', 'margin_pct']]
    
    return result