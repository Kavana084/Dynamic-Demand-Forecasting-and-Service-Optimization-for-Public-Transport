import re

file_path = 'f:/transit-ai-system/frontend/src/pages/TripPlanner.jsx'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

search_terms = ['travelTime', 'generateAlternatives', 'WHY_CARDS', 'AltRouteCard', 'busData', 'liveBus']

for i, line in enumerate(lines):
    for term in search_terms:
        if term in line:
            print(f"Line {i+1} contains {term}: {line.strip()}")
