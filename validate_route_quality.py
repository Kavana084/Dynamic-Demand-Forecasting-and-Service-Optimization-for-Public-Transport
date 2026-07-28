"""
Post-fix validation for:
  1. 21454 -> 21517 (regression route)
  2. 21454 -> 20789 (original test A)
  3. 21629 -> 20789 (original test B)
  4. 20789 -> 21454 (original test C)
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from app.database.connection import SessionLocal
from app.database.models import GTFSStop
from app.services.routing_service import resolve_route_dynamic, invalidate_transit_graph_cache

def run_test(db, test_name, source_id, dest_id):
    print(f"\n{'='*60}")
    print(f"  {test_name}: {source_id} -> {dest_id}")
    print(f"{'='*60}")
    
    try:
        source_name = db.get(GTFSStop, source_id).stop_name
        dest_name = db.get(GTFSStop, dest_id).stop_name
        print(f"  Source: {source_name} ({source_id})")
        print(f"  Dest:   {dest_name} ({dest_id})")
    except Exception:
        print(f"  Source: {source_id}")
        print(f"  Dest:   {dest_id}")

    invalidate_transit_graph_cache()
    
    # Force Dijkstra by monkey-patching the fast paths
    import app.services.routing_service as rs
    original_direct = rs._find_direct_route
    original_hub = rs._get_cached_hub_path
    rs._find_direct_route = lambda *args, **kwargs: None
    rs._get_cached_hub_path = lambda *args, **kwargs: None

    try:
        try:
            response = resolve_route_dynamic(
                db=db,
                source_id=source_id,
                destination_id=dest_id,
            )
        finally:
            # Restore
            rs._find_direct_route = original_direct
            rs._get_cached_hub_path = original_hub

        
        route_ids = response.get("route_ids", [])
        num_transfers = response.get("num_transfers", 0)
        total_stops = len(response.get("stops", []))
        eta_min = response.get("eta_min", 0)
        distance_km = response.get("total_distance_km", 0.0)
        
        print(f"\n  [OK] ROUTE FOUND")
        print(f"     route_ids:     {route_ids}")
        print(f"     num_transfers: {num_transfers}")
        print(f"     total_stops:   {total_stops}")
        print(f"     eta_min:       {eta_min}")
        print(f"     distance_km:   {distance_km}")
        
        # Loop detection
        stops = response.get("stops", [])
        
        # Check for repeated stop names
        seen_names = set()
        repeated = []
        for s in stops:
            if s in seen_names:
                repeated.append(s)
            seen_names.add(s)
        
        if repeated:
            print(f"     [WARN] Repeated names: {list(set(repeated))}")
        else:
            print(f"     [OK] No repeated stop names")

        # Route breakdown
        print(f"\n     Route legs:")
        for idx, leg in enumerate(response.get("route_legs", [])):
            print(f"       Leg {idx+1}: Route {leg.get('route_id')} from {leg.get('start_stop')}")
            
        print(f"\n     Full Stop Sequence:")
        for i, s in enumerate(stops):
            print(f"       {i}: {s}")
            
    except Exception as e:
        print(f"\n  [FAIL] {e}")

def main():
    db = SessionLocal()
    try:
        run_test(db, "REGRESSION: Ambedkar->Goraguntepalya(21517)", "21454", "21517")
        # run_test(db, "Test A: Ambedkar->Goraguntepalya(20789)", "21454", "20789")
        run_test(db, "Test B: 12th Block->Goraguntepalya(20789)", "21629", "20789")
        # run_test(db, "Test C: Goraguntepalya(20789)->Ambedkar", "20789", "21454")
    finally:
        db.close()

if __name__ == "__main__":
    main()
