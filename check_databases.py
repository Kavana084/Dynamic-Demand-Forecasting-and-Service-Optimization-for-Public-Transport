import sqlite3
import os

databases = [
    "F:\\transit-ai-system\\transit_data.db",
    "F:\\transit-ai-system\\backend\\transit.db",
    "F:\\transit-ai-system\\backend\\transit_ai.db"
]

for db_path in databases:
    if not os.path.exists(db_path):
        print(f"\n{db_path}: FILE NOT FOUND")
        continue
    
    print(f"\n{'='*80}")
    print(f"Database: {db_path}")
    print(f"Size: {os.path.getsize(db_path)} bytes")
    print(f"{'='*80}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"\nTables ({len(tables)}): {sorted(tables)}")
        
        # Check specific tables
        key_tables = ['gtfs_stops', 'gtfs_stop_times', 'forecast_history', 'optimization_results', 'users', 'routes']
        for table in key_tables:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  {table}: {count} rows")
            else:
                print(f"  {table}: NOT FOUND")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
