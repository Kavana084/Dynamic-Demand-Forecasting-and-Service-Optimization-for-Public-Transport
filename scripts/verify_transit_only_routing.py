"""
Transit-Only Routing Verification
==================================
Verifies routing works correctly after removing WALK edges.
"""

import sys
import os

# Add backend to path
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
sys.path.insert(0, backend_dir)

from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.database.models import GTFSStop
from app.services.routing_service import (
    build_transit_graph,
    invalidate_transit_graph_cache,
    resolve_route_dynamic,
    MAX_TRANSFERS
)
import networkx as nx

def print_section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def main():
    print("\n" + "=" * 80)
    print("  TRANSIT-ONLY ROUTING VERIFICATION")
    print("=" * 80)
    
    db = SessionLocal()
    
    try:
        # STEP 1: Rebuild graph
        print_section("STEP 1: Rebuild Graph")
        
        print("Invalidating graph cache...")
        invalidate_transit_graph_cache()
        
        print("Building transit graph...")
        G = build_transit_graph(db)
        
        print(f"\nGraph Statistics:")
        print(f"  Nodes: {G.number_of_nodes()}")
        print(f"  Total Edges: {G.number_of_edges()}")
        
        # Check for WALK edges
        walk_edges = 0
        for u, v, k, data in G.edges(keys=True, data=True):
            if data.get('route_id') == 'WALK':
                walk_edges += 1
        
        print(f"  WALK Edges: {walk_edges}")
        
        # Verify graph size
        expected_edges = 1_430_000  # Approximate expected size
        actual_edges = G.number_of_edges()
        edge_diff = abs(actual_edges - expected_edges) / expected_edges
        
        step1_pass = (walk_edges == 0) and (edge_diff < 0.10)  # Within 10% of expected
        
        if walk_edges == 0:
            print(f"  ✓ PASS: No WALK edges found")
        else:
            print(f"  ✗ FAIL: Found {walk_edges} WALK edges")
        
        if edge_diff < 0.10:
            print(f"  ✓ PASS: Edge count {actual_edges:,} within 10% of expected {expected_edges:,}")
        else:
            print(f"  ✗ FAIL: Edge count {actual_edges:,} differs from expected {expected_edges:,} by {edge_diff*100:.1f}%")
        
        # STEP 2: Verify no route contains route_id='WALK'
        print_section("STEP 2: Verify No WALK Routes")
        
        # This is already verified by checking edges, but let's also check route_ids
        route_ids = set()
        for u, v, k, data in G.edges(keys=True, data=True):
            route_ids.add(data.get('route_id'))
        
        if 'WALK' in route_ids:
            print(f"  ✗ FAIL: route_id 'WALK' found in graph")
            step2_pass = False
        else:
            print(f"  ✓ PASS: No route_id 'WALK' in graph")
            print(f"  Unique route_ids: {len(route_ids)}")
            step2_pass = True
        
        # STEP 3: Test direct routes
        print_section("STEP 3: Test Direct Routes")
        
        direct_tests = [
            ("21630", "22896"),  # Known direct route
            ("29506", "22950"),  # Hub route
            ("22890", "20940"),  # Hub route
        ]
        
        direct_passed = 0
        direct_failed = 0
        
        for source, dest in direct_tests:
            print(f"\nTest: {source} -> {dest}")
            try:
                route_info = resolve_route_dynamic(db, source, dest, bus_capacity=60)
                
                route_ids = route_info.get('route_ids', [])
                transfer_count = route_info.get('transfer_count', 0)
                eta = route_info.get('eta_minutes', 0)
                
                print(f"  Route IDs: {route_ids}")
                print(f"  Transfers: {transfer_count}")
                print(f"  ETA: {eta:.1f} min")
                
                # Direct route should have 0 transfers
                if transfer_count == 0 and len(route_ids) == 1:
                    print(f"  ✓ PASS: Direct route (0 transfers)")
                    direct_passed += 1
                else:
                    print(f"  ✗ FAIL: Expected direct route, got {transfer_count} transfers")
                    direct_failed += 1
                    
            except Exception as e:
                print(f"  ✗ FAIL: {e}")
                direct_failed += 1
        
        step3_pass = direct_failed == 0
        print(f"\nDirect Routes: {direct_passed} passed, {direct_failed} failed")
        
        # STEP 4: Test transfer routes
        print_section("STEP 4: Test Transfer Routes")
        
        transfer_tests = [
            ("21630", "29506"),  # Likely requires transfer
            ("22890", "21172"),  # Hub to hub
        ]
        
        transfer_passed = 0
        transfer_failed = 0
        
        for source, dest in transfer_tests:
            print(f"\nTest: {source} -> {dest}")
            try:
                route_info = resolve_route_dynamic(db, source, dest, bus_capacity=60)
                
                route_ids = route_info.get('route_ids', [])
                transfer_count = route_info.get('transfer_count', 0)
                eta = route_info.get('eta_minutes', 0)
                
                print(f"  Route IDs: {route_ids}")
                print(f"  Transfers: {transfer_count}")
                print(f"  ETA: {eta:.1f} min")
                
                # Transfer route should have >0 transfers but <= MAX_TRANSFERS
                if 0 < transfer_count <= MAX_TRANSFERS:
                    print(f"  ✓ PASS: Valid transfer route")
                    transfer_passed += 1
                else:
                    print(f"  ✗ FAIL: Invalid transfer count: {transfer_count}")
                    transfer_failed += 1
                    
            except Exception as e:
                print(f"  ✗ FAIL: {e}")
                transfer_failed += 1
        
        step4_pass = transfer_failed == 0
        print(f"\nTransfer Routes: {transfer_passed} passed, {transfer_failed} failed")
        
        # STEP 5: Verify ETA accuracy
        print_section("STEP 5: Verify ETA Accuracy")
        
        # Test a few routes and check ETA is reasonable
        eta_tests = [
            ("21630", "22896", 30),  # Expected ~30 min
            ("29506", "22950", 20),  # Expected ~20 min
        ]
        
        eta_passed = 0
        eta_failed = 0
        
        for source, dest, expected_eta in eta_tests:
            print(f"\nTest: {source} -> {dest} (expected ~{expected_eta} min)")
            try:
                route_info = resolve_route_dynamic(db, source, dest, bus_capacity=60)
                
                eta = route_info.get('eta_minutes', 0)
                print(f"  Actual ETA: {eta:.1f} min")
                
                # ETA should be within reasonable range (50% tolerance)
                if 0.5 * expected_eta <= eta <= 2.0 * expected_eta:
                    print(f"  ✓ PASS: ETA within reasonable range")
                    eta_passed += 1
                else:
                    print(f"  ✗ FAIL: ETA {eta:.1f} min outside expected range ({expected_eta} min)")
                    eta_failed += 1
                    
            except Exception as e:
                print(f"  ✗ FAIL: {e}")
                eta_failed += 1
        
        step5_pass = eta_failed == 0
        print(f"\nETA Tests: {eta_passed} passed, {eta_failed} failed")
        
        # STEP 6: Final Report
        print_section("STEP 6: Final Report")
        
        results = {
            "STEP 1 - Graph Rebuild (no WALK edges, correct size)": step1_pass,
            "STEP 2 - No WALK route_ids": step2_pass,
            "STEP 3 - Direct Routes": step3_pass,
            "STEP 4 - Transfer Routes": step4_pass,
            "STEP 5 - ETA Accuracy": step5_pass,
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
            print("\n✓ Transit-only routing is working correctly.")
            print("✓ Graph size is correct (~1.43M edges).")
            print("✓ No WALK edges present.")
            print("✓ Direct routes work (0 transfers).")
            print("✓ Transfer routes work (1-3 transfers).")
            print("✓ ETA values are reasonable.")
        else:
            print("  FINAL RESULT: FAIL")
            print("=" * 80)
            failed_steps = [step for step, passed in results.items() if not passed]
            print(f"\n✗ Failed steps: {', '.join(failed_steps)}")
        
        return all_passed
        
    finally:
        db.close()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
