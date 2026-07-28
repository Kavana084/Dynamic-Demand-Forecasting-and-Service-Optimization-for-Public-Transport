import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "transit_data.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transit_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            trip_id TEXT,
            route_id TEXT,
            stop_id TEXT,
            stop_sequence INTEGER,
            scheduled_time TEXT,
            hour INTEGER,
            weekday TEXT,
            weather TEXT,
            temperature REAL,
            rainfall REAL,
            delay_minutes REAL,
            congestion_score REAL,
            passenger_count INTEGER
        )
    ''')
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

def insert_observations(records):
    conn = get_connection()
    cursor = conn.cursor()
    
    query = '''
        INSERT INTO transit_observations (
            timestamp, trip_id, route_id, stop_id, stop_sequence, scheduled_time, hour, weekday,
            weather, temperature, rainfall, delay_minutes, congestion_score, passenger_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    
    data_tuples = [
        (
            r.get("timestamp"),
            r.get("trip_id"),
            r.get("route_id"),
            r.get("stop_id"),
            r.get("stop_sequence"),
            r.get("scheduled_time"),
            r.get("hour"),
            r.get("weekday"),
            r.get("weather"),
            r.get("temperature"),
            r.get("rainfall"),
            r.get("delay_minutes"),
            r.get("congestion_score"),
            r.get("passenger_count")
        ) for r in records
    ]
    
    cursor.executemany(query, data_tuples)
    conn.commit()
    conn.close()
    print(f"Inserted {len(records)} observations into database.")

if __name__ == "__main__":
    init_db()
