"""
_audit_db.py — Shared database connector for audit scripts.

Uses the backend's SQLAlchemy session to connect to Supabase PostgreSQL.
Falls back to local SQLite transit_data.db if that fails.
"""

import os
import sys

# Ensure backend is importable
_base = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.join(_base, "backend")
if _backend not in sys.path:
    sys.path.insert(0, _backend)

def get_sqlalchemy_session():
    """Return a SQLAlchemy Session connected to Supabase (or raise)."""
    from app.database.connection import SessionLocal
    return SessionLocal()

def get_models():
    """Return the ORM model classes."""
    from app.database import models
    return models

def get_sqlite_conn():
    """Fallback: raw sqlite3 connection to local transit_data.db."""
    import sqlite3
    for path in [
        os.path.join(_base, "transit_data.db"),
        os.path.join(_base, "backend", "transit.db"),
    ]:
        if os.path.exists(path):
            return sqlite3.connect(path), path
    return None, None
