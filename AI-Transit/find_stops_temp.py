import sqlite3
import pandas as pd

conn = sqlite3.connect('backend/transit.db')
queries = [
    '12th Block Nagarabhavi', 'Nayandahalli', '1st Stage 3rd Block Nagarabhavi', 
    'Banashankari', 'Majestic', 'Kempegowda', 'Nagarabhavi', 'Kengeri'
]

for q in queries:
    print(f'--- {q} ---')
    df = pd.read_sql_query(f"SELECT stop_id, stop_name FROM stops WHERE stop_name LIKE '%{q}%' LIMIT 5", conn)
    print(df)
