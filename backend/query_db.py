import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("POSTGRES_DATABASE_URL")

conn = psycopg2.connect(url)
cur = conn.cursor()

print("--- TASK 1: Actual Database Schema ---")
cur.execute("""
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'prediction_records' 
ORDER BY ordinal_position;
""")
for row in cur.fetchall():
    print(row)

print("--- TASK 8: Optimization Results Audit ---")
cur.execute("SELECT COUNT(*) FROM optimization_results;")
print("Count:", cur.fetchone()[0])

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'optimization_results';")
cols = [r[0] for r in cur.fetchall()]
time_col = "created_at" if "created_at" in cols else "timestamp"
if time_col in cols:
    cur.execute(f"SELECT MIN({time_col}), MAX({time_col}) FROM optimization_results;")
    print(f"Min/Max {time_col}:", cur.fetchone())

# Also verify prediction_records
cur.execute("SELECT COUNT(*) FROM prediction_records;")
print("prediction_records count:", cur.fetchone()[0])

cur.close()
conn.close()
