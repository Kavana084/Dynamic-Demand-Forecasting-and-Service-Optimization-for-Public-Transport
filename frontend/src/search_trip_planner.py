import re

file_path = 'f:/transit-ai-system/frontend/src/pages/TripPlanner.jsx'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

import_lines = []
demand_lines = []

for i, line in enumerate(content.split('\n')):
    if 'import' in line and 'lucide-react' in line:
        import_lines.append(f"{i}: {line}")
    if 'demandToOccupancy' in line:
        demand_lines.append(f"{i}: {line}")

print("Import lines:")
for line in import_lines:
    print(line)

print("\ndemandToOccupancy lines:")
for line in demand_lines:
    print(line)
