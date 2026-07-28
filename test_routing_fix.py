"""
Test script to validate the routing fix for duplicate stops.
This directly tests the routing service without requiring the HTTP server.
"""

import sys
import os

# Add backend to path
BACKEND_DIR = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, BACKEND_DIR)

from app.database.connection import SessionLocal
from app.services.routing_service import resolve_route_dynamic, build_transit_graph
from app.logger import app_logger

def test_route(source_id, destination_id, test_name):
    """Test a single route and print detailed results."""
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print(f"{'='*80}")
    print(f"Source: {source_id}")
    print(f"Destination: {destination_id}")
    
    db = SessionLocal()
    try:
        # Build graph
        G = build_transit_graph(db)
        
        # Get route
        result = resolve_route_dynamic(
            db,
            source_id,
            destination_id,
            bus_capacity=60,
            traffic="Medium",
            weather="Clear"
        )
        
        # Print results
        print(f"\n=== FINAL route_path ===")
        print(f"{'stop_id':<15} | {'stop_name':<40} | {'route_id':<10} | {'is_transfer'}")
        print("-" * 90)
        
        route_path = result.get('route_path', [])
        for i, stop in enumerate(route_path):
            print(f"{stop['stop_id']:<15} | {stop['stop_name']:<40} | {stop['route_id']:<10} | {stop['is_transfer']}")
        
        # Validation checks
        print(f"\n=== VALIDATION CHECKS ===")
        
        stop_ids = [s['stop_id'] for s in route_path]
        unique_stop_ids = set(stop_ids)
        total_stops = len(stop_ids)
        unique_count = len(unique_stop_ids)
        duplicate_count = total_stops - unique_count
        
        print(f"1. Total stops: {total_stops}")
        print(f"2. Unique stops: {unique_count}")
        print(f"3. Duplicate stop_ids: {duplicate_count}")
        
        # Check for consecutive duplicates
        consecutive_dupes = []
        for i in range(len(route_path) - 1):
            if route_path[i]['stop_id'] == route_path[i+1]['stop_id']:
                consecutive_dupes.append((i, route_path[i]['stop_id']))
        print(f"4. Consecutive duplicate stop names: {len(consecutive_dupes)}")
        if consecutive_dupes:
            for idx, stop_id in consecutive_dupes:
                print(f"   - Position {idx}: {stop_id}")
        
        # Transfer count
        transfer_count = result.get('num_transfers', 0)
        print(f"5. Transfer count: {transfer_count}")
        
        # Source preserved
        source_preserved = route_path[0]['stop_id'] == source_id if route_path else False
        print(f"6. Source preserved: {source_preserved}")
        
        # Destination preserved
        dest_preserved = route_path[-1]['stop_id'] == destination_id if route_path else False
        print(f"7. Destination preserved: {dest_preserved}")
        
        # Check for backtracking
        backtracking = []
        seen_stops = {}
        for i, stop_id in enumerate(stop_ids):
            if stop_id in seen_stops:
                backtracking.append((stop_id, seen_stops[stop_id], i))
            seen_stops[stop_id] = i
        
        print(f"8. Backtracking detected: {len(backtracking)}")
        if backtracking:
            for stop_id, first_idx, second_idx in backtracking:
                print(f"   - {stop_id}: first at {first_idx}, revisited at {second_idx}")
        
        # Consistency checks
        print(f"\n=== CONSISTENCY CHECKS ===")
        stops = result.get('stops', [])
        print(f"route_path length: {len(route_path)}")
        print(f"stops length: {len(stops)}")
        print(f"polyline length: {len(result.get('polyline', []))}")
        print(f"transfers count: {len(result.get('transfers', []))}")
        print(f"legs count: {len(result.get('route_legs', []))}")
        
        # Final verdict
        print(f"\n=== VERDICT ===")
        all_pass = (
            duplicate_count == 0 and
            len(consecutive_dupes) == 0 and
            len(backtracking) == 0 and
            source_preserved and
            dest_preserved
        )
        
        if all_pass:
            print("✅ PASS - No loops, no duplicates, valid route")
        else:
            print("❌ FAIL - Issues detected")
            if duplicate_count > 0:
                print(f"   - {duplicate_count} duplicate stop_ids found")
            if consecutive_dupes:
                print(f"   - {len(consecutive_dupes)} consecutive duplicates found")
            if backtracking:
                print(f"   - {len(backtracking)} backtracking instances found")
            if not source_preserved:
                print("   - Source not preserved")
            if not dest_preserved:
                print("   - Destination not preserved")
        
        return all_pass, result
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False, None
    finally:
        db.close()

if __name__ == "__main__":
    print("ROUTING FIX VALIDATION")
    print("=" * 80)
    
    # Test routes
    tests = [
        ("21630", "22897", "BHEL → Destination (22897)"),
        ("21630", "21454", "BHEL → 21454"),
        # Find a route with 2+ transfers by testing a longer distance
    ]
    
    results = []
    for source, dest, name in tests:
        passed, result = test_route(source, dest, name)
        results.append((name, passed))
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
