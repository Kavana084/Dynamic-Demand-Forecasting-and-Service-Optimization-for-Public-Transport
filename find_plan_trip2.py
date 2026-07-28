import re

with open('backend/app/api_routes.py', 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')

# Find all lines with plan_trip
for i, line in enumerate(lines, 1):
    if 'plan_trip' in line.lower():
        print(f"Line {i}: {line}")
