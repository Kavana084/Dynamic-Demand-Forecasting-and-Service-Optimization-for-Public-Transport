import psycopg2

conn = psycopg2.connect("postgresql://postgres.yugumogtpjbciwuphosu:Kavanajeevu08@aws-1-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require")
c = conn.cursor()

print('--- DATE VALIDATION ---')
try:
    c.execute('SELECT MIN(timestamp), MAX(timestamp) FROM demand_history;')
    print('DemandHistory min/max timestamp:', c.fetchone())
except Exception as e:
    print('Error DemandHistory:', e)
    conn.rollback()

try:
    c.execute('SELECT MIN(target_timestamp), MAX(target_timestamp) FROM forecast_history;')
    print('ForecastHistory min/max target_timestamp:', c.fetchone())
except Exception as e:
    print('Error ForecastHistory:', e)
    conn.rollback()

try:
    c.execute('SELECT MIN(generated_at), MAX(generated_at) FROM forecast_history;')
    print('ForecastHistory min/max generated_at:', c.fetchone())
except Exception as e:
    print('Error ForecastHistory generated_at:', e)
    conn.rollback()
