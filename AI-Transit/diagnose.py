"""
Diagnostic script: inspect DB schema, test auth, and check timestamps.
Run from: f:\transit-ai-system\backend
  python ..\diagnose.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

from dotenv import load_dotenv
load_dotenv('.env')

from app.database.connection import engine
from sqlalchemy import inspect, text

insp = inspect(engine)

print("=" * 60)
print("1. ALL TABLES IN DB")
print("=" * 60)
tables = sorted(insp.get_table_names())
for t in tables:
    print(f"  {t}")

print()
print("=" * 60)
print("2. USERS TABLE SCHEMA")
print("=" * 60)
if 'users' in tables:
    for col in insp.get_columns('users'):
        print(f"  {col['name']:30s}  {str(col['type']):20s}  nullable={col['nullable']}  default={col.get('default')}")
else:
    print("  ERROR: 'users' table NOT FOUND")

print()
print("=" * 60)
print("3. TEST ADMIN LOGIN")
print("=" * 60)
try:
    from app.services.user_service import authenticate_user
    from app.database.connection import SessionLocal
    db = SessionLocal()
    try:
        user = authenticate_user(db, "admin", "admin123")
        if user:
            print(f"  LOGIN SUCCESS: {user}")
        else:
            print("  LOGIN FAILED: authenticate_user returned None")
            # Check if user exists at all
            from app.database.models import User
            u = db.query(User).filter(User.username == "admin").first()
            if u:
                print(f"  User found in DB: id={u.id} username={u.username} role={u.role}")
                print(f"  is_active={getattr(u,'is_active',None)}")
                print(f"  is_locked={getattr(u,'is_locked',None)}")
                print(f"  mfa_enabled={getattr(u,'mfa_enabled',None)}")
            else:
                print("  User 'admin' NOT FOUND in database")
    except Exception as e:
        print(f"  ERROR during auth: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
except Exception as e:
    print(f"  IMPORT ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
print("4. PREDICTION_RECORDS TIMESTAMPS")
print("=" * 60)
with engine.connect() as conn:
    try:
        rows = conn.execute(text("""
            SELECT 
                MIN(timestamp)::date as min_ts,
                MAX(timestamp)::date as max_ts,
                MIN(target_timestamp)::date as min_target,
                MAX(target_timestamp)::date as max_target,
                COUNT(*) as cnt
            FROM prediction_records
        """)).fetchall()
        for r in rows:
            print(f"  count={r[4]}  timestamp: {r[0]} → {r[1]}  target: {r[2]} → {r[3]}")
    except Exception as e:
        print(f"  ERROR: {e}")

print()
print("=" * 60)
print("5. OPTIMIZATION_RESULTS TIMESTAMPS")
print("=" * 60)
with engine.connect() as conn:
    try:
        rows = conn.execute(text("""
            SELECT 
                MIN(timestamp)::date as min_ts,
                MAX(timestamp)::date as max_ts,
                COUNT(*) as cnt,
                COUNT(DISTINCT route_id) as routes
            FROM optimization_results
        """)).fetchall()
        for r in rows:
            print(f"  count={r[2]}  routes={r[3]}  timestamp: {r[0]} → {r[1]}")
    except Exception as e:
        print(f"  ERROR: {e}")

print()
print("=" * 60)
print("6. FORECAST_HISTORY TIMESTAMPS")
print("=" * 60)
with engine.connect() as conn:
    try:
        rows = conn.execute(text("""
            SELECT 
                MIN(target_timestamp)::date as min_target,
                MAX(target_timestamp)::date as max_target,
                COUNT(*) as cnt
            FROM forecast_history
        """)).fetchall()
        for r in rows:
            print(f"  count={r[2]}  target: {r[0]} → {r[1]}")
    except Exception as e:
        print(f"  ERROR (table may not exist): {e}")

print()
print("=" * 60)
print("7. TODAY (UTC) vs DATA WINDOW")
print("=" * 60)
from datetime import datetime
today_utc = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
print(f"  Today UTC (00:00): {today_utc.isoformat()}")

print()
print("=" * 60)
print("8. PIPELINE_VALIDATION DUPLICATE ROUTES CHECK")
print("=" * 60)
# Check if pipeline/validation route is registered more than once in the router
try:
    from app.main import app
    routes = [(r.path, r.methods) for r in app.routes if hasattr(r, 'path') and 'pipeline' in r.path]
    for path, methods in routes:
        print(f"  {methods} {path}")
    if not routes:
        print("  No pipeline routes found")
except Exception as e:
    print(f"  Could not inspect app routes: {e}")

print()
print("DONE")
