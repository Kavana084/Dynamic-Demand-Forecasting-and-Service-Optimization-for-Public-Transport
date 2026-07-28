"""
Inspect CatBoost model metadata and extract feature information.
"""
import sys
import json
from catboost import CatBoostRegressor

# Path to CatBoost model
model_path = 'F:/transit-ai-system/outputs/models/catboost_demand_model.cbm'
config_path = 'F:/transit-ai-system/outputs/model_config.json'
metrics_path = 'F:/transit-ai-system/outputs/training_metrics.json'

print("=" * 80)
print("CatBoost Model Inspection")
print("=" * 80)

# Load model
print(f"\nLoading model from: {model_path}")
try:
    model = CatBoostRegressor()
    model.load_model(model_path)
    print("✓ Model loaded successfully")
except Exception as e:
    print(f"✗ Failed to load model: {e}")
    sys.exit(1)

# Extract model metadata
print("\n" + "=" * 80)
print("Model Metadata")
print("=" * 80)

print(f"Tree count: {model.tree_count_}")
print(f"Number of features: {len(model.feature_names_) if hasattr(model, 'feature_names_') else 'Unknown'}")
print(f"Best iteration: {model.best_iteration_}")
print(f"Learning rate: {model.learning_rate_}")
print(f"Random seed: {model.random_seed_}")

# Get feature names from model
print("\n" + "=" * 80)
print("Feature Information from Model")
print("=" * 80)

try:
    feature_names = model.feature_names_
    print(f"Feature names count: {len(feature_names)}")
    print(f"First 10 features: {feature_names[:10]}")
except Exception as e:
    print(f"Could not extract feature names from model: {e}")

# Get categorical feature indices
print("\n" + "=" * 80)
print("Categorical Features")
print("=" * 80)

try:
    cat_features = model.cat_features_
    print(f"Categorical feature indices: {cat_features}")
    print(f"Categorical feature count: {len(cat_features)}")
except Exception as e:
    print(f"Could not extract categorical features from model: {e}")

# Load model config
print("\n" + "=" * 80)
print("Model Config from JSON")
print("=" * 80)

try:
    with open(config_path, 'r') as f:
        config = json.load(f)
    print(f"✓ Config loaded from: {config_path}")
    print(f"Feature names count: {len(config['feature_names'])}")
    print(f"Categorical features count: {len(config['categorical_features'])}")
    print(f"Training date: {config['training_date']}")
    print(f"Best iteration: {config['best_iteration']}")
except Exception as e:
    print(f"✗ Failed to load config: {e}")

# Load training metrics
print("\n" + "=" * 80)
print("Training Metrics")
print("=" * 80)

try:
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)
    print(f"✓ Metrics loaded from: {metrics_path}")
    print(f"RMSE: {metrics['RMSE']:.4f}")
    print(f"MAE: {metrics['MAE']:.4f}")
    print(f"R2: {metrics['R2']:.4f}")
    print(f"MAPE: {metrics['MAPE']:.2f}%")
    print(f"Number of features: {metrics['n_features']}")
    print(f"Number of categorical: {metrics['n_categorical']}")
except Exception as e:
    print(f"✗ Failed to load metrics: {e}")

print("\n" + "=" * 80)
print("Inspection Complete")
print("=" * 80)
