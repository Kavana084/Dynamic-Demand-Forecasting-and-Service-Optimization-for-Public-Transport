import sys
sys.path.insert(0, "f:/transit-ai-system/backend")

import math
from app.services.demand_prediction_service import demand_prediction_service
from app.services.fleet_optimization_service import compute_demand_metrics

routes_to_test = [
    {
        "name": "Route A (Full Route - Correct)",
        "source_id": "20921",
        "destination_id": "21817",
        "route_id": "1000",
        "journey_stops": 20,
        "total_route_stops": 20,
    },
    {
        "name": "Route B (Partial Route - Incorrect)",
        "source_id": "20921",
        "destination_id": "21138",
        "route_id": "1000",
        "journey_stops": 5,
        "total_route_stops": 20,
    }
]

print("="*80)
print("ROUTE-SPECIFIC DIAGNOSTIC AUDIT")
print("="*80)

for r in routes_to_test:
    segment_ratio = max(0.1, min(1.0, r["journey_stops"] / r["total_route_stops"]))
    
    # Mock feature dict as it would be passed to predict
    features = {
        "passenger_count": 75,
        "occupancy_ratio": 0.5,
        "weather_condition": "Clear",
        "traffic_level": "Medium",
        "hour": 8,
        "peak_hour_flag": 1
    }
    
    # 4 & 5. Call prediction and verify scaling
    pred = demand_prediction_service.predict(features, segment_ratio=segment_ratio)
    
    # 6. Fleet allocation is done inside compute_demand_metrics
    dm = compute_demand_metrics(
        route_predicted_passengers=pred["route_predicted_passengers"],
        journey_predicted_passengers=pred["journey_predicted_passengers"],
        available_buses=20,
        bus_capacity=60
    )
    
    print(f"\n{r['name']}")
    print("-" * 40)
    print(f"- source stop: {r['source_id']}")
    print(f"- destination stop: {r['destination_id']}")
    print(f"- selected route_id: {r['route_id']}")
    print(f"- prediction source: {pred['model_source']}")
    
    # Raw prediction is essentially the journey prediction for CatBoost
    raw_pred = pred['journey_predicted_passengers'] if pred['model_source'] == 'catboost' else pred['route_predicted_passengers']
    print(f"- raw prediction: {raw_pred}")
    print(f"- journey_predicted_passengers: {pred['journey_predicted_passengers']}")
    print(f"- route_predicted_passengers: {pred['route_predicted_passengers']}")
    print(f"- journey_stops: {r['journey_stops']}")
    print(f"- total_route_stops: {r['total_route_stops']}")
    print(f"- segment_ratio: {segment_ratio:.4f}")
    
    # Show fleet math
    print(f"- required_buses = ceil({pred['route_predicted_passengers']} / 60) = {dm['required_buses']}")
    print(f"- allocated_buses: {dm['allocated_buses']}")
    print(f"- available_buses: {dm['available_buses']}")
    print(f"- bus_capacity: 60")
    
    # Show occupancy math
    cap = max(1, dm['allocated_buses'] * 60)
    print(f"- occupancy_percentage = {pred['journey_predicted_passengers']} / {cap} = {dm['operational_occupancy_pct']}%")
    print(f"- crowd_level: {dm['crowd_level']}")
    print(f"- demand_level: {dm['demand_level']}")
