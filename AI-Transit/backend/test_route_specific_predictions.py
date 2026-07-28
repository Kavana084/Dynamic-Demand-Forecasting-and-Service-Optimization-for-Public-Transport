"""
Test script to verify route-specific predictions
Calls /api/plan_trip with two different routes and compares the outputs
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_route_predictions():
    """Test two different routes and compare predictions"""
    
    # Route 1: 12th Block Nagarabhavi -> Ambedkar Institute of Technology
    route1 = {
        "source_id": "21629",
        "destination_id": "21454",
        "bus_capacity": 60
    }
    
    # Route 2: Different destination for comparison
    # Using a different stop if available
    route2 = {
        "source_id": "21629",
        "destination_id": "21455",  # Different destination
        "bus_capacity": 60
    }
    
    print("=" * 80)
    print("TESTING ROUTE-SPECIFIC PREDICTIONS")
    print("=" * 80)
    
    # Test Route 1
    print("\n--- ROUTE 1: 12th Block Nagarabhavi -> Ambedkar Institute of Technology ---")
    try:
        response1 = requests.post(f"{BASE_URL}/api/plan_trip", json=route1)
        response1.raise_for_status()
        data1 = response1.json()
        
        print(f"Route ID: {data1.get('route_id')}")
        print(f"Predicted Demand: {data1.get('predicted_demand')}")
        print(f"Forecast Demand: {data1.get('forecast_demand')}")
        print(f"Current Fleet: {data1.get('current_fleet')}")
        print(f"Recommended Fleet: {data1.get('recommended_fleet')}")
        print(f"Fleet Utilization: {data1.get('fleet_utilization')}")
        print(f"AI Recommendation: {data1.get('ai_recommendation')}")
        print(f"Selection Reason: {data1.get('selection_reason')}")
        
    except Exception as e:
        print(f"Error testing route 1: {e}")
        data1 = None
    
    # Test Route 2
    print("\n--- ROUTE 2: 12th Block Nagarabhavi -> Different Destination ---")
    try:
        response2 = requests.post(f"{BASE_URL}/api/plan_trip", json=route2)
        response2.raise_for_status()
        data2 = response2.json()
        
        print(f"Route ID: {data2.get('route_id')}")
        print(f"Predicted Demand: {data2.get('predicted_demand')}")
        print(f"Forecast Demand: {data2.get('forecast_demand')}")
        print(f"Current Fleet: {data2.get('current_fleet')}")
        print(f"Recommended Fleet: {data2.get('recommended_fleet')}")
        print(f"Fleet Utilization: {data2.get('fleet_utilization')}")
        print(f"AI Recommendation: {data2.get('ai_recommendation')}")
        print(f"Selection Reason: {data2.get('selection_reason')}")
        
    except Exception as e:
        print(f"Error testing route 2: {e}")
        data2 = None
    
    # Compare results
    print("\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)
    
    if data1 and data2:
        print(f"\nRoute IDs are different: {data1.get('route_id') != data2.get('route_id')}")
        print(f"Predicted Demand same: {data1.get('predicted_demand') == data2.get('predicted_demand')}")
        print(f"Forecast Demand same: {data1.get('forecast_demand') == data2.get('forecast_demand')}")
        print(f"Current Fleet same: {data1.get('current_fleet') == data2.get('current_fleet')}")
        print(f"Recommended Fleet same: {data1.get('recommended_fleet') == data2.get('recommended_fleet')}")
        print(f"Fleet Utilization same: {data1.get('fleet_utilization') == data2.get('fleet_utilization')}")
        print(f"AI Recommendation same: {data1.get('ai_recommendation') == data2.get('ai_recommendation')}")
        
        if data1.get('route_id') == data2.get('route_id'):
            print("\n⚠️  WARNING: Both routes resolved to the same route_id!")
            print("This explains why predictions are identical.")
        else:
            if data1.get('predicted_demand') == data2.get('predicted_demand'):
                print("\n⚠️  WARNING: Different route_ids but same predicted demand!")
                print("This indicates the CatBoost model is not using route_id as a feature.")
            else:
                print("\n✓ Predictions are different for different routes.")

if __name__ == "__main__":
    test_route_predictions()
