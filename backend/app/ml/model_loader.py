import logging
import os
import json
import threading
from typing import List, Optional, Dict, Any
from catboost import CatBoostRegressor

from app.config import settings

logger = logging.getLogger(__name__)

class ModelLoader:
    _instance = None
    _model = None
    _model_config = None
    _training_metrics = None
    _feature_names = None
    _categorical_features = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelLoader, cls).__new__(cls)
        return cls._instance

    def load_model(self) -> bool:
        """Load CatBoost model and configuration. Thread-safe."""
        if self._model is not None:
            logger.info("Model already loaded, skipping reload.")
            return True

        with self._lock:
            # Double-check pattern
            if self._model is not None:
                return True

            # Resolve paths: the root .env may override settings with relative
            # paths (e.g. MODEL_PATH=outputs/models/...).  When cwd != project
            # root the relative lookup fails.  Always resolve against ROOT_DIR.
            from app.config import ROOT_DIR as _root
            def _resolve(p: str) -> str:
                if os.path.isabs(p):
                    return p
                return str(_root / p)

            model_path   = _resolve(settings.model_path)
            config_path  = _resolve(settings.model_config_path)
            metrics_path = _resolve(settings.training_metrics_path)

            logger.info("=" * 80)
            logger.info("MODEL LOADER DIAGNOSTICS")
            logger.info("=" * 80)
            logger.info(f"Model path: {model_path}")
            logger.info(f"Model path absolute: {os.path.abspath(model_path)}")
            logger.info(f"Config path: {config_path}")
            logger.info(f"Metrics path: {metrics_path}")
            logger.info(f"Model exists: {os.path.exists(model_path)}")
            logger.info(f"Config exists: {os.path.exists(config_path)}")
            logger.info(f"Metrics exists: {os.path.exists(metrics_path)}")
            logger.info(f"Current working directory: {os.getcwd()}")

            if not os.path.exists(model_path):
                logger.error(f"Model not found at path: {model_path}")
                logger.error(f"Absolute path would be: {os.path.abspath(model_path)}")
                return False

            try:
                # Load CatBoost model
                logger.info("Loading CatBoost model...")
                self._model = CatBoostRegressor()
                self._model.load_model(model_path)
                logger.info("✓ CatBoost model loaded successfully")
                logger.info("MODEL_LOADED_SUCCESS")
                logger.info(f"MODEL_PATH {model_path}")
                
                # Fetch version if possible, otherwise unknown
                version = "1.0.0"  # We don't have version in model itself without config
                logger.info(f"MODEL_VERSION {version}")
                
                logger.info(f"  Tree count: {self._model.tree_count_}")
                logger.info(f"  Best iteration: {self._model.best_iteration_}")
                logger.info(f"  Learning rate: {self._model.learning_rate_}")
                logger.info(f"  Feature count: {len(self._model.feature_names_) if hasattr(self._model, 'feature_names_') else 'Unknown'}")

                # Load model configuration (optional - feature names are available from binary)
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        self._model_config = json.load(f)
                    self._feature_names = self._model_config.get('feature_names', [])
                    self._categorical_features = self._model_config.get('categorical_features', [])
                    logger.info(f"✓ Model config loaded: {len(self._feature_names)} features, {len(self._categorical_features)} categorical")
                    logger.info(f"  Training date: {self._model_config.get('training_date', 'N/A')}")
                else:
                    self._model_config = {}
                    self._feature_names = []
                    self._categorical_features = []

                # Load feature names from CatBoost binary (always available, no dependency on model_config.json)
                if not self._feature_names and hasattr(self._model, 'feature_names_'):
                    self._feature_names = list(self._model.feature_names_)
                    logger.info(
                        "[OK] Feature names loaded from model binary: %d features", len(self._feature_names)
                    )
                    logger.info("  First 10 features: %s", self._feature_names[:10])
                elif self._feature_names:
                    logger.info("[OK] Feature names from model_config.json: %d features", len(self._feature_names))
                else:
                    logger.error(
                        "[FAIL] Feature names unavailable from model binary. "
                        "Predictions will fail feature validation."
                    )


                # Load training metrics
                if os.path.exists(metrics_path):
                    with open(metrics_path, 'r') as f:
                        self._training_metrics = json.load(f)
                    logger.info(f"✓ Training metrics loaded:")
                    logger.info(f"  RMSE: {self._training_metrics.get('RMSE', 'N/A'):.4f}")
                    logger.info(f"  MAE: {self._training_metrics.get('MAE', 'N/A'):.4f}")
                    logger.info(f"  R2: {self._training_metrics.get('R2', 'N/A'):.4f}")
                    logger.info(f"  MAPE: {self._training_metrics.get('MAPE', 'N/A'):.2f}%")
                else:
                    logger.warning(f"✗ Training metrics not found at {metrics_path}")
                    self._training_metrics = {}

                logger.info("=" * 80)
                return True

            except Exception as e:
                logger.exception("CATBOOST LOAD FAILURE")
                raise

    def get_model(self) -> Optional[CatBoostRegressor]:
        """Get the loaded CatBoost model."""
        if self._model is None:
            self.load_model()
        return self._model

    def get_feature_names(self) -> List[str]:
        """Get the feature names used during training."""
        if self._feature_names is None:
            self.load_model()
        return self._feature_names or []

    def get_categorical_features(self) -> List[str]:
        """Get the categorical feature names."""
        if self._categorical_features is None:
            self.load_model()
        return self._categorical_features or []

    def get_model_config(self) -> Dict[str, Any]:
        """Get the full model configuration."""
        if self._model_config is None:
            self.load_model()
        return self._model_config or {}

    def get_training_metrics(self) -> Dict[str, Any]:
        """Get the training metrics."""
        if self._training_metrics is None:
            self.load_model()
        return self._training_metrics or {}

    def is_model_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._model is not None

    def get_model_info(self) -> Dict[str, Any]:
        """Get comprehensive model information."""
        return {
            "model_loaded": self.is_model_loaded(),
            "model_path": settings.model_path,
            "algorithm": "CatBoostRegressor",
            "feature_count": len(self.get_feature_names()),
            "categorical_feature_count": len(self.get_categorical_features()),
            "training_metrics": self.get_training_metrics(),
            "model_config": self.get_model_config()
        }


model_loader = ModelLoader()