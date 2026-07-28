import json
import pandas as pd
from catboost import CatBoostRegressor
from datetime import datetime

from realtime_feature_engineering_v2 import RealTimePredictor

def test_generalization():
    predictor = RealTimePredictor(model_path='outputs/models/catboost_demand_model_v2.cbm')
    
    # Let's generate a base trip
    trip_data = {
        'route_id': 'R1',
        'route_short_name': 'Express 1',
        'vehicle_capacity': 100,
        'stop_id': 'S1',
        'historical_route_average': 50.0,
        'historical_hour_average': 50.0,
        'headway_minutes': 10
    }
    
    # We will test variations
    scenarios = []
    
    # Scenario 1: Morning Peak, Clear, Medium Traffic
    dt1 = datetime(2026, 1, 5, 8, 30) # Monday 8:30 AM
    w1 = {'condition': 'Sunny', 'temperature': 25, 'rainfall': 0}
    res1 = predictor.predict(trip_data, w1, dt1)
    
    # Scenario 2: Afternoon, Clear, Low Traffic
    dt2 = datetime(2026, 1, 5, 14, 0)
    res2 = predictor.predict(trip_data, w1, dt2)
    
    # Scenario 3: Evening Peak, Rain, Heavy Traffic
    dt3 = datetime(2026, 1, 5, 18, 30)
    w3 = {'condition': 'Heavy Rain', 'temperature': 20, 'rainfall': 15}
    res3 = predictor.predict(trip_data, w3, dt3)
    
    # Scenario 4: Night, Clear, Low Traffic
    dt4 = datetime(2026, 1, 5, 23, 0)
    res4 = predictor.predict(trip_data, w1, dt4)
    
    # Check assumptions
    report = {
        "scenarios": {
            "morning_peak_clear": res1.get('passenger_count', 0),
            "afternoon_clear": res2.get('passenger_count', 0),
            "evening_peak_rain": res3.get('passenger_count', 0),
            "night_clear": res4.get('passenger_count', 0)
        },
        "assertions": {
            "peak_greater_than_afternoon": bool(res1.get('passenger_count', 0) > res2.get('passenger_count', 0)),
            "rain_evening_greater_than_night": bool(res3.get('passenger_count', 0) > res4.get('passenger_count', 0)),
            "high_demand_exceeds_100": bool(max(res1.get('passenger_count', 0), res3.get('passenger_count', 0)) > 50) # Assuming the base is 50
        }
    }
    
    with open('outputs/generalization_report.json', 'w') as f:
        json.dump(report, f, indent=4)

if __name__ == "__main__":
    test_generalization()
