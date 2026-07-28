import sqlite3
conn = sqlite3.connect('backend/transit.db')
print([t[0] for t in conn.cursor().execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()])
