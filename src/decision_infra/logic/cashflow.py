"""
This module computes monthly cashflow and runway.

It models:
- starting cash
- expected inflows
- fixed monthly outflows
- resulting runway in months
"""


def compute_runway(starting_cash, monthly_inflow, monthly_outflow):
    """
    Compute cash runway and net burn rate.
    
    Args:
        starting_cash: Starting cash balance
        monthly_inflow: Expected monthly cash inflow
        monthly_outflow: Fixed monthly cash outflow
    
    Returns:
        tuple: (runway_months, net_burn)
            - runway_months: Number of months until cash runs out (inf if net_burn <= 0)
            - net_burn: Monthly net burn rate (outflow - inflow)
    """
    net_burn = monthly_outflow - monthly_inflow
    
    if net_burn > 0:
        runway_months = starting_cash / net_burn
    else:
        runway_months = float('inf')
    
    return runway_months, net_burn