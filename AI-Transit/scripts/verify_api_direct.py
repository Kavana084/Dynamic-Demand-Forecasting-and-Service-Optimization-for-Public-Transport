import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.api.navigation import plan_trip
from app.schemas.routing import TripPlanRequest
from app.database.connection import SessionLocal

def test_plan_trip():
    req = TripPlanRequest(source_id='stop_1', destination_id='stop_20', time_of_day='Morning', preferences={'optimize_for': 'time'})
    db = SessionLocal()
    try:
        res = plan_trip(req, db)
        # res is a TripPlanResponse Pydantic model
        route = res.recommended_routes[0]
        metrics = route.demand_metrics.dict()
        
        print("\nDemand Metrics Dictionary:")
        import json
        print(json.dumps(metrics, indent=2))
        
        if "predicted_passengers" in metrics:
            print("FAIL: 'predicted_passengers' is still in the response schema!")
            sys.exit(1)
            
        if "route_predicted_passengers" not in metrics:
            print("FAIL: 'route_predicted_passengers' missing from response schema!")
            sys.exit(1)
            
        if "journey_predicted_passengers" not in metrics:
            print("FAIL: 'journey_predicted_passengers' missing from response schema!")
            sys.exit(1)
            
        print("\nSUCCESS! DemandMetrics schema is fully updated.")
    finally:
        db.close()

if __name__ == "__main__":
    test_plan_trip()
