"""
Feature builder - reads ONLY from metrics outputs, never raw CSVs.
Builds canonical feature table for ML models.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Optional


class FeatureBuilder:
    """Builds features from metrics engine outputs."""
    
    def __init__(self, artifacts_dir: Optional[Path] = None):
        """
        Initialize feature builder.
        
        Args:
            artifacts_dir: Directory to save artifacts (default: ./artifacts)
        """
        if artifacts_dir is None:
            artifacts_dir = Path(__file__).parent.parent.parent / "artifacts"
        self.artifacts_dir = artifacts_dir
        self.parquet_dir = artifacts_dir / "parquet"
        self.parquet_dir.mkdir(parents=True, exist_ok=True)
    
    def build_project_monthly_features(
        self,
        income_statement_monthly: pd.DataFrame,
        cashflow_monthly: pd.DataFrame,
        projects_metrics: pd.DataFrame,
        people_utilization: pd.DataFrame,
        time_entries: pd.DataFrame,
        invoices: pd.DataFrame,
        expenses: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Build fact_project_monthly_features table from metrics outputs.
        
        Args:
            income_statement_monthly: Monthly income statement DataFrame
            cashflow_monthly: Monthly cashflow DataFrame
            projects_metrics: Project metrics DataFrame (from compute_project_metrics with by_month=True)
            people_utilization: Employee utilization DataFrame (from compute_employee_utilization with by_month=True)
            time_entries: Time entries DataFrame (for utilization aggregation)
            invoices: Invoices DataFrame (for revenue deltas)
        
        Returns:
            DataFrame with project-month features
        """
        # Start with project metrics by month
        if "month" not in projects_metrics.columns:
            # Need to compute monthly project metrics
            from ..metrics import compute_project_metrics
            # This is a fallback - ideally projects_metrics should already be monthly
            if expenses is None:
                expenses = pd.DataFrame()
            projects_monthly = compute_project_metrics(
                time_entries, invoices, expenses, by_month=True
            )
        else:
            projects_monthly = projects_metrics.copy()
        
        # Ensure month is Period type
        if "month" in projects_monthly.columns:
            projects_monthly["month"] = pd.to_datetime(projects_monthly["month"].astype(str)).dt.to_period("M")
        
        # Calculate month-over-month deltas
        projects_monthly = projects_monthly.sort_values(["project_id", "month"])
        
        # Revenue delta
        projects_monthly["revenue_prev"] = projects_monthly.groupby("project_id")["revenue"].shift(1)
        projects_monthly["revenue_delta_pct"] = (
            (projects_monthly["revenue"] - projects_monthly["revenue_prev"]) / 
            projects_monthly["revenue_prev"].replace(0, np.nan)
        )
        
        # Margin delta
        projects_monthly["margin_pct_prev"] = projects_monthly.groupby("project_id")["gross_margin_pct"].shift(1)
        projects_monthly["margin_delta_pct"] = (
            projects_monthly["gross_margin_pct"] - projects_monthly["margin_pct_prev"]
        )
        
        # Add utilization (aggregate by project and month)
        if "month" in people_utilization.columns and "employee_id" in people_utilization.columns:
            # Get project utilization from time entries
            time_entries_copy = time_entries.copy()
            time_entries_copy["month"] = pd.to_datetime(time_entries_copy["date"]).dt.to_period("M")
            
            # Calculate project-level utilization
            project_hours = time_entries_copy.groupby(["project_id", "month"]).agg({
                "hours_logged": "sum"
            }).reset_index()
            
            # Merge with people utilization to get capacity
            # For simplicity, aggregate utilization at project level
            # This is a proxy - in reality you'd want more sophisticated aggregation
            projects_monthly = projects_monthly.merge(
                project_hours[["project_id", "month", "hours_logged"]],
                on=["project_id", "month"],
                how="left"
            )
            projects_monthly["utilization_pct"] = np.nan  # Placeholder - would need more complex logic
        
        # Select and rename columns for canonical feature table
        feature_cols = [
            "project_id",
            "month",
            "revenue",
            "gross_margin_pct",
            "billable_hours",
            "effective_hourly_rate",
            "labor_cost",
            "allocated_expenses",
            "revenue_delta_pct",
            "margin_delta_pct"
        ]
        
        # Build feature table
        fact_features = projects_monthly[[col for col in feature_cols if col in projects_monthly.columns]].copy()
        
        # Fill missing values
        fact_features = fact_features.fillna(0)
        
        # Ensure month is string for parquet compatibility
        fact_features["month"] = fact_features["month"].astype(str)
        
        return fact_features
    
    def save_features(self, features_df: pd.DataFrame, filename: str = "fact_project_monthly_features.parquet"):
        """Save features to parquet file."""
        filepath = self.parquet_dir / filename
        features_df.to_parquet(filepath, index=False)
        return filepath
    
    def load_features(self, filename: str = "fact_project_monthly_features.parquet") -> Optional[pd.DataFrame]:
        """Load features from parquet file."""
        filepath = self.parquet_dir / filename
        if filepath.exists():
            return pd.read_parquet(filepath)
        return None
