"""
Configuration Management for CatBoost Demand Forecasting Pipeline
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Config:
    """Configuration management for the demand forecasting pipeline."""
    
    def __init__(self, config_path: str = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Optional path to custom config file
        """
        self.base_dir = Path(__file__).parent.parent
        self.config = self._load_config(config_path)
        
    def _load_config(self, config_path: str = None) -> Dict[str, Any]:
        """Load configuration from file or use defaults."""
        default_config = {
            # Paths
            "dataset_path": str(self.base_dir / "DataSet" / "syn_data" / "synthetic_passenger_demand.csv"),
            "output_dir": str(self.base_dir / "outputs"),
            "model_dir": str(self.base_dir / "outputs" / "models"),
            "plots_dir": str(self.base_dir / "outputs" / "plots"),
            
            # Model parameters
            "random_seed": 42,
            "iterations": 200,
            "learning_rate": 0.05,
            "depth": 8,
            "l2_leaf_reg": 3.0,
            "loss_function": "RMSE",
            "eval_metric": "RMSE",
            "early_stopping_rounds": 20,
            "verbose": 100,
            
            # Data split
            "train_split": 0.70,
            "val_split": 0.15,
            "test_split": 0.15,
            
            # Target variable
            "target_column": "passenger_count",
            
            # Features to exclude (leakage features)
            "exclude_features": [
                "boarding_count",
                "alighting_count",
                "onboard_passengers",
                "occupancy_ratio",
                "load_factor",
                "demand_class"
            ],
            
            # Categorical feature detection threshold
            "categorical_threshold": 10,  # Max unique values for auto-detection
            
            # Model export
            "model_format": "cbm",  # CatBoost native format
            "export_feature_importance": True,
            "export_predictions": True,
            
            # Evaluation
            "metrics": ["RMSE", "MAE", "R2", "MAPE"],
            
            # Plotting
            "plot_actual_vs_predicted": True,
            "plot_residuals": True,
            "plot_feature_importance": True,
            
            # Real-time inference
            "model_load_path": str(self.base_dir / "outputs" / "models" / "catboost_demand_model.cbm"),
            "inference_batch_size": 1000,
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
                logger.info(f"Loaded configuration from {config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}. Using defaults.")
        
        return default_config
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self.config[key] = value
    
    def save(self, path: str) -> None:
        """Save current configuration to file."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.config, f, indent=2)
        logger.info(f"Configuration saved to {path}")
    
    def ensure_directories(self) -> None:
        """Ensure all output directories exist."""
        for dir_key in ['output_dir', 'model_dir', 'plots_dir']:
            dir_path = self.get(dir_key)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
        logger.info("Output directories ensured")


# Global config instance
config = Config()
