"""
Test the segment extraction to see why it's returning 4 stops instead of 5.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database.connection import SessionLocal
from app.services.routing_service import build_transit_graph, _extract_route_segment
from app.logger import app_logger

print("=" * 80)
print("TESTING SEGMENT EXTRACTION")
print("=" * 80)

ORIGIN_STOP_ID = "21629"  # 12th Block Nagarabhavi
DESTINATION_STOP_ID = "21454"  # Ambedkar Institute of Technology
ROUTE_ID = "1852"  # One of the shared routes

print(f"\nOrigin: 12th Block Nagarabhavi ({ORIGIN_STOP_ID})")
print(f"Destination: Ambedkar Institute of Technology ({DESTINATION_STOP_ID})")
print(f"Route ID: {ROUTE_ID}")
print("\nExpected segment (from GTFS):")
print("  12th Block Nagarabhavi (21629)")
print("  NGEF Layout Nagarabhavi (21581)")
print("  Vinayaka Layout Nagarabhavi (21624)")
print("  Kengunte Circle (IIPM) (21555)")
print("  Ambedkar Institute of Technology (21454)")

db = SessionLocal()

try:
    print("\n" + "=" * 80)
    print("BUILDING TRANSIT GRAPH")
    print("=" * 80)
    
    G = build_transit_graph(db)
    
    print(f"\nGraph built successfully")
    print(f"Nodes: {G.number_of_nodes()}")
    print(f"Edges: {G.number_of_edges()}")
    
    print("\n" + "=" * 80)
    print("CHECKING EDGES ON ROUTE 1852")
    print("=" * 80)
    
    # Check edges from origin
    print(f"\nEdges from origin ({ORIGIN_STOP_ID}):")
    for nbr in G.successors(ORIGIN_STOP_ID):
        for edge_key, edge_data in G[ORIGIN_STOP_ID][nbr].items():
            if edge_data.get("route_id") == ROUTE_ID:
                print(f"  {ORIGIN_STOP_ID} -> {nbr} (route_id={edge_data.get('route_id')}, distance={edge_data.get('distance_km')})")
    
    # Check edges from NGEF Layout
    ngef_id = "21581"
    print(f"\nEdges from NGEF Layout ({ngef_id}):")
    for nbr in G.successors(ngef_id):
        for edge_key, edge_data in G[ngef_id][nbr].items():
            if edge_data.get("route_id") == ROUTE_ID:
                print(f"  {ngef_id} -> {nbr} (route_id={edge_data.get('route_id')}, distance={edge_data.get('distance_km')})")
    
    print("\n" + "=" * 80)
    print("CALLING _extract_route_segment")
    print("=" * 80)
    
    result = _extract_route_segment(G, ORIGIN_STOP_ID, DESTINATION_STOP_ID, ROUTE_ID)
    
    print("\n" + "=" * 80)
    print("RESULT")
    print("=" * 80)
    
    if result:
        segment, route_id = result
        print(f"\n✅ Segment found!")
        print(f"Length: {len(segment)} stops")
        print(f"Route ID: {route_id}")
        print(f"\nSegment stops:")
        for i, stop_id in enumerate(segment):
            node_data = G.nodes.get(stop_id, {})
            stop_name = node_data.get("name", "Unknown")
            print(f"  [{i}] {stop_name} ({stop_id})")
    else:
        print(f"\n❌ No segment found")
        
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
