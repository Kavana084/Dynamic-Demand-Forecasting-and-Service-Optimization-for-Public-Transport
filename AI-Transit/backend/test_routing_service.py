"""
Test the routing service with the identified stop IDs to see what it actually returns.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database.connection import SessionLocal
from app.services.routing_service import resolve_route_dynamic, build_transit_graph
from app.logger import app_logger

# Configure logging to see all messages
import logging
logging.basicConfig(level=logging.DEBUG)

print("=" * 80)
print("TESTING ROUTING SERVICE WITH IDENTIFIED STOP IDs")
print("=" * 80)

# Use the stop IDs from the investigation
ORIGIN_STOP_ID = "21629"  # 12th Block Nagarabhavi
DESTINATION_STOP_ID = "21454"  # Ambedkar Institute of Technology

print(f"\nOrigin: 12th Block Nagarabhavi ({ORIGIN_STOP_ID})")
print(f"Destination: Ambedkar Institute of Technology ({DESTINATION_STOP_ID})")
print("\nExpected: Direct route with 5 stops, 0 transfers")

db = SessionLocal()

try:
    print("\n" + "=" * 80)
    print("CALLING ROUTING SERVICE")
    print("=" * 80)
    
    result = resolve_route_dynamic(
        db,
        ORIGIN_STOP_ID,
        DESTINATION_STOP_ID,
        bus_capacity=60,
        traffic="Medium",
        weather="Clear"
    )
    
    print("\n" + "=" * 80)
    print("ROUTING SERVICE RESULT")
    print("=" * 80)
    
    print(f"\nSuccess: {result.get('success', False)}")
    print(f"Route Type: {result.get('route_type', 'N/A')}")
    print(f"Total Stops: {len(result.get('route_path', []))}")
    print(f"Transfers: {result.get('num_transfers', 'N/A')}")
    print(f"ETA: {result.get('eta_minutes', 'N/A')} minutes")
    print(f"Distance: {result.get('total_distance_km', 'N/A')} km")
    
    route_path = result.get('route_path', [])
    print(f"\nRoute Path ({len(route_path)} stops):")
    for i, stop in enumerate(route_path):
        print(f"  [{i}] {stop.get('stop_name', 'Unknown')} ({stop.get('stop_id', 'N/A')}) - Route: {stop.get('route_id', 'N/A')}")
    
    transfers = result.get('transfers', [])
    print(f"\nTransfers ({len(transfers)}):")
    for i, transfer in enumerate(transfers):
        print(f"  [{i}] {transfer}")
    
    # Check if this matches expectations
    print("\n" + "=" * 80)
    print("VALIDATION")
    print("=" * 80)
    
    expected_stops = 5
    expected_transfers = 0
    
    actual_stops = len(route_path)
    actual_transfers = result.get('num_transfers', 0)
    
    print(f"\nExpected: {expected_stops} stops, {expected_transfers} transfers")
    print(f"Actual: {actual_stops} stops, {actual_transfers} transfers")
    
    if actual_stops == expected_stops and actual_transfers == expected_transfers:
        print("\n✅ ROUTING SERVICE RETURNED EXPECTED DIRECT ROUTE")
    else:
        print(f"\n❌ ROUTING SERVICE DID NOT RETURN EXPECTED ROUTE")
        print(f"   Expected {expected_stops} stops, got {actual_stops}")
        print(f"   Expected {expected_transfers} transfers, got {actual_transfers}")
        
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
