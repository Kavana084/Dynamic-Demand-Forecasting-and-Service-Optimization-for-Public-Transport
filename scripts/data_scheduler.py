import os
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend'))
from database.connection import SessionLocal, Base, engine
from database.models import TransitObservation
from realtime_feature_engineering import RealTimeFeatureEngineer
# Globals for in-memory cache
GTFS_STOP_TIMES = None

def load_gtfs_data():
    global GTFS_STOP_TIMES
    base_dir = os.path.dirname(os.path.dirname(__file__))
    stop_times_path = os.path.join(base_dir, "DataSet", "real_data", "stop_times.txt")
    
    if os.path.exists(stop_times_path):
        print("Loading GTFS stop_times into memory...")
        # Load a subset of columns to save memory
        GTFS_STOP_TIMES = pd.read_csv(stop_times_path, usecols=['trip_id', 'arrival_time', 'departure_time', 'stop_id', 'stop_sequence'])
        
        # We need a route_id. If trips.txt exists, we can merge it.
        trips_path = os.path.join(base_dir, "DataSet", "real_data", "trips.txt")
        if os.path.exists(trips_path):
            trips_df = pd.read_csv(trips_path, usecols=['route_id', 'trip_id'])
            GTFS_STOP_TIMES = GTFS_STOP_TIMES.merge(trips_df, on='trip_id', how='left')
        else:
            GTFS_STOP_TIMES['route_id'] = "UNKNOWN"
            
        print(f"Loaded {len(GTFS_STOP_TIMES)} stop times.")
    else:
        print(f"Warning: GTFS stop_times.txt not found at {stop_times_path}. Using mock data for active trips.")
        GTFS_STOP_TIMES = pd.DataFrame(columns=['trip_id', 'arrival_time', 'departure_time', 'stop_id', 'stop_sequence', 'route_id'])

def get_active_trips(current_time):
    """
    Returns a DataFrame of GTFS stop_times that are scheduled within a 10 minute window 
    of the current time.
    """
    if GTFS_STOP_TIMES is None or GTFS_STOP_TIMES.empty:
        # Mocking active trips if GTFS missing
        return pd.DataFrame([
            {"route_id": "ROUTE1", "stop_id": "STOP1", "arrival_time": current_time.strftime("%H:%M:%S")},
            {"route_id": "ROUTE2", "stop_id": "STOP2", "arrival_time": current_time.strftime("%H:%M:%S")}
        ])
        
    # We find trips whose arrival_time is within -5 to +5 minutes of current_time
    # GTFS times can be like 08:30:00 or 25:30:00 (past midnight)
    current_hour = current_time.hour
    current_minute = current_time.minute
    
    # Simple string filtering for the current hour, since parsing 78M string times is slow
    # In production, you'd pre-parse times into minutes past midnight
    hour_str = f"{current_hour:02d}:"
    hour_str_alt = f"{current_hour}:"
    
    # Filter roughly by hour first to speed up
    mask = GTFS_STOP_TIMES['arrival_time'].astype(str).str.startswith(hour_str) | GTFS_STOP_TIMES['arrival_time'].astype(str).str.startswith(hour_str_alt)
    active_df = GTFS_STOP_TIMES[mask].copy()
    
    # We could further filter by minutes, but for generating training data, 
    # capturing all events scheduled in this hour is okay or we can just randomly sample
    # a subset to represent the "current active" snapshot.
    if len(active_df) > 50:
        active_df = active_df.sample(n=50) # limit to 50 active events per cycle to keep DB manageable
        
    return active_df

def fetch_weather_data():
    """Fetch real weather from Open-Meteo for Bangalore."""
    url = "https://api.open-meteo.com/v1/forecast?latitude=12.97&longitude=77.59&current=temperature_2m,weather_code,precipitation"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            curr = data.get("current", {})
            temp = curr.get("temperature_2m", 25.0)
            precip = curr.get("precipitation", 0.0)
            code = curr.get("weather_code", 0)
            
            weather = "Clear"
            if code in [61, 63, 65, 80, 81, 82]: weather = "Rain"
            elif code in [71, 73, 75, 95, 96, 99]: weather = "Heavy Rain"
            elif code in [3, 45, 48]: weather = "Cloudy"
            
            return {
                "temperature": temp,
                "weather": weather,
                "rainfall": precip
            }
    except Exception as e:
        print(f"Weather API error: {e}")
        
    return {"temperature": 25.0, "weather": "Clear", "rainfall": 0.0}

def pipeline_job():
    current_time = datetime.now()
    print(f"\n--- Running Data Pipeline at {current_time.strftime('%Y-%m-%d %H:%M:%S')} ---")
    
    # 1. Fetch weather
    weather_data = fetch_weather_data()
    print(f"Weather: {weather_data['weather']}, Temp: {weather_data['temperature']}C, Rain: {weather_data['rainfall']}mm")
    
    # 2. Get active trips from GTFS
    active_trips_df = get_active_trips(current_time)
    print(f"Found {len(active_trips_df)} active trip events for this time slice.")
    
    # 3. Generate Features
    engineer = RealTimeFeatureEngineer()
    records = engineer.generate_features_for_time_slice(current_time, weather_data, active_trips_df)
    
    # 4. Insert into MySQL via SQLAlchemy
    if records:
        db = SessionLocal()
        try:
            # AUDIT FIX 3 — Upsert missing routes before inserting observations
            unique_routes = set(r.get("route_id") for r in records if r.get("route_id"))
            from database.models import Route
            for r_id in unique_routes:
                existing_route = db.query(Route).filter(Route.route_id == r_id).first()
                if not existing_route:
                    new_route = Route(route_id=r_id, name=f"Route {r_id}", type="Bus")
                    db.add(new_route)
            try:
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"Error upserting routes: {e}")
                
            db_records = []
            for r in records:
                obs = TransitObservation(
                    timestamp=r.get("timestamp"),
                    trip_id=r.get("trip_id"),
                    route_id=r.get("route_id"),
                    stop_id=r.get("stop_id"),
                    stop_sequence=r.get("stop_sequence"),
                    scheduled_time=r.get("scheduled_time"),
                    hour=r.get("hour"),
                    weekday=r.get("weekday"),
                    weather=r.get("weather"),
                    temperature=r.get("temperature"),
                    rainfall=r.get("rainfall"),
                    delay_minutes=r.get("delay_minutes"),
                    congestion_score=r.get("congestion_score"),
                    passenger_count=r.get("passenger_count")
                )
                db_records.append(obs)
            
            db.bulk_save_objects(db_records)
            db.commit()
            print(f"Inserted {len(db_records)} observations into MySQL database.")
        except Exception as e:
            db.rollback()
            print(f"Error inserting into MySQL: {e}")
        finally:
            db.close()
    else:
        print("No active records to insert.")

def start_scheduler():
    # Ensure MySQL tables exist
    Base.metadata.create_all(bind=engine)
    print("MySQL tables verified.")
    load_gtfs_data()
    
    scheduler = BackgroundScheduler()
    # Run the job every 5 minutes
    scheduler.add_job(pipeline_job,trigger='interval',minutes=5,max_instances=1,coalesce=True,misfire_grace_time=120)
    scheduler.start()
    
    print("\nBackgroundScheduler started. Pipeline will run every 5 minutes.")
    print("Press Ctrl+C to exit.")
    
    try:
        # Keep the main thread alive since BackgroundScheduler runs in background
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("\nScheduler shut down successfully.")

if __name__ == "__main__":
    start_scheduler()
