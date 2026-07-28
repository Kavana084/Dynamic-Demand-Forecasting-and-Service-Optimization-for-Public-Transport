import sys
sys.path.insert(0, '.')

from app.database.connection import engine
from sqlalchemy import text

conn = engine.connect()

print("=== DATABASE TABLE COUNTS ===")
result = conn.execute(text('SELECT COUNT(*) FROM demand_history'))
print(f"DemandHistory: {result.scalar()}")

result = conn.execute(text('SELECT COUNT(*) FROM forecast_history'))
print(f"ForecastHistory: {result.scalar()}")

result = conn.execute(text('SELECT COUNT(*) FROM optimization_results'))
print(f"OptimizationResult: {result.scalar()}")

result = conn.execute(text('SELECT COUNT(*) FROM users'))
print(f"User: {result.scalar()}")

print("\n=== SAMPLE DEMAND HISTORY ===")
result = conn.execute(text('SELECT * FROM demand_history LIMIT 3'))
for row in result:
    print(row)

print("\n=== SAMPLE FORECAST HISTORY ===")
result = conn.execute(text('SELECT * FROM forecast_history LIMIT 3'))
for row in result:
    print(row)

print("\n=== SAMPLE OPTIMIZATION RESULTS ===")
result = conn.execute(text('SELECT * FROM optimization_results LIMIT 3'))
for row in result:
    print(row)

print("\n=== USERS ===")
result = conn.execute(text('SELECT username, role, is_active FROM users'))
for row in result:
    print(f"{row[0]} - {row[1]} - active={row[2]}")

conn.close()
