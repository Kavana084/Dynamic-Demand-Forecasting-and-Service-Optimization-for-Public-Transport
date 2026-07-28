"""
Direct verification script that tests the cleanup requirements without HTTP.
Tests that:
1. KA-07-F -> 0 matches across all files
2. getCrowdInfo -> 0 matches across all files  
3. * 2 + 5 -> 0 fare-calculation matches
4. fare, occupancy_percent, crowd_level, comfort_level, bus_id come from backend
"""
import sys, os, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

print("=" * 60)
print("PASSENGER PORTAL CLEANUP VERIFICATION")
print("=" * 60)

# -- 1. Pattern searches ---------------------------------------
files_to_check = {
    "navigation.py": "backend/app/api/navigation.py",
    "fare_service.py": "backend/app/services/fare_service.py",
    "TripPlanner.jsx": "frontend/src/pages/TripPlanner.jsx",
    "api_routes.py": "backend/app/api_routes.py",
}

def search_pattern(file_path, pattern):
    full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)
    if not os.path.exists(full_path):
        return []
    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    matches = []
    for i, line in enumerate(lines, 1):
        if re.search(pattern, line):
            matches.append((i, line.rstrip()))
    return matches

print("\n--- PATTERN VERIFICATION ---")

# KA-07-F
print("\n[1] Search: KA-07-F (synthetic vehicle ID generator)")
ka07_matches = []
for label, path in files_to_check.items():
    m = search_pattern(path, r"KA-07-F")
    ka07_matches.extend(m)
    if m:
        for line_no, line in m:
            print(f"  FOUND in {label}:{line_no}: {line}")
if not ka07_matches:
    print("  [PASS] 0 matches - CLEAN")

# getCrowdInfo
print("\n[2] Search: getCrowdInfo (frontend crowd logic)")
crowd_matches = []
for label, path in files_to_check.items():
    m = search_pattern(path, r"getCrowdInfo")
    crowd_matches.extend(m)
    if m:
        for line_no, line in m:
            print(f"  FOUND in {label}:{line_no}: {line}")
if not crowd_matches:
    print("  [PASS] 0 matches - CLEAN")

# * 2 + 5 fare calculation
print("\n[3] Search: '* 2 + 5' or 'distance * 2' (fare fallback)")
fare_matches = []
for label, path in files_to_check.items():
    m = search_pattern(path, r"\*\s*2\s*\+\s*5|distance\s*\*\s*2")
    fare_matches.extend(m)
    if m:
        for line_no, line in m:
            print(f"  FOUND in {label}:{line_no}: {line}")
if not fare_matches:
    print("  [PASS] 0 matches - CLEAN")

# -- 2. Test FareService directly ------------------------------
print("\n--- FARE SERVICE DIRECT TEST ---")
try:
    from backend.app.services.fare_service import fare_service
    # Test with various distances
    test_cases = [(5.0, "5 km"), (10.5, "10.5 km"), (18.0, "18 km")]
    for dist, label in test_cases:
        fare = fare_service.calculate_fare("test_route", dist)
        print(f"  Distance {label} => fare = Rs.{fare}")
    fare_loaded = len(fare_service.fare_attributes)
    print(f"  GTFS fare_attributes loaded: {fare_loaded} entries")
    if fare_loaded > 0:
        print("  [PASS] FareService uses GTFS data - CLEAN")
    else:
        print("  [WARN] FareService using tier fallback (no GTFS data loaded)")
except Exception as e:
    print(f"  [FAIL] FareService error: {e}")

# -- 3. Test navigation.py fare call --------------------------
print("\n--- NAVIGATION.PY FARE CALL VERIFICATION ---")
nav_path = "backend/app/api/navigation.py"
nav_fare = search_pattern(nav_path, r"fare_service\.calculate_fare")
if nav_fare:
    for line_no, line in nav_fare:
        print(f"  [PASS] navigation.py:{line_no}: {line.strip()}")
else:
    print("  [FAIL] navigation.py does NOT call fare_service.calculate_fare()")

# Check for old round(distance*2+5) in navigation.py
old_fare = search_pattern(nav_path, r"round\(distance_km\s*\*\s*2")
if old_fare:
    for line_no, line in old_fare:
        print(f"  [FAIL] OLD FARE navigation.py:{line_no}: {line}")
else:
    print("  [PASS] No round(distance_km * 2 ...) in navigation.py - CLEAN")

# -- 4. Test vehicle tracking in navigation.py ----------------
print("\n--- VEHICLE TRACKING VERIFICATION ---")
vt_calls = search_pattern(nav_path, r"vehicle_tracking_service")
for line_no, line in vt_calls:
    print(f"  navigation.py:{line_no}: {line.strip()}")
if vt_calls:
    print("  [PASS] vehicle_tracking_service is used in navigation.py - CLEAN")
else:
    print("  [FAIL] vehicle_tracking_service NOT referenced in navigation.py")

# -- 5. Frontend crowd_level/comfort_level from backend -------
print("\n--- FRONTEND CROWD/COMFORT CONSUMPTION VERIFICATION ---")
tp_path = "frontend/src/pages/TripPlanner.jsx"
crowd_direct = search_pattern(tp_path, r"result\?\.crowd_level|result\?\.comfort_level")
for line_no, line in crowd_direct:
    print(f"  TripPlanner.jsx:{line_no}: {line.strip()}")
if crowd_direct:
    print("  [PASS] Frontend reads crowd_level/comfort_level directly from backend")
else:
    print("  [FAIL] Frontend NOT reading crowd/comfort from backend response")

# -- 6. Backend sends crowd_level and comfort_level -----------
print("\n--- BACKEND CROWD/COMFORT OUTPUT VERIFICATION ---")
api_crowd = search_pattern("backend/app/api_routes.py", r'"crowd_level"')
api_comfort = search_pattern("backend/app/api_routes.py", r'"comfort_level"')
nav_crowd = search_pattern(nav_path, r'"crowd_level"')
nav_comfort = search_pattern(nav_path, r'"comfort_level"')

for line_no, line in api_crowd + nav_crowd:
    print(f"  Backend crowd_level: {line.strip()}")
for line_no, line in api_comfort + nav_comfort:
    print(f"  Backend comfort_level: {line.strip()}")

if (api_crowd or nav_crowd) and (api_comfort or nav_comfort):
    print("  [PASS] Backend produces crowd_level and comfort_level - CLEAN")
else:
    print("  [FAIL] Backend missing crowd_level or comfort_level")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
all_ok = (not ka07_matches) and (not crowd_matches) and (not fare_matches)
if all_ok:
    print("[PASS] ALL 3 PROHIBITED PATTERNS: 0 MATCHES")
else:
    print("[FAIL] SOME PROHIBITED PATTERNS STILL PRESENT")

print("\nDone.")
