import sqlite3
conn = sqlite3.connect("transit_ai.db")
cur = conn.cursor()

targets = [
    ("12th Block Nagarabhavi", 12.96018, 77.51398),
    ("8th Mile Dasarahalli", 13.04622, 77.50755),
]

cur.execute("SELECT stop_id, stop_name, stop_lat, stop_lon FROM gtfs_stops WHERE stop_name LIKE \"%Nagarabhavi%\" OR stop_name LIKE \"%Dasarahalli%\"")
rows = cur.fetchall()
for r in rows:
    print(r)
