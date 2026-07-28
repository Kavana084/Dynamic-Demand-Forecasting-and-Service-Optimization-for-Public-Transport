import sqlite3
import glob

dbs = glob.glob('F:/transit-ai-system/**/*.db', recursive=True)
for db in dbs:
    try:
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Database: {db}")
        for table in tables:
            print(f" - {table[0]}")
            
            # Print row counts for tables of interest
            if table[0] in ['gtfs_stops', 'gtfs_stop_times', 'forecast_history', 'optimization_results', 'users']:
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]};")
                count = cursor.fetchone()[0]
                print(f"    -> Count: {count}")
                
        conn.close()
    except Exception as e:
        print(f"Error reading {db}: {e}")
