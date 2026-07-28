import os
import sys
import asyncio
import json

base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.append(base_dir)
sys.path.append(os.path.join(base_dir, 'backend'))

from fastapi import Request
from backend.app.database.connection import SessionLocal
from backend.app.api_routes import plan_trip, TripPlanRequestV2

class DummyApp:
    def __init__(self):
        self.state = type('State', (), {})()
        self.state.prediction_service = None

class DummyRequest:
    def __init__(self):
        self.app = DummyApp()
        self.headers = {}

def main():
    db = SessionLocal()
    
    # Initialize the prediction service and model loader
    from backend.app.ml.model_loader import model_loader
    from backend.app.ml.predictor import predictor
    from backend.app.services.demand_prediction_service import demand_prediction_service
    
    model_loader.load_model()
    
    req = DummyRequest()
    req.app.state.prediction_service = demand_prediction_service

    routes_to_test = [
        ("1001", "1005"),
        ("1002", "1010"),
        ("1003", "1015"),
        ("1004", "1020"),
        ("1005", "1025"),
    ]
    
    for src, dst in routes_to_test:
        print(f"\n=======================")
        print(f"Testing route {src} -> {dst}")
        try:
            payload = TripPlanRequestV2(source_id=src, destination_id=dst, bus_capacity=60)
            res = plan_trip(payload, req, db)
            
            print(f"Route ID: {res.get('route_id')}")
            print(f"Predicted Demand: {res.get('predicted_demand')}")
            print(f"Forecast Demand: {res.get('forecast_demand')}")
            rec_fleet = res.get('recommended_fleet')
            print(f"Recommended Fleet: {rec_fleet}")
            print(f"Fleet Utilization: {res.get('fleet_utilization')}")
            
        except Exception as e:
            print(f"Error for {src}->{dst}: {e}")

if __name__ == '__main__':
    main()
