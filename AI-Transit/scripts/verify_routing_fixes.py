"""
Routing Fix Verification Script
================================
Verifies stop canonicalization and walking transfer edge implementation.
"""

import sys
import os

# Add backend to path
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
sys.path.insert(0, backend_dir)

from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.database.models import GTFSStop, GTFSStopTime
from app.services.routing_service import (
    build_transit_graph,
    invalidate_transit_graph_cache,
    _canonicalize_stop_id,
    resolve_route_dynamic,
    TRANSFER_PENALTY,
    MAX_TRANSFERS
)
from app.logger import app_logger
import networkx as nx
import random

def print_section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def step1_rebuild_graph(db: Session):
    """STEP 1: Rebuild graph and verify logs"""
    print_section("STEP 1: Rebuild Graph")
    
    # Invalidate cache
    print("Invalidating graph cache...")
    invalidate_transit_graph_cache()
    
    # Build graph
    print("Building transit graph...")
    G = build_transit_graph(db)
    
    print(f"\nGraph Statistics:")
    print(f"  Nodes: {G.number_of_nodes()}")
    print(f"  Total Edges: {G.number_of_edges()}")
    
    # Count walking transfer edges
    walk_edges = 0
    route_edges = 0
    for u, v, k, data in G.edges(keys=True, data=True):
        if data.get('route_id') == 'WALK':
            walk_edges += 1
        else:
            route_edges += 1
    
    print(f"  Route Edges: {route_edges}")
    print(f"  Walking Transfer Edges: {walk_edges}")
    
    return G, walk_edges > 0

def step2_verify_canonicalization(db: Session):
    """STEP 2: Verify canonicalization for source_id=21629"""
    print_section("STEP 2: Verify Canonicalization")
    
    source_id = "21629"
    stop = db.query(GTFSStop).filter(GTFSStop.stop_id == source_id).first()
    
    if not stop:
        print(f"✗ FAIL: Stop {source_id} not found")
        return False
    
    print(f"Original stop_id: {source_id}")
    print(f"Stop name: {stop.stop_name}")
    
    # Get all candidates
    from sqlalchemy import func
    stop_counts = db.query(
        GTFSStop.stop_id,
        func.count(GTFSStopTime.stop_id).label("occurrence_count")
    ).join(
        GTFSStopTime, GTFSStop.stop_id == GTFSStopTime.stop_id
    ).filter(
        GTFSStop.stop_name == stop.stop_name
    ).group_by(
        GTFSStop.stop_id
    ).all()
    
    print(f"\nCandidates for '{stop.stop_name}':")
    for stop_id, count in sorted(stop_counts, key=lambda x: x[1], reverse=True):
        marker = " <-- SELECTED" if stop_id == source_id else ""
        print(f"  stop_id={stop_id}, count={count}{marker}")
    
    # Canonicalize
    canonical_id = _canonicalize_stop_id(db, stop.stop_name)
    print(f"\nCanonical stop_id: {canonical_id}")
    
    expected = "21630"
    if canonical_id == expected:
        print(f"✓ PASS: Canonicalization correct (expected {expected})")
        return True
    else:
        print(f"✗ FAIL: Expected {expected}, got {canonical_id}")
        return False

def step3_verify_transfer_edge(G: nx.MultiDiGraph):
    """STEP 3: Verify transfer edge 21577 <-> 29205"""
    print_section("STEP 3: Verify Transfer Edge (21577 <-> 29205)")
    
    u, v = "21577", "29205"
    
    # Check forward edge
    forward_data = None
    if G.has_edge(u, v):
        edges = G.get_edge_data(u, v)
        for key, data in edges.items():
            if data.get('route_id') == 'WALK':
                forward_data = data
                break
    
    # Check reverse edge
    reverse_data = None
    if G.has_edge(v, u):
        edges = G.get_edge_data(v, u)
        for key, data in edges.items():
            if data.get('route_id') == 'WALK':
                reverse_data = data
                break
    
    print(f"Forward edge {u} -> {v}:")
    if forward_data:
        print(f"  ✓ EXISTS")
        print(f"  route_id: {forward_data.get('route_id')}")
        print(f"  distance_km: {forward_data.get('distance_km', 0):.3f}")
        print(f"  weight: {forward_data.get('weight', 0):.3f}")
    else:
        print(f"  ✗ NOT FOUND")
    
    print(f"\nReverse edge {v} -> {u}:")
    if reverse_data:
        print(f"  ✓ EXISTS")
        print(f"  route_id: {reverse_data.get('route_id')}")
        print(f"  distance_km: {reverse_data.get('distance_km', 0):.3f}")
        print(f"  weight: {reverse_data.get('weight', 0):.3f}")
    else:
        print(f"  ✗ NOT FOUND")
    
    if forward_data and reverse_data:
        distance = forward_data.get('distance_km', 0)
        if 0.30 <= distance <= 0.40:
            print(f"\n✓ PASS: Transfer edge exists with correct distance (~0.35 km)")
            return True
        else:
            print(f"\n✗ FAIL: Distance {distance:.3f} km not in expected range (0.30-0.40 km)")
            return False
    else:
        print(f"\n✗ FAIL: Missing bidirectional transfer edge")
        return False

