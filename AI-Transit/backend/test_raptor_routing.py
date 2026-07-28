"""
Test cases for RAPTOR routing integration.

Tests the specific failing stop pairs from the original Dijkstra implementation:
- 12th Block Nagarabhavi (21630) -> 8th Mile Dasarahalli (20594) - failed with Dijkstra
- Ananda Rao Circle (29506) -> KR Market (20940) - succeeded via Dijkstra in ~109s

Expected: RAPTOR should return equivalent or better results in well under a second.
"""

import sys
import os
import time
import datetime

# Add backend to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.services.raptor_service import plan_trip_raptor, check_repeated_stop_names, get_transit_data
from app.database.models import GTFSStop
from app.logger import app_logger


def test_raptor_routing():
    """Test RAPTOR routing with the specific failing stop pairs."""
    
    db = SessionLocal()
    
    try:
        # First, check for repeated stop names (pre-flight validation)
        app_logger.info("=" * 60)
        app_logger.info("PRE-FLIGHT VALIDATION: Checking for repeated stop names")
        app_logger.info("=" * 60)
        repeated_stops = check_repeated_stop_names(db)
        if repeated_stops:
            app_logger.warning(f"Found {len(repeated_stops)} routes with repeated stop names")
            for route_id, names in repeated_stops.items():
                app_logger.warning(f"  Route {route_id}: {names}")
        else:
            app_logger.info("No repeated stop names found - data is clean for RAPTOR")
        
        # Test Case 1: 12th Block Nagarabhavi (21630) -> 8th Mile Dasarahalli (20594)
        app_logger.info("=" * 60)
        app_logger.info("TEST CASE 1: 12th Block Nagarabhavi -> 8th Mile Dasarahalli")
        app_logger.info("=" * 60)
        
        source_id = "21630"
        dest_id = "20594"
        
        source_stop = db.query(GTFSStop).filter(GTFSStop.stop_id == source_id).first()
        dest_stop = db.query(GTFSStop).filter(GTFSStop.stop_id == dest_id).first()
        
        if source_stop and dest_stop:
            app_logger.info(f"Source: {source_stop.stop_name} ({source_id})")
            app_logger.info(f"Destination: {dest_stop.stop_name} ({dest_id})")
            
            # Debug: Check if stops exist in routes_by_stop
            data = get_transit_data(db)
            source_routes = data.routes_by_stop.get(source_id, [])
            dest_routes = data.routes_by_stop.get(dest_id, [])
            app_logger.info(f"Source stop serves {len(source_routes)} routes: {source_routes[:5]}")
            app_logger.info(f"Destination stop serves {len(dest_routes)} routes: {dest_routes[:5]}")
            
            # Check for common routes (direct route)
            common_routes = set(source_routes) & set(dest_routes)
            app_logger.info(f"Common routes (direct): {len(common_routes)} - {list(common_routes)[:5]}")
            
            current_time = datetime.datetime.now()
            start_time_sec = current_time.hour * 3600 + current_time.minute * 60 + current_time.second
            
            t0 = time.time()
            result = plan_trip_raptor(db, source_id, dest_id, start_time_sec, max_transfers=3)
            elapsed_ms = (time.time() - t0) * 1000
            
            app_logger.info(f"RAPTOR result: {result}")
            app_logger.info(f"Elapsed time: {elapsed_ms:.2f}ms")
            
            if result.get("status_code") == 200:
                app_logger.info(f"✓ SUCCESS: Found route in {elapsed_ms:.2f}ms")
                app_logger.info(f"  Transfer count: {result.get('transfer_count')}")
                app_logger.info(f"  Legs: {len(result.get('legs', []))}")
            else:
                app_logger.warning(f"✗ FAILED: {result.get('detail')}")
        else:
            app_logger.error(f"Stop not found: source={source_stop is not None}, dest={dest_stop is not None}")
        
        # Test Case 2: Ananda Rao Circle (29506) -> KR Market (20940)
        app_logger.info("=" * 60)
        app_logger.info("TEST CASE 2: Ananda Rao Circle -> KR Market")
        app_logger.info("=" * 60)
        
        source_id = "29506"
        dest_id = "20940"
        
        source_stop = db.query(GTFSStop).filter(GTFSStop.stop_id == source_id).first()
        dest_stop = db.query(GTFSStop).filter(GTFSStop.stop_id == dest_id).first()
        
        if source_stop and dest_stop:
            app_logger.info(f"Source: {source_stop.stop_name} ({source_id})")
            app_logger.info(f"Destination: {dest_stop.stop_name} ({dest_id})")
            
            # Debug: Check if stops exist in routes_by_stop
            source_routes = data.routes_by_stop.get(source_id, [])
            dest_routes = data.routes_by_stop.get(dest_id, [])
            app_logger.info(f"Source stop serves {len(source_routes)} routes: {source_routes[:5]}")
            app_logger.info(f"Destination stop serves {len(dest_routes)} routes: {dest_routes[:5]}")
            
            # Check for common routes (direct route)
            common_routes = set(source_routes) & set(dest_routes)
            app_logger.info(f"Common routes (direct): {len(common_routes)} - {list(common_routes)[:5]}")
            
            current_time = datetime.datetime.now()
            start_time_sec = current_time.hour * 3600 + current_time.minute * 60 + current_time.second
            
            t0 = time.time()
            result = plan_trip_raptor(db, source_id, dest_id, start_time_sec, max_transfers=3)
            elapsed_ms = (time.time() - t0) * 1000
            
            app_logger.info(f"RAPTOR result: {result}")
            app_logger.info(f"Elapsed time: {elapsed_ms:.2f}ms")
            
            if result.get("status_code") == 200:
                app_logger.info(f"✓ SUCCESS: Found route in {elapsed_ms:.2f}ms")
                app_logger.info(f"  Transfer count: {result.get('transfer_count')}")
                app_logger.info(f"  Legs: {len(result.get('legs', []))}")
                app_logger.info(f"  (Dijkstra took ~109s for this route)")
            else:
                app_logger.warning(f"✗ FAILED: {result.get('detail')}")
        else:
            app_logger.error(f"Stop not found: source={source_stop is not None}, dest={dest_stop is not None}")
        
        # Test data loading performance
        app_logger.info("=" * 60)
        app_logger.info("DATA LOADING PERFORMANCE TEST")
        app_logger.info("=" * 60)
        
        t0 = time.time()
        data = get_transit_data(db, force_reload=True)
        elapsed_ms = (time.time() - t0) * 1000
        
        app_logger.info(f"TransitData loaded in {elapsed_ms:.2f}ms")
        app_logger.info(f"  Routes: {len(data.routes)}")
        app_logger.info(f"  Total trips: {sum(len(r.trips) for r in data.routes.values())}")
        app_logger.info(f"  Routes by stop index: {len(data.routes_by_stop)}")
        
        app_logger.info("=" * 60)
        app_logger.info("TEST SUMMARY")
        app_logger.info("=" * 60)
        app_logger.info("RAPTOR routing integration test completed")
        app_logger.info("Expected: Both test cases should complete in < 1000ms")
        app_logger.info("Expected: Test Case 2 should match Dijkstra result but much faster")
        
    finally:
        db.close()


if __name__ == "__main__":
    test_raptor_routing()
