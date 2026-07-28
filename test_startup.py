import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from app.main import startup_event
from app.database.connection import engine
from sqlalchemy import inspect

print("Running startup event...")
startup_event()

print("\n--- Verification ---")
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"Number of tables created: {len(tables)}")
print("Tables:", tables)

if len(tables) > 10:
    print("SUCCESS: Database tables created.")
else:
    print("FAILURE: Tables were not created properly.")
