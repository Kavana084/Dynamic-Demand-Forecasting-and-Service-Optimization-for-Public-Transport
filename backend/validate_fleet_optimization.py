"""
Fleet Optimization Validation Script
Audits the complete calculation chain from predicted_demand to additional_buses.
"""
import requests
import json
import math
from datetime import datetime
from collections import defaultdict
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://localhost:8000"

def get_sample_stops(count=50):
    """Get sample stops from the database for testing."""
    try:
        from app.database.connection import engine
        from sqlalchemy import text
        conn = engine.connect()
        result = conn.execute(text(f"SELECT stop_id, stop_name FROM gtfs_stops LIMIT {count}"))
        stops = [{"stop_id": row[0], "stop_name": row[1]} for row in result]
        conn.close()
        return stops
    except Exception as e:
        print(f"Error fetching stops: {e}")
        return []

def generate_od_pairs(stops, count=5):
    """Generate origin-destination pairs for testing."""
    pairs = []
    for i in range(min(count, len(stops))):
        for j in range(i + 1, min(i + 3, len(stops))):
            pairs.append((stops[i]["stop_id"], stops[j]["stop_id"]))
            if len(pairs) >= count:
                break
        if len(pairs) >= count:
            break
    return pairs

def test_route_fleet_calculation(source_id, dest_id, bus_capacity=60):
    """Test fleet calculation for a single route."""
    try:
        response = requests.post(
            f"{BASE_URL}/api/plan_trip",
            json={
                "source_id": source_id,
                "destination_id": dest_id,
                "bus_capacity": bus_capacity
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract fleet-related fields
            predicted_demand = data.get("predicted_demand")
            current_fleet = data.get("current_fleet", 1)
            recommended_fleet = data.get("recommended_fleet", 1)
            required_buses = data.get("required_buses", 1)
            additional_buses = data.get("additional_buses", 0)
            fleet_utilization = data.get("fleet_utilization", 0)
            
            # Verify calculations
            calculated_required = math.ceil(predicted_demand / bus_capacity) if predicted_demand else 1
            calculated_additional = max(0, calculated_required - current_fleet)
            
            return {
                "success": True,
                "source_id": source_id,
                "destination_id": dest_id,
                "route_id": data.get("route_id"),
                "predicted_demand": predicted_demand,
                "current_fleet": current_fleet,
                "recommended_fleet": recommended_fleet,
                "required_buses": required_buses,
                "additional_buses": additional_buses,
                "fleet_utilization": fleet_utilization,
                "bus_capacity": bus_capacity,
                "calculated_required": calculated_required,
                "calculated_additional": calculated_additional,
                "required_matches": required_buses == calculated_required,
                "additional_matches": additional_buses == calculated_additional,
                "utilization_calc": (predicted_demand / (required_buses * bus_capacity) * 100) if required_buses and bus_capacity else 0
            }
        else:
            return {
                "success": False,
                "source_id": source_id,
                "destination_id": dest_id,
                "error": response.text
            }
    except Exception as e:
        return {
            "success": False,
            "source_id": source_id,
            "destination_id": dest_id,
            "error": str(e)
        }

def generate_fleet_table(results):
    """Generate a table showing fleet calculation chain."""
    table = []
    for r in results:
        if r["success"]:
            table.append({
                "Route": r["route_id"],
                "Demand": r["predicted_demand"],
                "Current Fleet": r["current_fleet"],
                "Required Fleet": r["required_buses"],
                "Additional Buses": r["additional_buses"],
                "Fleet Utilization": f"{r['fleet_utilization']:.1f}%"
            })
    return table

def verify_calculation_chain(results):
    """Verify the calculation chain correctness."""
    successful_results = [r for r in results if r["success"]]
    required_matches = [r for r in successful_results if r["required_matches"]]
    additional_matches = [r for r in successful_results if r["additional_matches"]]
    
    total_successful = len(successful_results)
    
    return {
        "total_tests": total_successful,
        "required_buses_correct": len(required_matches),
        "additional_buses_correct": len(additional_matches),
        "required_accuracy": len(required_matches) / total_successful * 100 if total_successful > 0 else 0,
        "additional_accuracy": len(additional_matches) / total_successful * 100 if total_successful > 0 else 0
    }

def categorize_bus_requirements(results):
    """Categorize routes by bus requirements."""
    categories = {
        "1 bus": 0,
        "2 buses": 0,
        "3 buses": 0,
        "4+ buses": 0
    }
    
    route_details = {
        "1 bus": [],
        "2 buses": [],
        "3 buses": [],
        "4+ buses": []
    }
    
    for r in results:
        if r["success"]:
            required = r["required_buses"]
            if required == 1:
                categories["1 bus"] += 1
                route_details["1 bus"].append(r["route_id"])
            elif required == 2:
                categories["2 buses"] += 1
                route_details["2 buses"].append(r["route_id"])
            elif required == 3:
                categories["3 buses"] += 1
                route_details["3 buses"].append(r["route_id"])
            elif required >= 4:
                categories["4+ buses"] += 1
                route_details["4+ buses"].append(r["route_id"])
    
    return categories, route_details

def check_hardcoded_values(results):
    """Check for hardcoded fleet values."""
    suspicious = []
    
    for r in results:
        if r["success"]:
            # Check if current_fleet is always 1 (potential hardcoded default)
            if r["current_fleet"] == 1:
                suspicious.append({
                    "route_id": r["route_id"],
                    "issue": "current_fleet always 1",
                    "value": r["current_fleet"]
                })
    
    return suspicious

def main():
    print("=" * 80)
    print("FLEET OPTIMIZATION VALIDATION")
    print("=" * 80)
    print(f"Started at: {datetime.now()}")
    print()
    
    # Get sample stops
    print("Fetching sample stops...")
    stops = get_sample_stops(50)
    print(f"Found {len(stops)} stops")
    print()
    
    # Generate OD pairs
    print("Generating origin-destination pairs...")
    od_pairs = generate_od_pairs(stops, 30)
    print(f"Generated {len(od_pairs)} OD pairs")
    print()
    
    # Test fleet calculations
    print("Testing fleet calculations...")
    results = []
    for i, (source_id, dest_id) in enumerate(od_pairs, 1):
        print(f"  Testing pair {i}/{len(od_pairs)}: {source_id} -> {dest_id}")
        result = test_route_fleet_calculation(source_id, dest_id)
        results.append(result)
    
    print()
    print(f"Completed {len(results)} fleet calculations")
    print()
    
    # Generate fleet table
    print("=" * 80)
    print("FLEET CALCULATION TABLE")
    print("=" * 80)
    table = generate_fleet_table(results)
    if table:
        print(f"{'Route':<15} {'Demand':<10} {'Current':<10} {'Required':<10} {'Additional':<12} {'Utilization':<15}")
        print("-" * 80)
        for row in table:
            print(f"{row['Route']:<15} {row['Demand']:<10} {row['Current Fleet']:<10} {row['Required Fleet']:<10} {row['Additional Buses']:<12} {row['Fleet Utilization']:<15}")
    else:
        print("No successful fleet calculations found")
    
    # Verify calculation chain
    print("\n" + "=" * 80)
    print("CALCULATION CHAIN VERIFICATION")
    print("=" * 80)
    verification = verify_calculation_chain(results)
    print(f"Total tests: {verification['total_tests']}")
    print(f"Required buses calculation correct: {verification['required_buses_correct']}/{verification['total_tests']} ({verification['required_accuracy']:.1f}%)")
    print(f"Additional buses calculation correct: {verification['additional_buses_correct']}/{verification['total_tests']} ({verification['additional_accuracy']:.1f}%)")
    
    # Categorize bus requirements
    print("\n" + "=" * 80)
    print("BUS REQUIREMENT CATEGORIES")
    print("=" * 80)
    categories, route_details = categorize_bus_requirements(results)
    for category, count in categories.items():
        print(f"{category}: {count} routes")
        if route_details[category]:
            print(f"  Routes: {route_details[category][:10]}{'...' if len(route_details[category]) > 10 else ''}")
    
    # Check for hardcoded values
    print("\n" + "=" * 80)
    print("HARDCODED VALUE CHECK")
    print("=" * 80)
    hardcoded = check_hardcoded_values(results)
    if hardcoded:
        print(f"Found {len(hardcoded)} potential hardcoded values:")
        for item in hardcoded[:10]:
            print(f"  Route {item['route_id']}: {item['issue']} = {item['value']}")
    else:
        print("No hardcoded values detected")
    
    # Save detailed results
    output_file = "outputs/fleet_validation_results.json"
    os.makedirs("outputs", exist_ok=True)
    
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "fleet_table": table,
            "calculation_verification": verification,
            "bus_requirements": categories,
            "route_details": route_details,
            "hardcoded_check": hardcoded,
            "detailed_results": results
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: {output_file}")
    print(f"\nCompleted at: {datetime.now()}")

if __name__ == "__main__":
    main()
