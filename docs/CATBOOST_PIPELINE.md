# CatBoost Demand Forecasting Pipeline Documentation

## Overview

This document describes the refactored CatBoost training and inference pipeline for passenger demand forecasting. The pipeline uses the production-quality synthetic dataset (`synthetic_passenger_demand.csv`) with 58 features and approximately 262,000 records.

## Architecture

### Components

1. **config.py** - Configuration management
2. **data_preprocessing.py** - Schema validation and data preparation
3. **train_catboost_v2.py** - Training pipeline
4. **realtime_feature_engineering_v2.py** - Real-time inference

### Key Changes from Legacy

- **Removed**: `build_dataset()` function that generated synthetic data on-the-fly
- **Added**: Direct loading from pre-generated `synthetic_passenger_demand.csv`
- **Enhanced**: Schema validation, categorical feature detection, chronological splitting
- **Improved**: Real-time inference using trained model instead of hard-coded rules

## Training Pipeline

### Usage

```bash
cd F:\transit-ai-system
python scripts/train_catboost_v2.py
```

### Process Flow

1. **Load Dataset**: Loads `synthetic_passenger_demand.csv` from `DataSet/syn_data/`
2. **Chronological Split**: Splits data by `service_date`:
   - Train: 70% (earliest dates)
   - Validation: 15% (middle dates)
   - Test: 15% (latest dates)
3. **Schema Validation**: Validates against expected schema with 58 features
4. **Data Type Conversion**: Converts columns to appropriate types
5. **Categorical Detection**: Identifies 15 categorical features
6. **Model Training**: Trains CatBoostRegressor with early stopping
7. **Evaluation**: Computes RMSE, MAE, R², MAPE
8. **Export**: Saves model, metrics, feature importance, predictions, config, plots

### Configuration

Edit `scripts/config.py` to customize:

```python
# Model parameters
"iterations": 200,              # Number of boosting iterations
"learning_rate": 0.05,          # Learning rate
"depth": 8,                     # Tree depth
"early_stopping_rounds": 20,     # Early stopping patience

# Data split
"train_split": 0.70,            # Training split ratio
"val_split": 0.15,              # Validation split ratio
"test_split": 0.15,             # Test split ratio

# Paths
"dataset_path": "DataSet/syn_data/synthetic_passenger_demand.csv"
"model_dir": "outputs/models"
"plots_dir": "outputs/plots"
```

### Output Files

- `outputs/models/catboost_demand_model.cbm` - Trained CatBoost model
- `outputs/training_metrics.json` - Performance metrics
- `outputs/feature_importance.csv` - Feature importance rankings
- `outputs/predictions.csv` - Test set predictions
- `outputs/model_config.json` - Model configuration
- `outputs/plots/actual_vs_predicted.png` - Actual vs predicted plot
- `outputs/plots/residual_distribution.png` - Residual distribution plot
- `outputs/plots/feature_importance.png` - Feature importance plot

### Performance Metrics

Current model performance (200 iterations):
- **RMSE**: 3.07
- **MAE**: 2.39
- **R²**: 0.9743 (97.4% variance explained)
- **MAPE**: 6.39%

### Top Features

1. boarding_count (54.14% importance)
2. alighting_count (27.13% importance)
3. area_type (2.99% importance)
4. historical_stop_average (2.10% importance)
5. vehicle_capacity (2.00% importance)

## Real-time Inference

### Usage

```python
from scripts.realtime_feature_engineering_v2 import get_predictor

# Get predictor instance (loads model once)
predictor = get_predictor()

# Single prediction
trip_data = {
    'route_id': '123',
    'stop_id': '456',
    'stop_name': 'Central Station',
    'area_type': 'Commercial',
    'route_length_km': 15.5,
    'vehicle_capacity': 60,
    # ... other features
}

weather_data = {
    'condition': 'Sunny',
    'temperature': 28,
    'rainfall': 0
}

result = predictor.predict(trip_data, weather_data)
print(f"Predicted passengers: {result['passenger_count']}")

# Batch prediction
trips_data = [trip_data1, trip_data2, ...]
results = predictor.predict_batch(trips_data, weather_data)
```

