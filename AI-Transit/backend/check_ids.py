import sqlite3
conn = sqlite3.connect("transit_ai.db")
cur = conn.cursor()
for sid in ["21629", "20593"]:
    cur.execute("SELECT * FROM gtfs_stops WHERE stop_id = ?", (sid,))
    row = cur.fetchone()
    print(sid, "->", row if row else "NOT FOUND (was merged away)")
