import os
import re

search_dir = 'backend'
pattern = re.compile(r'/chat', re.IGNORECASE)

matches = []
for root, dirs, files in os.walk(search_dir):
    dirs[:] = [d for d in dirs if d not in ('venv', '__pycache__', '.git')]
    for fn in files:
        if fn.endswith(('.py',)):
            p = os.path.join(root, fn)
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                for ln, line in enumerate(f, 1):
                    if pattern.search(line):
                        matches.append(f'{p}:{ln}: {line.strip()[:150]}')

for m in matches:
    print(m)
