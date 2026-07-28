import sqlite3

conn = sqlite3.connect(r'f:\transit-ai-system\transit_data.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
for t in tables:
    cur.execute(f"SELECT COUNT(*) FROM [{t}]")
    count = cur.fetchone()[0]
    cur.execute(f"PRAGMA table_info([{t}])")
    cols = [r[1] for r in cur.fetchall()]
    print(f"{t} ({count} rows): {cols}")
conn.close()
