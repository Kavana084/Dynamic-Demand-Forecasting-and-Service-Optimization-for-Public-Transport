import os
import sys
import pandas as pd
import numpy as np
import hashlib
import datetime
from sqlalchemy.orm import Session
from catboost import CatBoostRegressor

# Setup paths
base_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(base_dir, "backend"))

from app.database.connection import SessionLocal
from app.database import crud
from app.database.models import Route
from app.ml.model_loader import model_loader

def generate_features(route_id, current_hour=8, weather_condition="Clear", traffic_state="Medium"):
    # Replicate api_routes.py logic exactly
    current_dt = datetime.datetime.now()
    
    route_hash_base = int(hashlib.md5(str(route_id).encode()).hexdigest(), 16)
    base_demand = 20.0 + (route_hash_base % 100)
    
    is_peak = 1 if current_hour in [7,8,9,17,18,19] else 0
    time_mult = 1.8 if is_peak else 0.7 if current_hour in [22,23,0,1,2,3,4,5] else 1.0
    
    weather_mult = 0.8 if weather_condition.lower() in ["rain", "rainy", "storm"] else 1.0
    traffic_mult = 1.3 if traffic_state == "Heavy" else 1.15 if traffic_state == "High" else 1.0
    
    adjusted_demand = base_demand * time_mult * weather_mult * traffic_mult
    
    historical_route_average = base_demand
    historical_hour_average = adjusted_demand
    historical_stop_average = base_demand * 0.8
    historical_peak_average = base_demand * 1.8
    historical_weekend_average = base_demand * 0.6
    
    boarding_count = max(1, int(adjusted_demand * 0.55))
    alighting_count = max(1, int(adjusted_demand * 0.45))
    onboard_passengers = boarding_count + alighting_count
    
    total_distance_km = 15.0 # default dummy distance
    route_distance_km = total_distance_km
    
    traffic_factor = 1.0 if traffic_state == "Medium" else 1.5 if traffic_state == "High" else 0.8
    traffic_delay = int(route_distance_km * traffic_factor)
    weather_delay = 5 if weather_condition.lower() in ["rain", "rainy", "storm"] else 0
    total_delay = traffic_delay + weather_delay
    
    bus_cap = 60
    occupancy_ratio = min(1.0, onboard_passengers / bus_cap)
    load_factor = occupancy_ratio
    demand_class = "High" if load_factor > 0.8 else "Medium" if load_factor > 0.4 else "Low"
    
    features = {
        "service_date": int(current_dt.strftime("%Y%m%d")),
        "route_id": str(route_id),
        "route_short_name": str(route_id)[:10],
        "route_type": 3,
        "service_id": "default",
        "trip_id": f"trip_{route_id}_{current_hour}",
        "shape_id": f"shape_{route_id}",
        "direction_id": 0,
        "stop_id": "STOP_A",
        "stop_name": "Unknown",
        "stop_sequence": 1,
        "stop_lat": 0.0,
        "stop_lon": 0.0,
        "terminal_stop_flag": 0,
        "major_interchange_flag": 1,
        "area_type": "Mixed",
        "cumulative_distance": 0.0,
        "remaining_distance": total_distance_km,
        "number_of_stops": 20,
        "remaining_stops": 20,
        "route_length_km": total_distance_km,
        "scheduled_trip_duration": int((total_distance_km / 30.0) * 60),
        "trip_start_time": current_hour * 60,
        "trip_end_time": (current_hour + 1) * 60,
        "hour": current_hour,
        "minute": current_dt.minute,
        "time_slot": "Morning" if current_hour < 12 else "Afternoon" if current_hour < 17 else "Evening",
        "day_of_week": current_dt.strftime("%A"),
        "weekday_weekend": "Weekday" if current_dt.weekday() < 5 else "Weekend",
        "month": current_dt.month,
        "holiday_flag": 0,
        "peak_hour_flag": is_peak,
        "weather_condition": weather_condition,
        "temperature": 28.0,
        "rainfall_flag": 1 if weather_condition.lower() in ["rain", "rainy", "storm"] else 0,
        "congestion_index": 0.5 if traffic_state == "Medium" else 0.8 if traffic_state == "High" else 0.3,
        "traffic_level": traffic_state,
        "average_speed": 30.0,
        "traffic_delay": traffic_delay,
        "weather_delay": weather_delay,
        "boarding_delay": 0,
        "total_delay": total_delay,
        "headway_minutes": 15,
        "service_frequency_category": "Normal",
        "historical_route_average": historical_route_average,
        "historical_stop_average": historical_stop_average,
        "historical_hour_average": historical_hour_average,
        "historical_peak_average": historical_peak_average,
        "historical_weekend_average": historical_weekend_average,
        "route_popularity_score": 0.5,
        "vehicle_capacity": bus_cap,
        "boarding_count": boarding_count,
        "alighting_count": alighting_count,
        "onboard_passengers": onboard_passengers,
        "occupancy_ratio": occupancy_ratio,
        "load_factor": load_factor,
        "demand_class": demand_class,
    }
    return features

