"""
Training script for project margin risk model.
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
from pathlib import Path
from typing import Optional
import pandas as pd

from .datasets import ProjectMarginRiskDataset
from .nets import ProjectMarginRiskNet


def train_model(
    features_df: pd.DataFrame,
    model_save_path: Optional[Path] = None,
    epochs: int = 50,
    batch_size: int = 32,
    learning_rate: float = 0.01,
    seed: int = 42
):
    """
    Train the project margin risk model.
    
    Args:
        features_df: Features DataFrame
        model_save_path: Path to save model (default: artifacts/models/project_margin_risk.pt)
        epochs: Number of training epochs
        batch_size: Batch size
        learning_rate: Learning rate
        seed: Random seed for reproducibility
    
    Returns:
        dict with training metrics
    """
    # Set seed for reproducibility
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
    
    # Create dataset
    dataset = ProjectMarginRiskDataset(features_df)
    
    if len(dataset) == 0:
        raise ValueError("No valid training samples (need next-month labels)")
    
    # Split into train/val
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size], generator=torch.Generator().manual_seed(seed))
    
    # Create data loaders
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    # Create model
    input_dim = dataset.get_feature_dim()
    model = ProjectMarginRiskNet(input_dim=input_dim, hidden_dim=8)
    
    # Loss and optimizer
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    
    # Training loop
    model.train()
    train_losses = []
    val_losses = []
    val_accuracies = []
    
    for epoch in range(epochs):
        # Training
        train_loss = 0.0
        for features, labels in train_loader:
            optimizer.zero_grad()
            outputs = model(features)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        
        train_loss /= len(train_loader)
        train_losses.append(train_loss)
        
        # Validation
        model.eval()
        val_loss = 0.0
        correct = 0
        total = 0
        with torch.no_grad():
            for features, labels in val_loader:
                outputs = model(features)
                loss = criterion(outputs, labels)
                val_loss += loss.item()
                
                # Accuracy
                predicted = (outputs > 0.5).float()
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
        
        val_loss /= len(val_loader)
        val_accuracy = correct / total if total > 0 else 0.0
        val_losses.append(val_loss)
        val_accuracies.append(val_accuracy)
        
        model.train()
        
        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1}/{epochs} - Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}, Val Acc: {val_accuracy:.4f}")
    
    # Save model
    if model_save_path is None:
        artifacts_dir = Path(__file__).parent.parent.parent.parent / "artifacts" / "models"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        model_save_path = artifacts_dir / "project_margin_risk.pt"
    
    # Save model state and normalization params
    torch.save({
        "model_state_dict": model.state_dict(),
        "input_dim": input_dim,
        "hidden_dim": 8,
        "feature_min": dataset.feature_min,
        "feature_max": dataset.feature_max,
        "feature_range": dataset.feature_range,
        "feature_cols": dataset.feature_cols
    }, model_save_path)
    
    print(f"Model saved to {model_save_path}")
    
    return {
        "final_train_loss": train_losses[-1],
        "final_val_loss": val_losses[-1],
        "final_val_accuracy": val_accuracies[-1],
        "model_path": str(model_save_path)
    }


if __name__ == "__main__":
    # For testing
    from ...features.build_features import FeatureBuilder
    
    builder = FeatureBuilder()
    features_df = builder.load_features()
    
    if features_df is None:
        print("No features file found. Please build features first.")
    else:
        train_model(features_df)
