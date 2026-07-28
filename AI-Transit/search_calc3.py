import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

search_dir = "frontend/src"  # src only — exclude dist/
patterns = {
    "occupancy_percent": re.compile(r'occupancy_percent', re.IGNORECASE),
    "predicted_demand": re.compile(r'predicted_demand', re.IGNORECASE),
    "required_buses": re.compile(r'required_buses', re.IGNORECASE),
    "fleet_utilization": re.compile(r'fleet_utilization', re.IGNORECASE),
    "crowd_level": re.compile(r'crowd_level', re.IGNORECASE),
    "comfort_level": re.compile(r'comfort_level', re.IGNORECASE),
    "recommended_fleet": re.compile(r'recommended_fleet', re.IGNORECASE),
    "current_fleet": re.compile(r'current_fleet', re.IGNORECASE),
    "optimized_frequency": re.compile(r'optimized_frequency', re.IGNORECASE),
    "demandToOccupancy": re.compile(r'demandToOccupancy', re.IGNORECASE),
    "getServiceInfo": re.compile(r'getServiceInfo', re.IGNORECASE),
    "demand / 60": re.compile(r'demand\s*/\s*60', re.IGNORECASE),
    "/ 60": re.compile(r'/\s*60\b'),
}

matches = []
for root, dirs, files in os.walk(search_dir):
    dirs[:] = [d for d in dirs if d not in ('node_modules', 'dist', '.git')]
    for file in files:
        if file.endswith(('.js', '.jsx', '.ts', '.tsx')):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                try:
                    for line_num, line in enumerate(f, 1):
                        for pname, pat in patterns.items():
                            if pat.search(line):
                                matches.append(f"[{pname}] {path}:{line_num}: {line.strip()}")
                except Exception:
                    pass

for match in matches:
    print(match)
