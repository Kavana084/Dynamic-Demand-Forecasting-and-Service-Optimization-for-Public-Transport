import sqlite3

conn = sqlite3.connect('transit_data.db')
cursor = conn.cursor()

print("=" * 80)
print("STEP 1: FIND STOP IDs FOR ORIGIN AND DESTINATION")
print("=" * 80)

print("\nNagarabhavi stops:")
cursor.execute("SELECT stop_id, stop_name FROM stops WHERE stop_name LIKE '%Nagarabhavi%' ORDER BY stop_name")
rows = cursor.fetchall()
for r in rows[:20]:
    print(f"  {r[0]}: {r[1]}")

print("\nAmbedkar stops:")
cursor.execute("SELECT stop_id, stop_name FROM stops WHERE stop_name LIKE '%Ambedkar%' ORDER BY stop_name")
rows = cursor.fetchall()
for r in rows[:20]:
    print(f"  {r[0]}: {r[1]}")

print("\n" + "=" * 80)
print("STEP 2: FIND ROUTES CONTAINING 12th Block Nagarabhavi")
print("=" * 80)

# Find the specific stop ID for 12th Block Nagarabhavi
cursor.execute("SELECT stop_id FROM stops WHERE stop_name LIKE '%12th%Nagarabhavi%'")
nagarabhavi_stops = cursor.fetchall()
print(f"\nFound {len(nagarabhavi_stops)} stops matching '12th Block Nagarabhavi':")
for r in Nagarabhavi_stops:
    print(f"  {r[0]}")

if Nagarabhavi_stops:
    stop_id = Nagarabhavi_stops[0][0]
    print(f"\nUsing stop_id: {stop_id} for route analysis")
    
    # Find all routes containing this stop
    cursor.execute("""
        SELECT DISTINCT r.route_id, r.route_long_name, t.trip_id
        FROM routes r
        JOIN trips t ON r.route_id = t.route_id
        JOIN stop_times st ON t.trip_id = st.trip_id
        WHERE st.stop_id = ?
        ORDER BY r.route_long_name
    """, (stop_id,))
    routes = cursor.fetchall()
    print(f"\nRoutes containing 12th Block Nagarabhavi ({len(routes)} routes):")
    for r in routes[:10]:
        print(f"  Route ID: {r[0]}, Name: {r[1]}, Trip ID: {r[2]}")

print("\n" + "=" * 80)
print("STEP 3: FIND ROUTES CONTAINING Dr. Ambedkar Institute of Technology")
print("=" * 80)

cursor.execute("SELECT stop_id FROM stops WHERE stop_name LIKE '%Ambedkar%'")
ambedkar_stops = cursor.fetchall()
print(f"\nFound {len(ambedkar_stops)} stops matching 'Ambedkar':")
for r in ambedkar_stops:
    print(f"  {r[0]}")

if ambedkar_stops:
    stop_id = ambedkar_stops[0][0]
    print(f"\nUsing stop_id: {stop_id} for route analysis")
    
    # Find all routes containing this stop
    cursor.execute("""
        SELECT DISTINCT r.route_id, r.route_long_name, t.trip_id
        FROM routes r
        JOIN trips t ON r.route_id = t.route_id
        JOIN stop_times st ON t.trip_id = st.trip_id
        WHERE st.stop_id = ?
        ORDER BY r.route_long_name
    """, (stop_id,))
    routes = cursor.fetchall()
    print(f"\nRoutes containing Dr. Ambedkar Institute ({len(routes)} routes):")
    for r in routes[:10]:
        print(f"  Route ID: {r[0]}, Name: {r[1]}, Trip ID: {r[2]}")

print("\n" + "=" * 80)
print("STEP 4: FIND SHARED ROUTES (DIRECT ROUTES)")
print("=" * 80)

if Nagarabhavi_stops and ambedkar_stops:
    nagarabhavi_id = Nagarabhavi_stops[0][0]
    ambedkar_id = ambedkar_stops[0][0]
    
    cursor.execute("""
        SELECT DISTINCT r.route_id, r.route_long_name, t.trip_id
        FROM routes r
        JOIN trips t ON r.route_id = t.route_id
        JOIN stop_times st1 ON t.trip_id = st1.trip_id
        JOIN stop_times st2 ON t.trip_id = st2.trip_id
        WHERE st1.stop_id = ? AND st2.stop_id = ?
        ORDER BY r.route_long_name
    """, (nagarabhavi_id, ambedkar_id))
    shared_routes = cursor.fetchall()
    
    print(f"\nShared routes between the two stops ({len(shared_routes)} routes):")
    for r in shared_routes:
        print(f"  Route ID: {r[0]}, Name: {r[1]}, Trip ID: {r[2]}")
        
        # Get stop sequence for this route
        trip_id = r[2]
        cursor.execute("""
            SELECT st.stop_id, s.stop_name, st.stop_sequence
            FROM stop_times st
            JOIN stops s ON st.stop_id = s.stop_id
            WHERE st.trip_id = ?
            ORDER BY st.stop_sequence
        """, (trip_id,))
        stops = cursor.fetchall()
        
        # Find indices of origin and destination
        origin_idx = next((i for i, s in enumerate(stops) if s[0] == nagarabhavi_id), None)
        dest_idx = next((i for i, s in enumerate(stops) if s[0] == ambedkar_id), None)
        
        if origin_idx is not None and dest_idx is not None:
            segment_length = dest_idx - origin_idx + 1
            print(f"    Origin at index: {origin_idx}, Destination at index: {dest_idx}")
            print(f"    Segment length: {segment_length} stops")
            
            if origin_idx < dest_idx:
                print(f"    Segment stops:")
                for i in range(origin_idx, dest_idx + 1):
                    print(f"      [{i}] {stops[i][1]} ({stops[i][0]})")
            else:
                print(f"    WARNING: Destination comes before origin in route!")

conn.close()
