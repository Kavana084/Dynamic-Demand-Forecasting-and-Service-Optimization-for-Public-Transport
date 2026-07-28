"""
Data Migration: Supabase PostgreSQL -> SQLite3
Exports GTFS and core tables from Supabase and imports into transit_ai.db.

Tables migrated (in FK-safe order):
  routes, gtfs_stops, gtfs_trips, gtfs_stop_times,
  route_features, transit_observations, users, demand_history,
  fleet_allocations, peak_events, weather_records,
  prediction_records, forecast_history, optimization_results,
  drl_recommendations, system_metrics, model_metadata,
  pipeline_runs, pipeline_execution_logs, route_scopes,
  route_plan_logs, audit_logs, journey_history
"""

import sys
import os
sys.path.insert(0, os.path.abspath('backend'))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

# ── Source: Supabase PostgreSQL ──────────────────────────────────────────────
PG_URL = (
    "postgresql+psycopg2://postgres.yugumogtpjbciwuphosu:"
    "Kavanajeevu08@aws-1-ap-south-1.pooler.supabase.com:6543/"
    "postgres?sslmode=require"
)

# ── Destination: local SQLite ────────────────────────────────────────────────
SQLITE_PATH = os.path.abspath("transit_ai.db")
SQLITE_URL  = f"sqlite:///{SQLITE_PATH}"

print(f"Source  : PostgreSQL (Supabase)")
print(f"Dest    : {SQLITE_PATH}")
print()

# Build both engines
pg_engine  = create_engine(PG_URL, pool_pre_ping=True)
sq_engine  = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})

# Import all models so Base.metadata is fully populated
from app.database.connection import Base
from app.database import models  # noqa: registers all ORM models

# Create all tables in SQLite (fresh)
print("Creating SQLite schema …")
Base.metadata.create_all(bind=sq_engine)
print("Schema created.\n")

# ── FK-safe migration order ───────────────────────────────────────────────────
TABLES = [
    "routes",
    "gtfs_stops",
    "gtfs_trips",
    "gtfs_stop_times",
    "route_features",
    "transit_observations",
    "users",
    "demand_history",
    "fleet_allocations",
    "peak_events",
    "weather_records",
    "prediction_records",
    "forecast_history",
    "optimization_results",
    "drl_recommendations",
    "system_metrics",
    "model_metadata",
    "pipeline_runs",
    "pipeline_execution_logs",
    "route_scopes",
    "route_plan_logs",
    "audit_logs",
    "journey_history",
]

pg_insp = inspect(pg_engine)
pg_tables = pg_insp.get_table_names()

BATCH = 2000  # rows per batch to avoid memory issues

# Pre-fetch all destination columns to avoid locking during transaction
sq_insp = inspect(sq_engine)
dest_cols_cache = {}
for table in TABLES:
    try:
        dest_cols_cache[table] = {col['name'] for col in sq_insp.get_columns(table)}
    except Exception:
        dest_cols_cache[table] = set()

with sq_engine.begin() as sq_conn:
    # Disable FK enforcement temporarily for bulk load
    sq_conn.execute(text("PRAGMA foreign_keys=OFF"))

    for table in TABLES:
        if table not in pg_tables:
            print(f"  SKIP  {table} (not in source DB)")
            continue

        # Count source rows
        with pg_engine.connect() as pg_conn:
            total = pg_conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()

        if total == 0:
            print(f"  EMPTY {table} (0 rows) — skipping")
            continue

        # Get destination columns (SQLite schema is authoritative)
        dest_cols = dest_cols_cache.get(table, set())

        # Truncate destination first (idempotent re-runs)
        sq_conn.execute(text(f"DELETE FROM {table}"))

        # Stream in batches, only inserting columns that exist in dest
        imported = 0
        with pg_engine.connect() as pg_conn:
            result = pg_conn.execute(text(f"SELECT * FROM {table}"))
            all_cols = list(result.keys())
            # Only keep columns present in destination
            use_cols = [c for c in all_cols if c in dest_cols]
            skipped_cols = [c for c in all_cols if c not in dest_cols]
            if skipped_cols:
                print(f"  NOTE  {table}: skipping extra source cols: {skipped_cols}")

            col_placeholders = ", ".join([f":{c}" for c in use_cols])
            col_names = ", ".join(use_cols)
            insert_sql = text(
                f"INSERT OR IGNORE INTO {table} ({col_names}) VALUES ({col_placeholders})"
            )

            batch = []
            for row in result:
                full_row = dict(zip(all_cols, row))
                # Only include dest-compatible columns
                filtered = {c: full_row[c] for c in use_cols}
                batch.append(filtered)
                if len(batch) >= BATCH:
                    sq_conn.execute(insert_sql, batch)
                    imported += len(batch)
                    batch = []
            if batch:
                sq_conn.execute(insert_sql, batch)
                imported += len(batch)

        print(f"  OK    {table}: {imported}/{total} rows imported")

    # Re-enable FK enforcement
    sq_conn.execute(text("PRAGMA foreign_keys=ON"))

print("\nMigration complete.")

# ── Validation ────────────────────────────────────────────────────────────────
print("\n--- Row count validation ---")
with sq_engine.connect() as sq_conn:
    for table in TABLES:
        try:
            n = sq_conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"  {table}: {n} rows")
        except Exception as e:
            print(f"  {table}: ERROR - {e}")
