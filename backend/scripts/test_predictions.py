import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import SessionLocal
from sqlalchemy import text
from app.services.demand_prediction_service import demand_prediction_service
from app.services.fleet_optimization_service import compute_fleet_plan

def test_routes():
    db = SessionLocal()
    try:
        # Get 5 real route IDs from the database
        result = db.execute(text("SELECT route_id FROM routes LIMIT 5"))
        route_ids = [row[0] for row in result]
        
        test_cases = [
            {
                "desc": "Short local route",
                "features": {
                    "route_id": route_ids[0],
                    "route_length_km": 5.0,
                    "hour": 14,
                    "peak_hour_flag": 0,
                    "vehicle_capacity": 40,
                    "traffic_level": "Low",
                }
            },
            {
                "desc": "Medium route",
                "features": {
                    "route_id": route_ids[1],
                    "route_length_km": 15.0,
                    "hour": 11,
                    "peak_hour_flag": 0,
                    "vehicle_capacity": 60,
                    "traffic_level": "Medium",
                }
            },
            {
                "desc": "Long route",
                "features": {
                    "route_id": route_ids[2],
                    "route_length_km": 35.0,
                    "hour": 15,
                    "peak_hour_flag": 0,
                    "vehicle_capacity": 60,
                    "traffic_level": "Medium",
                }
            },
            {
                "desc": "Hub-to-hub route",
                "features": {
                    "route_id": route_ids[3],
                    "route_length_km": 20.0,
                    "hour": 12,
                    "peak_hour_flag": 0,
                    "vehicle_capacity": 80,
                    "traffic_level": "High",
                }
            },
            {
                "desc": "Peak-demand route",
                "features": {
                    "route_id": route_ids[4],
                    "route_length_km": 18.0,
                    "hour": 9,
                    "peak_hour_flag": 1,
                    "vehicle_capacity": 60,
                    "traffic_level": "High",
                }
            }
        ]
        
        print("ROUTE_ID\t| DESC\t| DEMAND\t| BUSES\t| UTILIZATION")
        print("-" * 75)
        for case in test_cases:
            feat = case["features"]
            res = demand_prediction_service.predict_legacy(
                route_id=feat["route_id"],
                passenger_count=50,
                occupancy_percent=60.0,
                weather="Clear",
                traffic=feat["traffic_level"],
                hour_of_day=feat["hour"],
                day_of_week=1,
                peak_status="normal" if feat["peak_hour_flag"] == 0 else "morning_peak"
            )
            pred_demand = res.get("route_predicted_passengers", 0)
            
            fleet_rec = compute_fleet_plan(
                route_data={
                    "route_id": feat["route_id"],
                    "bus_capacity": feat["vehicle_capacity"],
                    "current_buses": 2,
                    "occupancy_percent": 50,
                    "headway_minutes": 15,
                    "total_distance_km": feat["route_length_km"],
                },
                demand_data={
                    "route_predicted_passengers": pred_demand,
                    "demand_score": res.get("demand_score", 50),
                    "confidence": res.get("confidence", 0.9),
                }
            )
            buses = fleet_rec.get("buses_required", 1)
            util = fleet_rec.get("utilization_score", 0) * 100
            print(f"{feat['route_id']:12}\t| {case['desc'][:16]:16}\t| {pred_demand}\t\t| {buses}\t| {util:.1f}%")
            
    finally:
        db.close()

if __name__ == "__main__":
    test_routes()