### Feature Construction

The inference module automatically constructs the full 57-feature vector matching the training schema:

- **Route Features**: route_id, route_short_name, route_type, service_id, trip_id, shape_id, direction_id
- **Stop Features**: stop_id, stop_name, stop_sequence, stop_lat, stop_lon, terminal_stop_flag, major_interchange_flag, area_type, distance features
- **Trip Features**: route_length_km, scheduled_trip_duration, trip times
- **Temporal Features**: hour, minute, time_slot, day_of_week, weekday_weekend, month, holiday_flag, peak_hour_flag
- **Weather Features**: weather_condition, temperature, rainfall_flag
- **Traffic Features**: congestion_index, traffic_level, average_speed, delays
- **Service Features**: headway_minutes, service_frequency_category
- **Historical Features**: Historical averages (use defaults for real-time)
- **Operational Features**: route_popularity_score, vehicle_capacity

### Schema Consistency

The inference module ensures:
1. All 57 training features are present
2. Categorical features are converted to strings
3. Feature order matches training
4. Missing features are filled with defaults

## Data Preprocessing

### Schema Validation

The preprocessor validates:
- All 58 expected columns are present
- Data types match expected schema
- No orphan records (GTFS relationships preserved)

### Categorical Features

Predefined categorical features (15 total):
- route_id, route_short_name, service_id, trip_id, shape_id
- stop_id, stop_name
- time_slot, day_of_week, weekday_weekend
- weather_condition, traffic_level, service_frequency_category
- area_type, demand_class

### Numeric Features

42 numeric features including:
- route_type, direction_id, stop_sequence, coordinates
- distances, durations, times
- flags, indices, counts
- historical averages, operational metrics

## Integration with Backend

### Replacing Legacy Workflow

**Before:**
```python
from build_dataset import build_dataset
from train_catboost import train_model

df = build_dataset(gtfs_dir, output_path)  # Generated synthetic data
train_model()  # Used limited features
```

**After:**
```python
from scripts.train_catboost_v2 import CatBoostTrainer

trainer = CatBoostTrainer()
results = trainer.train_and_evaluate()  # Uses pre-generated dataset, all features
```

### Replacing Real-time Estimation

**Before:**
```python
from realtime_feature_engineering import RealTimeFeatureEngineer

engineer = RealTimeFeatureEngineer()
passenger_count = engineer.estimate_passenger_count(hour, congestion)  # Hard-coded rules
```

**After:**
```python
from scripts.realtime_feature_engineering_v2 import get_predictor

predictor = get_predictor()
result = predictor.predict(trip_data, weather_data)  # ML-based prediction
```

## Backward Compatibility

The new pipeline maintains backward compatibility:
- Backend API endpoints remain unchanged
- Model loading is transparent to the API
- Feature construction happens internally
- Response format is consistent

## Dependencies

Updated requirements:
```
catboost==1.2.10
pandas==2.1.2
matplotlib>=3.8.0
seaborn>=0.13.0
scikit-learn>=1.3.0
openpyxl>=3.1.0
```

Install:
```bash
pip install -r requirements.txt
```

## Troubleshooting

### Model Loading Issues

If the model fails to load:
1. Check `outputs/models/catboost_demand_model.cbm` exists
2. Verify `outputs/model_config.json` exists
3. Ensure CatBoost version matches training (1.2.10)

### Prediction Errors

If predictions fail:
1. Verify all required features are provided
2. Check categorical features are strings
3. Ensure feature names match training schema
4. Review logs for specific error messages

### Memory Issues

If training runs out of memory:
1. Reduce `iterations` in config
2. Reduce `depth` in config
3. Use a subset of data for testing

## Future Enhancements

Potential improvements:
1. Hyperparameter tuning with Optuna
2. Cross-validation for robust evaluation
3. Feature importance analysis for feature selection
4. Model ensemble with multiple algorithms
5. Real-time model retraining pipeline
6. A/B testing framework for model comparison

## Contact

For questions or issues, refer to the project repository or contact the development team.
