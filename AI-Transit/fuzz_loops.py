import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))
import random
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.database.models import GTFSStop
from app.services.routing_service import resolve_route_dynamic, invalidate_transit_graph_cache

def main():
    db = SessionLocal()
    
    # Get all stops
    stops = db.query(GTFSStop).all()
    stop_ids = [str(s.stop_id) for s in stops if s.stop_lat and s.stop_lon]
    
    print(f"Loaded {len(stop_ids)} stops. Starting random search...")
    
    # Force Dijkstra
    import app.services.routing_service as rs
    rs._find_direct_route = lambda *args, **kwargs: None
    rs._get_cached_hub_path = lambda *args, **kwargs: None
    
    attempts = 0
    while attempts < 20:
        attempts += 1
        source = random.choice(stop_ids)
        dest = random.choice(stop_ids)
        
        if source == dest:
            continue
            
        print(f"[{attempts}] Testing {source} -> {dest}")
        invalidate_transit_graph_cache()
        
        try:
            # We don't care about the response, just want to trigger the logs
            response = resolve_route_dynamic(db, source_id=source, destination_id=dest)
            
            # Check if any diagnostic caught something
            path = response.get("stops", [])
            
            # Detect repeated stop ids
            seen = set()
            dups = set()
            for s in path:
                if s in seen:
                    dups.add(s)
                seen.add(s)
            
            if dups:
                print(f"!!! FOUND LOOP in {source} -> {dest} !!!")
                print(f"    Path: {path}")
                print(f"    Dups: {dups}")
                break
                
        except Exception as e:
            # Ignore timeouts or heap limits
            print(f"    Failed: {e}")

    db.close()

if __name__ == "__main__":
    main()
