import os, sys
sys.path.insert(0, 'backend')
os.chdir('backend')
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv('POSTGRES_DATABASE_URL')
print(f"Connecting to: {DATABASE_URL[:50]}...")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name"))
    tables = [row[0] for row in result]
    print('ALL TABLES:', tables)
    
    # Check for journey/trip/history related tables
    trip_tables = [t for t in tables if any(kw in t.lower() for kw in ['journey', 'trip', 'route_plan', 'search', 'history', 'plan', 'request', 'result'])]
    print('TRIP-RELATED TABLES:', trip_tables)
    
    # Check users table structure
    if 'users' in tables:
        result2 = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='users' AND table_schema='public'"))
        print('USERS columns:', [(r[0], r[1]) for r in result2])
    
    print('DONE')
