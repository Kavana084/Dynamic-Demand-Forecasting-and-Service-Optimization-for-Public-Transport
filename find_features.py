with open("backend/app/api_routes.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "historical_route_average" in line:
        print(f"Line {i+1}: {line.strip()}")