def main():
    print("="*60)
    print("FEATURE DISTRIBUTION AUDIT")
    print("="*60)

    # 1. Select 20 random routes
    db = SessionLocal()
    routes = db.query(Route).limit(100).all()
    db.close()
    
    if len(routes) == 0:
        route_ids = [f"R{i:03d}" for i in range(1, 101)]
    else:
        route_ids = [r.route_id for r in routes]
    
    np.random.seed(42)
    sample_routes = np.random.choice(route_ids, 20, replace=False)
    
    generated_features = []
    keys_to_print = ["historical_route_average", "historical_hour_average", "boarding_count", "alighting_count", "onboard_passengers", "route_length_km", "peak_hour_flag", "weather_condition", "traffic_level"]
    
    for rid in sample_routes:
        fv = generate_features(rid, 8, "Clear", "Medium")
        generated_features.append(fv)
        
    df_gen = pd.DataFrame(generated_features)
    
    print("\n1. Sample Generated Features (Top 5 of 20):")
    print(df_gen[keys_to_print].head(5).to_string())
    
    print("\n2. Generated Statistics (n=20):")
    stats = df_gen[keys_to_print].describe().T[['min', 'max', 'mean', 'std']]
    print(stats.to_string())
    
    print("\n3. Comparing against Training Dataset:")
    train_path = os.path.join(base_dir, "outputs", "processed_dataset.csv")
    if os.path.exists(train_path):
        df_train = pd.read_csv(train_path)
        print(f"Columns in processed_dataset.csv: {df_train.columns.tolist()}")
        available_cols = [c for c in keys_to_print if c in df_train.columns]
        if available_cols:
            train_stats = df_train[available_cols].describe().T[['min', 'max', 'mean', 'std']]
            print("Training Statistics (processed_dataset.csv):")
            print(train_stats.to_string())
        else:
            print("None of the generated features are present in processed_dataset.csv!")
        
        # Why no prediction exceeds 60? Check demand target max
        if 'demand' in df_train.columns:
            print(f"\nTraining Target ('demand') Max: {df_train['demand'].max()}")
        elif 'passenger_count' in df_train.columns:
            print(f"\nTraining Target ('passenger_count') Max: {df_train['passenger_count'].max()}")
    else:
        print("processed_dataset.csv not found!")

    # 4. Find 5 high demand routes (those with highest base_demand)
    route_demands = []
    for rid in route_ids:
        fv = generate_features(rid, 8, "Clear", "Medium")
        route_demands.append((rid, fv["historical_route_average"]))
    
    route_demands.sort(key=lambda x: x[1], reverse=True)
    high_demand_routes = [x[0] for x in route_demands[:5]]
    
    print(f"\n4. Selected 5 High-Demand Routes:")
    for rid, bd in route_demands[:5]:
        print(f"  Route {rid}: base_demand = {bd}")
        
    # 5. Run CatBoost predictions
    print("\n5. CatBoost Predictions on High-Demand Routes:")
    import json
    model_path = os.path.join(base_dir, "outputs", "models", "catboost_demand_model.cbm")
    config_path = os.path.join(base_dir, "outputs", "model_config.json")
    model = CatBoostRegressor()
    model.load_model(model_path)
    
    with open(config_path, "r") as f:
        config = json.load(f)
    expected_feats = config["feature_names"]
    cat_feats = config.get("categorical_features", [])
    
    for rid in high_demand_routes:
        fv = generate_features(rid, 18, "Clear", "Medium") # peak hour
        df_pred = pd.DataFrame([{k: fv.get(k, 0) for k in expected_feats}])
        for cat in cat_feats:
            if cat in df_pred.columns:
                df_pred[cat] = df_pred[cat].astype(str)
        
        raw_pred = model.predict(df_pred)[0]
        demand = max(0, int(round(raw_pred)))
        buses = max(1, int(np.ceil(demand / 60)))
        print(f"  Route {rid} | Onboard (Generated): {fv['onboard_passengers']} | Raw Pred: {raw_pred:.2f} | Rounded: {demand} | Buses: {buses}")

if __name__ == "__main__":
    main()
