"""
Demand Prediction Validation Script
Tests 30+ origin-destination pairs to validate demand prediction consistency.
"""
import requests
import json
import statistics
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

def test_route_prediction(source_id, dest_id, bus_capacity=60):
    """Test a single route prediction."""
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
            return {
                "success": True,
                "source_id": source_id,
                "destination_id": dest_id,
                "route_id": data.get("route_id"),
                "predicted_demand": data.get("predicted_demand"),
                "occupancy_percent": data.get("occupancy_percent"),
                "peak_status": data.get("peak_status"),
                "demand_confidence": data.get("demand_confidence"),
                "weather": data.get("weather"),
                "traffic": data.get("traffic"),
                "fare": data.get("fare"),
                "eta_min": data.get("eta_min"),
                "distance_km": data.get("distance_km"),
                "current_fleet": data.get("current_fleet"),
                "recommended_fleet": data.get("recommended_fleet"),
                "required_buses": data.get("required_buses"),
                "additional_buses": data.get("additional_buses"),
                "fleet_utilization": data.get("fleet_utilization")
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

def calculate_statistics(results):
    """Calculate statistics from prediction results."""
    demands = [r["predicted_demand"] for r in results if r["success"] and r["predicted_demand"] is not None]
    
    if not demands:
        return None
    
    return {
        "count": len(demands),
        "min": min(demands),
        "max": max(demands),
        "average": statistics.mean(demands),
        "median": statistics.median(demands),
        "std_dev": statistics.stdev(demands) if len(demands) > 1 else 0,
        "unique_values": len(set(demands)),
        "demand_values": sorted(demands)
    }

def identify_suspicious_patterns(results):
    """Identify suspicious patterns in demand predictions."""
    demands = [(r["route_id"], r["predicted_demand"]) for r in results if r["success"] and r["predicted_demand"] is not None]
    
    # Count frequency of each demand value
    demand_counts = defaultdict(list)
    for route_id, demand in demands:
        demand_counts[demand].append(route_id)
    
    suspicious = []
    for demand, routes in demand_counts.items():
        if len(routes) > 3:  # More than 3 routes with identical demand
            suspicious.append({
                "demand_value": demand,
                "route_count": len(routes),
                "routes": routes
            })
    
    return suspicious

def verify_peak_hour_effect(results):
    """Verify that peak-hour routes produce higher demand."""
    peak_demands = [r["predicted_demand"] for r in results 
                   if r["success"] and r["peak_status"] and "peak" in r["peak_status"].lower()
                   and r["predicted_demand"] is not None]
    
    off_peak_demands = [r["predicted_demand"] for r in results 
                       if r["success"] and r["peak_status"] and ("off" in r["peak_status"].lower() or "normal" in r["peak_status"].lower())
                       and r["predicted_demand"] is not None]
    
    if not peak_demands or not off_peak_demands:
        return {
            "verified": False,
            "reason": "Insufficient data for peak/off-peak comparison",
            "peak_avg": None,
            "off_peak_avg": None
        }
    
    peak_avg = statistics.mean(peak_demands)
    off_peak_avg = statistics.mean(off_peak_demands)
    
    return {
        "verified": peak_avg > off_peak_avg,
        "peak_avg": peak_avg,
        "off_peak_avg": off_peak_avg,
        "peak_count": len(peak_demands),
        "off_peak_count": len(off_peak_demands),
        "difference": peak_avg - off_peak_avg
    }

def main():
    print("=" * 80)
    print("DEMAND PREDICTION VALIDATION")
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
    
    # Test predictions
    print("Testing route predictions...")
    results = []
    for i, (source_id, dest_id) in enumerate(od_pairs, 1):
        print(f"  Testing pair {i}/{len(od_pairs)}: {source_id} -> {dest_id}")
        result = test_route_prediction(source_id, dest_id)
        results.append(result)
    
    print()
    print(f"Completed {len(results)} predictions")
    print()
    
    # Calculate statistics
    print("Calculating statistics...")
    stats = calculate_statistics(results)
    
    if stats:
        print("\n" + "=" * 80)
        print("DEMAND STATISTICS")
        print("=" * 80)
        print(f"Total predictions: {stats['count']}")
        print(f"Minimum demand: {stats['min']}")
        print(f"Maximum demand: {stats['max']}")
        print(f"Average demand: {stats['average']:.2f}")
        print(f"Median demand: {stats['median']:.2f}")
        print(f"Standard deviation: {stats['std_dev']:.2f}")
        print(f"Unique demand values: {stats['unique_values']}")
        print(f"Demand values: {stats['demand_values']}")
    else:
        print("\n" + "=" * 80)
        print("DEMAND STATISTICS")
        print("=" * 80)
        print("No valid demand data found")
    
    # Identify suspicious patterns
    print("\n" + "=" * 80)
    print("SUSPICIOUS PATTERNS")
    print("=" * 80)
    suspicious = identify_suspicious_patterns(results)
    if suspicious:
        print(f"Found {len(suspicious)} suspicious patterns:")
        for pattern in suspicious:
            print(f"  Demand value {pattern['demand_value']} appears {pattern['route_count']} times")
            print(f"    Routes: {pattern['routes']}")
    else:
        print("No suspicious patterns detected")
    
    # Verify peak hour effect
    print("\n" + "=" * 80)
    print("PEAK HOUR VERIFICATION")
    print("=" * 80)
    peak_verification = verify_peak_hour_effect(results)
    print(f"Verified: {peak_verification['verified']}")
    print(f"Peak average demand: {peak_verification['peak_avg']}")
    print(f"Off-peak average demand: {peak_verification['off_peak_avg']}")
    if 'difference' in peak_verification:
        print(f"Difference: {peak_verification['difference']:.2f}")
    print(f"Reason: {peak_verification['reason']}")
    
    # Save detailed results
    output_file = "outputs/demand_validation_results.json"
    os.makedirs("outputs", exist_ok=True)
    
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "statistics": stats,
            "suspicious_patterns": suspicious,
            "peak_hour_verification": peak_verification,
            "detailed_results": results
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: {output_file}")
    print(f"\nCompleted at: {datetime.now()}")

if __name__ == "__main__":
    main()
