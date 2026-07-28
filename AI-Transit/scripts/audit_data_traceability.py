import os
import json

search_terms = ['predicted_demand', 'occupancy', 'crowd', 'travel_time', 'distance', 'weather', 'traffic', 'recommendation', 'demandLevel', '60', '85']

frontend_dir = "f:/transit-ai-system/frontend/src"

results = {}

for root, _, files in os.walk(frontend_dir):
    for file in files:
        if file.endswith('.jsx') or file.endswith('.js'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for i, line in enumerate(lines):
                    for term in search_terms:
                        if term in line:
                            if file not in results:
                                results[file] = []
                            results[file].append({"line_num": i+1, "content": line.strip()})

# Deduplicate lines for each file
for file in results:
    unique_lines = []
    seen = set()
    for item in results[file]:
        if item["line_num"] not in seen:
            seen.add(item["line_num"])
            unique_lines.append(item)
    results[file] = unique_lines

with open("f:/transit-ai-system/scripts/audit_results.json", "w", encoding='utf-8') as f:
    json.dump(results, f, indent=2)
