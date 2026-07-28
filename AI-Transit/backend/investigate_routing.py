"""
Routing Regression Investigation Script

This script investigates why the routing engine selected a 20-stop journey
instead of a direct 3-4 stop route for:
12th Block Nagarabhavi → Dr. Ambedkar Institute of Technology
"""

import os
import sys
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from app.database.connection import engine

SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

print("=" * 80)
print("STEP 1: FIND STOP IDs FOR ORIGIN AND DESTINATION")
print("=" * 80)

# Find 12th Block Nagarabhavi
print("\nSearching for '12th Block Nagarabhavi':")
result = db.execute(text("""
    SELECT stop_id, stop_name FROM gtfs_stops 
    WHERE stop_name ILIKE '%12th%Nagarabhavi%' 
    ORDER BY stop_name
"""))
nagarabhavi_stops = result.fetchall()
print(f"Found {len(nagarabhavi_stops)} stops:")
for r in nagarabhavi_stops:
    print(f"  {r[0]}: {r[1]}")

# Find Dr. Ambedkar Institute of Technology
print("\nSearching for 'Ambedkar':")
result = db.execute(text("""
    SELECT stop_id, stop_name FROM gtfs_stops 
    WHERE stop_name ILIKE '%Ambedkar%' 
    ORDER BY stop_name
"""))
ambedkar_stops = result.fetchall()
print(f"Found {len(ambedkar_stops)} stops:")
for r in ambedkar_stops:
    print(f"  {r[0]}: {r[1]}")

if not nagarabhavi_stops or not ambedkar_stops:
    print("\nERROR: Could not find one or both stops in database")
    db.close()
    sys.exit(1)

origin_stop_id = nagarabhavi_stops[0][0]
origin_stop_name = nagarabhavi_stops[0][1]
dest_stop_id = ambedkar_stops[0][0]
dest_stop_name = ambedkar_stops[0][1]

print(f"\nSelected:")
print(f"  Origin: {origin_stop_name} ({origin_stop_id})")
print(f"  Destination: {dest_stop_name} ({dest_stop_id})")

print("\n" + "=" * 80)
print("STEP 2: FIND ROUTES CONTAINING ORIGIN STOP")
print("=" * 80)

result = db.execute(text("""
    SELECT DISTINCT r.route_id, t.trip_id
    FROM routes r
    JOIN gtfs_trips t ON r.route_id = t.route_id
    JOIN gtfs_stop_times st ON t.trip_id = st.trip_id
    WHERE st.stop_id = :stop_id
    ORDER BY r.route_id
"""), {"stop_id": origin_stop_id})
origin_routes = result.fetchall()
print(f"\nRoutes containing origin ({len(origin_routes)} routes):")
for r in origin_routes[:15]:
    print(f"  Route ID: {r[0]}, Trip ID: {r[1]}")

print("\n" + "=" * 80)
print("STEP 3: FIND ROUTES CONTAINING DESTINATION STOP")
print("=" * 80)

result = db.execute(text("""
    SELECT DISTINCT r.route_id, t.trip_id
    FROM routes r
    JOIN gtfs_trips t ON r.route_id = t.route_id
    JOIN gtfs_stop_times st ON t.trip_id = st.trip_id
    WHERE st.stop_id = :stop_id
    ORDER BY r.route_id
"""), {"stop_id": dest_stop_id})
dest_routes = result.fetchall()
print(f"\nRoutes containing destination ({len(dest_routes)} routes):")
for r in dest_routes[:15]:
    print(f"  Route ID: {r[0]}, Trip ID: {r[1]}")

print("\n" + "=" * 80)
print("STEP 4: FIND SHARED ROUTES (DIRECT ROUTES)")
print("=" * 80)

origin_route_ids = set(r[0] for r in origin_routes)
dest_route_ids = set(r[0] for r in dest_routes)
shared_route_ids = origin_route_ids & dest_route_ids

print(f"\nOrigin route IDs: {len(origin_route_ids)}")
print(f"Destination route IDs: {len(dest_route_ids)}")
print(f"Shared route IDs: {len(shared_route_ids)}")

if shared_route_ids:
    print(f"\nShared routes ({len(shared_route_ids)}):")
    for route_id in list(shared_route_ids)[:10]:
        result = db.execute(text("""
            SELECT r.route_id, t.trip_id
            FROM routes r
            JOIN gtfs_trips t ON r.route_id = t.route_id
            WHERE r.route_id = :route_id
            LIMIT 1
        """), {"route_id": route_id})
        route_info = result.fetchone()
        print(f"  Route ID: {route_info[0]}, Trip ID: {route_info[1]}")
        
        # Get stop sequence for this trip
        trip_id = route_info[1]
        result = db.execute(text("""
            SELECT st.stop_id, s.stop_name, st.stop_sequence
            FROM gtfs_stop_times st
            JOIN gtfs_stops s ON st.stop_id = s.stop_id
            WHERE st.trip_id = :trip_id
            ORDER BY st.stop_sequence
        """), {"trip_id": trip_id})
        stops = result.fetchall()
        
        # Find indices
        origin_idx = next((i for i, s in enumerate(stops) if s[0] == origin_stop_id), None)
        dest_idx = next((i for i, s in enumerate(stops) if s[0] == dest_stop_id), None)
        
        if origin_idx is not None and dest_idx is not None:
            segment_length = dest_idx - origin_idx + 1
            print(f"    Origin at sequence: {stops[origin_idx][2]}, Destination at sequence: {stops[dest_idx][2]}")
            print(f"    Segment length: {segment_length} stops")
            
            if origin_idx < dest_idx:
                print(f"    Segment stops:")
                for i in range(origin_idx, dest_idx + 1):
                    print(f"      [{i}] {stops[i][1]} ({stops[i][0]})")
            else:
                print(f"    WARNING: Destination comes before origin in route!")
else:
    print("\nNO SHARED ROUTES FOUND - Direct route does not exist in GTFS data")
    print("This explains why transfers are required")

print("\n" + "=" * 80)
print("STEP 5: CHECK IF STOPS ARE CONNECTED IN GRAPH")
print("=" * 80)

# This would require building the graph, which we can do via the routing service
print("\nTo check graph connectivity, we need to use the routing service.")
print("This will be done in the next step.")

db.close()

print("\n" + "=" * 80)
print("INVESTIGATION SUMMARY")
print("=" * 80)
print(f"Origin: {origin_stop_name} ({origin_stop_id})")
print(f"Destination: {dest_stop_name} ({dest_stop_id})")
print(f"Shared routes in GTFS: {len(shared_route_ids)}")
print(f"Direct route available: {'YES' if shared_route_ids else 'NO'}")
