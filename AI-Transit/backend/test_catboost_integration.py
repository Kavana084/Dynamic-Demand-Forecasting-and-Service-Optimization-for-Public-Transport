"""
Test script for CatBoost integration
===================================
Tests the new CatBoost model loading, prediction, and API integration.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.ml.model_loader import model_loader
from app.ml.predictor import predictor
from app.services.demand_prediction_service import demand_prediction_service
from app.config import settings

def test_model_loading():
    """Test CatBoost model loading."""
    print("=" * 60)
    print("TEST 1: Model Loading")
    print("=" * 60)
    
    print(f"Model path: {settings.model_path}")
    print(f"Config path: {settings.model_config_path}")
    print(f"Metrics path: {settings.training_metrics_path}")
    
    success = model_loader.load_model()
    
    if success:
        print("✓ Model loaded successfully")
        print(f"✓ Model loaded: {model_loader.is_model_loaded()}")
        print(f"✓ Feature count: {len(model_loader.get_feature_names())}")
        print(f"✓ Categorical features: {len(model_loader.get_categorical_features())}")
        print(f"✓ Training metrics: {model_loader.get_training_metrics()}")
        return True
    else:
        print("✗ Failed to load model")
        return False

def test_prediction():
    """Test CatBoost prediction with sample features."""
    print("\n" + "=" * 60)
    print("TEST 2: Prediction")
    print("=" * 60)
    
    # Create sample features matching the 57-feature training schema
    # service_date should be numeric (day number from reference)
    features = {
        "service_date": 20240115,  # Numeric date format
        "route_id": "test_route_123",
        "route_short_name": "123",
        "route_type": 3,
        "service_id": "weekday",
        "trip_id": "test_trip_001",
        "shape_id": "shape_001",
        "direction_id": 0,
        "stop_id": "test_stop_456",
        "stop_name": "Test Stop",
        "stop_sequence": 1,
        "stop_lat": 12.9716,
        "stop_lon": 77.5946,
        "terminal_stop_flag": 0,
        "major_interchange_flag": 0,
        "area_type": "Commercial",
        "cumulative_distance": 0.0,
        "remaining_distance": 10.0,
        "number_of_stops": 20,
        "remaining_stops": 19,
        "route_length_km": 15.5,
        "scheduled_trip_duration": 45,
        "trip_start_time": 540,  # 9:00 AM
        "trip_end_time": 585,    # 9:45 AM
        "hour": 9,
        "minute": 0,
        "time_slot": "Morning",
        "day_of_week": "Monday",
        "weekday_weekend": "Weekday",
        "month": 1,
        "holiday_flag": 0,
        "peak_hour_flag": 1,
        "weather_condition": "Clear",
        "temperature": 28,
        "rainfall_flag": 0,
        "congestion_index": 1.2,
        "traffic_level": "Medium",
        "average_speed": 30,
        "traffic_delay": 2,
        "weather_delay": 0,
        "boarding_delay": 1,
        "total_delay": 3,
        "headway_minutes": 15,
        "service_frequency_category": "Normal",
        "historical_route_average": 35.0,
        "historical_stop_average": 30.0,
        "historical_hour_average": 40.0,
        "historical_peak_average": 50.0,
        "historical_weekend_average": 25.0,
        "route_popularity_score": 0.7,
        "vehicle_capacity": 60,
        "boarding_count": 5,
        "alighting_count": 2,
        "onboard_passengers": 30,
        "occupancy_ratio": 0.5,
        "load_factor": 0.5,
        "demand_class": "Medium",
    }
    
    print(f"Input features: {len(features)} features")
    
    result = predictor.predict_passenger_count(features)
    
    if result.get("success"):
        print("✓ Prediction successful")
        print(f"✓ Predicted passengers: {result.get('predicted_passenger_count')}")
        print(f"✓ Confidence: {result.get('confidence_score')}")
        print(f"✓ Demand class: {result.get('demand_class')}")
        print(f"✓ Inference time: {result.get('inference_time_ms')} ms")
        print(f"✓ Model version: {result.get('model_version')}")
        print(f"✓ Model source: {result.get('model_source')}")
        return True
    else:
        print(f"✗ Prediction failed: {result.get('error')}")
        return False

def test_demand_service():
    """Test demand prediction service."""
    print("\n" + "=" * 60)
    print("TEST 3: Demand Prediction Service")
    print("=" * 60)
    
    features = {
        "service_date": 20240115,  # Numeric date format
        "route_id": "test_route_123",
        "route_short_name": "123",
        "route_type": 3,
        "service_id": "weekday",
        "trip_id": "test_trip_001",
        "shape_id": "shape_001",
        "direction_id": 0,
        "stop_id": "test_stop_456",
        "stop_name": "Test Stop",
        "stop_sequence": 1,
        "stop_lat": 12.9716,
        "stop_lon": 77.5946,
        "terminal_stop_flag": 0,
        "major_interchange_flag": 0,
        "area_type": "Commercial",
        "cumulative_distance": 0.0,
        "remaining_distance": 10.0,
        "number_of_stops": 20,
        "remaining_stops": 19,
        "route_length_km": 15.5,
        "scheduled_trip_duration": 45,
        "trip_start_time": 540,
        "trip_end_time": 585,
        "hour": 9,
        "minute": 0,
        "time_slot": "Morning",
        "day_of_week": "Monday",
        "weekday_weekend": "Weekday",
        "month": 1,
        "holiday_flag": 0,
        "peak_hour_flag": 1,
        "weather_condition": "Clear",
        "temperature": 28,
        "rainfall_flag": 0,
        "congestion_index": 1.2,
        "traffic_level": "Medium",
        "average_speed": 30,
        "traffic_delay": 2,
        "weather_delay": 0,
        "boarding_delay": 1,
        "total_delay": 3,
        "headway_minutes": 15,
        "service_frequency_category": "Normal",
        "historical_route_average": 35.0,
        "historical_stop_average": 30.0,
        "historical_hour_average": 40.0,
        "historical_peak_average": 50.0,
        "historical_weekend_average": 25.0,
        "route_popularity_score": 0.7,
        "vehicle_capacity": 60,
        "boarding_count": 5,
        "alighting_count": 2,
        "onboard_passengers": 30,
        "occupancy_ratio": 0.5,
        "load_factor": 0.5,
        "demand_class": "Medium",
    }
    
    result = demand_prediction_service.predict(features)
    
    print(f"✓ Predicted passengers: {result.get('predicted_passengers')}")
    print(f"✓ Demand score: {result.get('demand_score')}")
    print(f"✓ Confidence: {result.get('confidence')}")
    print(f"✓ Model source: {result.get('model_source')}")
    print(f"✓ Model version: {result.get('model_version')}")
    print(f"✓ Inference time: {result.get('inference_time_ms')} ms")
    
    return True

def test_model_info():
    """Test model info retrieval."""
    print("\n" + "=" * 60)
    print("TEST 4: Model Info")
    print("=" * 60)
    
    info = model_loader.get_model_info()
    
    print(f"Model loaded: {info.get('model_loaded')}")
    print(f"Algorithm: {info.get('algorithm')}")
    print(f"Feature count: {info.get('feature_count')}")
    print(f"Categorical features: {info.get('categorical_feature_count')}")
    print(f"Training metrics: {info.get('training_metrics')}")
    
    return True

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("CatBoost Integration Test Suite")
    print("=" * 60 + "\n")
    
    results = []
    
    # Run tests
    results.append(("Model Loading", test_model_loading()))
    results.append(("Prediction", test_prediction()))
    results.append(("Demand Service", test_demand_service()))
    results.append(("Model Info", test_model_info()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    exit(main())
