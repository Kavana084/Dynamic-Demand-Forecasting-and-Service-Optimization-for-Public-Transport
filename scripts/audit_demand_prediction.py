"""
Passenger Demand Prediction Pipeline Audit
==========================================
Audits the demand prediction pipeline for 5 source-destination pairs.
Logs model input features, raw predictions, final predictions, and verifies model usage.
"""

import sys
import os

# Add backend to path
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
sys.path.insert(0, backend_dir)

from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.database.models import GTFSStop
from app.ml.model_loader import model_loader
from app.ml.predictor import predictor
from app.services.demand_prediction_service import demand_prediction_service
from app.services.routing_service import resolve_route_dynamic
import json

def print_section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def audit_demand_prediction(db: Session, source_id: str, destination_id: str):
    """Audit demand prediction for a single route."""
    print(f"\n--- Testing Route: {source_id} -> {destination_id} ---")
    
    # 1. Verify CatBoost model is loaded
    print("\n1. Model Status:")
    model_loaded = model_loader.is_model_loaded()
    print(f"   CatBoost model loaded: {model_loaded}")
    
    if model_loaded:
        feature_names = model_loader.get_feature_names()
        categorical_features = model_loader.get_categorical_features()
        print(f"   Feature count: {len(feature_names)}")
        print(f"   Categorical features: {len(categorical_features)}")
        print(f"   First 10 features: {feature_names[:10]}")
    
    # 2. Get route info
    print("\n2. Route Resolution:")
    try:
        route_info = resolve_route_dynamic(db, source_id, destination_id, bus_capacity=60)
        route_id = route_info.get("route_id", "unknown")
        print(f"   Route ID: {route_id}")
        print(f"   Path length: {len(route_info.get('path', []))}")
        print(f"   Transfers: {route_info.get('transfer_count', 0)}")
    except Exception as e:
        print(f"   ERROR: {e}")
        return None
    
    # 3. Build feature vector (mimic api_routes.py logic)
    print("\n3. Feature Vector Construction:")
    from datetime import datetime
    current_hour = datetime.now().hour
    current_day = datetime.now().weekday()
    
    # This is a simplified feature set - in production, this would be more complete
    features = {
        "route_id": route_id,
        "route_short_name": route_id,
        "route_type": 3,
        "service_id": "default",
        "trip_id": "default",
        "shape_id": "default",
        "direction_id": 0,
        "stop_id": source_id,
        "stop_name": "Unknown",
        "stop_sequence": 1,
        "stop_lat": 0.0,
        "stop_lon": 0.0,
        "terminal_stop_flag": 0,
        "major_interchange_flag": 0,
        "area_type": "Mixed",
        "cumulative_distance": 0.0,
        "remaining_distance": 0.0,
        "number_of_stops": len(route_info.get('path', [])),
        "remaining_stops": 5,
        "route_length_km": route_info.get('total_distance_km', 10.0),
        "scheduled_trip_duration": 30,
        "trip_start_time": current_hour * 60,
        "trip_end_time": (current_hour + 1) * 60,
        "minute": 0,
        "time_slot": "Morning" if current_hour < 12 else "Evening",
        "hour": current_hour,
        "day_of_week": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][current_day],
        "weekday_weekend": "Weekday" if current_day < 6 else "Weekend",
        "month": 1,
        "holiday_flag": 0,
        "temperature": 28,
        "rainfall_flag": 0,
        "congestion_index": 0.5,
        "average_speed": 30,
        "traffic_delay": 0,
        "weather_delay": 0,
        "boarding_delay": 0,
        "total_delay": 0,
        "headway_minutes": 15,
        "service_frequency_category": "Normal",
        "historical_route_average": 25.0,
        "historical_stop_average": 25.0,
        "historical_hour_average": 25.0,
        "historical_peak_average": 35.0,
        "historical_weekend_average": 20.0,
        "route_popularity_score": 0.5,
        "vehicle_capacity": 60,
        "passenger_count": 50,
        "boarding_count": 0,
        "alighting_count": 0,
        "onboard_passengers": 50,
        "load_factor": 0.83,
        "demand_class": "Medium",
        "weather_condition": "Clear",
        "traffic_level": "Medium",
        "peak_hour_flag": 1 if (7 <= current_hour <= 9 or 17 <= current_hour <= 19) else 0,
    }
    
    print(f"   Total features: {len(features)}")
    print(f"   Sample features:")
    for key in list(features.keys())[:10]:
        print(f"     {key}: {features[key]}")
    
    # 4. Get prediction using demand_prediction_service
    print("\n4. Demand Prediction:")
    try:
        result = demand_prediction_service.predict(features)
        
        print(f"   Model source: {result.get('model_source')}")
        print(f"   Model version: {result.get('model_version')}")
        print(f"   Predicted passengers: {result.get('predicted_passengers')}")
        print(f"   Demand score: {result.get('demand_score')}")
        print(f"   Confidence: {result.get('confidence')}")
        print(f"   Demand class: {result.get('demand_class')}")
        print(f"   Inference time: {result.get('inference_time_ms')} ms")
        
        # Check if fallback was used
        if result.get('model_source') == 'heuristic':
            print("   WARNING: Heuristic fallback used (not CatBoost)")
        elif result.get('model_source') == 'catboost':
            print("   ✓ CatBoost model used")
        else:
            print(f"   WARNING: Unknown model source: {result.get('model_source')}")
        
        return result
        
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("\n" + "=" * 80)
    print("  PASSENGER DEMAND PREDICTION PIPELINE AUDIT")
    print("=" * 80)
    
    db = SessionLocal()
    
    try:
        # 5 test routes
        test_routes = [
            ("22890", "20940"),  # Hub to hub
            ("21630", "22896"),  # Nagarabhavi area
            ("29506", "22950"),  # Hub route
            ("22890", "21172"),  # Major hub to major hub
            ("21629", "21454"),  # Nagarabhavi to Summanahalli
        ]
        
        results = []
        
        for source_id, dest_id in test_routes:
            print_section(f"Route: {source_id} -> {dest_id}")
            result = audit_demand_prediction(db, source_id, dest_id)
            if result:
                results.append({
                    "source": source_id,
                    "destination": dest_id,
                    "result": result
                })
        
        # Summary
        print_section("SUMMARY")
        print(f"\nTotal routes tested: {len(results)}")
        
        catboost_count = sum(1 for r in results if r['result'].get('model_source') == 'catboost')
        heuristic_count = sum(1 for r in results if r['result'].get('model_source') == 'heuristic')
        fallback_count = sum(1 for r in results if r['result'].get('model_source') == 'fallback')
        
        print(f"CatBoost predictions: {catboost_count}")
        print(f"Heuristic predictions: {heuristic_count}")
        print(f"Fallback predictions: {fallback_count}")
        
        print("\nDetailed Results:")
        for r in results:
            print(f"\n{r['source']} -> {r['destination']}:")
            print(f"  Model: {r['result'].get('model_source')}")
            print(f"  Predicted: {r['result'].get('predicted_passengers')}")
            print(f"  Confidence: {r['result'].get('confidence')}")
        
        # Verification
        print_section("VERIFICATION")
        if catboost_count == len(results):
            print("✓ PASS: All predictions used CatBoost model")
        else:
            print(f"✗ FAIL: {heuristic_count + fallback_count} predictions used fallback")
        
        if heuristic_count > 0:
            print("⚠ WARNING: Heuristic fallback was used - check model loading")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
