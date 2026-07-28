import re

with open('backend/app/api_routes.py', 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')

# Find all audit-relevant fields in the response
keywords = ['occupancy_percent', 'crowd_level', 'comfort_level', 'predicted_demand', 
            'forecast_demand', 'required_buses', 'recommended_fleet', 'current_fleet',
            'fleet_utilization', 'optimized_frequency', 'recommendation_reason',
            'plan_trip', 'demandToOccupancy', 'required_buses']

for kw in keywords:
    found = False
    for i, line in enumerate(lines, 1):
        if kw in line:
            print(f"[{kw}] Line {i}: {line.strip()}")
            found = True
    if not found:
        print(f"[{kw}] NOT FOUND in api_routes.py")
