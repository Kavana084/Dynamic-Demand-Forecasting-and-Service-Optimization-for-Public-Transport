import os
import re

search_dir = r"f:\transit-ai-system\frontend"
patterns = [
    r"crowd_level", r"crowdLevel", 
    r"occupancy_percentage", r"occupancy", 
    r"predicted_demand", r"forecast_demand", r"predictedDemand", r"forecastDemand",
    r"allocated_buses", r"required_buses", r"available_buses", r"bus_capacity",
    r"allocatedBuses", r"requiredBuses", r"availableBuses", r"busCapacity",
    r"fleet_optimized", r"fleetOptimized"
]
regex = re.compile("|".join(patterns), re.IGNORECASE)

matches_found = []

for root, _, files in os.walk(search_dir):
    if "node_modules" in root or ".next" in root or "dist" in root or "build" in root:
        continue
    for file in files:
        if file.endswith((".ts", ".tsx", ".js", ".jsx", ".html")):
            file_path = os.path.join(root, file)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        if regex.search(line):
                            matches_found.append(f"{file_path}:{line_num}: {line.strip()}")
            except Exception as e:
                pass

with open(r"f:\transit-ai-system\frontend_search_results.txt", "w", encoding="utf-8") as f:
    for m in matches_found:
        f.write(m + "\n")
