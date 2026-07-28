import os
import re
import sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

search_dir = "frontend/src"  # src only — exclude dist/
patterns = {
    "69": re.compile(r'\b69\b'),
    "83": re.compile(r'\b83\b'),
    "18": re.compile(r'\b18\b'),
    "100%": re.compile(r"100%"),
    "30%": re.compile(r"30%"),
    "1 Buses": re.compile(r'1 Buses', re.IGNORECASE),
    "2 Buses": re.compile(r'2 Buses', re.IGNORECASE),
    "Low Crowd": re.compile(r'Low Crowd', re.IGNORECASE),
    "High Crowd": re.compile(r'High Crowd', re.IGNORECASE),
    "Moderate Crowd": re.compile(r'Moderate Crowd', re.IGNORECASE),
}

matches = []
for root, dirs, files in os.walk(search_dir):
    # Skip node_modules and dist
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
                except Exception as e:
                    pass

if matches:
    for match in matches:
        print(match)
else:
    print("CLEAN: No hardcoded fallback values found in frontend/src.")
