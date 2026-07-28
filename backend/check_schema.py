import os
import sys
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from app.database.connection import engine

load_dotenv()

DATABASE_URL = os.getenv("POSTGRES_DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: POSTGRES_DATABASE_URL not found in environment")
    sys.exit(1)

SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

print("=" * 80)
print("DATABASE SCHEMA INVESTIGATION")
print("=" * 80)

# Get all tables
result = db.execute(text("""
    SELECT table_name FROM information_schema.tables 
    WHERE table_schema = 'public'
    ORDER BY table_name
"""))
tables = result.fetchall()

print(f"\nTables in database ({len(tables)}):")
for t in tables:
    print(f"  {t[0]}")

# Look for GTFS-related tables
gtfs_tables = [t[0] for t in tables if any(keyword in t[0].lower() for keyword in ['stop', 'route', 'trip', 'gtfs'])]
print(f"\nGTFS-related tables ({len(gtfs_tables)}):")
for t in gtfs_tables:
    print(f"  {t}")

# Get columns for relevant tables
if gtfs_tables:
    print("\n" + "=" * 80)
    print("TABLE STRUCTURES")
    print("=" * 80)
    
    for table in gtfs_tables[:5]:  # Check first 5 GTFS tables
        result = db.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = :table_name
            ORDER BY ordinal_position
        """), {"table_name": table})
        columns = result.fetchall()
        
        print(f"\n{table}:")
        for col in columns:
            print(f"  {col[0]}: {col[1]}")

db.close()
