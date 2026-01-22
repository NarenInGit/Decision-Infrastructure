"""
Inference for project margin risk model.
"""

import torch
import torch.nn as nn
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional

from .nets import ProjectMarginRiskNet


class ProjectMarginRiskModel:
    """Wrapper for project margin risk model inference."""
    
    def __init__(self):
        self.model = None
        self.feature_cols = None
        self.feature_min = None
        self.feature_max = None
        self.feature_range = None
        self.input_dim = None
    
    def load(self, model_path: Path):
        """Load model from file."""
        checkpoint = torch.load(model_path, map_location="cpu")
        
        self.input_dim = checkpoint["input_dim"]
        self.feature_cols = checkpoint["feature_cols"]
        self.feature_min = checkpoint["feature_min"]
        self.feature_max = checkpoint["feature_max"]
        self.feature_range = checkpoint["feature_range"]
        
        # Create model
        self.model = ProjectMarginRiskNet(input_dim=self.input_dim, hidden_dim=checkpoint.get("hidden_dim", 8))
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.eval()
    
    def predict(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """
        Make predictions on features DataFrame.
        
        Args:
            features_df: DataFrame with feature columns
        
        Returns:
            DataFrame with predictions added
        """
        if self.model is None:
            raise ValueError("Model not loaded. Call load() first.")
        
        # Select and normalize features
        available_cols = [col for col in self.feature_cols if col in features_df.columns]
        if len(available_cols) != len(self.feature_cols):
            raise ValueError(f"Missing feature columns. Expected: {self.feature_cols}, Got: {available_cols}")
        
        features = features_df[available_cols].fillna(0).values.astype(np.float32)
        features_normalized = (features - self.feature_min) / self.feature_range
        
        # Predict
        with torch.no_grad():
            features_tensor = torch.tensor(features_normalized, dtype=torch.float32)
            predictions = self.model(features_tensor).numpy()
        
        # Add predictions to DataFrame
        result_df = features_df.copy()
        result_df["risk_probability"] = predictions
        
        return result_df
    
    def predict_latest(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """
        Predict risk for latest month of each project.
        
        Args:
            features_df: DataFrame with project-month features
        
        Returns:
            DataFrame with latest month predictions per project
        """
        if "month" not in features_df.columns:
            raise ValueError("features_df must have 'month' column")
        
        # Get latest month per project
        features_df = features_df.copy()
        features_df["month_dt"] = pd.to_datetime(features_df["month"])
        latest_idx = features_df.groupby("project_id")["month_dt"].idxmax()
        latest_features = features_df.loc[latest_idx]
        
        return self.predict(latest_features)
