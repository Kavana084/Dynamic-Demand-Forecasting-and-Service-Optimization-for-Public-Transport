"""
Diagnose login failure: compare SQLAlchemy User model columns against actual DB schema.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from sqlalchemy import create_engine, inspect, text
from app.database.connection import engine

print("=" * 60)
print("DATABASE URL:", os.getenv("POSTGRES_DATABASE_URL", "NOT SET")[:60] + "...")
print("=" * 60)

insp = inspect(engine)

# --- 1. List all tables in the DB -----------------------------------------
print("\n[1] Tables in database:")
tables = insp.get_table_names()
for t in tables:
    print(f"  - {t}")

# --- 2. Get actual columns of 'users' table --------------------------------
print("\n[2] Actual columns in 'users' table (from DB):")
if "users" not in tables:
    print("  ERROR: 'users' table does NOT exist in the database!")
else:
    db_cols = {c["name"]: c for c in insp.get_columns("users")}
    for name, col in db_cols.items():
        nullable = col.get("nullable", "?")
        default  = col.get("default")
        print(f"  {name:30s} type={col['type']}  nullable={nullable}  default={default}")

# --- 3. Model columns from SQLAlchemy ------------------------------------
print("\n[3] Columns declared in SQLAlchemy User model:")
from app.database.models import User
model_cols = {c.name: c for c in User.__table__.columns}
for name, col in model_cols.items():
    print(f"  {name:30s} type={col.type}  nullable={col.nullable}  default={col.default}")

# --- 4. Diff: model vs DB ------------------------------------------------
print("\n[4] Schema diff (model vs database):")
if "users" in tables:
    db_col_names   = set(db_cols.keys())
    model_col_names = set(model_cols.keys())
    missing_in_db   = model_col_names - db_col_names
    extra_in_db     = db_col_names - model_col_names
    if missing_in_db:
        print(f"  MISSING in DB (exist in model): {missing_in_db}")
    else:
        print("  No columns missing from DB.")
    if extra_in_db:
        print(f"  EXTRA in DB (not in model):     {extra_in_db}")
    else:
        print("  No extra columns in DB.")

# --- 5. Quick login test --------------------------------------------------
print("\n[5] Testing login (admin / admin123):")
try:
    from sqlalchemy.orm import Session
    with Session(engine) as db:
        admin = db.query(User).filter(User.username == "admin").first()
        if admin is None:
            print("  ERROR: admin user NOT found in database!")
        else:
            print(f"  admin found: id={admin.id}, role={admin.role}, is_active={admin.is_active}")
            from app.services.auth_service import verify_password
            ok = verify_password("admin123", admin.password_hash)
            print(f"  Password verify result: {ok}")
except Exception as exc:
    import traceback
    print("  EXCEPTION during login test:")
    traceback.print_exc()

print("\nDone.")
