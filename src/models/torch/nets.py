"""
Simple PyTorch neural networks for project margin risk.
"""

import torch
import torch.nn as nn


class ProjectMarginRiskNet(nn.Module):
    """
    Simple neural network for predicting project margin risk.
    
    Very small model: Linear -> ReLU -> Linear -> Sigmoid
    """
    
    def __init__(self, input_dim: int, hidden_dim: int = 8):
        """
        Initialize network.
        
        Args:
            input_dim: Number of input features
            hidden_dim: Hidden layer dimension (default: 8, very small)
        """
        super(ProjectMarginRiskNet, self).__init__()
        
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        """Forward pass."""
        return self.net(x).squeeze()
