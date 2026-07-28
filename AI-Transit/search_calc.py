import os
import re

search_dir = "frontend"
regex = re.compile(r"occupancy|demand|required_buses|fleet", re.IGNORECASE)

matches = []
for root, dirs, files in os.walk(search_dir):
    for file in files:
        if file.endswith(('.js', '.jsx', '.ts', '.tsx')):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                try:
                    for line_num, line in enumerate(f, 1):
                        if regex.search(line):
                            matches.append(f"{path}:{line_num}: {line.strip()}")
                except UnicodeDecodeError:
                    pass

for match in matches:
    print(match)
