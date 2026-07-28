import sqlite3
conn = sqlite3.connect("transit_ai.db")
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type=\"table\"")
tables = [r[0] for r in cur.fetchall()]

for t in tables:
    cur.execute(f"PRAGMA table_info({t})")
    cols = cur.fetchall()
    stop_cols = [c[1] for c in cols if "stop" in c[1].lower()]
    if stop_cols:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        count = cur.fetchone()[0]
        print(f"{t} (rows={count}): {stop_cols}")
