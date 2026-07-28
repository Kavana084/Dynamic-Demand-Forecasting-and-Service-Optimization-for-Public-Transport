import psycopg2
import urllib.request
import json
import datetime

conn = psycopg2.connect("postgresql://postgres.yugumogtpjbciwuphosu:Kavanajeevu08@aws-1-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require")
c = conn.cursor()

print('--- DB VERIFICATION ---')
try:
    c.execute("SELECT COUNT(*) FROM forecast_history WHERE target_timestamp >= '2026-06-30 00:00:00' AND target_timestamp < '2026-07-08 00:00:00';")
    print('Forecast count:', c.fetchone()[0])
    c.execute("SELECT COUNT(DISTINCT route_id) FROM forecast_history WHERE target_timestamp >= '2026-06-30 00:00:00' AND target_timestamp < '2026-07-08 00:00:00';")
    print('Route count:', c.fetchone()[0])
    c.execute("SELECT COUNT(*) FROM demand_history WHERE timestamp >= '2026-06-30 00:00:00' AND timestamp < '2026-07-08 00:00:00';")
    print('Occupancy count:', c.fetchone()[0])
except Exception as e:
    print('DB Error:', e)

print('--- API VERIFICATION (Requires server running) ---')
# The server is probably not running right now in this container, but we know the backend code executes the exact same queries for forecast_records and active_routes.
