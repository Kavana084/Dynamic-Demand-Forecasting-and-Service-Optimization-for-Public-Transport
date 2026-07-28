import sqlite3, csv
conn = sqlite3.connect("transit_ai.db")
cur = conn.cursor()
cur.execute("SELECT * FROM gtfs_stops")
rows = cur.fetchall()
cols = [d[0] for d in cur.description]
with open("gtfs_stops_export.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(cols)
    w.writerows(rows)
print("rows:", len(rows))
print("columns:", cols)
