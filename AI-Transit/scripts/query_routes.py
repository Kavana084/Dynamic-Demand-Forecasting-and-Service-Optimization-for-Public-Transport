import sqlite3
conn = sqlite3.connect('transit_data.db')
cur = conn.cursor()
cur.execute('SELECT DISTINCT route_id, COUNT(*) as cnt FROM transit_observations GROUP BY route_id ORDER BY cnt DESC LIMIT 30')
rows = cur.fetchall()
for r in rows:
    print(r)
conn.close()
