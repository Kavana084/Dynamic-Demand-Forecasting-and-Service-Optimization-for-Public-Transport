"""
Phase 1 Validation Script — Transit AI System
Run from workspace root:
    .venv\Scripts\python.exe validate_phase1.py

Checks:
  A. Live DB column schemas for users + five KPI tables
  B. Timestamp ranges in each KPI table
  C. Row counts
  D. Whether mfa_secret exists in the DB
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

from dotenv import load_dotenv
load_dotenv(".env")

from app.database.connection import engine
from sqlalchemy import inspect, text

insp = inspect(engine)
all_tables = set(insp.get_table_names())

SEP  = "=" * 65
SEP2 = "-" * 65

# ──────────────────────────────────────────────────────────────────
# A. USERS TABLE SCHEMA
# ──────────────────────────────────────────────────────────────────
print(SEP)
print("A. USERS TABLE — LIVE SCHEMA")
print(SEP)
if "users" in all_tables:
    for c in insp.get_columns("users"):
        print(f"  {c['name']:30s}  {str(c['type']):25s}  nullable={c['nullable']}")
else:
    print("  ERROR: 'users' table not found in DB")

# Check critical columns
REQUIRED_USER_COLS = {"is_active", "is_locked", "mfa_enabled", "mfa_secret"}
live_user_cols = {c["name"] for c in insp.get_columns("users")} if "users" in all_tables else set()
missing_user_cols = REQUIRED_USER_COLS - live_user_cols
print()
print(f"  Required columns: {sorted(REQUIRED_USER_COLS)}")
print(f"  Live columns:     {sorted(live_user_cols & REQUIRED_USER_COLS)}")
print(f"  MISSING:          {sorted(missing_user_cols) or 'NONE — all present'}")

# ──────────────────────────────────────────────────────────────────
# B. KPI TABLES — SCHEMAS
# ──────────────────────────────────────────────────────────────────
KPI_TABLES = [
    "forecast_history",
    "optimization_results",
    "demand_history",
    "route_plan_logs",
    "prediction_records",
]

print()
print(SEP)
print("B. KPI TABLE SCHEMAS")
print(SEP)

for tbl in KPI_TABLES:
    print(f"\n  [{tbl}]  {'(EXISTS)' if tbl in all_tables else '(NOT FOUND)'}")
    if tbl not in all_tables:
        continue
    for c in insp.get_columns(tbl):
        print(f"    {c['name']:35s}  {str(c['type']):25s}  nullable={c['nullable']}")

# ──────────────────────────────────────────────────────────────────
# C. TIMESTAMP RANGES + ROW COUNTS
# ──────────────────────────────────────────────────────────────────
print()
print(SEP)
print("C. TIMESTAMP RANGES & ROW COUNTS")
print(SEP)

TABLE_QUERIES = {
    "forecast_history": {
        "count": "SELECT COUNT(*) FROM forecast_history",
        "range": """
            SELECT
                MIN(target_timestamp) AS min_target,
                MAX(target_timestamp) AS max_target,
                MIN(generated_at)     AS min_generated,
                MAX(generated_at)     AS max_generated
            FROM forecast_history
        """,
    },
    "optimization_results": {
        "count": "SELECT COUNT(*) FROM optimization_results",
        "range": """
            SELECT
                MIN(timestamp) AS min_ts,
                MAX(timestamp) AS max_ts,
                COUNT(DISTINCT route_id) AS distinct_routes,
                COUNT(DISTINCT model_version) AS distinct_model_versions
            FROM optimization_results
        """,
    },
    "demand_history": {
        "count": "SELECT COUNT(*) FROM demand_history",
        "range": """
            SELECT
                MIN(timestamp) AS min_ts,
                MAX(timestamp) AS max_ts,
                COUNT(DISTINCT route_id) AS distinct_routes
            FROM demand_history
        """,
    },
    "route_plan_logs": {
        "count": "SELECT COUNT(*) FROM route_plan_logs",
        "range": """
            SELECT
                MIN(created_at) AS min_created,
                MAX(created_at) AS max_created
            FROM route_plan_logs
        """,
    },
    "prediction_records": {
        "count": "SELECT COUNT(*) FROM prediction_records",
        "range": """
            SELECT
                MIN(timestamp)        AS min_ts,
                MAX(timestamp)        AS max_ts,
                MIN(target_timestamp) AS min_target,
                MAX(target_timestamp) AS max_target,
                COUNT(DISTINCT route_id) AS distinct_routes,
                COUNT(DISTINCT model_version) AS distinct_model_versions
            FROM prediction_records
        """,
    },
}

from datetime import datetime, timezone
now_utc = datetime.now(timezone.utc)
today_utc_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
print(f"\n  Server UTC now: {now_utc.isoformat()}")
print(f"  Today UTC window: {today_utc_start.isoformat()} → +24h\n")

with engine.connect() as conn:
    for tbl, queries in TABLE_QUERIES.items():
        if tbl not in all_tables:
            print(f"  {tbl}: SKIPPED (table missing)\n")
            continue
        try:
            cnt = conn.execute(text(queries["count"])).scalar()
            print(f"  {tbl}: {cnt} rows")
            row = conn.execute(text(queries["range"])).fetchone()
            if row:
                for k, v in zip(row._fields, row):
                    print(f"    {k}: {v}")
            print()
        except Exception as e:
            print(f"  {tbl}: ERROR — {e}\n")

# ──────────────────────────────────────────────────────────────────
# D. TODAY-WINDOW RECORD CHECK
# ──────────────────────────────────────────────────────────────────
print(SEP)
print("D. TODAY UTC WINDOW RECORD COUNTS (what dashboard currently sees)")
print(SEP)

today_queries = {
    "forecast_history": "SELECT COUNT(*) FROM forecast_history WHERE target_timestamp >= NOW()::date AND target_timestamp < NOW()::date + INTERVAL '1 day'",
    "optimization_results": "SELECT COUNT(*) FROM optimization_results WHERE timestamp >= NOW()::date AND timestamp < NOW()::date + INTERVAL '1 day'",
    "demand_history": "SELECT COUNT(*) FROM demand_history WHERE timestamp >= NOW()::date AND timestamp < NOW()::date + INTERVAL '1 day'",
    "prediction_records": "SELECT COUNT(*) FROM prediction_records WHERE timestamp >= NOW()::date AND timestamp < NOW()::date + INTERVAL '1 day'",
}

with engine.connect() as conn:
    for tbl, q in today_queries.items():
        if tbl not in all_tables:
            print(f"  {tbl}: SKIPPED")
            continue
        try:
            cnt = conn.execute(text(q)).scalar()
            print(f"  {tbl} (today): {cnt}")
        except Exception as e:
            print(f"  {tbl}: ERROR — {e}")

# ──────────────────────────────────────────────────────────────────
# E. LATEST AVAILABLE DATA WINDOW (for KPI fallback recommendation)
# ──────────────────────────────────────────────────────────────────
print()
print(SEP)
print("E. LATEST AVAILABLE DATA — recommended fallback window")
print(SEP)

LATEST_QUERIES = {
    "forecast_history (target_timestamp)":
        "SELECT MAX(target_timestamp)::date FROM forecast_history",
    "optimization_results (timestamp)":
        "SELECT MAX(timestamp)::date FROM optimization_results",
    "prediction_records (timestamp)":
        "SELECT MAX(timestamp)::date FROM prediction_records",
    "demand_history (timestamp)":
        "SELECT MAX(timestamp)::date FROM demand_history",
}

with engine.connect() as conn:
    for label, q in LATEST_QUERIES.items():
        tbl = label.split()[0]
        if tbl not in all_tables:
            print(f"  {label}: SKIPPED")
            continue
        try:
            val = conn.execute(text(q)).scalar()
            print(f"  {label}: {val}")
        except Exception as e:
            print(f"  {label}: ERROR — {e}")

# ──────────────────────────────────────────────────────────────────
# F. OPTIMIZATION_RESULTS MODEL_VERSION DISTRIBUTION
# ──────────────────────────────────────────────────────────────────
print()
print(SEP)
print("F. OPTIMIZATION_RESULTS — model_version distribution")
print(SEP)
if "optimization_results" in all_tables:
    with engine.connect() as conn:
        try:
            rows = conn.execute(text("""
                SELECT model_version, COUNT(*) as cnt
                FROM optimization_results
                GROUP BY model_version
                ORDER BY cnt DESC
            """)).fetchall()
            for r in rows:
                print(f"  model_version={r[0]!r:35s}  count={r[1]}")
        except Exception as e:
            print(f"  ERROR: {e}")

# ──────────────────────────────────────────────────────────────────
# G. ADMIN LOGIN TEST
# ──────────────────────────────────────────────────────────────────
print()
print(SEP)
print("G. AUTHENTICATION TEST — admin/admin123")
print(SEP)
try:
    from app.database.connection import SessionLocal
    from app.database.models import User
    db = SessionLocal()
    try:
        # Direct model query to check if columns exist
        u = db.query(User).filter(User.username == "admin").first()
        if u:
            print(f"  User found:    id={u.id}  username={u.username}  role={u.role}")
            print(f"  is_active:     {getattr(u, 'is_active', 'ATTR_MISSING')}")
            print(f"  is_locked:     {getattr(u, 'is_locked', 'ATTR_MISSING')}")
            print(f"  mfa_enabled:   {getattr(u, 'mfa_enabled', 'ATTR_MISSING')}")
            print(f"  mfa_secret:    {getattr(u, 'mfa_secret', 'ATTR_MISSING')}")
        else:
            print("  User 'admin' NOT FOUND in DB (needs seeding)")
    except Exception as e:
        print(f"  ERROR querying User model: {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()
    finally:
        db.close()
except Exception as e:
    print(f"  IMPORT ERROR: {type(e).__name__}: {e}")
    import traceback; traceback.print_exc()

print()
print("=== VALIDATION COMPLETE ===")
