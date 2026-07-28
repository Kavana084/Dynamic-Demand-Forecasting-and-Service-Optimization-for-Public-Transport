import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

import networkx as nx
from typing import List

# We need to monkey-patch or copy the _transfer_aware_dijkstra logic here to test it 
# directly on a synthetic graph.
from app.services.routing_service import _transfer_aware_dijkstra, MAX_TRANSFERS

def build_synthetic_graph():
    # S = Source, T = Target
    # We want two paths to node M:
    # Path A: S -> A1 -> M. (Cost 10, Transfers 0)  (Route R_A)
    # Path B: S -> K -> B1 -> M. (Cost 20, Transfers 0) (Route R_B)
    
    # Wait, the bug requires Path B (cost 20) to have fewer transfers than Path A (cost 10)
    # so that Path B overwrites Path A in best_cost, but Path A pops from the heap and 
    # continues to T.
    
    # Path A (Cost 10, Transfers 1): S --(R_X)--> A1 --(R_A)--> M
    # Path B (Cost 20, Transfers 0): S --(R_A)--> K --(R_A)--> B1 --(R_A)--> M
    
    # So both reach M on Route R_A.
    # Path B reaches (M, R_A) with (0 transfers, cost 20).
    # Path A reaches (M, R_A) with (1 transfer, cost 10).
    # (0, 20) < (1, 10). So Path B overwrites Path A's parent pointer for M!
    # But Path B pops FIRST from the heap.
    # When Path B pops (M, R_A), it tries to expand to K. But it visited K! So it is blocked.
    # When Path A pops (M, R_A), it tries to expand to K. It did not visit K! So it succeeds.
    # It reaches K, then T.
    # Reconstruction: T -> K -> M -> (parent[M, R_A] which is B1) -> K -> S.
    # LOOP on K!
    
    G = nx.MultiDiGraph()
    
    for node in ["S", "A1", "M", "K", "B1", "T"]:
        G.add_node(node, lat=0.0, lon=0.0) 
        
    # Path 1 (Transfer 0, Cost 20, VISITED C): S -> C -> A -> M
    # Route R1 all the way.
    G.add_edge("S", "C", key=0, route_id="R1", distance_km=5, stop_sequence=1)
    G.add_edge("C", "A", key=0, route_id="R1", distance_km=5, stop_sequence=2)
    G.add_edge("A", "M", key=0, route_id="R1", distance_km=10, stop_sequence=3)
    
    # Path 2 (Transfer 1, Cost 10, DID NOT VISIT C): S -> B -> M
    # S -> B is on Route R2. B -> M is on Route R1.
    G.add_edge("S", "B", key=0, route_id="R2", distance_km=5, stop_sequence=1)
    G.add_edge("B", "M", key=0, route_id="R1", distance_km=5, stop_sequence=2)
    
    # Continuation from M to T via C
    # M -> C is on Route R1.
    G.add_edge("M", "C", key=1, route_id="R1", distance_km=2, stop_sequence=4)
    # C -> T is on Route R1.
    G.add_edge("C", "T", key=1, route_id="R1", distance_km=2, stop_sequence=5)

    return G

def main():
    G = build_synthetic_graph()
    
    import app.services.routing_service as rs
    rs.haversine = lambda *args: 0.0
    rs.TRANSFER_PENALTY = 0.0 # Make transfers cheap so cost dictates best_cost pruning initially
    
    # Wait, if TRANSFER_PENALTY is 0, cost is the same. Let's leave TRANSFER_PENALTY at 5.0 (default).
    
    path = _transfer_aware_dijkstra(G, "S", "T", max_explored=1000, max_transfers=5)
    
    print("\n--- SYNTHETIC TEST RESULT ---")
    print(f"Path: {path}")
    
    if path:
        seen = set()
        loop = False
        for node in path:
            if node in seen:
                loop = True
            seen.add(node)
        
        if loop:
            print("!!! LOOP DETECTED !!!")
            print("This mathematically proves the parent-pointer overwrite bug.")
        else:
            print("No loop detected. The hypothesis might need adjustment.")

if __name__ == "__main__":
    main()
