import os
import re

search_dir = "frontend"
# Search for frontend-side calculation or re-derivation of audit fields
patterns = {
    "occupancy_percent (read)": re.compile(r'occupancy_percent', re.IGNORECASE),
    "predicted_demand (read)": re.compile(r'predicted_demand', re.IGNORECASE),
    "required_buses (read)": re.compile(r'required_buses', re.IGNORECASE),
    "fleet_utilization (read)": re.compile(r'fleet_utilization', re.IGNORECASE),
    "crowd_level (read)": re.compile(r'crowd_level', re.IGNORECASE),
    "comfort_level (read)": re.compile(r'comfort_level', re.IGNORECASE),
    "recommended_fleet (read)": re.compile(r'recommended_fleet', re.IGNORECASE),
    "current_fleet (read)": re.compile(r'current_fleet', re.IGNORECASE),
    "optimized_frequency (read)": re.compile(r'optimized_frequency', re.IGNORECASE),
    "demandToOccupancy": re.compile(r'demandToOccupancy', re.IGNORECASE),
    "getServiceInfo": re.compile(r'getServiceInfo', re.IGNORECASE),
    "Math.round.*demand": re.compile(r'Math\.round.*demand', re.IGNORECASE),
    "/ 60": re.compile(r'/\s*60', re.IGNORECASE),
}

matches = []
for root, dirs, files in os.walk(search_dir):
    for file in files:
        if file.endswith(('.js', '.jsx', '.ts', '.tsx')):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                try:
                    for line_num, line in enumerate(f, 1):
                        for pname, pat in patterns.items():
                            if pat.search(line):
                                matches.append(f"[{pname}] {path}:{line_num}: {line.strip()}")
                except UnicodeDecodeError:
                    pass

for match in matches:
    print(match)
