import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from app.database.connection import SessionLocal
from app.services.routing_service import build_transit_graph
import networkx as nx

def main():
    db = SessionLocal()
    G = build_transit_graph(db)
    
    source = "21454"
    target = "36719"
    
    print(f"Source {source} out edges: {len(list(G.out_edges(source)))}")
    print(f"Target {target} in edges: {len(list(G.in_edges(target)))}")
    
    try:
        path = nx.shortest_path(G, source=source, target=target)
        print(f"Shortest path (nodes): {len(path)}")
        # calculate transfers
        transfers = 0
        curr_route = None
        for i in range(len(path)-1):
            u = path[i]
            v = path[i+1]
            edges = G[u][v]
            # pick any route
            route = list(edges.values())[0]['route_id']
            if curr_route and route != curr_route:
                transfers += 1
            curr_route = route
        print(f"Estimated transfers: {transfers}")
    except nx.NetworkXNoPath:
        print("No path found!")

if __name__ == "__main__":
    main()
