import sys
import os
import json
import logging

# Setup path so we can import backend
backend_dir = os.path.abspath('backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.database.models import GTFSStop
from fastapi.testclient import TestClient
from app.main import app

logging.basicConfig(level=logging.INFO)

# 1. 12th Block Nagarabhavi → Nayandahalli
# 2. 1st Stage 3rd Block Nagarabhavi → Banashankari Bus Station
# 3. Banashankari → Majestic
# 4. Nagarabhavi → Kengeri

def get_stop_id_by_name(db: Session, name_like: str) -> str:
    # Use ILIKE for case-insensitive search
    stops = db.query(GTFSStop).filter(GTFSStop.stop_name.ilike(f"%{name_like}%")).all()
    if not stops:
        raise ValueError(f"Stop matching '{name_like}' not found")
    # Return the first one
    return stops[0].stop_id

def main():
    client = TestClient(app)
    db = SessionLocal()
    
    try:
        routes = [
            ("12th Block Nagarabhavi", "Nayandahalli"),
            ("1st Stage 3rd Block Nagarabhavi", "Banashankari"),
            ("Banashankari", "Majestic"),
            ("Nagarabhavi", "Kengeri"),
        ]
        
        results = []
        for src_name, dst_name in routes:
            src_id = get_stop_id_by_name(db, src_name)
            dst_id = get_stop_id_by_name(db, dst_name)
            print(f"Testing route: {src_name} ({src_id}) -> {dst_name} ({dst_id})")
            
            response = client.get(f"/api/navigation/plan?source_id={src_id}&destination_id={dst_id}")
            if response.status_code != 200:
                print(f"FAILED: {response.status_code} - {response.text}")
                continue
                
            data = response.json()
            # Verify:
            # - distance must equal actual route geometry distance (we can't easily check actual here, but we check if > 0)
            # - travel time must originate from schedule/ETA logic (eta_minutes > 0)
            # - fare must come from backend calculation (Wait, fare is missing in the api response payload in navigation.py!)
            # - stop count must equal actual returned stop list
            
            poly_len = len(data.get("polyline", []))
            stops_len = len(data.get("stops", []))
            
            # Print the results
            print(f"  route_id: {data.get('route_id')}")
            print(f"  distance_km: {data.get('distance_km')}")
            print(f"  eta_minutes: {data.get('eta_minutes')}")
            print(f"  fare: {data.get('fare')} (Wait, is it returned?)")
            print(f"  transfers: {data.get('transfers')}")
            print(f"  polyline coords count: {poly_len}")
            print(f"  stops list count: {stops_len}")
            print("-" * 40)
            
    finally:
        db.close()

if __name__ == "__main__":
    main()
