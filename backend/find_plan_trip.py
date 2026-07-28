import os
import json

backend_dir = 'f:/transit-ai-system/backend'

for root, dirs, files in os.walk(backend_dir):
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'def plan_trip' in content:
                    print(f"Found plan_trip in {path}")
                    # print lines around plan_trip
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'def plan_trip' in line:
                            start = max(0, i-5)
                            end = min(len(lines), i+30)
                            print('\n'.join(lines[start:end]))
