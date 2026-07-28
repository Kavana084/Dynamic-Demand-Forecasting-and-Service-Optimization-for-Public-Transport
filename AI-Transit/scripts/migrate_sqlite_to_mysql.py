import sqlite3
import pandas as pd
from sqlalchemy import create_engine
import os
import sys

# Add backend directory to path to import database models
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend'))
from database.connection import Base, engine, DATABASE_URL

def migrate_data():
    print("--- Starting Database Migration: SQLite -> MySQL ---")
    
    sqlite_db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "transit_data.db")
    
    if not os.path.exists(sqlite_db_path):
        print(f"Error: SQLite database not found at {sqlite_db_path}")
        return

    # 1. Ensure MySQL tables exist
    print(f"Connecting to MySQL: {DATABASE_URL}")
    Base.metadata.create_all(bind=engine)
    print("MySQL tables created/verified.")

    # 2. Connect to SQLite and fetch data
    print("Reading data from SQLite...")
    sqlite_conn = sqlite3.connect(sqlite_db_path)
    
    try:
        df = pd.read_sql_query("SELECT * FROM transit_observations", sqlite_conn)
        sqlite_count = len(df)
        print(f"Found {sqlite_count} records in SQLite.")
    except Exception as e:
        print(f"Error reading SQLite: {e}")
        return
    finally:
        sqlite_conn.close()
        
    if df.empty:
        print("No data to migrate.")
        return
        
    # 3. Clean up the dataframe to match MySQL schema if necessary
    # ID is auto-increment in MySQL, we can drop it to let MySQL handle it,
    # or keep it if we want to preserve exact IDs. We'll drop to avoid PK conflicts
    # if the table already has data.
    if 'id' in df.columns:
        df = df.drop(columns=['id'])
        
    # Ensure datetime format is correct for MySQL
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])

    # 4. Write to MySQL using SQLAlchemy engine
    print("Migrating data to MySQL (this may take a few minutes for large datasets)...")
    try:
        df.to_sql(name='transit_observations', con=engine, if_exists='append', index=False, chunksize=10000)
        print("Data successfully migrated to MySQL!")
        
        # Validate count
        mysql_count = pd.read_sql_query("SELECT COUNT(*) as count FROM transit_observations", engine).iloc[0]['count']
        print(f"Validation: SQLite records={sqlite_count}, MySQL total records={mysql_count}")
        
    except Exception as e:
        print(f"Error writing to MySQL: {e}")

if __name__ == "__main__":
    migrate_data()
