"""Model registry for managing models."""

from pathlib import Path
from typing import Optional
from .torch.infer import ProjectMarginRiskModel


def get_model_path(model_name: str = "project_margin_risk") -> Path:
    """Get path to model file."""
    artifacts_dir = Path(__file__).parent.parent.parent / "artifacts" / "models"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return artifacts_dir / f"{model_name}.pt"


def load_model_if_exists(model_name: str = "project_margin_risk") -> Optional[ProjectMarginRiskModel]:
    """Load model if it exists, otherwise return None."""
    model_path = get_model_path(model_name)
    if model_path.exists():
        try:
            model = ProjectMarginRiskModel()
            model.load(model_path)
            return model
        except Exception as e:
            print(f"Error loading model: {e}")
            return None
    return None
