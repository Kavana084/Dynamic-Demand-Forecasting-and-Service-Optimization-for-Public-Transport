import sys
sys.path.insert(0, "f:/transit-ai-system/backend")

from app.database.connection import SessionLocal
from app.database.models import GTFSStopTime, GTFSTrip

db = SessionLocal()
try:
    routes_seen = set()
    trips = db.query(GTFSTrip).all()
    print("ROUTE_ID | SOURCE_ID | DEST_ID | MID_ID")
    for trip in trips:
        if trip.route_id in routes_seen:
            continue
        routes_seen.add(trip.route_id)
        
        stops = db.query(GTFSStopTime).filter(GTFSStopTime.trip_id == trip.trip_id).order_by(GTFSStopTime.stop_sequence).all()
        if not stops: continue
        source = stops[0].stop_id
        dest = stops[-1].stop_id
        mid = stops[len(stops)//2].stop_id
        
        print(f"{trip.route_id} | {source} | {dest} | {mid}")
        if len(routes_seen) >= 10:
            break
finally:
    db.close()
