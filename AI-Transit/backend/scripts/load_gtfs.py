import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add backend to sys path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.append(base_dir)

from app.database.models import Base, Route, GTFSStop, GTFSTrip, GTFSStopTime
from app.database.connection import engine, get_db

def load_gtfs_data():
    print("--- Starting GTFS Data Ingestion ---")
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Try to add columns to routes table in case it already existed before models.py was updated
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE routes ADD COLUMN route_short_name VARCHAR(50)"))
            conn.commit()
    except Exception:
        pass
        
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE routes ADD COLUMN route_long_name VARCHAR(255)"))
            conn.commit()
    except Exception:
        pass
    
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    
    dataset_dir = os.path.join(os.path.dirname(base_dir), 'DataSet', 'real_data')
    
    if not os.path.exists(dataset_dir):
        print(f"Error: Dataset directory not found at {dataset_dir}")
        return
        
    try:
        # 1. Load Routes
        print("Loading routes.txt...")
        routes_df = pd.read_csv(os.path.join(dataset_dir, 'routes.txt'))
        routes_to_insert = []
        for _, row in routes_df.iterrows():
            # Only add if it doesn't exist to avoid primary key conflicts, 
            # or we can update. For simplicity, we'll merge.
            existing = db.query(Route).filter(Route.route_id == str(row['route_id'])).first()
            if not existing:
                routes_to_insert.append(Route(
                    route_id=str(row['route_id']),
                    name=row.get('route_long_name', ''),
                    type='Bus',
                    route_short_name=str(row.get('route_short_name', '')),
                    route_long_name=str(row.get('route_long_name', ''))
                ))
            else:
                existing.route_short_name = str(row.get('route_short_name', ''))
                existing.route_long_name = str(row.get('route_long_name', ''))
                
        if routes_to_insert:
            db.bulk_save_objects(routes_to_insert)
        db.commit()
        print(f"Inserted/Updated Routes.")
        
        # 2. Load Stops
        print("Loading stops.txt...")
        stops_df = pd.read_csv(os.path.join(dataset_dir, 'stops.txt'))
        stops_to_insert = []
        # Clear existing GTFS stops to avoid duplicates (this is an initialization script)
        db.query(GTFSStop).delete()
        for _, row in stops_df.iterrows():
            stops_to_insert.append(GTFSStop(
                stop_id=str(row['stop_id']),
                stop_name=str(row.get('stop_name', '')),
                stop_lat=float(row.get('stop_lat', 0.0)),
                stop_lon=float(row.get('stop_lon', 0.0))
            ))
        db.bulk_save_objects(stops_to_insert)
        db.commit()
        print(f"Inserted {len(stops_to_insert)} Stops.")
        
        # 3. Load Trips
        print("Loading trips.txt...")
        trips_df = pd.read_csv(os.path.join(dataset_dir, 'trips.txt'))
        trips_to_insert = []
        db.query(GTFSTrip).delete()
        for _, row in trips_df.iterrows():
            trips_to_insert.append(GTFSTrip(
                trip_id=str(row['trip_id']),
                route_id=str(row['route_id']),
                service_id=str(row.get('service_id', '')),
                trip_headsign=str(row.get('trip_headsign', ''))
            ))
        db.bulk_save_objects(trips_to_insert)
        db.commit()
        print(f"Inserted {len(trips_to_insert)} Trips.")
        
        # 4. Load Stop Times
        print("Loading stop_times.txt... (This might take a while)")
        stop_times_df = pd.read_csv(os.path.join(dataset_dir, 'stop_times.txt'))
        db.query(GTFSStopTime).delete()
        
        # Use bulk insert core for performance
        stop_times_dicts = stop_times_df[['trip_id', 'stop_id', 'arrival_time', 'departure_time', 'stop_sequence']].to_dict(orient='records')
        # Convert all to string/int as needed
        for d in stop_times_dicts:
            d['trip_id'] = str(d['trip_id'])
            d['stop_id'] = str(d['stop_id'])
            d['arrival_time'] = str(d['arrival_time'])
            d['departure_time'] = str(d['departure_time'])
            d['stop_sequence'] = int(d['stop_sequence'])
            
        # Batch insert
        batch_size = 10000
        for i in range(0, len(stop_times_dicts), batch_size):
            db.bulk_insert_mappings(GTFSStopTime, stop_times_dicts[i:i+batch_size])
        db.commit()
        print(f"Inserted {len(stop_times_dicts)} Stop Times.")
        
        print("--- GTFS Data Ingestion Complete ---")
        
    except Exception as e:
        db.rollback()
        print(f"Error during ingestion: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    load_gtfs_data()
