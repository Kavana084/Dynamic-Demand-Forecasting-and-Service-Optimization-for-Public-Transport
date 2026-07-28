"""
Regression Test Suite for Transit Routing Engine

Tests specific routes to ensure:
- Direct routes are preferred
- Stop counts are realistic
- Transfers are minimal
- No backtracking or revisits
"""

import sys
import os
from typing import Dict, List, Any

# Add backend to path
BACKEND_DIR = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, BACKEND_DIR)

from app.database.connection import SessionLocal
from app.services.routing_service import resolve_route_dynamic, build_transit_graph
from app.logger import app_logger


class RoutingTestResult:
    def __init__(self, test_name: str, passed: bool, details: Dict[str, Any]):
        self.test_name = test_name
        self.passed = passed
        self.details = details
    
    def __str__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"{status} - {self.test_name}"


def test_route(
    source_id: str,
    destination_id: str,
    test_name: str,
    expected_transfers: int = 0,
    max_stops: int = 4,
    expected_route_type: str = "DIRECT_ROUTE"
) -> RoutingTestResult:
    """
    Test a single route and validate against expectations.
    
    Returns:
        RoutingTestResult with pass/fail status and details
    """
    app_logger.info(f"\n{'='*80}")
    app_logger.info(f"TEST: {test_name}")
    app_logger.info(f"{'='*80}")
    app_logger.info(f"Source: {source_id}")
    app_logger.info(f"Destination: {destination_id}")
    app_logger.info(f"Expected transfers: {expected_transfers}")
    app_logger.info(f"Max stops: {max_stops}")
    app_logger.info(f"Expected route type: {expected_route_type}")
    
    db = SessionLocal()
    details = {}
    
    try:
        # Build graph
        G = build_transit_graph(db)
        
        # Get route
        result = resolve_route_dynamic(
            db,
            source_id,
            destination_id,
            bus_capacity=60,
            traffic="Medium",
            weather="Clear"
        )
        
        # Extract metrics
        route_path = result.get('route_path', [])
        transfers = result.get('num_transfers', 0)
        total_stops = len(route_path)
        
        # Check for duplicates
        stop_ids = [s['stop_id'] for s in route_path]
        unique_stop_ids = set(stop_ids)
        duplicate_count = len(stop_ids) - len(unique_stop_ids)
        
        # Check for backtracking
        backtracking_detected = False
        for i in range(len(stop_ids) - 1):
            if stop_ids[i] in stop_ids[i+1:]:
                backtracking_detected = True
                break
        
        # Store details
        details = {
            'total_stops': total_stops,
            'unique_stops': len(unique_stop_ids),
            'duplicate_count': duplicate_count,
            'transfers': transfers,
            'backtracking_detected': backtracking_detected,
            'route_path': route_path,
            'source_id': source_id,
            'destination_id': destination_id
        }
        
        # Validation checks
        failures = []
        
        # Check 1: Transfer count
        if transfers > expected_transfers:
            failures.append(f"Too many transfers: {transfers} > {expected_transfers}")
        
        # Check 2: Stop count
        if total_stops > max_stops:
            failures.append(f"Too many stops: {total_stops} > {max_stops}")
        
        # Check 3: No duplicates
        if duplicate_count > 0:
            failures.append(f"Duplicate stops detected: {duplicate_count}")
        
        # Check 4: No backtracking
        if backtracking_detected:
            failures.append("Backtracking detected")
        
        # Check 5: Source preserved
        if route_path and route_path[0]['stop_id'] != source_id:
            failures.append("Source not preserved")
        
        # Check 6: Destination preserved
        if route_path and route_path[-1]['stop_id'] != destination_id:
            failures.append("Destination not preserved")
        
        # Determine pass/fail
        passed = len(failures) == 0
        
        if not passed:
            app_logger.error(f"TEST FAILED:")
            for failure in failures:
                app_logger.error(f"  - {failure}")
        else:
            app_logger.info(f"TEST PASSED")
        
        app_logger.info(f"Results:")
        app_logger.info(f"  Total stops: {total_stops}")
        app_logger.info(f"  Transfers: {transfers}")
        app_logger.info(f"  Duplicates: {duplicate_count}")
        app_logger.info(f"  Backtracking: {backtracking_detected}")
        
        return RoutingTestResult(test_name, passed, details)
        
    except Exception as e:
        app_logger.error(f"TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        details['error'] = str(e)
        return RoutingTestResult(test_name, False, details)
    finally:
        db.close()


def run_regression_tests() -> List[RoutingTestResult]:
    """
    Run all regression tests and return results.
    """
    results = []
    
    # Test Case 1: 12th Block Nagarabhavi → 1st Stage 3rd Block Nagarabhavi
    # Expected: Direct route, 0 transfers, ≤ 4 stops
    # Note: Need to find actual stop IDs for these locations
    # For now, using placeholder IDs - these should be updated with real IDs
    
    results.append(test_route(
        source_id="21630",  # Placeholder - should be 12th Block Nagarabhavi
        destination_id="22897",  # Placeholder - should be 1st Stage 3rd Block Nagarabhavi
        test_name="Test Case 1: 12th Block Nagarabhavi → 1st Stage 3rd Block Nagarabhavi",
        expected_transfers=0,
        max_stops=4,
        expected_route_type="DIRECT_ROUTE"
    ))
    
    # Test Case 2: 12th Block Nagarabhavi → Dr. Ambedkar Institute of Technology
    # Expected: Direct route, 0 transfers, ≤ 4 stops
    
    results.append(test_route(
        source_id="21630",  # Placeholder - should be 12th Block Nagarabhavi
        destination_id="21454",  # Placeholder - should be Dr. Ambedkar Institute of Technology
        test_name="Test Case 2: 12th Block Nagarabhavi → Dr. Ambedkar Institute of Technology",
        expected_transfers=0,
        max_stops=4,
        expected_route_type="DIRECT_ROUTE"
    ))
    
    # Additional test cases can be added here
    
    return results


def print_summary(results: List[RoutingTestResult]):
    """Print test summary."""
    print(f"\n{'='*80}")
    print("REGRESSION TEST SUMMARY")
    print(f"{'='*80}")
    
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    
    for result in results:
        print(result)
    
    print(f"\nTotal: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed > 0:
        print("\nFailed tests details:")
        for result in results:
            if not result.passed:
                print(f"\n{result.test_name}:")
                for key, value in result.details.items():
                    if key != 'route_path':
                        print(f"  {key}: {value}")


if __name__ == "__main__":
    print("TRANSIT ROUTING ENGINE - REGRESSION TEST SUITE")
    print("=" * 80)
    
    results = run_regression_tests()
    print_summary(results)
    
    # Exit with error code if any tests failed
    if not all(r.passed for r in results):
        sys.exit(1)
    else:
        sys.exit(0)
