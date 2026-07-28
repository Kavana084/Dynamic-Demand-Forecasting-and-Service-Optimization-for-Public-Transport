import sqlite3

conn = sqlite3.connect('backend/transit.db')
c = conn.cursor()

print('--- OCCUPANCY VALIDATION ---')
try:
    c.execute('''
    SELECT route_id, AVG(occupancy_percent)
    FROM demand_history
    GROUP BY route_id;
    ''')
    occupancy = c.fetchall()
    if len(occupancy) == 0:
        print('Occupancy Result: No occupancy data available')
    else:
        print('Occupancy Result:', occupancy)
except Exception as e:
    print('Error occupancy:', e)

print('\n--- ROUTE COUNT VALIDATION ---')
try:
    c.execute('SELECT DISTINCT route_id FROM forecast_history;')
    dist_routes = c.fetchall()
    print('Distinct Routes:', dist_routes)

    c.execute('SELECT COUNT(DISTINCT route_id) FROM forecast_history;')
    count_dist = c.fetchall()
    print('Count Distinct:', count_dist)
except Exception as e:
    print('Error distinct routes:', e)

try:
    c.execute('''
    SELECT route_id, route_short_name, predicted_passengers
    FROM latest_forecast_query
    ''')
    latest = c.fetchall()
    print('Latest Forecast:', latest)
except Exception as e:
    print('Error latest_forecast_query:', e)

print('\n--- FORECAST RECORD VALIDATION ---')
try:
    c.execute('SELECT COUNT(*) FROM forecast_history;')
    total_forecasts = c.fetchall()
    print('Total Forecasts:', total_forecasts)

    c.execute('SELECT COUNT(*) FROM forecast_history WHERE generated_at >= CURRENT_DATE;')
    recent_forecasts = c.fetchall()
    print('Recent Forecasts (>= CURRENT_DATE):', recent_forecasts)
except Exception as e:
    print('Error forecast history count:', e)
