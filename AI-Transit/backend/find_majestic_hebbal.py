import sqlite3
conn = sqlite3.connect("transit_ai.db")
cur = conn.cursor()
cur.execute("SELECT stop_id, stop_name FROM gtfs_stops WHERE stop_name LIKE \"%Majestic%\" OR stop_name LIKE \"%Hebbal%\"")
for r in cur.fetchall():
    print(r)
