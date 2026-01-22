"""
PyTorch Dataset for project margin risk prediction.
"""

import torch
from torch.utils.data import Dataset
import pandas as pd
import numpy as np


class ProjectMarginRiskDataset(Dataset):
    """
    Dataset for predicting project margin risk.
    
    Label: 1 if next_month_gross_margin_pct < 0, else 0
    """
    
    def __init__(self, features_df: pd.DataFrame):
        """
        Initialize dataset.
        
        Args:
            features_df: DataFrame with columns: project_id, month, revenue, gross_margin_pct, etc.
        """
        self.features_df = features_df.copy()
        
        # Create labels: next month's margin < 0
        self.features_df = self.features_df.sort_values(["project_id", "month"])
        self.features_df["next_month_margin_pct"] = self.features_df.groupby("project_id")["gross_margin_pct"].shift(-1)
        self.features_df["label"] = (self.features_df["next_month_margin_pct"] < 0).astype(int)
        
        # Drop rows where next month label is unavailable
        self.features_df = self.features_df[self.features_df["next_month_margin_pct"].notna()]
        
        # Select feature columns (exclude metadata)
        feature_cols = [
            "revenue",
            "gross_margin_pct",
            "billable_hours",
            "effective_hourly_rate",
            "labor_cost",
            "allocated_expenses",
            "revenue_delta_pct",
            "margin_delta_pct"
        ]
        
        # Filter to available columns
        available_cols = [col for col in feature_cols if col in self.features_df.columns]
        self.feature_cols = available_cols
        
        # Extract features and labels
        self.features = self.features_df[available_cols].fillna(0).values.astype(np.float32)
        self.labels = self.features_df["label"].values.astype(np.float32)
        
        # Normalize features (simple min-max)
        self.feature_min = self.features.min(axis=0, keepdims=True)
        self.feature_max = self.features.max(axis=0, keepdims=True)
        self.feature_range = self.feature_max - self.feature_min
        self.feature_range[self.feature_range == 0] = 1  # Avoid division by zero
        
        self.features_normalized = (self.features - self.feature_min) / self.feature_range
    
    def __len__(self):
        return len(self.features)
    
    def __getitem__(self, idx):
        return (
            torch.tensor(self.features_normalized[idx], dtype=torch.float32),
            torch.tensor(self.labels[idx], dtype=torch.float32)
        )
    
    def get_feature_dim(self):
        """Get number of features."""
        return self.features.shape[1]
