import os
import sys
import datetime
import requests
from sqlalchemy.orm import sessionmaker

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.append(base_dir)

from app.database.models import Base, WeatherRecord
from app.database.connection import engine

def backfill_weather(days=7):
    print(f"--- Starting Weather Data Backfill (Past {days} days) ---")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    # Bangalore coordinates
    lat, lon = 12.9716, 77.5946
    end_date = datetime.date.today() - datetime.timedelta(days=1)
    start_date = end_date - datetime.timedelta(days=days-1)
    
    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&hourly=temperature_2m,precipitation,weather_code&timezone=auto"
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        records_to_insert = []
        for i, time_str in enumerate(data['hourly']['time']):
            dt = datetime.datetime.fromisoformat(time_str)
            temp = data['hourly']['temperature_2m'][i]
            precip = data['hourly']['precipitation'][i]
            code = data['hourly']['weather_code'][i]
            
            if code <= 0:
                condition = 'Clear'
            elif code <= 3:
                condition = 'Cloudy'
            else:
                condition = 'Rainy'
                
            # Check if record already exists for this exact hour
            existing = db.query(WeatherRecord).filter(WeatherRecord.timestamp == dt).first()
            if not existing:
                records_to_insert.append(WeatherRecord(
                    timestamp=dt,
                    temperature=temp,
                    condition=condition,
                    precipitation=precip
                ))
                
        if records_to_insert:
            db.bulk_save_objects(records_to_insert)
            db.commit()
            print(f"Successfully backfilled {len(records_to_insert)} historical weather records.")
        else:
            print("No new records to backfill. Database is already up to date for this period.")
            
    except Exception as e:
        db.rollback()
        print(f"Failed to backfill weather data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    backfill_weather()
