"""
Test the backtracking issue in routes.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database.connection import SessionLocal
from app.services.routing_service import build_transit_graph, _find_direct_route, resolve_route_dynamic
from app.logger import app_logger

print("=" * 80)
print("TESTING BACKTRACKING ISSUE")
print("=" * 80)

# Test case 1: 12th Block Nagarabhavi → Ambedkar Institute of Technology
ORIGIN_STOP_ID = "21629"  # 12th Block Nagarabhavi
DESTINATION_STOP_ID = "21454"  # Ambedkar Institute of Technology

print(f"\nTest Case 1: {ORIGIN_STOP_ID} → {DESTINATION_STOP_ID}")
print("Expected: Direct route with 5 stops")
print("Actual from user: 19 stops with backtracking to origin")

db = SessionLocal()

try:
    G = build_transit_graph(db)
    
    print("\n" + "=" * 80)
    print("CHECKING DIRECT ROUTE")
    print("=" * 80)
    
    direct_result = _find_direct_route(G, ORIGIN_STOP_ID, DESTINATION_STOP_ID, log_result=True)
    
    if direct_result:
        direct_path, direct_route_id = direct_result
        print(f"\n✅ Direct route found!")
        print(f"Length: {len(direct_path)} stops")
        print(f"Route ID: {direct_route_id}")
        print(f"\nDirect route stops:")
        for i, stop_id in enumerate(direct_path):
            node_data = G.nodes.get(stop_id, {})
            stop_name = node_data.get("name", "Unknown")
            print(f"  [{i}] {stop_name} ({stop_id})")
    else:
        print(f"\n❌ No direct route found")
    
    print("\n" + "=" * 80)
    print("CALLING resolve_route_dynamic")
    print("=" * 80)
    
    result = resolve_route_dynamic(db, ORIGIN_STOP_ID, DESTINATION_STOP_ID)
    
    print("\n" + "=" * 80)
    print("RESULT")
    print("=" * 80)
    
    if result:
        stops = result.get("stops", [])
        transfers = result.get("transfers", 0)
        print(f"\nStops: {len(stops)}")
        print(f"Transfers: {transfers}")
        print(f"\nRoute stops:")
        for i, stop_name in enumerate(stops):
            print(f"  [{i}] {stop_name}")
        
        # Check for duplicates
        stop_ids = result.get("path", [])
        unique_stops = len(set(stop_ids))
        if unique_stops < len(stop_ids):
            print(f"\n⚠️  DUPLICATE STOPS DETECTED!")
            print(f"Total stops: {len(stop_ids)}, Unique stops: {unique_stops}")
            
            # Find duplicates
            from collections import Counter
            stop_counts = Counter(stop_ids)
            duplicates = {stop_id: count for stop_id, count in stop_counts.items() if count > 1}
            print(f"Duplicate stop IDs: {duplicates}")
            
            for stop_id, count in duplicates.items():
                node_data = G.nodes.get(stop_id, {})
                stop_name = node_data.get("name", "Unknown")
                print(f"  {stop_name} ({stop_id}) appears {count} times")
        
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
