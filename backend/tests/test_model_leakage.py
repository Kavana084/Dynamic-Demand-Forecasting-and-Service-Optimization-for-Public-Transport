import os
import json
import pytest
from app.config import settings
from app.config import ROOT_DIR

def test_model_leakage_in_features():
    """
    Test to ensure that no target-derived features are present in the model's feature set.
    This acts as a strict gate to prevent data leakage.
    """
    def _resolve(p: str) -> str:
        if os.path.isabs(p):
            return p
        return str(ROOT_DIR / p)

    config_path = _resolve(settings.training_metrics_path)
    
    # If the file doesn't exist yet, we pass but warn, or we could fail. 
    # Since this is an acceptance gate for retraining, it should fail if the file is missing 
    # or if the features are leaked.
    assert os.path.exists(config_path), f"Training metrics not found at {config_path}. Run training first."

    with open(config_path, 'r') as f:
        model_config = json.load(f)

    feature_names = model_config.get('feature_names', [])
    assert len(feature_names) > 0, "Feature names list is empty"

    leaked_features = [
        "passenger_count",
        "boarding_count",
        "alighting_count",
        "onboard_passengers",
        "occupancy_ratio",
        "load_factor",
        "demand_class",
        "congestion_index",
        "traffic_delay",
        "total_delay"
    ]

    found_leaks = [feat for feat in leaked_features if feat in feature_names]
    
    assert not found_leaks, f"CRITICAL LEAKAGE DETECTED: Found target-derived features in model inputs: {found_leaks}"
