import psycopg2

conn = psycopg2.connect("postgresql://postgres.yugumogtpjbciwuphosu:Kavanajeevu08@aws-1-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require")
c = conn.cursor()

print('--- TODAY QUERIES ---')
try:
    c.execute("SELECT COUNT(*) FROM forecast_history WHERE target_timestamp >= '2026-07-07 00:00:00' AND target_timestamp < '2026-07-08 00:00:00';")
    print('Forecasts today:', c.fetchone())

    c.execute("SELECT COUNT(DISTINCT route_id) FROM forecast_history WHERE target_timestamp >= '2026-07-07 00:00:00' AND target_timestamp < '2026-07-08 00:00:00';")
    print('Distinct routes today:', c.fetchone())
except Exception as e:
    print('Error:', e)
