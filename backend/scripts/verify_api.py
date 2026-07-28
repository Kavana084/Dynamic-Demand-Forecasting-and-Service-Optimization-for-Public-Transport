from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_plan_trip():
    payload = {
        "source_id": "stop_1",
        "destination_id": "stop_20",
        "time_of_day": "Morning",
        "preferences": {
            "optimize_for": "time"
        }
    }
    response = client.post("/api/plan_trip", json=payload)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code != 200:
        print(f"Error Response: {response.text}")
        return False
        
    data = response.json()
    
    routes = data.get("recommended_routes", [])
    if not routes:
        print("No routes returned!")
        return False
        
    route = routes[0]
    metrics = route.get("demand_metrics", {})
    
    print("\nDemand Metrics JSON:")
    import json
    print(json.dumps(metrics, indent=2))
    
    # Assert old key is gone and new keys exist
    if "predicted_passengers" in metrics:
        print("FAIL: 'predicted_passengers' is still in the response schema!")
        return False
        
    if "route_predicted_passengers" not in metrics:
        print("FAIL: 'route_predicted_passengers' missing from response schema!")
        return False
        
    if "journey_predicted_passengers" not in metrics:
        print("FAIL: 'journey_predicted_passengers' missing from response schema!")
        return False
        
    print("\nSUCCESS! DemandMetrics schema is fully updated in the API response.")
    return True

if __name__ == "__main__":
    test_plan_trip()
