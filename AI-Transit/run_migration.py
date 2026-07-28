"""
One-shot migration runner: adds the missing mfa_secret column to the users table.
Safe to re-run: uses IF NOT EXISTS so it's idempotent.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("POSTGRES_DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: POSTGRES_DATABASE_URL not set in environment!")
    sys.exit(1)

print(f"Connecting to: {DATABASE_URL[:60]}...")

engine = create_engine(DATABASE_URL)

MIGRATIONS = [
    (
        "users.mfa_secret",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_secret TEXT;",
    ),
]

with engine.begin() as conn:
    for label, sql in MIGRATIONS:
        try:
            conn.execute(text(sql))
            print(f"[OK]     {label}")
        except Exception as exc:
            msg = str(exc).lower()
            if "duplicate" in msg or "exists" in msg or "already" in msg:
                print(f"[SKIP]   {label} (already exists)")
            else:
                print(f"[ERROR]  {label}: {exc}")
                sys.exit(1)

    # Verify column now exists
    result = conn.execute(text(
        "SELECT column_name, data_type, is_nullable "
        "FROM information_schema.columns "
        "WHERE table_name='users' ORDER BY ordinal_position;"
    ))
    rows = result.fetchall()
    print("\nCurrent users table schema:")
    for row in rows:
        print(f"  {row[0]:30s} {row[1]:20s} nullable={row[2]}")

    # Count users
    cnt = conn.execute(text("SELECT COUNT(*) FROM users;")).scalar()
    print(f"\nTotal users in DB: {cnt}")

    # Check if admin exists
    admin = conn.execute(text(
        "SELECT id, username, role, is_active FROM users WHERE username='admin' LIMIT 1;"
    )).fetchone()
    if admin:
        print(f"Admin user found: id={admin[0]}, username={admin[1]}, role={admin[2]}, is_active={admin[3]}")
    else:
        print("WARNING: admin user not found — will be seeded on next server restart.")

print("\nMigration complete. Restart the server to apply all startup migrations.")
