"""Base model interfaces."""

from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd


class BaseModel(ABC):
    """Base interface for all models."""
    
    @abstractmethod
    def predict(self, features: pd.DataFrame) -> pd.DataFrame:
        """Make predictions on features."""
        pass
    
    @abstractmethod
    def train(self, features: pd.DataFrame, labels: pd.Series) -> dict:
        """Train the model."""
        pass
