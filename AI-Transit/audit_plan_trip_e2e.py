"""
End-to-end audit script for /api/plan_trip endpoint
Tests 5 route cases and captures detailed logging output
"""

import requests
import json
from datetime import datetime

# Test cases with actual GTFS stop IDs from database
test_cases = [
    {"source_id": "21629", "destination_id": "22890", "name": "Route Nagarabhavi-Jayanagara"},
    {"source_id": "20568", "destination_id": "29393", "name": "Route HSR-Kodichikkanahalli"},
    {"source_id": "22896", "destination_id": "22897", "name": "Route Nayandahalli-Summanahalli"},
    {"source_id": "21630", "destination_id": "24300", "name": "Route Nagarabhavi-HSR"},
    {"source_id": "22891", "destination_id": "35599", "name": "Route HSR-Kodichikkanahalli Alt"},
]

base_url = "http://127.0.0.1:8000"
results = []

print("=" * 80)
print("E2E AUDIT: /api/plan_trip Endpoint")
print("=" * 80)
print(f"Started at: {datetime.now().isoformat()}")
print()

for i, test_case in enumerate(test_cases, 1):
    print(f"\nTest Case {i}: {test_case['name']}")
    print(f"Source: {test_case['source_id']} -> Destination: {test_case['destination_id']}")
    
    try:
        response = requests.post(
            f"{base_url}/api/plan_trip",
            json={
                "source_id": test_case["source_id"],
                "destination_id": test_case["destination_id"],
                "bus_capacity": 60
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Success - Route ID: {data.get('route_id')}")
            print(f"  Distance: {data.get('distance_km')} km")
            print(f"  Transfers: {len(data.get('transfers', []))}")
            print(f"  Predicted Demand: {data.get('predicted_demand')}")
            print(f"  Forecast Demand: {data.get('forecast_demand')}")
            print(f"  Recommended Fleet: {data.get('recommended_fleet')}")
            print(f"  Fleet Utilization: {data.get('fleet_utilization')}%")
            
            results.append({
                "test_case": test_case["name"],
                "source_id": test_case["source_id"],
                "destination_id": test_case["destination_id"],
                "route_id": data.get('route_id'),
                "distance_km": data.get('distance_km'),
                "transfers": len(data.get('transfers', [])),
                "predicted_demand": data.get('predicted_demand'),
                "forecast_demand": data.get('forecast_demand'),
                "recommended_fleet": data.get('recommended_fleet'),
                "fleet_utilization": data.get('fleet_utilization'),
                "status": "success",
                "error": None
            })
        else:
            print(f"✗ Failed - Status: {response.status_code}")
            print(f"  Error: {response.text}")
            results.append({
                "test_case": test_case["name"],
                "source_id": test_case["source_id"],
                "destination_id": test_case["destination_id"],
                "route_id": None,
                "distance_km": None,
                "transfers": None,
                "predicted_demand": None,
                "forecast_demand": None,
                "recommended_fleet": None,
                "fleet_utilization": None,
                "status": "failed",
                "error": response.text
            })
    except Exception as e:
        print(f"✗ Exception: {str(e)}")
        results.append({
            "test_case": test_case["name"],
            "source_id": test_case["source_id"],
            "destination_id": test_case["destination_id"],
            "route_id": None,
            "distance_km": None,
            "transfers": None,
            "predicted_demand": None,
            "forecast_demand": None,
            "recommended_fleet": None,
            "fleet_utilization": None,
            "status": "error",
            "error": str(e)
        })

# Save results to JSON
output_file = "f:\\transit-ai-system\\outputs\\plan_trip_e2e_audit.json"
with open(output_file, 'w') as f:
    json.dump({
        "audit_timestamp": datetime.now().isoformat(),
        "endpoint": "/api/plan_trip",
        "test_results": results,
        "summary": {
            "total_tests": len(test_cases),
            "successful": sum(1 for r in results if r["status"] == "success"),
            "failed": sum(1 for r in results if r["status"] == "failed"),
            "errors": sum(1 for r in results if r["status"] == "error")
        }
    }, f, indent=2)

print()
print("=" * 80)
print("AUDIT COMPLETE")
print("=" * 80)
print(f"Results saved to: {output_file}")
print(f"Total tests: {len(test_cases)}")
print(f"Successful: {sum(1 for r in results if r['status'] == 'success')}")
print(f"Failed: {sum(1 for r in results if r['status'] == 'failed')}")
print(f"Errors: {sum(1 for r in results if r['status'] == 'error')}")
