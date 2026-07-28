import os
import sqlite3
from data_scheduler import init_db, load_gtfs_data, pipeline_job

def test_pipeline():
    print("--- Starting Automated Test for Data Pipeline ---")
    
    # 1. Initialize DB and Load Data
    init_db()
    load_gtfs_data()
    
    # 2. Trigger pipeline job once
    print("Triggering manual pipeline job run...")
    pipeline_job()
    
    # 3. Assert DB insertion success and validity
    print("\n--- Validating Database ---")
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "transit_data.db")
    
    assert os.path.exists(db_path), "Database file not created."
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM transit_observations ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    
    assert row is not None, "No observations inserted into the database."
    
    print("Most recent inserted row:")
    print(row)
    
    # Validation checks based on schema
    # row index: 
    # 0: id, 1: timestamp, 2: route_id, 3: stop_id, 4: scheduled_time, 
    # 5: hour, 6: weekday, 7: weather, 8: temperature, 9: rainfall, 
    # 10: delay_minutes, 11: congestion_score, 12: passenger_count
    
    assert row[7] is not None, "Weather API data is null"
    assert row[8] >= 0, f"Temperature {row[8]} is unexpectedly low or null"
    assert row[10] >= 0, f"Delay minutes {row[10]} is not computed correctly"
    assert 1.0 <= row[11] <= 10.0, f"Congestion score {row[11]} is out of bounds"
    assert row[12] >= 0, f"Passenger count {row[12]} is negative"
    
    # Optional: check if there are multiple records
    cursor.execute("SELECT COUNT(*) FROM transit_observations")
    count = cursor.fetchone()[0]
    assert count > 0, "No records found overall."
    print(f"Total rows in DB: {count}")
    
    conn.close()
    print("\n✔ All automated tests passed successfully!")

if __name__ == "__main__":
    test_pipeline()
