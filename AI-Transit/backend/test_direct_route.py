"""
Test the _find_direct_route function directly to see why it's not finding the 13 direct routes.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database.connection import SessionLocal
from app.services.routing_service import build_transit_graph, _find_direct_route
from app.logger import app_logger

print("=" * 80)
print("TESTING _find_direct_route FUNCTION DIRECTLY")
print("=" * 80)

ORIGIN_STOP_ID = "21629"  # 12th Block Nagarabhavi
DESTINATION_STOP_ID = "21454"  # Ambedkar Institute of Technology

print(f"\nOrigin: 12th Block Nagarabhavi ({ORIGIN_STOP_ID})")
print(f"Destination: Ambedkar Institute of Technology ({DESTINATION_STOP_ID})")
print("\nGTFS data shows 13 shared routes with 5-stop segments")

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
    print("CHECKING GRAPH FOR ORIGIN AND DESTINATION")
    print("=" * 80)
    
    print(f"\nOrigin node exists: {G.has_node(ORIGIN_STOP_ID)}")
    print(f"Destination node exists: {G.has_node(DESTINATION_STOP_ID)}")
    
    if G.has_node(ORIGIN_STOP_ID):
        origin_data = G.nodes[ORIGIN_STOP_ID]
        print(f"Origin node data: {origin_data}")
        
        # Check outgoing edges from origin
        successors = list(G.successors(ORIGIN_STOP_ID))
        print(f"Origin has {len(successors)} outgoing edges")
        print(f"First 5 successors: {successors[:5]}")
        
        # Check route IDs on outgoing edges
        route_ids = set()
        for nbr in successors[:5]:
            for edge_key, edge_data in G[ORIGIN_STOP_ID][nbr].items():
                route_id = edge_data.get('route_id')
                route_ids.add(route_id)
        print(f"Route IDs on origin edges: {route_ids}")
    
    if G.has_node(DESTINATION_STOP_ID):
        dest_data = G.nodes[DESTINATION_STOP_ID]
        print(f"Destination node data: {dest_data}")
        
        # Check incoming edges to destination
        predecessors = list(G.predecessors(DESTINATION_STOP_ID))
        print(f"Destination has {len(predecessors)} incoming edges")
        print(f"First 5 predecessors: {predecessors[:5]}")
        
        # Check route IDs on incoming edges
        route_ids = set()
        for pred in predecessors[:5]:
            for edge_key, edge_data in G[pred][DESTINATION_STOP_ID].items():
                route_id = edge_data.get('route_id')
                route_ids.add(route_id)
        print(f"Route IDs on destination edges: {route_ids}")
    
    print("\n" + "=" * 80)
    print("CALLING _find_direct_route")
    print("=" * 80)
    
    direct_route = _find_direct_route(G, ORIGIN_STOP_ID, DESTINATION_STOP_ID, log_result=True)
    
    print("\n" + "=" * 80)
    print("RESULT")
    print("=" * 80)
    
    if direct_route:
        print(f"\n✅ Direct route found!")
        print(f"Length: {len(direct_route)} stops")
        print(f"Route: {direct_route}")
    else:
        print(f"\n❌ No direct route found")
        print(f"This is the ROOT CAUSE of the regression")
        
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