def step4_route_validation(db: Session):
    """STEP 4: Route validation tests"""
    print_section("STEP 4: Route Validation")
    
    test_cases = [
        ("21629", "22897"),
        ("21630", "22897"),
        ("21629", "21455"),
    ]
    
    all_passed = True
    for source, dest in test_cases:
        print(f"\nTest: {source} -> {dest}")
        try:
            route_info = resolve_route_dynamic(db, source, dest, bus_capacity=60)
            
            path = route_info.get('path', [])
            stop_ids = route_info.get('stop_ids', [])
            route_ids = route_info.get('route_ids', [])
            transfer_count = route_info.get('transfer_count', 0)
            eta = route_info.get('eta_minutes', 0)
            
            print(f"  Path length: {len(path)} stops")
            print(f"  Stop IDs: {stop_ids[:5]}{'...' if len(stop_ids) > 5 else ''}")
            print(f"  Route IDs: {route_ids}")
            print(f"  Transfers: {transfer_count}")
            print(f"  ETA: {eta:.1f} min")
            
            if len(path) > 0 and transfer_count <= MAX_TRANSFERS:
                print(f"  ✓ PASS")
            else:
                print(f"  ✗ FAIL")
                all_passed = False
                
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            all_passed = False
    
    return all_passed

def step5_sanity_check(db: Session):
    """STEP 5: Sanity check with 20 random OD pairs"""
    print_section("STEP 5: Sanity Check (20 Random OD Pairs)")
    
    # Get all stop IDs
    stops = db.query(GTFSStop.stop_id).all()
    stop_ids = [s[0] for s in stops]
    
    if len(stop_ids) < 2:
        print("✗ FAIL: Not enough stops in database")
        return False
    
    print(f"Total stops in database: {len(stop_ids)}")
    
    # Run 20 random tests
    passed = 0
    failed = 0
    loops = 0
    transfers_exceeded = 0
    
    for i in range(20):
        source = random.choice(stop_ids)
        dest = random.choice(stop_ids)
        
        if source == dest:
            continue
        
        try:
            route_info = resolve_route_dynamic(db, source, dest, bus_capacity=60)
            
            path = route_info.get('path', [])
            transfer_count = route_info.get('transfer_count', 0)
            
            # Check for loops
            if len(path) != len(set(path)):
                loops += 1
                print(f"  Test {i+1}: {source} -> {dest} ✗ LOOP DETECTED")
                failed += 1
                continue
            
            # Check transfer count
            if transfer_count > MAX_TRANSFERS:
                transfers_exceeded += 1
                print(f"  Test {i+1}: {source} -> {dest} ✗ TRANSFERS EXCEEDED ({transfer_count})")
                failed += 1
                continue
            
            # Check path length
            if len(path) == 0:
                print(f"  Test {i+1}: {source} -> {dest} ✗ EMPTY PATH")
                failed += 1
                continue
            
            passed += 1
            
        except Exception as e:
            failed += 1
    
    print(f"\nResults:")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Loops: {loops}")
    print(f"  Transfers exceeded: {transfers_exceeded}")
    
    if failed == 0:
        print(f"✓ PASS: All sanity checks passed")
        return True
    else:
        print(f"✗ FAIL: {failed} sanity checks failed")
        return False

def main():
    print("\n" + "=" * 80)
    print("  ROUTING FIX VERIFICATION")
    print("=" * 80)
    
    db = SessionLocal()
    
    try:
        # STEP 1
        G, has_walk_edges = step1_rebuild_graph(db)
        step1_pass = has_walk_edges
        
        # STEP 2
        step2_pass = step2_verify_canonicalization(db)
        
        # STEP 3
        step3_pass = step3_verify_transfer_edge(G)
        
        # STEP 4
        step4_pass = step4_route_validation(db)
        
        # STEP 5
        step5_pass = step5_sanity_check(db)
        
        # STEP 6: Final Report
        print_section("STEP 6: Final Report")
        
        results = {
            "STEP 1 - Graph Rebuild": step1_pass,
            "STEP 2 - Canonicalization": step2_pass,
            "STEP 3 - Transfer Edge": step3_pass,
            "STEP 4 - Route Validation": step4_pass,
            "STEP 5 - Sanity Check": step5_pass,
        }
        
        print("\nResults Summary:")
        for step, passed in results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {step}: {status}")
        
        all_passed = all(results.values())
        
        print("\n" + "=" * 80)
        if all_passed:
            print("  FINAL RESULT: PASS")
            print("=" * 80)
            print("\n✓ Routing engine is stable.")
            print("✓ Ready to proceed with Passenger Portal integration.")
            print("✓ Next task: Remove hardcoded routes and service alerts.")
        else:
            print("  FINAL RESULT: FAIL")
            print("=" * 80)
            failed_steps = [step for step, passed in results.items() if not passed]
            print(f"\n✗ Failed steps: {', '.join(failed_steps)}")
            print("Please review logs above for details.")
        
        return all_passed
        
    finally:
        db.close()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
